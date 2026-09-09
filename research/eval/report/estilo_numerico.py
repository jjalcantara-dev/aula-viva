"""¿Cuanta de la ventaja medida en exp-004 es reconocimiento y cuanta es ortografia?

MOTIVO. El normalizador congelado no equipara "2010" con "dos mil diez". Mientras se
comparan variantes de Whisper da igual, porque comparten convencion de escritura. Al
comparar ARQUITECTURAS entrenadas con transcripciones distintas deja de dar igual: uno
escribe cifras donde la referencia escribe letras y el otro no.

El efecto no es menor y ademas se AMPLIFICA. "dos mil diez" son tres fichas; "2010" es
una. El alineamiento casa una y cuenta las otras dos como omitidas, de modo que una cifra
correctamente reconocida genera TRES errores. En habla parlamentaria, llena de anios e
importes, eso basta para inventar una diferencia que no existe.

QUE HACE. Dos comprobaciones independientes, ninguna de las cuales toca el normalizador
congelado (cambiarlo invalidaria la comparabilidad con todos los experimentos anteriores):

  1. Cuenta fichas con digitos por sistema, para ver quien se desvia del estilo de la
     referencia y cuanto.
  2. Repite el contraste pareado SOLO sobre los clips cuya referencia no contiene ningun
     numeral. Si la ventaja sobrevive ahi, no es un artefacto de escritura.

La segunda es la decisiva: responde a la pregunta sin depender de ningun conversor de
cifras a letras, que seria una pieza nueva con sus propios errores.

Uso:  .venv/bin/python research/eval/report/estilo_numerico.py
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "research"))

from eval.metrics.criticos import categoria  # noqa: E402
from eval.metrics.wer import evaluar  # noqa: E402
from eval.normalizers.basico import basico  # noqa: E402
from eval.stats.pareado import conteo_signos, ic_bootstrap, prueba_signos, veredicto  # noqa: E402

RESULTADOS = RAIZ / "research" / "experiments" / "exp-004-arquitecturas" / "results"
DESTINO_MD = RAIZ / "research" / "results"

_DIGITOS = re.compile(r"\d")

# El modelo base de la comparativa: es el que hace de referencia en los contrastes.
BASE = "openai_whisper-medium"


def cargar() -> dict[str, dict[str, list[dict]]]:
    """{corpus: {sistema: filas}}"""
    por_corpus: dict[str, dict[str, list[dict]]] = defaultdict(dict)
    for f in sorted(RESULTADOS.glob("transcripciones_*.jsonl")):
        # transcripciones_<modelo>__<corpus>__<decodificacion>.jsonl
        partes = f.stem.replace("transcripciones_", "").split("__")
        if len(partes) != 3:
            continue
        modelo, corpus, _ = partes
        por_corpus[corpus][modelo] = [
            json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    return por_corpus


def fichas_con_digitos(texto: str) -> int:
    return sum(1 for p in basico(texto).split() if _DIGITOS.search(p))


def tiene_numeral(texto: str) -> bool:
    return any(categoria(p) == "numeral" for p in basico(texto).split())


def main():
    por_corpus = cargar()
    if not por_corpus:
        raise SystemExit("sin transcripciones de exp-004 todavia")

    lineas = ["# Estilo numérico: ¿cuánta de la ventaja de exp-004 es ortografía?", ""]

    for corpus, sistemas in sorted(por_corpus.items()):
        if BASE not in sistemas:
            continue
        filas_base = sistemas[BASE]
        refs = [x["referencia"] for x in filas_base]

        lineas += [f"## `{corpus}`", "",
                   "### Fichas escritas con dígitos", "",
                   "| Sistema | Referencia | Hipótesis | Desviación |",
                   "|---|---:|---:|---:|"]
        dig_ref = sum(fichas_con_digitos(r) for r in refs)
        for modelo, filas in sorted(sistemas.items()):
            dig_hip = sum(fichas_con_digitos(x["hipotesis"]) for x in filas)
            lineas.append(f"| `{modelo}` | {dig_ref} | {dig_hip} | {dig_hip - dig_ref:+d} |")
        lineas.append("")

        # --- contraste restringido a clips sin numerales en la referencia ---
        indices = [i for i, r in enumerate(refs) if not tiene_numeral(r)]
        lineas += [f"### Contraste sobre los {len(indices)} de {len(refs)} clips "
                   "cuya referencia no contiene numerales", ""]
        if len(indices) < 30:
            lineas += ["> Muestra insuficiente para concluir nada sobre este subconjunto.", ""]
            continue

        refs_n = [basico(refs[i]) for i in indices]
        hip_base = [basico(filas_base[i]["hipotesis"]) for i in indices]
        wer_base = evaluar(refs_n, hip_base).wer * 100

        lineas += ["| Sistema | WER (sin numerales) | Δ (pp) | IC 95% | p | Veredicto |",
                   "|---|---:|---:|---|---:|---|",
                   f"| `{BASE}` | {wer_base:.2f} | — | — | — | referencia |"]

        for modelo, filas in sorted(sistemas.items()):
            if modelo == BASE:
                continue
            hip_b = [basico(filas[i]["hipotesis"]) for i in indices]
            wer_b = evaluar(refs_n, hip_b).wer * 100
            mej, emp, _ = conteo_signos(refs_n, hip_base, hip_b)
            p = prueba_signos(mej, emp)
            ic = ic_bootstrap(refs_n, hip_base, hip_b)
            lineas.append(
                f"| `{modelo}` | {wer_b:.2f} | {wer_b - wer_base:+.2f} | "
                f"[{ic[0] * 100:+.2f}, {ic[1] * 100:+.2f}] | {p:.2g} | {veredicto(ic, p)} |")
        lineas.append("")

    texto = "\n".join(lineas)
    print(texto)
    DESTINO_MD.mkdir(parents=True, exist_ok=True)
    (DESTINO_MD / "estilo_numerico.md").write_text(texto + "\n", encoding="utf-8")
    print(f"\n-> {(DESTINO_MD / 'estilo_numerico.md').relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
