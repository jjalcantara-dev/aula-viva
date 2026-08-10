"""exp-100: compromiso entre latencia y calidad al trocear el audio en vivo.

Numeracion: 000-099 son experimentos del nucleo investigador (tecnicas de adaptacion);
100+ son del nucleo aplicado (decisiones de ingenieria del sistema en vivo).

PREGUNTA: la aplicacion no puede esperar a que termine la frase; debe trocear el audio en
ventanas y transcribir cada una. Ventanas cortas bajan la latencia pero dan al modelo
menos contexto acustico. ¿Cuanto cuesta, en WER, cada segundo de latencia que se ahorra?

Sin este barrido, el tamano de ventana de la aplicacion seria un numero elegido a ojo. Con
el, es una decision de diseno justificada con datos -- que es lo que un tribunal espera.

La latencia se estima como:  ventana + tiempo de inferencia por ventana
Es una cota inferior: no incluye red ni renderizado, que se miden aparte en la aplicacion.

Uso:
  .venv/bin/python research/experiments/exp-100-ventana/run.py \
      --manifiesto research/corpus/manifests/voxpopuli_es.jsonl --limite 40
"""

import argparse
import json
import sys
import time
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
# 0 = sin trocear: transcribir el clip entero. Es la cota superior de calidad y la
# referencia contra la que se mide cuanto cuesta trocear.
VENTANAS = [1.0, 2.0, 3.0, 5.0, 8.0, 0.0]



#: Fraccion maxima de la ventana que puede ocupar el solapamiento.
#
# Sin este limite, un solape igual o mayor que la ventana deja el paso en una sola
# muestra y el troceado explota: con ventana=1 s y solape=1 s salian 256.000 trozos por
# clip de 16 s (16.000 veces mas de lo previsto). El barrido parecia estar funcionando,
# solo que muy lento; nada avisaba del error salvo que no terminaba nunca.
SOLAPE_MAXIMO = 0.5


def trocear(audio: np.ndarray, sr: int, ventana_s: float, solape_s: float):
    """Divide en ventanas con solapamiento. ventana_s=0 devuelve el audio entero.

    El solapamiento se recorta a `SOLAPE_MAXIMO` de la ventana. Es preferible ajustarlo
    en silencio y avisar a abortar: el barrido recorre ventanas de distinto tamano y un
    solape fijo no puede ser valido para todas.
    """
    if ventana_s <= 0:
        return [audio]

    solape_efectivo = min(solape_s, ventana_s * SOLAPE_MAXIMO)
    n_v, n_s = int(ventana_s * sr), int(solape_efectivo * sr)
    paso = n_v - n_s
    assert paso > 0, f"paso no positivo: ventana={ventana_s}s solape={solape_efectivo}s"

    return [trozo for i in range(0, len(audio), paso)
            if len(trozo := audio[i:i + n_v]) > sr * 0.2]


def solape_efectivo(ventana_s: float, solape_s: float) -> float:
    return min(solape_s, ventana_s * SOLAPE_MAXIMO) if ventana_s > 0 else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifiesto", type=Path, required=True)
    ap.add_argument("--modelo", default="openai/whisper-medium")
    ap.add_argument("--idioma", default="es")
    ap.add_argument("--dtype", default="float16")
    ap.add_argument("--solape", type=float, default=1.0)
    ap.add_argument("--limite", type=int, default=40)
    ap.add_argument("--semilla", type=int, default=42)
    args = ap.parse_args()

    torch.manual_seed(args.semilla)
    dtype = getattr(torch, args.dtype)
    disp = "cuda" if torch.cuda.is_available() else "cpu"

    from transformers import AutoProcessor, WhisperForConditionalGeneration

    filas = [json.loads(l) for l in args.manifiesto.read_text(encoding="utf-8").splitlines() if l.strip()]
    filas = filas[:args.limite]

    procesador = AutoProcessor.from_pretrained(args.modelo)
    modelo = WhisperForConditionalGeneration.from_pretrained(
        args.modelo, dtype=dtype).to(disp).eval()

    def transcribir(muestras: np.ndarray, sr: int) -> tuple[str, float]:
        feats = procesador(muestras, sampling_rate=sr, return_tensors="pt")\
            .input_features.to(disp, dtype=dtype)
        if disp == "cuda":
            torch.cuda.synchronize()
        t = time.perf_counter()
        with torch.no_grad():
            ids = modelo.generate(feats, language=args.idioma, task="transcribe", **DECODIFICACION)
        if disp == "cuda":
            torch.cuda.synchronize()
        dt = time.perf_counter() - t
        return procesador.batch_decode(ids, skip_special_tokens=True)[0].strip(), dt

    a0, sr0 = sf.read(RAIZ / filas[0]["audio"], dtype="float32")
    transcribir(a0[:sr0], sr0)  # calentamiento

    print(f"modelo: {args.modelo}   clips: {len(filas)}   solape: {args.solape}s\n")
    print(f"{'ventana':>9}{'WER':>9}{'infer/vent':>13}{'latencia est.':>15}{'trozos':>9}")
    print("-" * 56)

    resultados = []
    for ventana in VENTANAS:
        refs, hips, tiempos, n_trozos = [], [], [], 0
        for fila in filas:
            audio, sr = sf.read(RAIZ / fila["audio"], dtype="float32")
            partes = trocear(audio, sr, ventana, args.solape)
            textos = []
            for parte in partes:
                texto, dt = transcribir(parte, sr)
                textos.append(texto)
                tiempos.append(dt)
            n_trozos += len(partes)
            refs.append(basico(fila["referencia"]))
            hips.append(basico(" ".join(textos)))

        r = evaluar(refs, hips)
        medio = sum(tiempos) / len(tiempos)
        # Con ventana=0 no hay streaming: la latencia seria la duracion del clip entero.
        latencia = (ventana + medio) if ventana > 0 else float("nan")
        etiqueta = f"{ventana:.0f}s" if ventana > 0 else "sin trocear"
        print(f"{etiqueta:>9}{r.wer:>8.2%}{medio * 1000:>11.0f} ms"
              f"{(f'{latencia:.2f} s' if ventana > 0 else '—'):>15}{n_trozos:>9}")
        resultados.append({"ventana_s": ventana,
                           "solape_pedido_s": args.solape,
                           "solape_efectivo_s": solape_efectivo(ventana, args.solape),
                           "wer": r.wer, "cer": r.cer,
                           "ms_por_ventana": medio * 1000, "latencia_estimada_s": latencia,
                           "n_trozos": n_trozos})

    salida = AQUI / "results"
    salida.mkdir(exist_ok=True)
    # El solapamiento forma parte de la identidad del resultado: cambia el numero de
    # trozos y, sobre todo, cuanto texto se duplica. Dos barridos con solapes distintos
    # no son comparables y no deben compartir fichero.
    etiqueta = (f"{args.modelo.replace('/', '_')}__{args.manifiesto.stem}"
                f"__solape{args.solape:g}")
    (salida / f"metricas_{etiqueta}.json").write_text(json.dumps({
        "experimento": "exp-100-ventana",
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "procedencia": procedencia(RAIZ, args.manifiesto),
        "config": vars(args) | {"manifiesto": str(args.manifiesto)},
        "resultados": resultados,
    }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nresultados -> {(salida / f'metricas_{etiqueta}.json').relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
