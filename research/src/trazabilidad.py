"""Trazabilidad de resultados experimentales.

Un resultado que no se puede atar al estado exacto del codigo Y de los datos que lo
produjeron no es reproducible, aunque lo parezca.

Incidente que motiva el hash del manifiesto (M0): al ampliar `teleconciencia_es` de 40 a
1200 clips se sobrescribio el manifiesto. Los resultados anteriores seguian apuntando a
`teleconciencia_es.jsonl`, pero ese fichero ya contenia otra cosa. Sin hash, nada delataba
la discrepancia: las cifras viejas parecian perfectamente reproducibles y no lo eran.
"""

import hashlib
import subprocess
from pathlib import Path


def commit_actual(raiz: Path) -> str:
    """Hash corto del commit, o 'sin-git' si no hay repositorio."""
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=raiz, text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "sin-git"


def hay_cambios_sin_confirmar(raiz: Path) -> bool:
    """True si el arbol de trabajo esta sucio.

    Un resultado producido con cambios sin confirmar no se puede reconstruir desde el
    commit que dice haber usado. Conviene registrarlo junto al resultado.
    """
    try:
        salida = subprocess.check_output(["git", "status", "--porcelain"], cwd=raiz,
                                         text=True, stderr=subprocess.DEVNULL)
        return bool(salida.strip())
    except Exception:
        return False


def hash_fichero(ruta: Path, n: int = 12) -> str:
    """SHA-256 truncado del contenido. Identifica la version exacta de un manifiesto."""
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()[:n]


def hash_lineas(lineas: list[str], n: int = 12) -> str:
    """SHA-256 truncado de un conjunto concreto de lineas del manifiesto.

    Hace falta porque un experimento puede evaluar solo las primeras N: en ese caso el
    hash del FICHERO identifica un superconjunto de lo medido, no lo medido.
    """
    h = hashlib.sha256()
    for l in lineas:
        h.update(l.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()[:n]


def sufijo_muestra(manifiesto: Path, clips_evaluados: int | None) -> str:
    """Trozo de nombre que declara la submuestra, o cadena vacia si no la hay.

    La regla que este proyecto pago con dos incidentes: cualquier eje de variacion tiene
    que entrar en la IDENTIDAD del resultado, y el tamano de la muestra es uno. Omitirlo
    no da error, da una comparacion invalida con aspecto de tabla.

    Lo ideal sigue siendo que la submuestra tenga su propio manifiesto (como
    `voxpopuli_es_400`); esto cubre el caso en que se use `--limite` de todos modos.
    """
    if not clips_evaluados:
        return ""
    total = _lineas(manifiesto)
    return "" if clips_evaluados >= len(total) else f"__n{clips_evaluados}"


def _lineas(manifiesto: Path) -> list[str]:
    return [l for l in manifiesto.read_text(encoding="utf-8").splitlines() if l.strip()]


def procedencia(raiz: Path, manifiesto: Path, clips_evaluados: int | None = None) -> dict:
    """Bloque de procedencia listo para volcar en el JSON de resultados.

    `clips_evaluados` no es opcional por comodidad: cuando el experimento evalua solo una
    parte del manifiesto, el hash del fichero describe material que no se ha medido. En
    ese caso se registra ademas el hash de la submuestra efectiva, que es lo que de verdad
    identifica al resultado.
    """
    lineas = _lineas(manifiesto)
    bloque = {
        "commit": commit_actual(raiz),
        "arbol_sucio": hay_cambios_sin_confirmar(raiz),
        "manifiesto": str(manifiesto),
        "manifiesto_sha256": hash_fichero(manifiesto),
        "manifiesto_lineas": len(lineas),
    }
    if clips_evaluados is not None and clips_evaluados < len(lineas):
        bloque["clips_evaluados"] = clips_evaluados
        bloque["submuestra_sha256"] = hash_lineas(lineas[:clips_evaluados])
        bloque["aviso"] = (
            "Submuestra: manifiesto_sha256 identifica el fichero completo, no lo medido. "
            "Comparar solo contra resultados con el mismo submuestra_sha256, o generar un "
            "manifiesto propio para esta muestra.")
    return bloque
