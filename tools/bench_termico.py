"""Compara configuraciones de inferencia por temperatura de CPU y tiempo.

Motivacion: durante los experimentos la CPU llegaba a ~85 C mientras la GPU no pasaba de
50 C. La causa es que parte del trabajo lo hace la CPU aunque haya GPU disponible:

  1. El espectrograma mel se calcula en CPU salvo que se le pase `device`.
  2. torch reserva 8 hilos para operaciones de CPU aunque el computo vaya a GPU.
  3. La decodificacion autorregresiva lanza miles de kernels diminutos, y despacharlos
     es trabajo de CPU en Python.

Este banco mide si mover el mel a GPU y limitar los hilos reduce la temperatura, y cuanto
cuesta en tiempo.

Uso:  .venv/bin/python tools/bench_termico.py --clips 30
"""

import argparse
import json
import time
from pathlib import Path

import soundfile as sf
import torch

RAIZ = Path(__file__).resolve().parents[1]


def temperatura_cpu() -> float:
    """Tctl del sensor k10temp, en grados. -1 si no se encuentra."""
    for h in Path("/sys/class/hwmon").glob("hwmon*"):
        try:
            if (h / "name").read_text().strip() not in ("k10temp", "zenpower"):
                continue
            for etiqueta in h.glob("temp*_label"):
                if etiqueta.read_text().strip() == "Tctl":
                    return int((etiqueta.parent /
                                etiqueta.name.replace("_label", "_input")).read_text()) / 1000
        except Exception:
            continue
    return -1.0


def medir(nombre, filas, modelo, procesador, dispositivo, dtype, mel_en_gpu, hilos):
    torch.set_num_threads(hilos)
    temps, t0 = [], time.perf_counter()

    for fila in filas:
        audio, sr = sf.read(RAIZ / fila["audio"], dtype="float32")
        extra = {"device": dispositivo} if mel_en_gpu else {}
        entradas = procesador(audio, sampling_rate=sr, return_tensors="pt", **extra)
        feats = entradas.input_features.to(dispositivo, dtype=dtype)
        with torch.no_grad():
            modelo.generate(feats, language="es", task="transcribe",
                            temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
                            logprob_threshold=-1.0, compression_ratio_threshold=1.35,
                            no_speech_threshold=0.6, return_timestamps=True)
        temps.append(temperatura_cpu())

    torch.cuda.synchronize()
    segundos = time.perf_counter() - t0
    validas = [t for t in temps if t > 0]
    return {
        "config": nombre, "segundos": round(segundos, 1),
        "hilos": hilos, "mel_en_gpu": mel_en_gpu,
        "temp_media": round(sum(validas) / len(validas), 1) if validas else None,
        "temp_max": round(max(validas), 1) if validas else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifiesto", type=Path,
                    default=RAIZ / "research/corpus/manifests/voxpopuli_es.jsonl")
    ap.add_argument("--modelo", default="openai/whisper-medium")
    ap.add_argument("--clips", type=int, default=30)
    ap.add_argument("--enfriado", type=int, default=45, help="segundos entre pruebas")
    args = ap.parse_args()

    from transformers import AutoProcessor, WhisperForConditionalGeneration

    filas = [json.loads(l) for l in args.manifiesto.read_text(encoding="utf-8").splitlines()
             if l.strip()][:args.clips]
    disp, dtype = "cuda", torch.float16
    procesador = AutoProcessor.from_pretrained(args.modelo)
    modelo = WhisperForConditionalGeneration.from_pretrained(
        args.modelo, dtype=dtype).to(disp).eval()

    # Calentamiento, para no contaminar la primera configuracion medida.
    a0, sr0 = sf.read(RAIZ / filas[0]["audio"], dtype="float32")
    with torch.no_grad():
        modelo.generate(procesador(a0, sampling_rate=sr0, return_tensors="pt")
                        .input_features.to(disp, dtype=dtype), language="es", task="transcribe")
    torch.cuda.synchronize()

    configuraciones = [
        ("actual (8 hilos, mel en CPU)", False, 8),
        ("mel en GPU, 8 hilos", True, 8),
        ("mel en GPU, 2 hilos", True, 2),
    ]

    print(f"modelo {args.modelo} · {len(filas)} clips · reposo {temperatura_cpu():.1f} C\n")
    print(f"{'configuracion':<32}{'tiempo':>9}{'T media':>10}{'T max':>8}")
    print("-" * 59)

    resultados = []
    for nombre, mel_gpu, hilos in configuraciones:
        # Enfriar entre pruebas: sin esto, cada configuracion hereda el calor de la
        # anterior y la comparacion no vale nada.
        espera = time.time() + args.enfriado
        while time.time() < espera:
            time.sleep(1)
        r = medir(nombre, filas, modelo, procesador, disp, dtype, mel_gpu, hilos)
        resultados.append(r)
        print(f"{nombre:<32}{r['segundos']:>8.1f}s{r['temp_media']:>9.1f}C{r['temp_max']:>7.1f}C")

    base = resultados[0]
    print("\nfrente a la configuracion actual:")
    for r in resultados[1:]:
        dt = (r["segundos"] - base["segundos"]) / base["segundos"] * 100
        print(f"  {r['config']:<30} T max {r['temp_max'] - base['temp_max']:+.1f} C"
              f"   tiempo {dt:+.1f} %")

    destino = RAIZ / "research/results/bench_termico.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n-> {destino.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
