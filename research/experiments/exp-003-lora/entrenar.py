"""exp-003, fase 1: ajuste fino de Whisper con LoRA.

Tercera tecnica de la comparativa, y la unica que modifica el modelo. Las otras dos
(prompting, post-correccion) actuan sin tocar los pesos.

SIN FUGA POR CONSTRUCCION: se entrena con la particion `train` de VoxPopuli y se evalua
con `test`. La separacion la garantiza el propio dataset, no una division nuestra.

POR QUE VOXPOPULI Y NO CIEMPIESS, que tiene mas clips: sus referencias omiten tildes de
forma sistematica (R11). Ajustar el modelo sobre ellas le ensenaria a NO acentuar, y al
medirlo contra esas mismas referencias sucias el WER *mejoraria*. Estariamos optimizando
hacia el error y la metrica nos daria la razon. Es la trampa mas peligrosa de todo el
trabajo, porque el resultado seria excelente sobre el papel.

LoRA en lugar de ajuste completo: entrena una fraccion minima de los pesos, cabe de sobra
en 16 GB y produce un adaptador de pocos MB en lugar de un modelo entero.

Uso:
  .venv/bin/python research/experiments/exp-003-lora/entrenar.py --epocas 2
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from torch.utils.data import DataLoader, Dataset

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "research"))

from src.trazabilidad import procedencia  # noqa: E402

AQUI = Path(__file__).resolve().parent


class CorpusAudio(Dataset):
    """Manifiesto -> (rasgos mel, etiquetas). El mel se calcula al vuelo."""

    def __init__(self, manifiesto: Path, procesador, idioma="es"):
        self.filas = [json.loads(l) for l in
                      manifiesto.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.procesador = procesador
        self.tokenizador = procesador.tokenizer
        self.tokenizador.set_prefix_tokens(language=idioma, task="transcribe")

    def __len__(self):
        return len(self.filas)

    def __getitem__(self, i):
        fila = self.filas[i]
        audio, sr = sf.read(RAIZ / fila["audio"], dtype="float32")
        rasgos = self.procesador.feature_extractor(
            audio, sampling_rate=sr, return_tensors="pt").input_features[0]
        etiquetas = self.tokenizador(fila["referencia"]).input_ids
        return {"input_features": rasgos, "labels": etiquetas}


@dataclass
class Agrupador:
    """Agrupa ejemplos rellenando las etiquetas.

    El relleno se marca con -100 para que la funcion de perdida lo ignore: si no, el
    modelo aprenderia a predecir relleno, que es exactamente lo contrario de lo que
    interesa.
    """
    procesador: object
    inicio_decodificador: int

    def __call__(self, lote):
        rasgos = torch.stack([e["input_features"] for e in lote])
        etiquetas = self.procesador.tokenizer.pad(
            [{"input_ids": e["labels"]} for e in lote], return_tensors="pt")
        ids = etiquetas.input_ids.masked_fill(etiquetas.attention_mask.eq(0), -100)

        # Se descarta <|startoftranscript|> porque el modelo lo antepone el mismo al
        # desplazar las etiquetas. Si se deja, el decodificador lo recibe DUPLICADO y
        # todo queda desalineado una posicion: la perdida se dispara y el entrenamiento
        # diverge, sin que nada mas lo delate.
        #
        # Ojo: el token a quitar es `decoder_start_token_id` (50258), NO `bos_token_id`,
        # que en Whisper es <|endoftext|> (50257). Comparar con el segundo hace que la
        # comprobacion nunca se cumpla.
        if (ids[:, 0] == self.inicio_decodificador).all().item():
            ids = ids[:, 1:]
        return {"input_features": rasgos, "labels": ids}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifiesto", type=Path,
                    default=RAIZ / "research/corpus/manifests/voxpopuli_es_train.jsonl")
    ap.add_argument("--modelo", default="openai/whisper-medium")
    ap.add_argument("--epocas", type=int, default=2)
    ap.add_argument("--lote", type=int, default=4)
    ap.add_argument("--tasa", type=float, default=1e-4)
    ap.add_argument("--rango", type=int, default=16, help="rango de LoRA")
    ap.add_argument("--semilla", type=int, default=42)
    args = ap.parse_args()

    torch.manual_seed(args.semilla)
    disp = "cuda" if torch.cuda.is_available() else "cpu"

    from peft import LoraConfig, get_peft_model
    from transformers import AutoProcessor, WhisperForConditionalGeneration

    procesador = AutoProcessor.from_pretrained(args.modelo)
    modelo = WhisperForConditionalGeneration.from_pretrained(args.modelo).to(disp)
    modelo.config.forced_decoder_ids = None
    modelo.config.suppress_tokens = []

    # Solo las proyecciones de atencion: es donde LoRA aporta mas por parametro.
    config = LoraConfig(r=args.rango, lora_alpha=args.rango * 2, lora_dropout=0.05,
                        target_modules=["q_proj", "v_proj"], bias="none")
    modelo = get_peft_model(modelo, config)
    entrenables = sum(p.numel() for p in modelo.parameters() if p.requires_grad)
    totales = sum(p.numel() for p in modelo.parameters())
    print(f"modelo      : {args.modelo}")
    print(f"entrenables : {entrenables/1e6:.2f}M de {totales/1e6:.0f}M "
          f"({entrenables/totales:.3%})")

    datos = CorpusAudio(args.manifiesto, procesador)
    cargador = DataLoader(
        datos, batch_size=args.lote, shuffle=True, num_workers=2,
        collate_fn=Agrupador(procesador, modelo.config.decoder_start_token_id))
    print(f"clips       : {len(datos)}   lotes/epoca: {len(cargador)}\n")

    optimizador = torch.optim.AdamW(
        [p for p in modelo.parameters() if p.requires_grad], lr=args.tasa)
    # Calentamiento de la tasa: los primeros pasos con LoRA recien inicializado son los
    # mas propensos a desestabilizar el modelo.
    planificador = torch.optim.lr_scheduler.OneCycleLR(
        optimizador, max_lr=args.tasa, pct_start=0.1,
        total_steps=args.epocas * len(cargador))
    modelo.train()
    historial = []
    t0 = time.perf_counter()
    for epoca in range(args.epocas):
        perdidas = []
        for paso, lote in enumerate(cargador, 1):
            lote = {k: v.to(disp) for k, v in lote.items()}
            optimizador.zero_grad()
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=disp == "cuda"):
                perdida = modelo(**lote).loss
            perdida.backward()
            optimizador.step()
            planificador.step()
            perdidas.append(perdida.item())
            if paso % 25 == 0:
                print(f"  epoca {epoca+1}/{args.epocas}  paso {paso}/{len(cargador)}  "
                      f"perdida {np.mean(perdidas[-25:]):.4f}")
        media = float(np.mean(perdidas))
        historial.append(media)
        print(f"  --> epoca {epoca+1}: perdida media {media:.4f}\n")

    minutos = (time.perf_counter() - t0) / 60
    salida = AQUI / "adaptador"
    modelo.save_pretrained(salida)
    tam = sum(f.stat().st_size for f in salida.rglob("*") if f.is_file()) / 1e6
    print(f"entrenamiento: {minutos:.1f} min")
    print(f"adaptador    : {salida.relative_to(RAIZ)}  ({tam:.1f} MB)")

    (AQUI / "entrenamiento.json").write_text(json.dumps({
        "experimento": "exp-003-lora/entrenamiento",
        "procedencia": procedencia(RAIZ, args.manifiesto),
        "config": vars(args) | {"manifiesto": str(args.manifiesto)},
        "parametros_entrenables": entrenables,
        "perdida_por_epoca": historial,
        "minutos": round(minutos, 1),
        "adaptador_mb": round(tam, 1),
    }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
