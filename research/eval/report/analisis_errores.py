"""Analisis cualitativo de errores: NO cuantos falla, sino QUE tipo de cosa falla.

Un WER agregado no distingue entre confundir "de" por "del" y destrozar un termino
tecnico. Para un sistema de accesibilidad esa diferencia lo es todo: el alumno tolera
una preposicion mal, no tolera que el concepto clave de la clase salga mal escrito.

Esta clasificacion es la que justifica en la memoria por que hace falta adaptacion al
dominio, y sobre que clase de error se espera que actue cada tecnica.

Uso:
  .venv/bin/python research/eval/report/analisis_errores.py \
      --transcripciones research/experiments/exp-000-baseline/results/transcripciones_openai_whisper-medium.jsonl
"""

import argparse
import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import jiwer

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "research"))

from eval.normalizers.basico import basico, sin_tildes  # noqa: E402

NUMEROS_PALABRA = {
    "cero", "un", "uno", "una", "dos", "tres", "cuatro", "cinco", "seis", "siete",
    "ocho", "nueve", "diez", "once", "doce", "trece", "catorce", "quince", "dieciseis",
    "diecisiete", "dieciocho", "diecinueve", "veinte", "treinta", "cuarenta",
    "cincuenta", "sesenta", "setenta", "ochenta", "noventa", "cien", "ciento",
    "mil", "millon", "millones", "primero", "segundo", "tercero",
}


def _sin_marcas(t: str) -> str:
    d = unicodedata.normalize("NFD", t)
    return "".join(c for c in d if unicodedata.category(c) != "Mn")


def clasificar(ref: str, hip: str) -> str:
    """Categoria de una sustitucion. El orden importa: se aplica la primera que encaja."""
    if sin_tildes(ref) == sin_tildes(hip):
        return "solo tildes"
    if any(c.isdigit() for c in ref + hip) or \
       (_sin_marcas(ref) in NUMEROS_PALABRA or _sin_marcas(hip) in NUMEROS_PALABRA):
        return "numerales (cifra vs. letra)"
    if len(ref) <= 3 and len(hip) <= 3:
        return "palabra funcional corta"
    if _sin_marcas(ref)[:4] == _sin_marcas(hip)[:4]:
        return "variante morfologica"
    return "lexico / termino"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcripciones", type=Path, required=True)
    ap.add_argument("--top", type=int, default=15, help="ejemplos a listar por categoria")
    args = ap.parse_args()

    filas = [json.loads(l) for l in args.transcripciones.read_text(encoding="utf-8").splitlines() if l.strip()]
    refs = [basico(f["referencia"]) for f in filas]
    hips = [basico(f["hipotesis"]) for f in filas]

    salida = jiwer.process_words(refs, hips)

    categorias = Counter()
    ejemplos: dict[str, list[str]] = {}
    n_borrados = n_insertados = 0

    for frase_ref, frase_hip, trozos in zip(salida.references, salida.hypotheses, salida.alignments):
        for t in trozos:
            if t.type == "substitute":
                for r, h in zip(frase_ref[t.ref_start_idx:t.ref_end_idx],
                                frase_hip[t.hyp_start_idx:t.hyp_end_idx]):
                    cat = clasificar(r, h)
                    categorias[cat] += 1
                    ejemplos.setdefault(cat, []).append(f"{r!r} -> {h!r}")
            elif t.type == "delete":
                n_borrados += t.ref_end_idx - t.ref_start_idx
            elif t.type == "insert":
                n_insertados += t.hyp_end_idx - t.hyp_start_idx

    total_sust = sum(categorias.values())
    print(f"fichero : {args.transcripciones.name}")
    print(f"clips   : {len(filas)}   palabras de referencia: {sum(len(r) for r in salida.references)}")
    print(f"WER     : {salida.wer:.2%}\n")
    print(f"{'categoria':<32} {'n':>4}  {'% de sustituciones':>18}")
    print("-" * 60)
    for cat, n in categorias.most_common():
        print(f"{cat:<32} {n:>4}  {n / total_sust:>17.1%}")
    print("-" * 60)
    print(f"{'TOTAL sustituciones':<32} {total_sust:>4}")
    print(f"{'borrados (omitidos)':<32} {n_borrados:>4}")
    print(f"{'insertados (inventados)':<32} {n_insertados:>4}")

    print("\n\nEJEMPLOS POR CATEGORIA")
    for cat, _ in categorias.most_common():
        print(f"\n--- {cat} ---")
        for e in ejemplos[cat][:args.top]:
            print(f"    {e}")


if __name__ == "__main__":
    main()
