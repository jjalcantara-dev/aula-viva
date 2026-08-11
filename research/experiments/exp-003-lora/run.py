"""exp-003, fase 2: evaluar el adaptador LoRA frente al modelo sin ajustar.

Diseno PAREADO, igual que exp-001 y exp-002: ambas condiciones sobre exactamente los
mismos clips, misma decodificacion, y comparacion clip a clip.

La particion de evaluacion (`test` de VoxPopuli) es disjunta de la de entrenamiento
(`train`) por construccion del propio dataset.

Requiere haber ejecutado antes `entrenar.py`.

Uso:
  .venv/bin/python research/experiments/exp-003-lora/run.py
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

from eval.metrics.criticos import evaluar as evaluar_criticos  # noqa: E402
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


def prueba_signos(mejoras: int, empeoramientos: int) -> float:
    n = mejoras + empeoramientos
    if n == 0:
        return 1.0
    k = min(mejoras, empeoramientos)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n))


def ic_bootstrap(refs, hip_a, hip_b, repeticiones=2000, semilla=42):
    def errores(hips):
        salida = []
        for r, h in zip(refs, hips):
            o = jiwer.process_words([r], [h])
            salida.append((o.substitutions + o.deletions + o.insertions, len(r.split())))
        return salida

    ea, eb = errores(hip_a), errores(hip_b)
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
    ap.add_argument("--manifiesto", type=Path,
                    default=RAIZ / "research/corpus/manifests/voxpopuli_es_400.jsonl")
    ap.add_argument("--modelo", default="openai/whisper-medium")
    ap.add_argument("--adaptador", type=Path, default=AQUI / "adaptador")
    ap.add_argument("--limite", type=int, default=None)
    ap.add_argument("--semilla", type=int, default=42)
    args = ap.parse_args()

    if not args.adaptador.exists():
        raise SystemExit(f"no existe {args.adaptador}. Ejecuta antes entrenar.py")

    torch.manual_seed(args.semilla)
    disp, dtype = ("cuda", torch.float16) if torch.cuda.is_available() else ("cpu", torch.float32)

    from peft import PeftModel
    from transformers import AutoProcessor, WhisperForConditionalGeneration

    filas = [json.loads(l) for l in args.manifiesto.read_text(encoding="utf-8").splitlines()
             if l.strip()]
    if args.limite:
        filas = filas[:args.limite]

    procesador = AutoProcessor.from_pretrained(args.modelo)
    base = WhisperForConditionalGeneration.from_pretrained(
        args.modelo, dtype=dtype).to(disp).eval()
    # El adaptador se activa y desactiva sobre el MISMO modelo cargado, en lugar de
    # cargar dos copias: garantiza que la unica diferencia entre condiciones es LoRA.
    ajustado = PeftModel.from_pretrained(base, str(args.adaptador)).eval()

    print(f"modelo     : {args.modelo}")
    print(f"adaptador  : {args.adaptador.relative_to(RAIZ)}")
    print(f"corpus     : {args.manifiesto.stem}  ({len(filas)} clips)\n")

    def transcribir(feats, con_lora: bool) -> str:
        if con_lora:
            ajustado.enable_adapter_layers()
        else:
            ajustado.disable_adapter_layers()
        with torch.no_grad():
            ids = ajustado.generate(feats, language="es", task="transcribe", **DECODIFICACION)
        return procesador.batch_decode(ids, skip_special_tokens=True)[0].strip()

    a0, sr0 = sf.read(RAIZ / filas[0]["audio"], dtype="float32")
    f0 = procesador(a0[:sr0], sampling_rate=sr0, return_tensors="pt")\
        .input_features.to(disp, dtype=dtype)
    transcribir(f0, False)  # calentamiento

    refs, sin_l, con_l = [], [], []
    t0 = time.perf_counter()
    for n, fila in enumerate(filas, 1):
        audio, sr = sf.read(RAIZ / fila["audio"], dtype="float32")
        feats = procesador(audio, sampling_rate=sr, return_tensors="pt")\
            .input_features.to(disp, dtype=dtype)
        refs.append(basico(fila["referencia"]))
        sin_l.append(basico(transcribir(feats, False)))
        con_l.append(basico(transcribir(feats, True)))
        if n % 25 == 0:
            print(f"  [{n}/{len(filas)}]")
    print(f"  tiempo: {time.perf_counter() - t0:.0f} s\n")

    r_sin, r_con = evaluar(refs, sin_l), evaluar(refs, con_l)
    mejor = peor = igual = 0
    for r, a, b in zip(refs, sin_l, con_l):
        wa, wb = jiwer.wer(r, a), jiwer.wer(r, b)
        mejor += wb < wa - 1e-9
        peor += wb > wa + 1e-9
        igual += abs(wb - wa) <= 1e-9

    p = prueba_signos(mejor, peor)
    lo, hi = ic_bootstrap(refs, sin_l, con_l, semilla=args.semilla)
    delta = (r_con.wer - r_sin.wer) * 100
    c_base, c_tec = evaluar_criticos(refs, sin_l), evaluar_criticos(refs, con_l)

    ic_excluye_cero = (lo < 0 and hi < 0) or (lo > 0 and hi > 0)
    signos_confirma = p < 0.05
    concluyente = ic_excluye_cero and signos_confirma

    print("=" * 68)
    print(f"  sin LoRA : {r_sin}")
    print(f"  con LoRA : {r_con}")
    print("-" * 68)
    print(f"  crítico sin LoRA : {c_base}")
    print(f"  crítico con LoRA : {c_tec}")
    print("-" * 68)
    print(f"  diferencia : {delta:+.2f} puntos de WER   (negativo = LoRA ayuda)")
    print(f"  IC 95%     : [{lo * 100:+.2f}, {hi * 100:+.2f}]")
    print(f"  pareado    : {mejor} mejoran, {peor} empeoran, {igual} sin cambio")
    print(f"  test signos: p = {p:.4f}")
    if concluyente:
        veredicto = "DIFERENCIA SIGNIFICATIVA (IC y test de signos coinciden)"
    elif ic_excluye_cero or signos_confirma:
        veredicto = "NO CONCLUYENTE (las dos pruebas discrepan: efecto en el limite)"
    else:
        veredicto = "NO CONCLUYENTE"
    print(f"  veredicto  : {veredicto}")
    print("=" * 68)

    salida = AQUI / "results"
    salida.mkdir(exist_ok=True)
    etiqueta = f"{args.modelo.replace('/', '_')}__{args.manifiesto.stem}"
    (salida / f"metricas_{etiqueta}.json").write_text(json.dumps({
        "experimento": "exp-003-lora",
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "procedencia": procedencia(RAIZ, args.manifiesto),
        "config": vars(args) | {"manifiesto": str(args.manifiesto),
                                "adaptador": str(args.adaptador)},
        "metricas": {"sin_lora": r_sin.como_dict(), "con_lora": r_con.como_dict()},
        "criticos": {"sin_lora": c_base.como_dict(), "con_lora": c_tec.como_dict()},
        "pareado": {"mejoran": mejor, "empeoran": peor, "sin_cambio": igual,
                    "p_test_signos": p, "delta_wer_pp": delta,
                    "ic95_pp": [lo * 100, hi * 100], "concluyente": concluyente,
                    "ic_excluye_cero": ic_excluye_cero, "signos_confirma": signos_confirma},
    }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    (salida / f"transcripciones_{etiqueta}.jsonl").write_text(
        "\n".join(json.dumps({"id": f["id"], "referencia": f["referencia"],
                              "sin_lora": a, "con_lora": b}, ensure_ascii=False)
                  for f, a, b in zip(filas, sin_l, con_l)), encoding="utf-8")
    print(f"\nresultados -> {salida.relative_to(RAIZ)}/")


if __name__ == "__main__":
    main()
