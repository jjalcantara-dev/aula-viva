"""exp-001: prompting contextual con glosario de dominio.

Diseno PAREADO: las dos condiciones (sin prompt / con prompt) se ejecutan sobre
EXACTAMENTE los mismos clips en la misma ejecucion. Eso permite comparar clip a clip en
lugar de comparar dos medias, que es lo unico que da poder estadistico con corpus
pequenos (ver R6 y el calculo de tamano en corpus/FUENTES.md).

Particion sin fuga: los clips se barajan con semilla fija y se parten en
  - CONTEXTO   : de aqui sale el glosario. Nunca se evalua.
  - EVALUACION : aqui se mide. Su texto no interviene en el prompt.

Uso:
  .venv/bin/python research/experiments/exp-001-prompting/run.py \
      --manifiesto research/corpus/manifests/voxpopuli_es.jsonl \
      --modelo openai/whisper-medium
"""

import argparse
import json
import math
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import jiwer
import soundfile as sf
import torch

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "research"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval.metrics.terminologia import evaluar as evaluar_terminos  # noqa: E402
from eval.metrics.wer import evaluar  # noqa: E402
from eval.normalizers.basico import basico  # noqa: E402
from src.trazabilidad import procedencia  # noqa: E402
from glosario import construir_prompt, extraer  # noqa: E402

AQUI = Path(__file__).resolve().parent
DECODIFICACION = dict(
    temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
    logprob_threshold=-1.0,
    compression_ratio_threshold=1.35,
    no_speech_threshold=0.6,
    return_timestamps=True,
)



def prueba_signos(mejoras: int, empeoramientos: int) -> float:
    """p-valor bilateral del test de signos. Sin dependencias externas.

    Hipotesis nula: el prompt no cambia nada, asi que cada clip que cambia tiene la
    misma probabilidad de mejorar que de empeorar.
    """
    n = mejoras + empeoramientos
    if n == 0:
        return 1.0
    k = min(mejoras, empeoramientos)
    cola = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * cola)


def _errores_por_clip(refs, hips) -> list[tuple[int, int]]:
    """(errores, palabras_referencia) por clip. Se calcula UNA vez."""
    salida = []
    for r, h in zip(refs, hips):
        o = jiwer.process_words([r], [h])
        salida.append((o.substitutions + o.deletions + o.insertions, len(r.split())))
    return salida


