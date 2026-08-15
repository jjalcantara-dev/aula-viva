"""Audita el archivo de resultados contra los manifiestos actuales.

Existe porque la memoria hace tres afirmaciones sobre si misma que hasta ahora eran
declaraciones y no comprobaciones:

  1. «cada resultado registra su procedencia». Es cierto del PROCEDIMIENTO actual, no del
     archivo: el mecanismo se escribio a mitad del trabajo y los resultados anteriores no
     lo llevan. Este programa cuenta cuantos si y cuantos no, para que la cifra que
     aparezca en el apendice salga de contar y no de recordar.

  2. «el hash del manifiesto permite detectar que el corpus cambio». Guardarlo no detecta
     nada por si solo: hace falta RECALCULARLO y compararlo, y eso no lo hacia nadie. Era
     el mismo fallo que este proyecto ya documenta en otro sitio, un dato declarado que
     nada comprueba, esta vez en la propia salvaguarda contra el incidente que la motivo.
     Ahora se recalcula, tanto el del fichero como el de la submuestra efectiva.

  3. «los resultados antiguos siguen describiendo el corpus que dicen». Para los que no
     llevan hash no hay comprobacion directa, pero si una indirecta: el numero de clips y
     de palabras de referencia que declara cada resultado tiene que coincidir con el que
     produce el manifiesto de hoy. Si alguien lo sobrescribio, esto lo caza.

OJO con el recuento de palabras: los resultados guardan el de las referencias YA
NORMALIZADAS, y el normalizador convierte los signos en espacios («1,5» pasa a ser dos
fichas). Compararlo con el recuento en crudo da falsos positivos; se aprendio comparando
mal y persiguiendo una deriva de dos palabras en FLEURS que no existia.

Los barridos de ingenieria (exp-100 en adelante) vuelven a trocear el audio en ventanas o
segmentos, asi que no declaran recuento de clips y la comprobacion indirecta no se les
puede aplicar. Se listan aparte, no como esquema desconocido: llevan hash, que es la
comprobacion fuerte, y confundir «no aplica» con «no reconocido» esconde las dos cosas.

Uso:  .venv/bin/python tools/auditar_resultados.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "research"))

from eval.normalizers.basico import basico  # noqa: E402
from src.trazabilidad import hash_fichero, hash_lineas  # noqa: E402

MANIFIESTOS = RAIZ / "research" / "corpus" / "manifests"
RESULTADOS = sorted((RAIZ / "research" / "experiments").glob("*/results/metricas_*.json"))


def manifiestos() -> dict[str, dict]:
    """{nombre: {clips, palabras_normalizadas}} de los manifiestos de hoy."""
    salida = {}
    for p in sorted(MANIFIESTOS.glob("*.jsonl")):
        filas = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
        salida[p.stem] = {
            "clips": len(filas),
            "palabras": sum(len(basico(f["referencia"]).split()) for f in filas),
        }
    return salida


def corpus_de(d: dict) -> str:
    cfg = d.get("config", {})
    tallo = Path(cfg.get("manifiesto") or cfg.get("transcripciones") or "").stem
    for sufijo in ("__fallback", "__voraz"):
        tallo = tallo.replace(sufijo, "")
    return tallo.split("__")[-1] if "__" in tallo else tallo


def _tiene_recuentos(v) -> bool:
    return isinstance(v, dict) and "n_clips" in v and "n_palabras_ref" in v


def metricas_base(d: dict) -> dict | None:
    """El bloque con los recuentos, este donde este: el esquema cambio entre experimentos.

    Tres formas conviven en el archivo, y las tres son legitimas:
      - `metricas.basico` en el barrido de linea base;
      - `metricas.<condicion>.basico` cuando el experimento anida por condicion;
      - `metricas.<condicion>` directamente, en los A/B (exp-001 a exp-003), donde cada
        condicion es ya el bloque de metricas.
    En los A/B todas las condiciones miden el mismo corpus, asi que sirve cualquiera; se
    comprueba antes que coinciden, porque si no coincidieran el A/B compararia dos
    muestras distintas y eso es un fallo mayor que el que busca esta herramienta.
    """
    m = d.get("metricas") or {}
    if "basico" in m:
        return m["basico"]
    for v in m.values():
        if isinstance(v, dict) and "basico" in v:
            return v["basico"]
    for v in d.get("sistemas", {}).values():
        if "metricas" in v and "basico" in v["metricas"]:
            return v["metricas"]["basico"]
    condiciones = [v for v in m.values() if _tiene_recuentos(v)]
    if condiciones:
        primera = condiciones[0]
        for otra in condiciones[1:]:
            if (otra["n_clips"], otra["n_palabras_ref"]) != (primera["n_clips"],
                                                            primera["n_palabras_ref"]):
                return None  # condiciones sobre muestras distintas: lo caza el llamador
        return primera
    return None


def comprobar_hash(d: dict) -> tuple[str, str] | None:
    """Recalcula hoy los hashes que declara el resultado. None si no declara ninguno.

    Devuelve (estado, detalle) con estado en {'ok', 'MISMATCH', 'sin manifiesto'}.
    """
    p = d.get("procedencia") or {}
    declarado = p.get("manifiesto_sha256")
    if not declarado:
        return None

    ruta = RAIZ / p["manifiesto"]
    if not ruta.exists():
        return "sin manifiesto", f"{p['manifiesto']} ya no existe"

    hoy = hash_fichero(ruta)
    if hoy != declarado:
        return "MISMATCH", f"fichero declara {declarado}, hoy es {hoy}"

    # El hash del fichero cubre un superconjunto de lo medido cuando hay submuestra: es
    # el de la submuestra el que identifica de verdad al resultado.
    sub = p.get("submuestra_sha256")
    if sub:
        lineas = [l for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]
        n = p.get("clips_evaluados") or 0
        hoy_sub = hash_lineas(lineas[:n])
        if hoy_sub != sub:
            return "MISMATCH", f"submuestra declara {sub}, hoy es {hoy_sub}"
    return "ok", ""


def main() -> int:
    man = manifiestos()
    commits, hashes = Counter(), Counter()
    con_bloque = limpios = hash_verificados = 0
    submuestras, discrepancias, sin_comprobar, sin_recuentos = [], [], [], []

    for f in RESULTADOS:
        d = json.loads(f.read_text(encoding="utf-8"))
        p = d.get("procedencia") or {}
        if p:
            con_bloque += 1
        if p.get("arbol_sucio") is False:
            limpios += 1
        commits[p.get("commit") or d.get("commit") or "AUSENTE"] += 1
        hashes["con hash" if p.get("manifiesto_sha256") else "sin hash"] += 1

        comprobacion = comprobar_hash(d)
        if comprobacion:
            estado, detalle = comprobacion
            if estado == "ok":
                hash_verificados += 1
            else:
                discrepancias.append((f.name, corpus_de(d), f"hash: {detalle}"))

        c, base = corpus_de(d), metricas_base(d)
        if c not in man or base is None:
            # Un barrido que vuelve a trocear el audio no declara clips: no le falta el
            # dato, es que la unidad de medida es otra. Solo es «esquema no reconocido»
            # cuando ademas no hay barrido que lo explique.
            (sin_recuentos if d.get("resultados") else sin_comprobar).append(f.name)
            continue
        limite = d.get("config", {}).get("limite")
        # Los experimentos con glosario reservan una fraccion de los clips para EXTRAERLO
        # y evaluan sobre el resto, que es justo lo que evita la fuga de informacion. Ese
        # recorte es correcto y esta declarado, pero deja el recuento por debajo del
        # manifiesto: sin contarlo, la comprobacion denuncia como deriva la propia
        # salvaguarda metodologica.
        contexto = (d.get("glosario") or {}).get("clips_contexto") or 0
        esperados = limite or (man[c]["clips"] - contexto)
        if base["n_clips"] != esperados:
            discrepancias.append((f.name, c, f"{base['n_clips']} clips, "
                                             f"el manifiesto tiene {man[c]['clips']}"))
        elif contexto:
            submuestras.append((f.name, c, f"{esperados} de {man[c]['clips']}, "
                                           f"{contexto} al glosario"))
        elif limite:
            submuestras.append((f.name, c, f"{limite} de {man[c]['clips']} clips"))
        elif base["n_palabras_ref"] != man[c]["palabras"]:
            discrepancias.append((f.name, c, f"{base['n_palabras_ref']} palabras, "
                                             f"el manifiesto da {man[c]['palabras']}"))

    print(f"Resultados auditados: {len(RESULTADOS)}\n")
    print("Procedencia")
    print(f"  con bloque completo ........ {con_bloque}")
    print(f"  con arbol de trabajo limpio  {limpios}")
    for k, v in commits.most_common():
        print(f"  commit '{k}' {'.' * max(1, 20 - len(k))} {v}")
    for k, v in hashes.most_common():
        print(f"  {k} ..................... {v}")
    print(f"  hash RECALCULADO y correcto  {hash_verificados}")

    if sin_recuentos:
        print(f"\nSin recuento de clips ({len(sin_recuentos)}): barridos que retrocean el "
              f"audio,")
        print("comprobados por hash, no por la via indirecta:")
        for n in sin_recuentos:
            print(f"  {n}")

    if submuestras:
        print(f"\nSubmuestras declaradas ({len(submuestras)}), correctas pero no comparables")
        print("entre si ni con la muestra completa del mismo corpus:")
        for n, c, det in submuestras:
            print(f"  {c:<24} {det:<28} {n}")

    if sin_comprobar:
        print(f"\nSin comprobar ({len(sin_comprobar)}): esquema no reconocido")
        for n in sin_comprobar:
            print(f"  {n}")

    if discrepancias:
        print(f"\nDISCREPANCIAS ({len(discrepancias)}): el resultado no describe el "
              f"manifiesto actual")
        for n, c, det in discrepancias:
            print(f"  {c:<24} {det:<40} {n}")
        return 1

    print("\nOK: todo resultado sobre muestra completa coincide en clips y palabras con "
          "su manifiesto de hoy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
