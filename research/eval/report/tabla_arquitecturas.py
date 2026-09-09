"""Tabla de exp-004: modelo base elegido frente a arquitecturas alternativas.

A diferencia de tabla_tecnicas.py, aqui las columnas que importan no son solo WER: la
pregunta es si cambiar de arquitectura mueve las tres magnitudes que este trabajo sostiene
que hay que mirar a la vez, calidad agregada, supervivencia del contenido critico y coste
en tiempo real. Una tabla que solo trajera el WER reproduciria justo el error que el TFM
denuncia.

Uso:  .venv/bin/python research/eval/report/tabla_arquitecturas.py
"""

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
RESULTADOS = RAIZ / "research" / "experiments" / "exp-004-arquitecturas" / "results"
DESTINO_TEX = RAIZ / "memoria" / "tablas"
DESTINO_MD = RAIZ / "research" / "results"


def corto(nombre: str) -> str:
    return nombre.split("/")[-1]


def cargar() -> list[dict]:
    filas = []
    for f in sorted(RESULTADOS.glob("metricas_arquitecturas__*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        corpus = Path(d["config"]["manifiesto"]).stem
        contrastes = d.get("contrastes", {})
        for nombre, s in d["sistemas"].items():
            c = contrastes.get(nombre, {})
            rtf = s["coste"]["factor_tiempo_real"]
            # Los numerales quedan fuera de esta segunda tasa porque su recuento esta
            # contaminado por la ortografia: la referencia escribe "dos mil diez" y
            # Whisper "2010", de modo que una cifra BIEN reconocida genera tres errores al
            # alinear tres fichas contra una. Negaciones y cuantificadores no tienen ese
            # problema, asi que comparan reconocimiento y no convencion de escritura.
            cat = s["criticos"]["por_categoria"]
            limpios = {k: v for k, v in cat.items() if k != "numeral"}
            total_limpio = sum(v["total"] for v in limpios.values())
            err_limpio = sum(v["errores"] for v in limpios.values())
            filas.append({
                "corpus": corpus,
                "modelo": corto(nombre),
                "params": s["parametros_M"],
                "decod": s["decodificacion"],
                "wer": s["metricas"]["basico"]["wer"] * 100,
                "cer": s["metricas"]["basico"]["cer"] * 100,
                "criticos": s["criticos"]["tasa_error"] * 100,
                "criticos_sin_num": 100 * err_limpio / total_limpio if total_limpio else 0.0,
                "veces_tiempo_real": 1 / rtf if rtf else float("nan"),
                "delta": c.get("delta_wer_pp"),
                "ic": c.get("ic95_pp"),
                "p": c.get("p_signos"),
                "veredicto": c.get("veredicto", "referencia"),
                "es_referencia": not c,
            })
    return filas


def markdown(filas) -> str:
    L = ["| Corpus | Modelo | Params | Decod. | WER | CER | Crít. | Crít. sin num. | × tiempo real | Δ WER (pp) | IC 95% | p | Veredicto |",
         "|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|---:|---|"]
    for r in filas:
        ic = f"[{r['ic'][0]:+.2f}, {r['ic'][1]:+.2f}]" if r["ic"] else "—"
        delta = "—" if r["delta"] is None else f"{r['delta']:+.2f}"
        p = "—" if r["p"] is None else f"{r['p']:.2g}"
        L.append(
            f"| `{r['corpus']}` | `{r['modelo']}` | {r['params']}M | {r['decod']} | "
            f"{r['wer']:.2f} | {r['cer']:.2f} | {r['criticos']:.2f} | "
            f"{r['criticos_sin_num']:.2f} | "
            f"{r['veces_tiempo_real']:.0f}× | {delta} | {ic} | {p} | {r['veredicto']} |")
    L += ["", "> **Crít. sin num.** excluye los numerales: su recuento mide en parte la "
          "convención de escritura y no el reconocimiento, porque la referencia escribe "
          "«dos mil diez» donde Whisper escribe «2010» y el alineamiento cuenta tres "
          "errores por una cifra bien reconocida. Negaciones y cuantificadores no tienen "
          "ese sesgo. Ver `estilo_numerico.md`."]
    return "\n".join(L)


def _fila_latex(r: dict) -> str:
    delta = "---" if r["delta"] is None else f"{r['delta']:+.2f}"
    ic = "---" if not r["ic"] else f"[{r['ic'][0]:+.2f}, {r['ic'][1]:+.2f}]"
    return (f"    \\texttt{{{r['corpus'].replace('_', '-')}}} & "
            f"\\texttt{{{r['modelo'].replace('_', '-')}}} & {r['params']} & "
            f"{r['wer']:.2f} & {r['criticos']:.2f} & {r['criticos_sin_num']:.2f} & "
            f"{r['veces_tiempo_real']:.0f}$\\times$ & {delta} & {ic} & "
            f"{r['veredicto']} \\\\")


def latex(filas) -> str:
    cuerpo = "\n".join(_fila_latex(r) for r in filas)
    return f"""% GENERADO AUTOMATICAMENTE por research/eval/report/tabla_arquitecturas.py
% No editar a mano.
\\begin{{table}}[h]
\\centering
\\footnotesize
\\setlength{{\\tabcolsep}}{{4pt}}
\\resizebox{{\\textwidth}}{{!}}{{%
\\begin{{tabular}}{{|l|l|r|r|r|r|r|r|c|l|}}
    \\hline
    \\textbf{{Corpus}} & \\textbf{{Modelo}} & \\textbf{{Par. (M)}} & \\textbf{{WER}} &
    \\textbf{{Crít.}} & \\textbf{{Crít. s/n}} & \\textbf{{Vel.}} &
    \\textbf{{$\\Delta$ (pp)}} & \\textbf{{IC 95\\%}} & \\textbf{{Veredicto}} \\\\
    \\hline
{cuerpo}
    \\hline
\\end{{tabular}}}}
\\caption{{Modelo base de la comparativa frente a una arquitectura de transductor, sobre
los mismos clips. \\textbf{{Crít.}} es la tasa de error sobre negaciones, numerales y
cuantificadores, y \\textbf{{Crít. s/n}} la misma tasa excluyendo numerales, cuyo recuento
mide en parte la convención de escritura: la referencia escribe «dos mil diez» donde
Whisper escribe «2010», y el alineamiento contabiliza tres errores por una cifra bien
reconocida. \\textbf{{Vel.}} es cuántas veces más rápido que el audio se procesa.
$\\Delta$ negativo indica mejora respecto al modelo base. Las decodificaciones no son
equiparables entre arquitecturas: cada sistema se evalúa en su configuración estándar.}}
\\label{{tab:comparativa-arquitecturas}}
\\end{{table}}
"""


if __name__ == "__main__":
    filas = cargar()
    if not filas:
        raise SystemExit("sin resultados de exp-004 todavia")

    md = markdown(filas)
    print(md)
    DESTINO_MD.mkdir(parents=True, exist_ok=True)
    DESTINO_TEX.mkdir(parents=True, exist_ok=True)
    (DESTINO_MD / "comparativa_arquitecturas.md").write_text(md + "\n", encoding="utf-8")
    (DESTINO_TEX / "comparativa_arquitecturas.tex").write_text(latex(filas), encoding="utf-8")
    print(f"\n-> {(DESTINO_MD / 'comparativa_arquitecturas.md').relative_to(RAIZ)}")
    print(f"-> {(DESTINO_TEX / 'comparativa_arquitecturas.tex').relative_to(RAIZ)}")
