"""exp-004-arquitecturas: ¿es Whisper el modelo base correcto?

Toda la comparativa de tecnicas de adaptacion (exp-001 a exp-003) se hizo sobre Whisper,
elegido en exp-000 entre seis variantes de la propia familia. Eso responde "que Whisper",
no "por que Whisper". Desde entonces han aparecido modelos multilingues de arquitectura
distinta que declaran mejor calidad y mucho mas caudal.

Este experimento contrasta el modelo base elegido con un transductor (Parakeet TDT) sobre
los MISMOS clips, y reporta lo que la memoria sostiene que hay que reportar: no solo WER,
tambien errores criticos para accesibilidad y coste en tiempo real.

Aviso metodologico que NO se puede eliminar: Whisper se evalua con reintento por
temperatura (la decodificacion congelada en R14) y Parakeet con la suya, porque un
transductor no tiene bucle autorregresivo sobre el texto y por tanto no admite reintento.
Cada modelo va en su configuracion estandar; la comparacion es entre sistemas completos,
no entre codificadores con la decodificacion igualada. Se declara y no se disimula.

Uso:
  .venv/bin/python research/experiments/exp-004-arquitecturas/run.py \
      --manifiesto research/corpus/manifests/voxpopuli_es_400.jsonl
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

from eval.metrics.criticos import evaluar as evaluar_criticos  # noqa: E402
from eval.metrics.wer import evaluar  # noqa: E402
from eval.normalizers.basico import NORMALIZADORES, basico  # noqa: E402
from eval.stats.pareado import conteo_signos, ic_bootstrap, prueba_signos, veredicto  # noqa: E402
from src.asr.motores import cargar, decodificacion_por_defecto  # noqa: E402
from src.trazabilidad import procedencia, sufijo_muestra  # noqa: E402

AQUI = Path(__file__).resolve().parent

# El primero es la referencia: el modelo base sobre el que se hizo toda la comparativa.
MODELOS = ["openai/whisper-medium", "nvidia/parakeet-tdt-0.6b-v3"]


def cargar_manifiesto(ruta: Path) -> list[dict]:
    with ruta.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def transcribir_corpus(motor, filas, lote, dispositivo):
    """Transcribe el corpus midiendo el coste, con calentamiento previo.

    El calentamiento no es cosmetico: la primera inferencia paga compilacion de kernels
    (varios segundos en ROCm) y penalizaria mas a unos modelos que a otros, invalidando
    justo la comparacion de coste que este experimento quiere hacer.
    """
    audio, sr = sf.read(RAIZ / filas[0]["audio"], dtype="float32")
    motor.transcribir([audio], sr)
    if dispositivo == "cuda":
        torch.cuda.synchronize()

    hipotesis, audio_s, infer_s = [], 0.0, 0.0
    for inicio in range(0, len(filas), lote):
        grupo = filas[inicio:inicio + lote]
        audios = []
        for fila in grupo:
            a, sr = sf.read(RAIZ / fila["audio"], dtype="float32")
            audios.append(a)

        if dispositivo == "cuda":
            torch.cuda.synchronize()
        t = time.perf_counter()
        textos = motor.transcribir(audios, sr)
        if dispositivo == "cuda":
            torch.cuda.synchronize()
        dt = time.perf_counter() - t

        hipotesis.extend(textos)
        audio_s += sum(f["duracion_s"] for f in grupo)
        infer_s += dt
        if inicio % (lote * 10) == 0:
            print(f"  [{inicio + len(grupo):4d}/{len(filas)}] {dt:5.2f}s  {textos[0][:60]}")

    return hipotesis, audio_s, infer_s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifiesto", type=Path,
                    default=RAIZ / "research/corpus/manifests/voxpopuli_es_400.jsonl")
    ap.add_argument("--modelos", nargs="+", default=MODELOS,
                    help="el PRIMERO es la referencia contra la que se contrastan los demas")
    ap.add_argument("--idioma", default="es")
    ap.add_argument("--dispositivo", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--dtype", default="float16", choices=["float16", "bfloat16", "float32"])
    # Lote 1 a proposito: Whisper rellena a 30 s y agrupar no le anade relleno, pero
    # Parakeet procesa la duracion real y agruparlo exigiria rellenar hasta el clip mas
    # largo del lote. Ese relleno puede cambiar su salida, y una optimizacion que cambia
    # los resultados no es una optimizacion. Ademas el coste medido dejaria de ser
    # comparable entre las dos arquitecturas.
    ap.add_argument("--lote", type=int, default=1)
    ap.add_argument("--semilla", type=int, default=42)
    ap.add_argument("--limite", type=int, default=None)
    args = ap.parse_args()

    torch.manual_seed(args.semilla)
    dtype = getattr(torch, args.dtype)

    filas = cargar_manifiesto(args.manifiesto)
    if args.limite:
        filas = filas[:args.limite]
    referencias = [f["referencia"] for f in filas]

    # La muestra entra en el NOMBRE del resultado, no solo en su contenido. Evaluar 400
    # clips de un manifiesto de 1200 y guardarlo con el nombre del manifiesto completo
    # produce dos ficheros distintos que se pisan, y una tabla que compara cifras medidas
    # sobre material distinto sin que nada lo delate. Ya paso dos veces en este proyecto.
    muestra = sufijo_muestra(args.manifiesto, len(filas))
    if muestra:
        print(f"AVISO: submuestra de {len(filas)} clips. Lo suyo es darle su propio "
              f"manifiesto, como voxpopuli_es_400.")

    print(f"corpus      : {args.manifiesto.stem} ({len(filas)} clips)")
    print(f"dispositivo : {args.dispositivo} ({args.dtype})")
    print(f"modelos     : {', '.join(args.modelos)}\n")

    salida = AQUI / "results"
    salida.mkdir(exist_ok=True)

    sistemas = {}
    for nombre in args.modelos:
        decod = decodificacion_por_defecto(nombre)
        print(f"--- {nombre} ({decod})")
        motor = cargar(nombre, decod, args.idioma, args.dispositivo, dtype)
        print(f"  carga: {motor.carga_s}s  ({motor.parametros_M}M parametros)")

        hipotesis, audio_s, infer_s = transcribir_corpus(
            motor, filas, args.lote, args.dispositivo)

        metricas = {}
        for norm, fn in NORMALIZADORES.items():
            metricas[norm] = evaluar([fn(x) for x in referencias],
                                     [fn(x) for x in hipotesis]).como_dict()
        criticos = evaluar_criticos([basico(x) for x in referencias],
                                    [basico(x) for x in hipotesis])
        rtf = infer_s / audio_s

        etiqueta = (f"{nombre.replace('/', '_')}__{args.manifiesto.stem}"
                    f"{muestra}__{decod}")
        (salida / f"transcripciones_{etiqueta}.jsonl").write_text(
            "\n".join(json.dumps({"id": f["id"], "referencia": f["referencia"],
                                  "hipotesis": h}, ensure_ascii=False)
                      for f, h in zip(filas, hipotesis)), encoding="utf-8")

        sistemas[nombre] = {
            "decodificacion": decod,
            "parametros_M": motor.parametros_M,
            "carga_s": motor.carga_s,
            "metricas": metricas,
            "criticos": criticos.como_dict(),
            "coste": {"audio_s": round(audio_s, 1), "inferencia_s": round(infer_s, 1),
                      "factor_tiempo_real": round(rtf, 4)},
            "hipotesis": hipotesis,
        }

        print(f"  WER (basico) {metricas['basico']['wer']:.2%}   "
              f"criticos {criticos.tasa_error:.2%}   "
              f"tiempo real {rtf:.4f} ({1 / rtf:.0f}x)\n")

    # ------------------------------------------------------------- contrastes --
    base = args.modelos[0]
    refs_n = [basico(x) for x in referencias]
    hip_base = [basico(x) for x in sistemas[base]["hipotesis"]]

    contrastes = {}
    for nombre in args.modelos[1:]:
        hip_b = [basico(x) for x in sistemas[nombre]["hipotesis"]]
        mej, emp, eq = conteo_signos(refs_n, hip_base, hip_b)
        p = prueba_signos(mej, emp)
        ic = ic_bootstrap(refs_n, hip_base, hip_b)
        contrastes[nombre] = {
            "frente_a": base,
            "delta_wer_pp": round((sistemas[nombre]["metricas"]["basico"]["wer"]
                                   - sistemas[base]["metricas"]["basico"]["wer"]) * 100, 2),
            "clips_mejora": mej, "clips_empeora": emp, "clips_empate": eq,
            "p_signos": round(p, 6),
            "ic95_pp": [round(ic[0] * 100, 2), round(ic[1] * 100, 2)],
            "veredicto": veredicto(ic, p),
        }

    print("=" * 78)
    print(f"{'sistema':<32} {'WER':>7} {'crit.':>7} {'x tiempo real':>14} {'veredicto':>12}")
    print("-" * 78)
    for nombre in args.modelos:
        s = sistemas[nombre]
        v = contrastes.get(nombre, {}).get("veredicto", "referencia")
        print(f"{nombre:<32} {s['metricas']['basico']['wer']:>6.2%} "
              f"{s['criticos']['tasa_error']:>6.2%} "
              f"{1 / s['coste']['factor_tiempo_real']:>13.0f}x {v:>12}")
    print("=" * 78)
    for nombre, c in contrastes.items():
        print(f"\n{nombre} frente a {base}:")
        print(f"  diferencia de WER : {c['delta_wer_pp']:+.2f} pp  "
              f"(IC95 [{c['ic95_pp'][0]:+.2f}, {c['ic95_pp'][1]:+.2f}])")
        print(f"  clips             : {c['clips_mejora']} mejoran, "
              f"{c['clips_empeora']} empeoran, {c['clips_empate']} empatan "
              f"(p={c['p_signos']:.2g})")
        print(f"  veredicto         : {c['veredicto']}")

    abrev = "-vs-".join(m.split("/")[-1] for m in args.modelos)
    destino = (salida /
               f"metricas_arquitecturas__{args.manifiesto.stem}{muestra}__{abrev}.json")
    destino.write_text(json.dumps({
        "experimento": "exp-004-arquitecturas",
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "procedencia": procedencia(RAIZ, args.manifiesto, len(filas)),
        "config": vars(args) | {"manifiesto": str(args.manifiesto)},
        "entorno": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        },
        # Las hipotesis ya estan en su .jsonl; aqui solo estorbarian.
        "sistemas": {n: {k: v for k, v in s.items() if k != "hipotesis"}
                     for n, s in sistemas.items()},
        "contrastes": contrastes,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nresultados -> {destino.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
