"""exp-103: ¿ayuda pasar la transcripcion anterior como contexto de la siguiente ventana?

En el sistema en vivo cada ventana se transcribe A CIEGAS: Whisper no sabe nada de lo que
se dijo en los segundos previos. Si el corte cae en mitad de un termino o de una
construccion larga, no tiene con que resolverlo. Es lo que se observo con microfono real:
"encantado de conoceros" partido entre dos ventanas salio como "Es encantado hacer".

Whisper admite un prompt que actua como contexto previo ya transcrito. La implementacion
de referencia de OpenAI lo usa (condition_on_previous_text). Aqui se mide cuanto aporta.

HIPOTESIS: el contexto deberia ayudar MAS cuando los cortes son arbitrarios (ventana fija)
que cuando caen en pausas naturales (silencios), porque es ahi donde falta informacion.
Por eso se cruzan las dos estrategias de troceado con las dos de contexto.

Uso:
  .venv/bin/python research/experiments/exp-103-contexto/run.py --limite 40
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
sys.path.insert(0, str(RAIZ / "research" / "experiments" / "exp-102-vad"))

from eval.metrics.wer import evaluar  # noqa: E402
from eval.normalizers.basico import basico  # noqa: E402
from segmentador import segmentar  # noqa: E402
from src.trazabilidad import procedencia  # noqa: E402

AQUI = Path(__file__).resolve().parent
DECODIFICACION = dict(
    temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
    logprob_threshold=-1.0,
    compression_ratio_threshold=1.35,
    no_speech_threshold=0.6,
    return_timestamps=True,
)
#: Palabras de contexto que se arrastran. El prompt de Whisper esta limitado (~224
#: tokens) y ademas un contexto muy largo diluye lo relevante, que es el final.
PALABRAS_CONTEXTO = 30

VENTANA_FIJA_S = 5.0
TOPE_SILENCIOS_S = 8.0


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

    def transcribir(muestras, sr, contexto: str | None) -> str:
        feats = procesador(muestras, sampling_rate=sr, return_tensors="pt")\
            .input_features.to(disp, dtype=dtype)
        extra = {}
        if contexto:
            extra["prompt_ids"] = procesador.get_prompt_ids(
                contexto, return_tensors="pt").to(disp)
        with torch.no_grad():
            ids = modelo.generate(feats, language="es", task="transcribe",
                                  **DECODIFICACION, **extra)
        texto = procesador.batch_decode(ids, skip_special_tokens=True)[0].strip()
        # Con prompt_ids el decodificado puede devolver el propio contexto por delante.
        if contexto and texto.startswith(contexto):
            texto = texto[len(contexto):].strip()
        return texto

    a0, sr0 = sf.read(RAIZ / filas[0]["audio"], dtype="float32")
    transcribir(a0[:sr0], sr0, None)  # calentamiento

    print(f"modelo: {args.modelo}   clips: {len(filas)}\n")
    print(f"{'troceado':<18}{'contexto':<12}{'WER':>9}{'CER':>9}{'segs':>7}")
    print("-" * 55)

    resultados = []
    for troceado in ("ventana fija", "silencios"):
        for con_contexto in (False, True):
            refs, hips, n_segs = [], [], 0
            for fila in filas:
                audio, sr = sf.read(RAIZ / fila["audio"], dtype="float32")
                partes = (trocear_fijo(audio, sr, VENTANA_FIJA_S) if troceado == "ventana fija"
                          else segmentar(audio, sr, s_maximo=TOPE_SILENCIOS_S))
                n_segs += len(partes)

                textos: list[str] = []
                for parte in partes:
                    # El contexto es la cola de lo ya transcrito en ESTE clip, que es lo
                    # que tendria el sistema en vivo: no puede mirar hacia delante.
                    contexto = None
                    if con_contexto and textos:
                        contexto = " ".join(" ".join(textos).split()[-PALABRAS_CONTEXTO:])
                    textos.append(transcribir(parte, sr, contexto))

                refs.append(basico(fila["referencia"]))
                hips.append(basico(" ".join(textos)))

            r = evaluar(refs, hips)
            etiqueta = "sí" if con_contexto else "no"
            print(f"{troceado:<18}{etiqueta:<12}{r.wer:>8.2%}{r.cer:>8.2%}{n_segs:>7}")
            resultados.append({"troceado": troceado, "contexto": con_contexto,
                               "wer": r.wer, "cer": r.cer, "n_segmentos": n_segs})

    print("\naporte del contexto (negativo = ayuda):")
    for troceado in ("ventana fija", "silencios"):
        sin = next(r for r in resultados if r["troceado"] == troceado and not r["contexto"])
        con = next(r for r in resultados if r["troceado"] == troceado and r["contexto"])
        print(f"  {troceado:<16}{(con['wer'] - sin['wer']) * 100:+6.2f} pp de WER")

    salida = AQUI / "results"
    salida.mkdir(exist_ok=True)
    (salida / f"metricas_{args.modelo.replace('/', '_')}__{args.manifiesto.stem}.json")\
        .write_text(json.dumps({
            "experimento": "exp-103-contexto",
            "fecha_utc": datetime.now(timezone.utc).isoformat(),
            "procedencia": procedencia(RAIZ, args.manifiesto),
            "config": vars(args) | {"manifiesto": str(args.manifiesto),
                                    "palabras_contexto": PALABRAS_CONTEXTO,
                                    "ventana_fija_s": VENTANA_FIJA_S,
                                    "tope_silencios_s": TOPE_SILENCIOS_S},
            "resultados": resultados,
        }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nresultados -> {salida.relative_to(RAIZ)}/")


if __name__ == "__main__":
    main()