def ic_bootstrap(refs, hip_a, hip_b, repeticiones=2000, semilla=42):
    """IC 95% de la diferencia de WER (con prompt - sin prompt) remuestreando CLIPS.

    Remuestrear clips y no palabras es lo correcto: los errores se agrupan dentro de un
    mismo clip y hablante, y tratarlos como independientes estrecharia el intervalo de
    forma artificial.

    Los alineamientos se calculan una sola vez y cada replica solo suma conteos: con 700
    clips y 2000 replicas, realinear en cada una supondria millones de alineamientos.
    """
    ea, eb = _errores_por_clip(refs, hip_a), _errores_por_clip(refs, hip_b)
    rng = random.Random(semilla)
    n = len(refs)
    difs = []
    for _ in range(repeticiones):
        idx = [rng.randrange(n) for _ in range(n)]
        err_a = sum(ea[i][0] for i in idx)
        err_b = sum(eb[i][0] for i in idx)
        palabras = sum(ea[i][1] for i in idx)
        if palabras:
            difs.append(err_b / palabras - err_a / palabras)
    difs.sort()
    return difs[int(0.025 * len(difs))], difs[int(0.975 * len(difs))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifiesto", type=Path, required=True)
    ap.add_argument("--modelo", default="openai/whisper-medium")
    ap.add_argument("--idioma", default="es")
    ap.add_argument("--dtype", default="float16")
    ap.add_argument("--semilla", type=int, default=42)
    ap.add_argument("--fraccion-contexto", type=float, default=0.4,
                    help="proporcion de clips reservados para extraer el glosario")
    ap.add_argument("--terminos", type=int, default=40)
    args = ap.parse_args()

    random.seed(args.semilla)
    torch.manual_seed(args.semilla)
    dtype = getattr(torch, args.dtype)
    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"

    from transformers import AutoProcessor, WhisperForConditionalGeneration

    filas = [json.loads(l) for l in args.manifiesto.read_text(encoding="utf-8").splitlines() if l.strip()]
    orden = list(range(len(filas)))
    random.Random(args.semilla).shuffle(orden)
    corte = int(len(orden) * args.fraccion_contexto)
    idx_ctx, idx_eval = orden[:corte], sorted(orden[corte:])

    terminos = extraer([filas[i]["referencia"] for i in idx_ctx], maximo=args.terminos)
    prompt = construir_prompt(terminos)

    print(f"modelo     : {args.modelo}")
    print(f"corpus     : {args.manifiesto.stem}")
    print(f"contexto   : {len(idx_ctx)} clips (solo glosario)")
    print(f"evaluacion : {len(idx_eval)} clips")
    print(f"glosario   : {len(terminos)} terminos -> {', '.join(terminos[:12])}...")
    print()

    procesador = AutoProcessor.from_pretrained(args.modelo)
    modelo = WhisperForConditionalGeneration.from_pretrained(
        args.modelo, dtype=dtype).to(dispositivo).eval()
    prompt_ids = procesador.get_prompt_ids(prompt, return_tensors="pt").to(dispositivo)

    def transcribir(feats, con_prompt: bool) -> str:
        extra = {"prompt_ids": prompt_ids} if con_prompt else {}
        with torch.no_grad():
            ids = modelo.generate(feats, language=args.idioma, task="transcribe",
                                  **DECODIFICACION, **extra)
        texto = procesador.batch_decode(ids, skip_special_tokens=True)[0].strip()
        # Con prompt_ids, el decodificado puede devolver el propio prompt por delante.
        return texto[len(prompt):].strip() if texto.startswith(prompt) else texto

    # Calentamiento (ver run.py de exp-000).
    a0, sr0 = sf.read(RAIZ / filas[idx_eval[0]]["audio"], dtype="float32")
    f0 = procesador(a0, sampling_rate=sr0, return_tensors="pt").input_features.to(dispositivo, dtype=dtype)
    transcribir(f0, False)

    refs, sin_p, con_p = [], [], []
    t0 = time.perf_counter()
    for n, i in enumerate(idx_eval, 1):
        fila = filas[i]
        audio, sr = sf.read(RAIZ / fila["audio"], dtype="float32")
        feats = procesador(audio, sampling_rate=sr, return_tensors="pt").input_features.to(dispositivo, dtype=dtype)
        refs.append(basico(fila["referencia"]))
        sin_p.append(basico(transcribir(feats, False)))
        con_p.append(basico(transcribir(feats, True)))
        if n % 5 == 0:
            print(f"  [{n}/{len(idx_eval)}]")
    print(f"  tiempo: {time.perf_counter() - t0:.0f} s\n")

    r_sin, r_con = evaluar(refs, sin_p), evaluar(refs, con_p)

    # --- Analisis pareado, clip a clip ---
    mejor = peor = igual = 0
    detalle = []
    for i, r, a, b in zip(idx_eval, refs, sin_p, con_p):
        wa, wb = jiwer.wer(r, a), jiwer.wer(r, b)
        if wb < wa - 1e-9:
            mejor += 1
        elif wb > wa + 1e-9:
            peor += 1
        else:
            igual += 1
        detalle.append({"id": filas[i]["id"], "wer_sin": wa, "wer_con": wb})

    p = prueba_signos(mejor, peor)
    lo, hi = ic_bootstrap(refs, sin_p, con_p, semilla=args.semilla)
    delta = (r_con.wer - r_sin.wer) * 100

    # --- Terminologia: la metrica que el WER global esconde ---
    terminos_norm = [basico(t) for t in terminos]
    t_sin = evaluar_terminos(refs, sin_p, terminos_norm)
    t_con = evaluar_terminos(refs, con_p, terminos_norm)

    print("=" * 66)
    print(f"  sin prompt : {r_sin}")
    print(f"  con prompt : {r_con}")
    print("-" * 66)
    print(f"  terminologia sin prompt : {t_sin}")
    print(f"  terminologia con prompt : {t_con}")
    print(f"  cobertura de terminos   : {(t_con.cobertura - t_sin.cobertura) * 100:+.2f} puntos")
    if t_sin.terminos_perdidos:
        print("  terminos peor reproducidos (sin prompt): "
              + ", ".join(f"{t}({h}/{r})" for t, r, h in t_sin.terminos_perdidos[:6]))
    print("-" * 66)
    print(f"  diferencia : {delta:+.2f} puntos de WER   (negativo = el prompt ayuda)")
    print(f"  IC 95%     : [{lo * 100:+.2f}, {hi * 100:+.2f}]  (bootstrap sobre clips)")
    print(f"  pareado    : {mejor} mejoran, {peor} empeoran, {igual} sin cambio")
    print(f"  test signos: p = {p:.4f}")
    concluyente = (lo < 0 and hi < 0) or (lo > 0 and hi > 0)
    print(f"  veredicto  : {'DIFERENCIA SIGNIFICATIVA' if concluyente else 'NO CONCLUYENTE (el IC cruza el cero)'}")
    print("=" * 66)

    salida = AQUI / "results"
    salida.mkdir(exist_ok=True)
    etiqueta = f"{args.modelo.replace('/', '_')}__{args.manifiesto.stem}"
    (salida / f"metricas_{etiqueta}.json").write_text(json.dumps({
        "experimento": "exp-001-prompting",
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "procedencia": procedencia(RAIZ, args.manifiesto),
        "config": vars(args) | {"manifiesto": str(args.manifiesto)},
        "glosario": {"terminos": terminos, "prompt": prompt,
                     "clips_contexto": len(idx_ctx)},
        "metricas": {"sin_prompt": r_sin.como_dict(), "con_prompt": r_con.como_dict()},
        "terminologia": {"sin_prompt": t_sin.como_dict(), "con_prompt": t_con.como_dict()},
        "pareado": {"mejoran": mejor, "empeoran": peor, "sin_cambio": igual,
                    "p_test_signos": p, "delta_wer_pp": delta,
                    "ic95_pp": [lo * 100, hi * 100], "concluyente": concluyente},
        "por_clip": detalle,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nresultados -> {(salida / f'metricas_{etiqueta}.json').relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
