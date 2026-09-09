"""Convencion decimal espanola para las tablas que consume la memoria.

La memoria esta escrita en espanol, donde el separador decimal es la coma. Los generadores
formatean con el punto de Python, asi que el documento mezclaba «se reduce 1,23 puntos» en
la prosa con «1.23» en la tabla de al lado.

Se resuelve al final, sobre el texto ya generado, y no en cada `f-string`: hay del orden de
cuarenta puntos de formateo repartidos por siete generadores, y tocarlos uno a uno invita a
olvidar alguno cuando se anada el siguiente.

Uso:  texto = decimales_es(texto)
"""

import re

# Un punto decimal es el que separa DIGITO de DIGITO y no forma parte de un identificador.
# Las dos guardas son necesarias, y cada una atrapa un caso real de este proyecto:
#
#   (?<![\w.-])  descarta `parakeet-tdt-0.6b-v3`, donde el 0.6 va pegado a un guion, y
#                descarta el `5.1` de una version `2.5.1`, precedido de punto.
#   (?![\w.-])   descarta `cuda12.4-cudnn9`, donde el 12.4 continua en letra o guion.
#
# Quedan convertidos justo los que interesan: celdas numericas y cifras en los pies.
_DECIMAL = re.compile(r"(?<![\w.-])(\d+)\.(\d+)(?![\w.-])")


def decimales_es(texto: str, latex: bool = True) -> str:
    """Sustituye el punto decimal por coma.

    En LaTeX la coma se envuelve en llaves (`1{,}23`). Sin ellas, dentro de modo
    matematico TeX la trata como separador y le anade espacio detras, de modo que la cifra
    sale partida. Fuera de LaTeX (markdown) se usa la coma a secas.
    """
    reemplazo = r"\1{,}\2" if latex else r"\1,\2"
    return _DECIMAL.sub(reemplazo, texto)
