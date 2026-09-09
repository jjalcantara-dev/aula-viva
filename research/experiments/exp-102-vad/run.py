"""exp-102: segmentar por silencios frente a trocear por tiempo fijo.

Contrasta la recomendacion que dejo planteada exp-100. Aquella medicion mostro que cortar
cada N segundos degrada mucho (a 3 s, el WER casi se duplica) y sugirio que la causa son
los cortes arbitrarios en mitad de palabra. Aqui se comprueba.

Comparacion JUSTA: cada condicion de ventana fija se enfrenta a una segmentacion por
silencios con tope de duracion equivalente, de forma que ambas produzcan segmentos de
duracion media parecida. Comparar segmentos de 2 s contra segmentos de 8 s no diria nada
sobre la estrategia de corte, solo sobre la duracion.

La latencia de la segmentacion por silencios NO es constante: depende de cuando calle el
hablante. Por eso se reporta la duracion media y el p95 de los segmentos, no un solo
numero.

Uso:
  .venv/bin/python research/experiments/exp-102-vad/run.py --limite 40
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval.metrics.wer import evaluar  # noqa: E402
from eval.normalizers.basico import basico  # noqa: E402
from eval.stats.pareado import (conteo_signos, ic_bootstrap,  # noqa: E402
                                prueba_signos, veredicto)
from segmentador import segmentar  # noqa: E402
from src.trazabilidad import procedencia  # noqa: E402

AQUI = Path(__file__).resolve().parent

#: Par que sostiene el resultado principal del TFM: ambas estrategias con la MISMA
#: latencia media (2.68 s frente a 2.93 s), que es la unica comparacion honesta. Comparar
#: por filas, con el mismo tope, mide sobre todo la duracion del segmento.
PAR_LATENCIA_EQUIVALENTE = (("ventana fija", 3.0), ("silencios", 8.0))
DECODIFICACION = dict(
    temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
    logprob_threshold=-1.0,
    compression_ratio_threshold=1.35,
    no_speech_threshold=0.6,
    return_timestamps=True,
)
TOPES = [2.0, 3.0, 5.0, 8.0]


def trocear_fijo(audio: np.ndarray, sr: int, ventana_s: float) -> list[np.ndarray]:
    n = int(ventana_s * sr)
    return [t for i in range(0, len(audio), n) if len(t := audio[i:i + n]) > sr * 0.2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifiesto", type=Path,
                    default=RAIZ / "research/corpus/manifests/voxpopuli_es.jsonl")
    ap.add_argument("--modelo", default="openai/whisper-medium")
    ap.add_argument("--limite", type=int, default=40)
    ap.add_argument("--semilla", type=int, default=42)
    args = ap.parse_args()

    torch.manual_seed(args.semilla)
    disp, dtype = ("cuda", torch.float16) if torch.cuda.is_available() else ("cpu", torch.float32)

    from transformers import AutoProcessor, WhisperForConditionalGeneration

    filas = [json.loads(l) for l in args.manifiesto.read_text(encoding="utf-8").splitlines()
             if l.strip()][:args.limite]
    procesador = AutoProcessor.from_pretrained(args.modelo)
    modelo = WhisperForConditionalGeneration.from_pretrained(
        args.modelo, dtype=dtype).to(disp).eval()

    def transcribir(muestras, sr):
        feats = procesador(muestras, sampling_rate=sr, return_tensors="pt")\
            .input_features.to(disp, dtype=dtype)
        with torch.no_grad():
            ids = modelo.generate(feats, language="es", task="transcribe", **DECODIFICACION)
        return procesador.batch_decode(ids, skip_special_tokens=True)[0].strip()

    a0, sr0 = sf.read(RAIZ / filas[0]["audio"], dtype="float32")
    transcribir(a0[:sr0], sr0)  # calentamiento

    print(f"modelo: {args.modelo}   clips: {len(filas)}\n")
    print(f"{'estrategia':<22}{'tope':>6}{'WER':>9}{'dur.media':>11}{'dur.p95':>9}{'segs':>7}")
    print("-" * 64)

    resultados = []
    # Las hipotesis POR CLIP de cada condicion, para poder contrastar el par de latencia
    # equivalente sin volver a transcribir. Sin esto no hay intervalo de confianza, y el
    # resultado principal del trabajo quedaba siendo el unico sin doble criterio.
    hipotesis_por_condicion: dict[tuple[str, float], list[str]] = {}
    referencias = [basico(f["referencia"]) for f in filas]

    for tope in TOPES:
        for estrategia in ("ventana fija", "silencios"):
            refs, hips, duraciones = [], [], []
            for fila in filas:
                audio, sr = sf.read(RAIZ / fila["audio"], dtype="float32")
                partes = (trocear_fijo(audio, sr, tope) if estrategia == "ventana fija"
                          else segmentar(audio, sr, s_maximo=tope))
                duraciones.extend(len(p) / sr for p in partes)
                hips.append(basico(" ".join(transcribir(p, sr) for p in partes)))
                refs.append(basico(fila["referencia"]))

            hipotesis_por_condicion[(estrategia, tope)] = hips
            r = evaluar(refs, hips)
            media = float(np.mean(duraciones))
            p95 = float(np.percentile(duraciones, 95))
            print(f"{estrategia:<22}{tope:>5.0f}s{r.wer:>8.2%}{media:>10.2f}s{p95:>8.2f}s"
                  f"{len(duraciones):>7}")
            resultados.append({"estrategia": estrategia, "tope_s": tope, "wer": r.wer,
                               "cer": r.cer, "duracion_media_s": media,
                               "duracion_p95_s": p95, "n_segmentos": len(duraciones)})

    print("\ndiferencia (silencios - ventana fija), negativo = los silencios ganan:")
    for tope in TOPES:
        f = next(r for r in resultados if r["tope_s"] == tope and r["estrategia"] == "ventana fija")
        s = next(r for r in resultados if r["tope_s"] == tope and r["estrategia"] == "silencios")
        print(f"  tope {tope:.0f}s: {(s['wer'] - f['wer']) * 100:+6.2f} pp de WER"
              f"   (duracion media {f['duracion_media_s']:.1f}s -> {s['duracion_media_s']:.1f}s)")

    # --- Contraste del par de latencia equivalente -------------------------------------
    # Es el par del que sale la cifra que la memoria compara con las tecnicas de
    # adaptacion. Aquellas se miden con IC bootstrap y test de signos; esta no lo hacia, de
    # modo que el resultado central del trabajo era el unico sin doble criterio.
    (est_a, tope_a), (est_b, tope_b) = PAR_LATENCIA_EQUIVALENTE
    hip_a = hipotesis_por_condicion[(est_a, tope_a)]
    hip_b = hipotesis_por_condicion[(est_b, tope_b)]

    ic = ic_bootstrap(referencias, hip_a, hip_b, semilla=args.semilla)
    mejoran, empeoran, empates = conteo_signos(referencias, hip_a, hip_b)
    p = prueba_signos(mejoran, empeoran)
    fila_a = next(r for r in resultados
                  if r["estrategia"] == est_a and r["tope_s"] == tope_a)
    fila_b = next(r for r in resultados
                  if r["estrategia"] == est_b and r["tope_s"] == tope_b)
    delta = (fila_b["wer"] - fila_a["wer"]) * 100

    pareado = {
        "condicion_a": {"estrategia": est_a, "tope_s": tope_a,
                        "wer": fila_a["wer"], "duracion_media_s": fila_a["duracion_media_s"]},
        "condicion_b": {"estrategia": est_b, "tope_s": tope_b,
                        "wer": fila_b["wer"], "duracion_media_s": fila_b["duracion_media_s"]},
        "delta_wer_pp": round(delta, 2),
        "ic95_pp": [round(ic[0] * 100, 2), round(ic[1] * 100, 2)],
        "mejoran": mejoran, "empeoran": empeoran, "sin_cambio": empates,
        "p_test_signos": p,
        "n_palabras_ref": sum(len(r.split()) for r in referencias),
        "veredicto": veredicto((ic[0] * 100, ic[1] * 100), p),
    }

    print(f"\ncontraste a latencia media equivalente "
          f"({fila_a['duracion_media_s']:.2f}s frente a {fila_b['duracion_media_s']:.2f}s):")
    print(f"  {est_b} (tope {tope_b:.0f}s) frente a {est_a} (tope {tope_a:.0f}s)")
    print(f"  diferencia de WER : {delta:+.2f} pp  "
          f"(IC95 [{ic[0] * 100:+.2f}, {ic[1] * 100:+.2f}])")
    print(f"  clips             : {mejoran} mejoran, {empeoran} empeoran, "
          f"{empates} empatan (p={p:.2g})")
    print(f"  palabras de ref.  : {pareado['n_palabras_ref']}")
    print(f"  veredicto         : {pareado['veredicto']}")

    salida = AQUI / "results"
    salida.mkdir(exist_ok=True)
    (salida / f"metricas_{args.modelo.replace('/', '_')}__{args.manifiesto.stem}.json")\
        .write_text(json.dumps({
            "experimento": "exp-102-vad",
            "fecha_utc": datetime.now(timezone.utc).isoformat(),
            "procedencia": procedencia(RAIZ, args.manifiesto, len(filas)),
            "config": vars(args) | {"manifiesto": str(args.manifiesto)},
            "resultados": resultados,
            "pareado": pareado,
        }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nresultados -> {salida.relative_to(RAIZ)}/")


if __name__ == "__main__":
    main()
