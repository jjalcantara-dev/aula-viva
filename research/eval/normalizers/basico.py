"""Normalizacion de texto previa al calculo de WER/CER.

IMPORTANTE (hito H2 del PLANNING): este modulo se CONGELA antes de ejecutar la
comparativa. Cambiarlo a mitad invalida la comparabilidad entre experimentos,
porque el WER medido depende tanto del modelo como de como se normaliza.

Toda decision de normalizacion debe quedar justificada en la memoria: cada regla
perdona una clase de error, y perdonar de mas oculta diferencias entre tecnicas.
"""

import re
import unicodedata

# Se conservan tildes y enies: en espanol son informacion lexica real
# ("papa"/"papa" con tilde, "ano"/"anio"), no ruido ortografico.
_PUNTUACION = re.compile(r"[^\w\s]", re.UNICODE)
_ESPACIOS = re.compile(r"\s+")

_ENIE_MIN = "ñ"
_ENIE_MAY = "Ñ"
_CENTINELA = "\x00"


def basico(texto: str) -> str:
    """Normalizacion minima y defendible.

    Perdona: mayusculas, puntuacion, espaciado, forma unicode.
    NO perdona: tildes, numeros en digitos vs. letras, abreviaturas.
    """
    texto = unicodedata.normalize("NFC", texto)
    texto = texto.lower()
    texto = _PUNTUACION.sub(" ", texto)
    return _ESPACIOS.sub(" ", texto).strip()


def sin_tildes(texto: str) -> str:
    """Variante mas permisiva: quita tildes pero PRESERVA la enie.

    Solo para analisis de sensibilidad (que parte del WER se debe a tildes).
    No usar como metrica principal.
    """
    t = basico(texto).replace(_ENIE_MIN, _CENTINELA).replace(_ENIE_MAY, _CENTINELA)
    desc = unicodedata.normalize("NFD", t)
    sin = "".join(c for c in desc if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFC", sin).replace(_CENTINELA, _ENIE_MIN)


NORMALIZADORES = {"crudo": lambda t: t, "basico": basico, "sin_tildes": sin_tildes}
