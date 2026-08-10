"""exp-104: robustez frente al ruido de aula.

Todas las mediciones anteriores usan audio limpio. Un aula real tiene proyector, sillas,
toses y murmullo de fondo. Sin este barrido, cualquier afirmacion sobre el sistema
"funcionando en clase" es una extrapolacion.

Dos tipos de ruido, porque degradan de forma muy distinta:
  - BLANCO   : estacionario. Es lo que mejor maneja la supresion de ruido del navegador.
  - MURMULLO : varias voces de fondo, sintetizado mezclando otros clips del propio corpus.
    Es no estacionario y comparte espectro con la voz util, asi que ni la supresion de
    ruido ni el modelo lo separan bien. Es lo que de verdad hay en un aula.

La relacion senal-ruido (SNR) se controla en decibelios. Como referencia aproximada:
20 dB es una sala tranquila, 10 dB un aula con actividad, 0 dB voz y ruido al mismo nivel.

Ademas del WER se mide la tasa de ALUCINACION, porque con ruido alto Whisper tiende a
inventar texto sobre el silencio o el murmullo -- el modo de fallo mas peligroso para
accesibilidad.

Uso:
  .venv/bin/python research/experiments/exp-104-ruido/run.py --limite 40
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "research"))

from eval.metrics.wer import evaluar  # noqa: E402
from eval.normalizers.basico import basico  # noqa: E402
from src.trazabilidad import procedencia  # noqa: E402

AQUI = Path(__file__).resolve().parent
DECODIFICACION = dict(
    temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
    logprob_threshold=-1.0,
    compression_ratio_threshold=1.35,
    no_speech_threshold=0.6,
    return_timestamps=True,
)
#: None = audio limpio, sin ruido anadido.
SNRS_DB = [None, 20.0, 15.0, 10.0, 5.0, 0.0]


def mezclar(senal: np.ndarray, ruido: np.ndarray, snr_db: float) -> np.ndarray:
    """Suma ruido a la senal escalandolo para obtener la SNR pedida."""
    if len(ruido) < len(senal):
        ruido = np.tile(ruido, int(np.ceil(len(senal) / len(ruido))))
    ruido = ruido[:len(senal)]

    pot_senal = float(np.mean(senal ** 2))
    pot_ruido = float(np.mean(ruido ** 2))
    if pot_ruido <= 0 or pot_senal <= 0:
        return senal

    factor = np.sqrt(pot_senal / (pot_ruido * (10 ** (snr_db / 10))))
    mezcla = senal + factor * ruido
    # Normalizar solo si hay recorte: cambiar el nivel siempre introduciria una
    # variable adicional que no es la que se quiere medir.
    pico = float(np.max(np.abs(mezcla)))
    return mezcla / pico * 0.99 if pico > 1.0 else mezcla


def construir_murmullo(filas, rng, n_voces=6) -> np.ndarray:
    """Murmullo sintetico: varias voces del corpus superpuestas y desfasadas.

    Mezclar voces reales del mismo idioma reproduce el enmascaramiento que sufre un
    sistema ASR en un aula: el ruido comparte espectro con la senal util.
    """
    elegidos = rng.choice(len(filas), size=min(n_voces, len(filas)), replace=False)
    pistas = []
    for i in elegidos:
        audio, _ = sf.read(RAIZ / filas[int(i)]["audio"], dtype="float32")
        desfase = rng.integers(0, max(1, len(audio) // 2))
        pistas.append(np.roll(audio, int(desfase)))

    largo = max(len(p) for p in pistas)
    suma = np.zeros(largo, dtype=np.float32)
    for p in pistas:
        suma[:len(p)] += p
    return suma / max(1e-9, float(np.max(np.abs(suma))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifiesto", type=Path,
                    default=RAIZ / "research/corpus/manifests/voxpopuli_es.jsonl")
    ap.add_argument("--modelo", default="openai/whisper-medium")
    ap.add_argument("--limite", type=int, default=40)
    ap.add_argument("--semilla", type=int, default=42)
    args = ap.parse_args()

    rng = np.random.default_rng(args.semilla)
    torch.manual_seed(args.semilla)
    disp, dtype = ("cuda", torch.float16) if torch.cuda.is_available() else ("cpu", torch.float32)

    from transformers import AutoProcessor, WhisperForConditionalGeneration

    filas = [json.loads(l) for l in args.manifiesto.read_text(encoding="utf-8").splitlines()
             if l.strip()][:args.limite]
    procesador = AutoProcessor.from_pretrained(args.modelo)
    modelo = WhisperForConditionalGeneration.from_pretrained(
        args.modelo, dtype=dtype).to(disp).eval()

    murmullo = construir_murmullo(filas, rng)

    def transcribir(muestras, sr):
        feats = procesador(muestras, sampling_rate=sr, return_tensors="pt")\
            .input_features.to(disp, dtype=dtype)
        with torch.no_grad():
            ids = modelo.generate(feats, language="es", task="transcribe", **DECODIFICACION)
        return procesador.batch_decode(ids, skip_special_tokens=True)[0].strip()

    a0, sr0 = sf.read(RAIZ / filas[0]["audio"], dtype="float32")
    transcribir(a0[:sr0], sr0)  # calentamiento

    print(f"modelo: {args.modelo}   clips: {len(filas)}\n")
    print(f"{'ruido':<12}{'SNR':>7}{'WER':>9}{'CER':>9}{'anomalos':>10}")
    print("-" * 48)

    resultados = []
    for tipo in ("blanco", "murmullo"):
        for snr in SNRS_DB:
            if snr is None and tipo != "blanco":
                continue   # el audio limpio se mide una sola vez
            refs, hips, anomalos = [], [], 0
            for fila in filas:
                audio, sr = sf.read(RAIZ / fila["audio"], dtype="float32")
                if snr is not None:
                    ruido = (rng.normal(0, 1, len(audio)).astype(np.float32)
                             if tipo == "blanco" else murmullo)
                    audio = mezclar(audio, ruido, snr)
                texto = transcribir(audio, sr)
                refs.append(basico(fila["referencia"]))
                hips.append(basico(texto))
                # Salida anomala: menos de un cuarto de las palabras esperadas.
                if len(texto.split()) < 0.25 * len(fila["referencia"].split()):
                    anomalos += 1

            r = evaluar(refs, hips)
            etiqueta = "limpio" if snr is None else tipo
            snr_txt = "—" if snr is None else f"{snr:.0f} dB"
            print(f"{etiqueta:<12}{snr_txt:>7}{r.wer:>8.2%}{r.cer:>8.2%}{anomalos:>9}/{len(filas)}")
            resultados.append({"ruido": etiqueta, "snr_db": snr, "wer": r.wer,
                               "cer": r.cer, "anomalos": anomalos, "n": len(filas)})

    limpio = next(r for r in resultados if r["ruido"] == "limpio")["wer"]
    print(f"\ndegradacion frente a audio limpio ({limpio:.2%}):")
    for r in resultados:
        if r["snr_db"] is not None:
            print(f"  {r['ruido']:<10}{r['snr_db']:>5.0f} dB  {(r['wer'] - limpio) * 100:+7.2f} pp")

    salida = AQUI / "results"
    salida.mkdir(exist_ok=True)
    (salida / f"metricas_{args.modelo.replace('/', '_')}__{args.manifiesto.stem}.json")\
        .write_text(json.dumps({
            "experimento": "exp-104-ruido",
            "fecha_utc": datetime.now(timezone.utc).isoformat(),
            "procedencia": procedencia(RAIZ, args.manifiesto),
            "config": vars(args) | {"manifiesto": str(args.manifiesto)},
            "resultados": resultados,
        }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nresultados -> {salida.relative_to(RAIZ)}/")


if __name__ == "__main__":
    main()
