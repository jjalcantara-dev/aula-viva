"""exp-000-baseline: Whisper SIN adaptar sobre el corpus.

Es la referencia contra la que se compara todo lo demas (hito H3 del PLANNING).
Mide calidad (WER/CER) y coste (factor de tiempo real), porque en un sistema de
subtitulado en vivo la latencia es un requisito, no un detalle.

Uso:
  .venv/bin/python research/experiments/exp-000-baseline/run.py \
      --manifiesto research/corpus/manifests/fleurs_es.jsonl \
      --modelo openai/whisper-small
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

from eval.metrics.wer import evaluar  # noqa: E402
from eval.normalizers.basico import NORMALIZADORES  # noqa: E402
from src.trazabilidad import procedencia  # noqa: E402

AQUI = Path(__file__).resolve().parent

# Reintento con temperatura, como en la implementacion de referencia de Whisper: si la
# salida degenera (logprob medio bajo o ratio de compresion alto), se reintenta con
# temperatura creciente.
#
# NO es un detalle de implementacion, es un FACTOR DE CONFUSION. Medido en M0 sobre
# voxpopuli_es: con decodificacion voraz, large-v3-turbo trunca 6 de 40 clips y llega a
# inventar frases plausibles del dominio ("Gracias, senora presidenta.") en lugar del
# contenido real; su WER sube de ~10% a 24.22%. Con reintento, cuatro de esos seis clips
# se recuperan (uno pasa de 100% a 4.5% de WER).
#
# Comparar tecnicas de adaptacion sin fijar esto mediria artefactos de decodificacion en
# lugar del efecto de la adaptacion. Debe quedar congelado y documentado (hito H2).
DECODIFICACION = {
    "voraz": {},
    "fallback": dict(
        temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
        logprob_threshold=-1.0,
        compression_ratio_threshold=1.35,
        no_speech_threshold=0.6,
        return_timestamps=True,
    ),
}



def cargar_manifiesto(ruta: Path) -> list[dict]:
    with ruta.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifiesto", type=Path, required=True)
    ap.add_argument("--modelo", default="openai/whisper-small")
    ap.add_argument("--idioma", default="es")
    ap.add_argument("--dispositivo", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--dtype", default="float16", choices=["float16", "bfloat16", "float32"])
    ap.add_argument("--decodificacion", default="fallback", choices=list(DECODIFICACION),
                    help="voraz = greedy simple; fallback = reintento con temperatura")
    ap.add_argument("--lote", type=int, default=1,
                    help="clips por lote. >1 acelera mucho, pero verificar antes que no "
                         "altera los resultados (tools/verificar_lote.py)")
    ap.add_argument("--semilla", type=int, default=42)
    ap.add_argument("--limite", type=int, default=None, help="solo los N primeros clips")
    args = ap.parse_args()

    torch.manual_seed(args.semilla)
    dtype = getattr(torch, args.dtype)

    from transformers import AutoProcessor, WhisperForConditionalGeneration

    filas = cargar_manifiesto(args.manifiesto)
    if args.limite:
        filas = filas[:args.limite]

    print(f"modelo      : {args.modelo}")
    print(f"dispositivo : {args.dispositivo} ({args.dtype})")
    print(f"clips       : {len(filas)}")

    t0 = time.perf_counter()
    procesador = AutoProcessor.from_pretrained(args.modelo)
    modelo = WhisperForConditionalGeneration.from_pretrained(
        args.modelo, dtype=dtype).to(args.dispositivo).eval()
    t_carga = time.perf_counter() - t0
    n_par = sum(p.numel() for p in modelo.parameters())
    print(f"carga       : {t_carga:.1f} s  ({n_par / 1e6:.0f}M parametros)\n")

    # Calentamiento: la primera inferencia paga compilacion de kernels (varios
    # segundos en ROCm). Incluirla falsearia el factor de tiempo real y penalizaria
    # mas a unos modelos que a otros, invalidando la comparativa de coste.
    audio_cal, sr_cal = sf.read(RAIZ / filas[0]["audio"], dtype="float32")
    ent_cal = procesador(audio_cal, sampling_rate=sr_cal, return_tensors="pt")
    with torch.no_grad():
        modelo.generate(ent_cal.input_features.to(args.dispositivo, dtype=dtype),
                        language=args.idioma, task="transcribe")
    if args.dispositivo == "cuda":
        torch.cuda.synchronize()
    print("calentamiento hecho\n")

    hipotesis, audio_total_s, infer_total_s = [], 0.0, 0.0

    # Procesamiento por lotes. Whisper rellena toda entrada a 30 s, asi que los ejemplos
    # de un lote tienen forma identica y agruparlos no requiere relleno adicional.
    #
    # Por que importa: el cuello de botella de estos barridos no es la GPU sino el
    # DESPACHO de kernels desde Python, un token cada vez (medido en M0: ~3 nucleos
    # saturados con la GPU al 45% de su potencia). Agrupar amortiza ese coste.
    #
    # ATENCION: el lote NO debe cambiar los resultados. Si lo hiciera, seria un factor de
    # confusion como la decodificacion (R14). Verificar con tools/verificar_lote.py antes
    # de usarlo en la comparativa.
    for inicio in range(0, len(filas), args.lote):
        grupo = filas[inicio:inicio + args.lote]
        audios = []
        for fila in grupo:
            audio, sr = sf.read(RAIZ / fila["audio"], dtype="float32")
            audios.append(audio)

        entradas = procesador(audios, sampling_rate=sr, return_tensors="pt")
        feats = entradas.input_features.to(args.dispositivo, dtype=dtype)

        if args.dispositivo == "cuda":
            torch.cuda.synchronize()
        t = time.perf_counter()
        with torch.no_grad():
            ids = modelo.generate(feats, language=args.idioma, task="transcribe",
                                  **DECODIFICACION[args.decodificacion])
        if args.dispositivo == "cuda":
            torch.cuda.synchronize()
        dt = time.perf_counter() - t

        textos = [t.strip() for t in procesador.batch_decode(ids, skip_special_tokens=True)]
        hipotesis.extend(textos)
        duracion_grupo = sum(f["duracion_s"] for f in grupo)
        audio_total_s += duracion_grupo
        infer_total_s += dt
        print(f"[{inicio + len(grupo):4d}/{len(filas)}] {dt:5.2f}s "
              f"(RTF {dt / duracion_grupo:.3f})  {textos[0][:64]}")

    referencias = [f["referencia"] for f in filas]

    print("\n" + "=" * 72)
    print(f"{'normalizador':<14} resultado")
    print("-" * 72)
    metricas = {}
    for nombre, fn in NORMALIZADORES.items():
        r = evaluar([fn(x) for x in referencias], [fn(x) for x in hipotesis])
        metricas[nombre] = r.como_dict()
        print(f"{nombre:<14} {r}")
    print("=" * 72)

    rtf = infer_total_s / audio_total_s
    print(f"\naudio total     : {audio_total_s / 60:.1f} min")
    print(f"inferencia total: {infer_total_s:.1f} s")
    print(f"FACTOR DE TIEMPO REAL: {rtf:.3f}  "
          f"({'apto' if rtf < 1 else 'NO apto'} para tiempo real: "
          f"{1 / rtf:.1f}x mas rapido que el audio)" if rtf > 0 else "")

    salida = AQUI / "results"
    salida.mkdir(exist_ok=True)
    # La etiqueta incluye el corpus: un mismo modelo se evalua sobre varios
    # manifiestos y los resultados no deben pisarse entre si.
    # La decodificacion forma parte de la identidad del resultado: dos ejecuciones del
    # mismo modelo sobre el mismo corpus con distinta decodificacion NO son comparables.
    etiqueta = (f"{args.modelo.replace('/', '_')}__{args.manifiesto.stem}"
                f"__{args.decodificacion}")

    (salida / f"transcripciones_{etiqueta}.jsonl").write_text(
        "\n".join(json.dumps({"id": f["id"], "referencia": f["referencia"], "hipotesis": h},
                             ensure_ascii=False) for f, h in zip(filas, hipotesis)),
        encoding="utf-8")

    (salida / f"metricas_{etiqueta}.json").write_text(json.dumps({
        "experimento": "exp-000-baseline",
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "procedencia": procedencia(RAIZ, args.manifiesto),
        "config": vars(args) | {"manifiesto": str(args.manifiesto)},
        "entorno": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        },
        "modelo": {"nombre": args.modelo, "parametros_M": round(n_par / 1e6)},
        "metricas": metricas,
        "coste": {"audio_s": round(audio_total_s, 1),
                  "inferencia_s": round(infer_total_s, 1),
                  "factor_tiempo_real": round(rtf, 4)},
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nresultados -> {salida.relative_to(RAIZ)}/")


if __name__ == "__main__":
    main()
