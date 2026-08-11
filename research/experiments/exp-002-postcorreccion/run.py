"""exp-002: post-correccion de la transcripcion con un LLM ligero local.

Segunda tecnica de la comparativa. Diseno PAREADO, igual que exp-001.

Decision de diseno importante: **no se vuelve a ejecutar Whisper**. Se parte de las
transcripciones que ya produjo exp-000, asi que la salida del ASR esta fija y la unica
variable es la correccion del LLM. Eso aisla el efecto por completo (y ahorra la mitad
del computo).

Metricas, mas alla del WER:
  - terminologia : cobertura y precision sobre el glosario del dominio
  - razon de longitud : detecta si el LLM esta reescribiendo en lugar de corregir
  - descartes : correcciones rechazadas por las salvaguardas del corrector

Uso:
  .venv/bin/python research/experiments/exp-002-postcorreccion/run.py \
      --transcripciones research/experiments/exp-000-baseline/results/\
transcripciones_openai_whisper-medium__voxpopuli_es__fallback.jsonl
"""

import argparse
import json
import math
import random
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import jiwer
import torch

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "research"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from corrector import construir_mensajes, limpiar  # noqa: E402
from eval.metrics.terminologia import evaluar as evaluar_terminos  # noqa: E402
from eval.metrics.criticos import evaluar as evaluar_criticos  # noqa: E402
from eval.metrics.wer import evaluar  # noqa: E402
from eval.normalizers.basico import basico  # noqa: E402
from src.trazabilidad import commit_actual, hash_fichero  # noqa: E402

AQUI = Path(__file__).resolve().parent


def prueba_signos(mejoras: int, empeoramientos: int) -> float:
    n = mejoras + empeoramientos
    if n == 0:
        return 1.0
    k = min(mejoras, empeoramientos)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n))


def errores_por_clip(refs, hips):
    salida = []
    for r, h in zip(refs, hips):
        o = jiwer.process_words([r], [h])
        salida.append((o.substitutions + o.deletions + o.insertions, len(r.split())))
    return salida


