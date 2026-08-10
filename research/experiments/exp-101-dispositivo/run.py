"""exp-101: cuanto aporta realmente la GPU.

Justifica con medidas propias el requisito de hardware del sistema, en lugar de darlo por
supuesto. Es material directo para el capitulo de requisitos de la memoria.

Contexto que motiva el experimento: durante los barridos la CPU alcanzaba ~85 C mientras
la GPU no pasaba de 50 C, lo que hacia dudar de si el modelo se estaba ejecutando de
verdad en la GPU. Se estaba: lo que ocupa la CPU es el DESPACHO de kernels desde el bucle
de Python, un token cada vez, no el calculo. La GPU marca 99% de uso porque siempre hay
algun kernel activo, pero consume solo ~45% de su potencia porque cada kernel es diminuto.

Este experimento zanja la duda de la unica forma valida: apagando la GPU y comparando.

Uso:
  .venv/bin/python research/experiments/exp-101-dispositivo/run.py --clips 5
"""

import argparse
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import soundfile as sf
import torch

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "research"))

from src.trazabilidad import procedencia  # noqa: E402

AQUI = Path(__file__).resolve().parent
DECODIFICACION = dict(
    temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
    logprob_threshold=-1.0,
    compression_ratio_threshold=1.35,
    no_speech_threshold=0.6,
    return_timestamps=True,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifiesto", type=Path,
                    default=RAIZ / "research/corpus/manifests/voxpopuli_es.jsonl")
    ap.add_argument("--modelos", nargs="*",
                    default=["openai/whisper-small", "openai/whisper-medium"])
    ap.add_argument("--clips", type=int, default=5)
    args = ap.parse_args()

    from transformers import AutoProcessor, WhisperForConditionalGeneration

    filas = [json.loads(l) for l in args.manifiesto.read_text(encoding="utf-8").splitlines()
             if l.strip()][:args.clips]
    audio_s = sum(f["duracion_s"] for f in filas)

    print(f"audio: {audio_s:.1f} s en {len(filas)} clips\n")
    print(f"{'modelo':<16}{'dispositivo':>12}{'tiempo':>10}{'x tiempo real':>16}")
    print("-" * 54)

    resultados = []
    for nombre in args.modelos:
        procesador = AutoProcessor.from_pretrained(nombre)
        por_dispositivo = {}
        # En CPU se usa float32: la precision reducida no esta acelerada ahi, y forzarla
        # mediria una limitacion de formato en lugar de la diferencia de dispositivo.
        for dispositivo, dtype in (("cuda", torch.float16), ("cpu", torch.float32)):
            if dispositivo == "cuda" and not torch.cuda.is_available():
                continue
            modelo = WhisperForConditionalGeneration.from_pretrained(
                nombre, dtype=dtype).to(dispositivo).eval()

            a0, sr0 = sf.read(RAIZ / filas[0]["audio"], dtype="float32")
            with torch.no_grad():  # calentamiento
                modelo.generate(
                    procesador(a0[:sr0], sampling_rate=sr0, return_tensors="pt")
                    .input_features.to(dispositivo, dtype=dtype),
                    language="es", task="transcribe")

            t0 = time.perf_counter()
            for fila in filas:
                audio, sr = sf.read(RAIZ / fila["audio"], dtype="float32")
                feats = procesador(audio, sampling_rate=sr, return_tensors="pt")\
                    .input_features.to(dispositivo, dtype=dtype)
                with torch.no_grad():
                    modelo.generate(feats, language="es", task="transcribe", **DECODIFICACION)
            if dispositivo == "cuda":
                torch.cuda.synchronize()
            segundos = time.perf_counter() - t0

            por_dispositivo[dispositivo] = segundos
            print(f"{nombre.split('/')[-1]:<16}{dispositivo:>12}{segundos:>9.1f}s"
                  f"{audio_s / segundos:>15.1f}x")
            del modelo
            if dispositivo == "cuda":
                torch.cuda.empty_cache()

        aceleracion = (por_dispositivo.get("cpu", 0) / por_dispositivo["cuda"]
                       if "cuda" in por_dispositivo and por_dispositivo.get("cpu") else None)
        resultados.append({
            "modelo": nombre,
            "segundos": {k: round(v, 2) for k, v in por_dispositivo.items()},
            "factor_tiempo_real": {k: round(audio_s / v, 2) for k, v in por_dispositivo.items()},
            "aceleracion_gpu": round(aceleracion, 2) if aceleracion else None,
        })

    print("\naceleracion de la GPU frente a la CPU:")
    for r in resultados:
        if r["aceleracion_gpu"]:
            apto = r["factor_tiempo_real"].get("cpu", 0)
            print(f"  {r['modelo'].split('/')[-1]:<16} {r['aceleracion_gpu']:.1f}x"
                  f"   (en CPU: {apto:.1f}x tiempo real"
                  f"{' — margen insuficiente para subtitulado en vivo' if apto < 3 else ''})")

    salida = AQUI / "results"
    salida.mkdir(exist_ok=True)
    (salida / "metricas.json").write_text(json.dumps({
        "experimento": "exp-101-dispositivo",
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "procedencia": procedencia(RAIZ, args.manifiesto),
        "config": vars(args) | {"manifiesto": str(args.manifiesto)},
        "entorno": {
            "python": platform.python_version(), "torch": torch.__version__,
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "cpu": platform.processor(),
            "hilos_torch": torch.get_num_threads(),
        },
        "audio_s": round(audio_s, 1),
        "resultados": resultados,
    }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nresultados -> {(salida / 'metricas.json').relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
