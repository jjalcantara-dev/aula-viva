"""Verifica que procesar por lotes NO altera las transcripciones.

Por que hace falta: el lote es una optimizacion de rendimiento, y una optimizacion que
cambia los resultados deja de ser una optimizacion para convertirse en un factor de
confusion. Ya se aprendio esa leccion con la decodificacion (R14): comparar tecnicas bajo
configuraciones distintas mide la configuracion, no las tecnicas.

Si este script encuentra diferencias, el lote NO puede usarse en la comparativa, por
rapido que sea.

Uso:  .venv/bin/python tools/verificar_lote.py --lotes 1 4 8
"""

import argparse
import difflib
import json
import sys
import time
from pathlib import Path

import soundfile as sf
import torch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "research"))

from eval.normalizers.basico import basico  # noqa: E402

DECODIFICACION = dict(
    temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
    logprob_threshold=-1.0,
    compression_ratio_threshold=1.35,
    no_speech_threshold=0.6,
    return_timestamps=True,
)


def potencia_gpu() -> float:
    """Vatios que consume la GPU ahora mismo, via sysfs. -1 si no esta disponible.

    La potencia, no la temperatura, es lo que indica cuanto trabajo esta haciendo de
    verdad la GPU: una tarjeta bien refrigerada puede estar al 100% de ocupacion y
    quedarse fria. La temperatura mide refrigeracion, no utilizacion.
    """
    for h in Path("/sys/class/hwmon").glob("hwmon*"):
        try:
            if (h / "name").read_text().strip() != "amdgpu":
                continue
            for f in ("power1_average", "power1_input"):
                if (h / f).exists():
                    return int((h / f).read_text()) / 1_000_000
        except Exception:
            continue
    return -1.0


def transcribir(filas, procesador, modelo, dispositivo, dtype, lote, potencias=None):
    salida = []
    t0 = time.perf_counter()
    for inicio in range(0, len(filas), lote):
        grupo = filas[inicio:inicio + lote]
        audios = [sf.read(RAIZ / f["audio"], dtype="float32")[0] for f in grupo]
        sr = sf.read(RAIZ / grupo[0]["audio"], dtype="float32")[1]
        feats = procesador(audios, sampling_rate=sr, return_tensors="pt")\
            .input_features.to(dispositivo, dtype=dtype)
        with torch.no_grad():
            ids = modelo.generate(feats, language="es", task="transcribe", **DECODIFICACION)
        if potencias is not None:
            p = potencia_gpu()
            if p > 0:
                potencias.append(p)
        salida.extend(t.strip() for t in procesador.batch_decode(ids, skip_special_tokens=True))
    if dispositivo == "cuda":
        torch.cuda.synchronize()
    return salida, time.perf_counter() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifiesto", type=Path,
                    default=RAIZ / "research/corpus/manifests/voxpopuli_es.jsonl")
    ap.add_argument("--modelo", default="openai/whisper-medium")
    ap.add_argument("--clips", type=int, default=16)
    ap.add_argument("--lotes", type=int, nargs="*", default=[1, 4, 8])
    args = ap.parse_args()

    from transformers import AutoProcessor, WhisperForConditionalGeneration

    filas = [json.loads(l) for l in args.manifiesto.read_text(encoding="utf-8").splitlines()
             if l.strip()][:args.clips]
    audio_s = sum(f["duracion_s"] for f in filas)
    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if dispositivo == "cuda" else torch.float32

    procesador = AutoProcessor.from_pretrained(args.modelo)
    modelo = WhisperForConditionalGeneration.from_pretrained(
        args.modelo, dtype=dtype).to(dispositivo).eval()

    a0, sr0 = sf.read(RAIZ / filas[0]["audio"], dtype="float32")
    with torch.no_grad():  # calentamiento
        modelo.generate(procesador(a0[:sr0], sampling_rate=sr0, return_tensors="pt")
                        .input_features.to(dispositivo, dtype=dtype),
                        language="es", task="transcribe")

    print(f"{args.modelo} · {len(filas)} clips · {audio_s:.0f} s de audio\n")
    print(f"{'lote':>6}{'tiempo':>10}{'x t.real':>11}{'acel.':>8}"
          f"{'W GPU medios':>14}{'identicas':>12}")
    print("-" * 62)

    referencia = None
    for lote in args.lotes:
        potencias: list[float] = []
        textos, segundos = transcribir(filas, procesador, modelo, dispositivo, dtype,
                                       lote, potencias)
        vatios = sum(potencias) / len(potencias) if potencias else -1
        if referencia is None:
            referencia, base = textos, segundos
            iguales = "—"
        else:
            # Comparar normalizado: diferencias de puntuacion o mayusculas no afectan a
            # la metrica y no deben marcarse como discrepancia.
            iguales = sum(1 for a, b in zip(referencia, textos) if basico(a) == basico(b))
            iguales = f"{iguales}/{len(textos)}"
        print(f"{lote:>6}{segundos:>9.1f}s{audio_s / segundos:>10.1f}x"
              f"{base / segundos:>7.2f}x{vatios:>13.0f}W{iguales:>12}")

        if referencia is not textos:
            for a, b in zip(referencia, textos):
                if basico(a) != basico(b):
                    print("\n  DISCREPANCIA:")
                    for linea in difflib.unified_diff([basico(a)], [basico(b)],
                                                      "lote=1", f"lote={lote}", lineterm="", n=0):
                        print("   ", linea)
                    break

    print("\nSi alguna fila muestra discrepancias, el lote NO puede usarse en la comparativa.")


if __name__ == "__main__":
    main()
