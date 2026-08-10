"""Agrega los resultados de exp-000-baseline en una tabla comparativa.

Genera a la vez la version legible (markdown, para revisar) y la version LaTeX
(para la memoria). La tabla de la memoria SIEMPRE se genera desde aqui: ninguna
cifra se teclea a mano en el .tex.

Uso:  .venv/bin/python research/eval/report/tabla_modelos.py
"""

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
RESULTADOS = RAIZ / "research" / "experiments" / "exp-000-baseline" / "results"
DESTINO_TEX = RAIZ / "memoria" / "tablas"
DESTINO_MD = RAIZ / "research" / "results"

NORMALIZADOR = "basico"  # metrica principal (ver docs/preguntas-director.md)


def cargar(corpus: str = "fleurs_es", decodificacion: str = "fallback") -> list[dict]:
    filas = []
    for f in sorted(RESULTADOS.glob(f"metricas_*__{corpus}__{decodificacion}.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        m = d["metricas"][NORMALIZADOR]
        filas.append({
            "modelo": d["modelo"]["nombre"].split("/")[-1],
            "params": d["modelo"]["parametros_M"],
            "wer": m["wer"] * 100,
            "cer": m["cer"] * 100,
            "rtf": d["coste"]["factor_tiempo_real"],
            "veces": 1 / d["coste"]["factor_tiempo_real"] if d["coste"]["factor_tiempo_real"] else 0,
        })
    return sorted(filas, key=lambda r: r["params"])


def markdown(filas) -> str:
    L = ["| Modelo | Parámetros (M) | WER (%) | CER (%) | RTF | Veces tiempo real |",
         "|---|---:|---:|---:|---:|---:|"]
    for r in filas:
        L.append(f"| `{r['modelo']}` | {r['params']} | {r['wer']:.2f} | {r['cer']:.2f} | "
                 f"{r['rtf']:.3f} | {r['veces']:.1f}× |")
    return "\n".join(L)


def latex(filas, n_clips, duracion_min) -> str:
    cuerpo = "\n".join(
        f"    \\texttt{{{r['modelo'].replace('_', '-')}}} & {r['params']} & "
        f"{r['wer']:.2f} & {r['cer']:.2f} & {r['rtf']:.3f} & {r['veces']:.1f} \\\\"
        for r in filas)
    return f"""% GENERADO AUTOMATICAMENTE por research/eval/report/tabla_modelos.py
% No editar a mano: los cambios se pierden en la siguiente regeneracion.
\\begin{{table}}[h]
\\centering
\\begin{{tabular}}{{|l|r|r|r|r|r|}}
    \\hline
    \\textbf{{Modelo}} & \\textbf{{Par.\\ (M)}} & \\textbf{{WER (\\%)}} &
    \\textbf{{CER (\\%)}} & \\textbf{{RTF}} & \\textbf{{$\\times$ tiempo real}} \\\\
    \\hline
{cuerpo}
    \\hline
\\end{{tabular}}
\\caption{{Rendimiento de los modelos Whisper sin adaptar sobre {n_clips} fragmentos
({duracion_min:.1f} minutos de audio). Normalizacion \\texttt{{{NORMALIZADOR}}}.
RTF: factor de tiempo real (menor es mejor).}}
\\label{{tab:baseline-modelos}}
\\end{{table}}
"""


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="fleurs_es",
                    help="sufijo del manifiesto (fleurs_es, tedx_es, ...)")
    ap.add_argument("--decodificacion", default="fallback", choices=["voraz", "fallback"])
    args = ap.parse_args()

    filas = cargar(args.corpus, args.decodificacion)
    if not filas:
        raise SystemExit(
            f"sin resultados para '{args.corpus}' / '{args.decodificacion}' en {RESULTADOS}")

    muestra = json.loads(
        next(RESULTADOS.glob(f"metricas_*__{args.corpus}__{args.decodificacion}.json"))
        .read_text(encoding="utf-8"))
    n_clips = muestra["metricas"][NORMALIZADOR]["n_clips"]
    dur_min = muestra["coste"]["audio_s"] / 60

    md = markdown(filas)
    print(md)

    DESTINO_MD.mkdir(parents=True, exist_ok=True)
    DESTINO_TEX.mkdir(parents=True, exist_ok=True)
    nombre = f"baseline_modelos_{args.corpus}_{args.decodificacion}"
    (DESTINO_MD / f"{nombre}.md").write_text(md + "\n", encoding="utf-8")
    (DESTINO_TEX / f"{nombre}.tex").write_text(
        latex(filas, n_clips, dur_min), encoding="utf-8")

    print(f"\n-> {(DESTINO_MD / f'{nombre}.md').relative_to(RAIZ)}")
    print(f"-> {(DESTINO_TEX / f'{nombre}.tex').relative_to(RAIZ)}")
