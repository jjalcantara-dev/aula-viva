"""Deteccion de salidas anomalas: truncamiento y expansion (alucinacion).

El WER agregado esconde el peor modo de fallo de un sistema de subtitulado. Un clip
truncado y un clip con veinte errores repartidos pueden dar el mismo WER, pero no son
equivalentes para un alumno con discapacidad auditiva:

  - Truncamiento: falta informacion. Se nota, y el alumno sabe que se ha perdido algo.
  - Alucinacion : el modelo emite texto fluido y plausible pero falso. NO se nota.
    Es el fallo peligroso, porque nadie puede detectarlo desde el subtitulo.

Medido en M0: `large-v3-turbo` con decodificacion voraz emitio "Gracias, senora
presidenta." en tres clips distintos de voxpopuli_es, en lugar del contenido real.

Esta metrica es una aproximacion barata basada en la longitud relativa. No detecta una
alucinacion de longitud parecida a la referencia; para eso hace falta inspeccion manual
o una metrica semantica. Sirve como criba, no como veredicto.

Uso:  .venv/bin/python research/eval/report/anomalias.py [--decodificacion fallback]
"""

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
RESULTADOS = RAIZ / "research" / "experiments" / "exp-000-baseline" / "results"
DESTINO_MD = RAIZ / "research" / "results"

UMBRAL_TRUNCADO = 0.5    # menos de la mitad de palabras que la referencia
UMBRAL_GRAVE = 0.25      # menos de un cuarto: practicamente sin contenido
UMBRAL_EXPANDIDO = 2.0   # mas del doble: repeticion o texto inventado


def analizar(ruta: Path) -> dict:
    filas = [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]
    ratios, truncados, graves, expandidos, ejemplos = [], 0, 0, 0, []

    for f in filas:
        n_ref = len(f["referencia"].split())
        n_hip = len(f["hipotesis"].split())
        if n_ref == 0:
            continue
        r = n_hip / n_ref
        ratios.append(r)
        if r < UMBRAL_TRUNCADO:
            truncados += 1
            if r < UMBRAL_GRAVE:
                graves += 1
                if len(ejemplos) < 3:
                    ejemplos.append((f["id"], f["hipotesis"][:60]))
        elif r > UMBRAL_EXPANDIDO:
            expandidos += 1

    ratios.sort()
    return {
        "n": len(ratios),
        "truncados": truncados,
        "graves": graves,
        "expandidos": expandidos,
        "ratio_mediano": ratios[len(ratios) // 2] if ratios else 0.0,
        "ejemplos": ejemplos,
    }


def etiquetar(nombre: str) -> tuple[str, str, str]:
    """transcripciones_<modelo>__<corpus>__<decod>.jsonl -> (modelo, corpus, decod)"""
    partes = nombre.removeprefix("transcripciones_").removesuffix(".jsonl").split("__")
    modelo = partes[0].split("_")[-1] if partes else "?"
    return modelo, (partes[1] if len(partes) > 1 else "?"), (partes[2] if len(partes) > 2 else "?")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--decodificacion", default=None,
                    help="filtrar por decodificacion; omitir para ver todas y comparar")
    args = ap.parse_args()

    patron = (f"transcripciones_*__{args.decodificacion}.jsonl"
              if args.decodificacion else "transcripciones_*.jsonl")
    ficheros = sorted(RESULTADOS.glob(patron))
    if not ficheros:
        raise SystemExit(f"sin transcripciones que analizar en {RESULTADOS}")

    L = ["| Modelo | Corpus | Decod. | Clips | Truncados | Graves | Expandidos | Ratio med. |",
         "|---|---|---|---:|---:|---:|---:|---:|"]
    avisos = []
    for f in ficheros:
        modelo, corpus, decod = etiquetar(f.name)
        a = analizar(f)
        marca = " ⚠️" if a["graves"] else ""
        L.append(f"| `{modelo}` | `{corpus}` | {decod} | {a['n']} | "
                 f"{a['truncados']} | **{a['graves']}**{marca} | {a['expandidos']} | "
                 f"{a['ratio_mediano']:.2f} |")
        for uid, texto in a["ejemplos"]:
            avisos.append(f"- `{modelo}`/`{corpus}`/{decod} — {uid}: «{texto}»")

    md = "\n".join(L)
    if avisos:
        md += ("\n\n## Salidas gravemente truncadas\n\n"
               "Menos de un cuarto de las palabras de la referencia. Revisar a mano: "
               "una salida corta **y fluida** es una alucinación, no un truncamiento.\n\n"
               + "\n".join(avisos) + "\n")

    print(md)
    DESTINO_MD.mkdir(parents=True, exist_ok=True)
    nombre = f"anomalias_{args.decodificacion or 'todas'}.md"
    (DESTINO_MD / nombre).write_text(md + "\n", encoding="utf-8")
    print(f"\n-> {(DESTINO_MD / nombre).relative_to(RAIZ)}")
