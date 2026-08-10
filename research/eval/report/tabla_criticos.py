"""Errores criticos por modelo y corpus: lo que el WER agregado no deja ver.

Recorre las transcripciones ya generadas y calcula la tasa de error sobre negaciones,
numerales y cuantificadores. Sirve para responder a la pregunta que de verdad importa en
accesibilidad: no "cuantas palabras falla" sino "cuanto del SENTIDO sobrevive".

Uso:  .venv/bin/python research/eval/report/tabla_criticos.py --decodificacion fallback
"""

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "research"))

from eval.metrics.criticos import evaluar  # noqa: E402
from eval.metrics.wer import evaluar as evaluar_wer  # noqa: E402
from eval.normalizers.basico import basico  # noqa: E402

RESULTADOS = RAIZ / "research" / "experiments" / "exp-000-baseline" / "results"
DESTINO_MD = RAIZ / "research" / "results"
DESTINO_TEX = RAIZ / "memoria" / "tablas"


def etiquetar(nombre: str) -> tuple[str, str]:
    partes = nombre.removeprefix("transcripciones_").removesuffix(".jsonl").split("__")
    return partes[0].split("_")[-1], (partes[1] if len(partes) > 1 else "?")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--decodificacion", default="fallback", choices=["voraz", "fallback"])
    args = ap.parse_args()

    ficheros = sorted(RESULTADOS.glob(f"transcripciones_*__{args.decodificacion}.jsonl"))
    if not ficheros:
        raise SystemExit(f"sin transcripciones '{args.decodificacion}' en {RESULTADOS}")

    L = ["| Modelo | Corpus | WER | **Error crítico** | Negaciones | Numerales | Cuantif. |",
         "|---|---|---:|---:|---:|---:|---:|"]
    avisos: list[str] = []

    for f in ficheros:
        modelo, corpus = etiquetar(f.name)
        filas = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        refs = [basico(x["referencia"]) for x in filas]
        hips = [basico(x["hipotesis"]) for x in filas]

        wer = evaluar_wer(refs, hips).wer
        r = evaluar(refs, hips)

        def celda(cat):
            d = r.por_categoria.get(cat)
            return f"{d['errores']}/{d['total']}" if d and d["total"] else "—"

        L.append(f"| `{modelo}` | `{corpus}` | {wer:.2%} | **{r.tasa_error:.2%}** | "
                 f"{celda('negacion')} | {celda('numeral')} | {celda('cuantificador')} |")

        neg = r.por_categoria.get("negacion", {})
        if neg.get("inventados"):
            avisos.append(f"- `{modelo}`/`{corpus}`: **{neg['inventados']} negaciones "
                          f"inventadas** (el sistema niega algo que no se negó)")

    md = "\n".join(L)
    md += ("\n\n> **Error crítico**: proporción de negaciones, numerales y cuantificadores "
           "de la referencia que el sistema no reproduce correctamente. Un error aquí "
           "cambia el sentido; un error de WER corriente suele reconstruirse por contexto.\n")
    if avisos:
        md += "\n### Negaciones inventadas\n\nEl fallo más grave posible: el sistema " \
              "introduce una negación que nadie dijo, invirtiendo la afirmación.\n\n" \
              + "\n".join(avisos) + "\n"

    print(md)
    DESTINO_MD.mkdir(parents=True, exist_ok=True)
    (DESTINO_MD / f"criticos_{args.decodificacion}.md").write_text(md + "\n", encoding="utf-8")
    print(f"\n-> {(DESTINO_MD / f'criticos_{args.decodificacion}.md').relative_to(RAIZ)}")
