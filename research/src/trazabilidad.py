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


def procedencia(raiz: Path, manifiesto: Path) -> dict:
    """Bloque de procedencia listo para volcar en el JSON de resultados."""
    return {
        "commit": commit_actual(raiz),
        "arbol_sucio": hay_cambios_sin_confirmar(raiz),
        "manifiesto": str(manifiesto),
        "manifiesto_sha256": hash_fichero(manifiesto),
        "manifiesto_lineas": sum(1 for l in manifiesto.read_text(encoding="utf-8").splitlines() if l.strip()),
    }
