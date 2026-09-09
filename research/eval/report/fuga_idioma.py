"""Deteccion de fuga de idioma: el sistema TRADUCE en lugar de transcribir.

POR QUE HACE FALTA. anomalias.py detecta salidas anomalas por su LONGITUD (truncamiento y
expansion). Una frase traducida al ingles tiene longitud normal, asi que le pasa por
delante sin activarla. Es un punto ciego, y resulto no ser teorico: al contrastar
arquitecturas en exp-004, el transductor multilingue devolvio "Hello, what are you talking
about?" ante habla espanola espontanea.

POR QUE IMPORTA MAS QUE EL WER. Para accesibilidad es el peor fallo posible, y el mismo
que descarto a large-v3-turbo en docs/decisiones/002-modelo-base.md: la salida es fluida y
verosimil, de modo que el alumno sordo no tiene forma de saber que no corresponde a lo
dicho. Un subtitulo ausente se nota; uno traducido, no.

COMO LO MIDE. Cuenta palabras funcionales inglesas de alta frecuencia que NO son palabras
espanolas. Se evitan deliberadamente las ambiguas ("no", "a", "he", "son", "van", "sin",
"me", "mi", "un", "en", "de", "la", "el", "y", "o", "ser", "es"), que existen en ambos
idiomas y produciran falsos positivos.

Es una heuristica de superficie, no un identificador de idioma: basta para contar casos y
sacarlos a la luz, que es lo que hace falta para decidir entre modelos. No pretende ser
exacta y no debe presentarse como tal.

Uso:  .venv/bin/python research/eval/report/fuga_idioma.py [--directorio ruta]
"""

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "research"))

from eval.normalizers.basico import basico  # noqa: E402

DESTINO_MD = RAIZ / "research" / "results"
POR_DEFECTO = RAIZ / "research" / "experiments" / "exp-004-arquitecturas" / "results"

#: Funcionales inglesas frecuentes SIN homografo espanol. La lista es corta a proposito:
#: prefiero pasar por alto alguna fuga que inflar el recuento con falsos positivos.
INGLESAS = frozenset("""
the and of is are was were been being have has had will would should could
what when where which who whom whose why how that this these those they them their
you your yours we our ours it its he's she's i'm don't doesn't didn't isn't aren't
about because before after through during between into onto from than then there
very much many more most other another something anything everything nothing
going talking speaking looking making taking getting doing saying thinking
with without within also although however therefore though while
""".split())

#: A partir de dos coincidencias se considera fuga. Con una sola, un anglicismo suelto o
#: un nombre propio bastarian para marcar un clip correcto.
MINIMO_COINCIDENCIAS = 2


def coincidencias(texto: str) -> list[str]:
    return [p for p in basico(texto).split() if p in INGLESAS]


def analizar(ruta: Path) -> dict:
    filas = [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]
    fugas, vacias, ejemplos = 0, 0, []

    for fila in filas:
        hip = fila["hipotesis"].strip()
        if not hip:
            vacias += 1
            if len(ejemplos) < 8:
                ejemplos.append(f"[{fila['id']}] (salida vacía) ← «{fila['referencia'][:60]}…»")
            continue

        marcas = coincidencias(hip)
        # Se exige ademas que la referencia NO las tenga: si el hablante dijo esas
        # palabras, transcribirlas es correcto y no es fuga.
        if len(marcas) >= MINIMO_COINCIDENCIAS and not coincidencias(fila["referencia"]):
            fugas += 1
            if len(ejemplos) < 8:
                ejemplos.append(f"[{fila['id']}] «{hip[:70]}…» ({', '.join(marcas[:4])})")

    return {"clips": len(filas), "fugas": fugas, "vacias": vacias, "ejemplos": ejemplos}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--directorio", type=Path, default=POR_DEFECTO)
    args = ap.parse_args()

    ficheros = sorted(args.directorio.glob("transcripciones_*.jsonl"))
    if not ficheros:
        raise SystemExit(f"sin transcripciones en {args.directorio}")

    L = ["# Fuga de idioma y salidas vacías", "",
         "Casos en que el sistema traduce en lugar de transcribir, o no devuelve nada.",
         "El detector de anomalías por longitud no ve los primeros: una frase traducida",
         "tiene longitud normal.", "",
         "| Sistema | Clips | Fuga de idioma | Vacías |", "|---|---:|---:|---:|"]

    detalles = []
    for f in ficheros:
        a = analizar(f)
        etiqueta = f.stem.replace("transcripciones_", "")
        marca = " ⚠️" if a["fugas"] or a["vacias"] else ""
        L.append(f"| `{etiqueta}` | {a['clips']} | **{a['fugas']}**{marca} | {a['vacias']} |")
        if a["ejemplos"]:
            detalles += [f"", f"### `{etiqueta}`", ""] + [f"- {e}" for e in a["ejemplos"]]

    L += detalles
    texto = "\n".join(L)
    print(texto)
    DESTINO_MD.mkdir(parents=True, exist_ok=True)
    (DESTINO_MD / "fuga_idioma.md").write_text(texto + "\n", encoding="utf-8")
    print(f"\n-> {(DESTINO_MD / 'fuga_idioma.md').relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
