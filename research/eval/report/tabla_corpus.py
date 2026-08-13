"""Tabla comparativa CORPUS x MODELO.

Mientras `tabla_modelos.py` responde "que modelo elijo", esta responde la pregunta que
de verdad condiciona el diseno experimental: **cuanto depende el WER del material**, y
en particular de la variedad dialectal (R13) y de la calidad de la referencia (R11).

Uso:  .venv/bin/python research/eval/report/tabla_corpus.py
"""

import json
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
RESULTADOS = RAIZ / "research" / "experiments" / "exp-000-baseline" / "results"
DESTINO_TEX = RAIZ / "memoria" / "tablas"
DESTINO_MD = RAIZ / "research" / "results"

# Caracterizacion de cada corpus. Fuente: research/corpus/FUENTES.md.
# La variedad NO es un detalle: ver R13 en PLANNING.md.
CARACTERIZACION = {
    "fleurs_es":         ("Latinoamérica", "Leída, enciclopédica"),
    "tedx_es":           ("México",        "Charla espontánea"),
    "teleconciencia_es": ("México",        "Divulgación científica"),
    "voxpopuli_es":      ("Peninsular",    "Parlamentario"),
    "mediaspeech_es":    ("Peninsular",    "Medios, locución"),
    "mls_es":            ("Mixta",         "Audiolibro"),
    "minds14_es":        ("Peninsular",    "Telefónico, banca"),
}

ORDEN_MODELOS = ["whisper-tiny", "whisper-base", "whisper-small",
                 "whisper-medium", "whisper-large-v3-turbo", "whisper-large-v3"]


def cargar(decodificacion: str = "fallback") -> tuple[dict, list[str]]:
    """Devuelve {corpus: {modelo: {basico, sin_tildes}}} y la lista de modelos presentes.

    Se filtra por decodificacion: mezclar resultados de decodificacion voraz y con
    reintento en la misma tabla los haria incomparables (ver run.py, DECODIFICACION).
    """
    datos: dict[str, dict[str, dict]] = defaultdict(dict)
    modelos: set[str] = set()
    for f in sorted(RESULTADOS.glob(f"metricas_*__{decodificacion}.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        corpus = Path(d["config"]["manifiesto"]).stem
        modelo = d["modelo"]["nombre"].split("/")[-1]
        datos[corpus][modelo] = {
            "basico": d["metricas"]["basico"]["wer"] * 100,
            "sin_tildes": d["metricas"]["sin_tildes"]["wer"] * 100,
            "palabras": d["metricas"]["basico"]["n_palabras_ref"],
        }
        modelos.add(modelo)
    presentes = [m for m in ORDEN_MODELOS if m in modelos]
    return datos, presentes


def _fila_valores(datos, corpus, modelos, referencia="whisper-medium"):
    v = [datos[corpus].get(m, {}).get("basico") for m in modelos]
    ref = datos[corpus].get(referencia)
    delta = None if not ref else ref["basico"] - ref["sin_tildes"]
    return v, delta


def markdown(datos, modelos) -> str:
    cab = ["Corpus", "Variedad", "Registro"] + [m.replace("whisper-", "") for m in modelos]
    cab += ["Δ tildes"]
    L = ["| " + " | ".join(cab) + " |",
         "|" + "---|" * 3 + "---:|" * (len(modelos) + 1)]
    for corpus in sorted(datos, key=lambda c: CARACTERIZACION.get(c, ("", ""))[0]):
        var, reg = CARACTERIZACION.get(corpus, ("?", "?"))
        vals, delta = _fila_valores(datos, corpus, modelos)
        celdas = [f"{v:.2f}" if v is not None else "—" for v in vals]
        d = f"−{delta:.2f}" if delta else "—"
        L.append(f"| `{corpus}` | {var} | {reg} | " + " | ".join(celdas) + f" | {d} |")
    return "\n".join(L)


def latex(datos, modelos) -> str:
    cols = "|l|l|l|" + "r|" * (len(modelos) + 1)
    cab = " & ".join([r"\textbf{Corpus}", r"\textbf{Variedad}", r"\textbf{Registro}"] +
                     [rf"\textbf{{{m.replace('whisper-', '').replace('-', '--')}}}" for m in modelos] +
                     [r"\textbf{$\Delta$ tildes}"])
    filas = []
    for corpus in sorted(datos, key=lambda c: CARACTERIZACION.get(c, ("", ""))[0]):
        var, reg = CARACTERIZACION.get(corpus, ("?", "?"))
        vals, delta = _fila_valores(datos, corpus, modelos)
        celdas = [f"{v:.2f}" if v is not None else "--" for v in vals]
        d = f"$-${delta:.2f}" if delta else "--"
        filas.append(f"    \\texttt{{{corpus.replace('_', '-')}}} & {var} & {reg} & "
                     + " & ".join(celdas) + f" & {d} \\\\")
    cuerpo = "\n".join(filas)
    return f"""% GENERADO AUTOMATICAMENTE por research/eval/report/tabla_corpus.py
% No editar a mano.
\\begin{{table}}[h]
\\centering
\\footnotesize
\\setlength{{\\tabcolsep}}{{4pt}}
\\resizebox{{\\textwidth}}{{!}}{{%
\\begin{{tabular}}{{{cols}}}
    \\hline
    {cab} \\\\
    \\hline
{cuerpo}
    \\hline
\\end{{tabular}}}}
\\caption{{WER (\\%) de los modelos Whisper sin adaptar segun corpus, con normalizacion
basica. La columna $\\Delta$ tildes indica cuanto baja el WER de \\texttt{{medium}} al
ignorar la acentuacion: valores altos delatan referencias con tildes omitidas (R11), no
mejor reconocimiento.}}
\\label{{tab:baseline-corpus}}
\\end{{table}}
"""


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--decodificacion", default="fallback", choices=["voraz", "fallback"])
    args = ap.parse_args()

    datos, modelos = cargar(args.decodificacion)
    if not datos:
        raise SystemExit(f"sin resultados '{args.decodificacion}' en {RESULTADOS}")

    md = markdown(datos, modelos)
    print(md)

    DESTINO_MD.mkdir(parents=True, exist_ok=True)
    DESTINO_TEX.mkdir(parents=True, exist_ok=True)
    nombre = f"baseline_corpus_{args.decodificacion}"
    (DESTINO_MD / f"{nombre}.md").write_text(md + "\n", encoding="utf-8")
    (DESTINO_TEX / f"{nombre}.tex").write_text(latex(datos, modelos), encoding="utf-8")
    print(f"\n-> {(DESTINO_MD / f'{nombre}.md').relative_to(RAIZ)}")
    print(f"-> {(DESTINO_TEX / f'{nombre}.tex').relative_to(RAIZ)}")