def ic_bootstrap(refs, hip_a, hip_b, repeticiones=2000, semilla=42):
    """IC 95% de la diferencia de WER remuestreando CLIPS (los errores se agrupan)."""
    ea, eb = errores_por_clip(refs, hip_a), errores_por_clip(refs, hip_b)
    rng = random.Random(semilla)
    n = len(refs)
    difs = []
    for _ in range(repeticiones):
        idx = [rng.randrange(n) for _ in range(n)]
        palabras = sum(ea[i][1] for i in idx)
        if palabras:
            difs.append((sum(eb[i][0] for i in idx) - sum(ea[i][0] for i in idx)) / palabras)
    difs.sort()
    return difs[int(0.025 * len(difs))], difs[int(0.975 * len(difs))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcripciones", type=Path, required=True)
    ap.add_argument("--modelo", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--glosario", type=Path, default=None,
                    help="fichero con un termino por linea; sin el, correccion sin dominio")
    ap.add_argument("--limite", type=int, default=None)
    ap.add_argument("--semilla", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.semilla)
    torch.manual_seed(args.semilla)
    disp, dtype = ("cuda", torch.bfloat16) if torch.cuda.is_available() else ("cpu", torch.float32)

    from transformers import AutoModelForCausalLM, AutoTokenizer

    filas = [json.loads(l) for l in args.transcripciones.read_text(encoding="utf-8").splitlines()
             if l.strip()]
    if args.limite:
        filas = filas[:args.limite]

    glosario = None
    if args.glosario and args.glosario.exists():
        glosario = [l.strip() for l in args.glosario.read_text(encoding="utf-8").splitlines()
                    if l.strip()]

    print(f"corrector  : {args.modelo}")
    print(f"entrada    : {args.transcripciones.name}")
    print(f"clips      : {len(filas)}")
    print(f"glosario   : {len(glosario) if glosario else 0} terminos\n")

    tokenizador = AutoTokenizer.from_pretrained(args.modelo)
    llm = AutoModelForCausalLM.from_pretrained(args.modelo, dtype=dtype).to(disp).eval()

    corregidas, motivos = [], Counter()
    t0 = time.perf_counter()
    for n, fila in enumerate(filas, 1):
        original = fila["hipotesis"]
        entrada = tokenizador.apply_chat_template(
            construir_mensajes(original, glosario),
            add_generation_prompt=True, return_tensors="pt", return_dict=True).to(disp)
        with torch.no_grad():
            salida = llm.generate(**entrada, max_new_tokens=len(original.split()) * 3 + 64,
                                  do_sample=False,
                                  pad_token_id=tokenizador.eos_token_id)
        respuesta = tokenizador.decode(salida[0][entrada["input_ids"].shape[1]:],
                                       skip_special_tokens=True)
        texto, motivo = limpiar(respuesta, original)
        motivos[motivo] += 1
        corregidas.append(texto)
        if n % 20 == 0:
            print(f"  [{n}/{len(filas)}]  descartes: "
                  f"{sum(v for k, v in motivos.items() if k != 'ok')}")
    print(f"  tiempo: {time.perf_counter() - t0:.0f} s\n")

    refs = [basico(f["referencia"]) for f in filas]
    antes = [basico(f["hipotesis"]) for f in filas]
    despues = [basico(t) for t in corregidas]

    r_antes, r_despues = evaluar(refs, antes), evaluar(refs, despues)
    mejor = peor = igual = 0
    for r, a, b in zip(refs, antes, despues):
        wa, wb = jiwer.wer(r, a), jiwer.wer(r, b)
        mejor += wb < wa - 1e-9
        peor += wb > wa + 1e-9
        igual += abs(wb - wa) <= 1e-9

    p = prueba_signos(mejor, peor)
    lo, hi = ic_bootstrap(refs, antes, despues, semilla=args.semilla)
    delta = (r_despues.wer - r_antes.wer) * 100
    razon = (sum(len(t.split()) for t in despues) /
             max(1, sum(len(t.split()) for t in antes)))

    # Errores que cambian el sentido. El WER agregado los esconde: medido en M0,
    # con 18.6% de WER se pierde el 28% de las negaciones.
    c_base = evaluar_criticos(refs, antes)
    c_tec = evaluar_criticos(refs, despues)

    print("=" * 68)
    print(f"  sin corregir : {r_antes}")
    print(f"  corregido    : {r_despues}")
    print("-" * 68)
    if glosario:
        t_a = evaluar_terminos(refs, antes, [basico(t) for t in glosario])
        t_d = evaluar_terminos(refs, despues, [basico(t) for t in glosario])
        print(f"  terminologia sin corregir : {t_a}")
        print(f"  terminologia corregida    : {t_d}")
        print("-" * 68)
    print(f"  crítico sin corregir : {c_base}")
    print(f"  crítico corregido    : {c_tec}")
    print("-" * 68)
    print(f"  diferencia   : {delta:+.2f} puntos de WER   (negativo = el LLM ayuda)")
    print(f"  IC 95%       : [{lo * 100:+.2f}, {hi * 100:+.2f}]")
    print(f"  pareado      : {mejor} mejoran, {peor} empeoran, {igual} sin cambio")
    print(f"  test signos  : p = {p:.4f}")
    print(f"  razon long.  : {razon:.3f}  ({'reescribe' if razon > 1.05 else 'conserva'})")
    print(f"  descartes    : {dict(motivos)}")
    # El veredicto exige que AMBAS pruebas coincidan. Basar la conclusion solo en el
    # intervalo de confianza etiqueta como significativo un efecto cuyo IC llega hasta
    # -0.05 y que el test de signos no confirma (ocurrio con prompting sobre
    # voxpopuli_es_400). Cuando discrepan, el efecto esta en el limite de deteccion y lo
    # honesto es no concluir.
    ic_excluye_cero = (lo < 0 and hi < 0) or (lo > 0 and hi > 0)
    signos_confirma = p < 0.05
    concluyente = ic_excluye_cero and signos_confirma
    if concluyente:
        veredicto = "DIFERENCIA SIGNIFICATIVA (IC y test de signos coinciden)"
    elif ic_excluye_cero or signos_confirma:
        veredicto = "NO CONCLUYENTE (las dos pruebas discrepan: efecto en el limite)"
    else:
        veredicto = "NO CONCLUYENTE"
    print(f"  veredicto    : {veredicto}")
    print("=" * 68)

    salida_dir = AQUI / "results"
    salida_dir.mkdir(exist_ok=True)
    etiqueta = f"{args.modelo.replace('/', '_')}__{args.transcripciones.stem}"
    (salida_dir / f"metricas_{etiqueta}.json").write_text(json.dumps({
        "experimento": "exp-002-postcorreccion",
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "procedencia": {"commit": commit_actual(RAIZ),
                        "transcripciones": str(args.transcripciones),
                        "transcripciones_sha256": hash_fichero(args.transcripciones)},
        "config": vars(args) | {"transcripciones": str(args.transcripciones)},
        "metricas": {"sin_corregir": r_antes.como_dict(), "corregido": r_despues.como_dict()},
        "pareado": {"mejoran": mejor, "empeoran": peor, "sin_cambio": igual,
                    "p_test_signos": p, "delta_wer_pp": delta,
                    "ic95_pp": [lo * 100, hi * 100], "concluyente": concluyente,
                    "ic_excluye_cero": ic_excluye_cero, "signos_confirma": signos_confirma},
        "criticos": {"sin_corregir": c_base.como_dict(), "corregido": c_tec.como_dict()},
        "control": {"razon_longitud": razon, "descartes": dict(motivos)},
    }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    (salida_dir / f"corregidas_{etiqueta}.jsonl").write_text(
        "\n".join(json.dumps({"id": f["id"], "referencia": f["referencia"],
                              "antes": f["hipotesis"], "despues": c}, ensure_ascii=False)
                  for f, c in zip(filas, corregidas)), encoding="utf-8")
    print(f"\nresultados -> {salida_dir.relative_to(RAIZ)}/")


if __name__ == "__main__":
    main()
