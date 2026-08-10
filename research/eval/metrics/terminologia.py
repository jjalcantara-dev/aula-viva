"""Acierto sobre terminologia del dominio.

Por que hace falta, ademas del WER: si un sistema corrige cinco terminos tecnicos en mil
palabras, el WER global se mueve 0.5 puntos y queda enterrado bajo el ruido. Pero para un
alumno con discapacidad auditiva esos cinco terminos son justamente el contenido de la
clase; el resto es relleno sintactico que puede reconstruir por contexto.

Dicho de otro modo: el WER trata "de" y "mitocondria" como un error cada uno. El alumno no.

Esta metrica mide, sobre una lista de terminos del dominio:

  cobertura : de las veces que un termino APARECE en la referencia, cuantas reproduce
              el sistema. Es lo que importa: terminologia perdida.
  precision : de las veces que el sistema ESCRIBE un termino, cuantas eran correctas.
              Detecta el efecto adverso del prompting -- que el modelo empiece a colar
              terminos del glosario donde no los hay.

Ambas se calculan por conteo de ocurrencias, no por presencia/ausencia: un termino que
aparece cuatro veces en la referencia y una en la hipotesis esta reproducido al 25%.
"""

from collections import Counter
from dataclasses import asdict, dataclass


@dataclass
class ResultadoTerminologia:
    cobertura: float
    precision: float
    f1: float
    ocurrencias_referencia: int
    ocurrencias_hipotesis: int
    aciertos: int
    n_terminos: int
    terminos_perdidos: list[tuple[str, int, int]]  # (termino, en_ref, en_hip)

    def como_dict(self):
        return asdict(self)

    def __str__(self):
        return (f"cobertura={self.cobertura:6.2%}  precision={self.precision:6.2%}  "
                f"F1={self.f1:6.2%}  ({self.aciertos}/{self.ocurrencias_referencia} "
                f"ocurrencias de {self.n_terminos} terminos)")


def _contar(textos: list[str], terminos: set[str]) -> Counter:
    """Ocurrencias de cada termino. Los textos deben venir ya normalizados."""
    c: Counter[str] = Counter()
    for t in textos:
        palabras = t.split()
        for p in palabras:
            if p in terminos:
                c[p] += 1
    return c


def evaluar(referencias: list[str], hipotesis: list[str],
            terminos: list[str], top_perdidos: int = 15) -> ResultadoTerminologia:
    """Cobertura y precision sobre `terminos`.

    Los textos deben estar normalizados con el mismo normalizador que el WER, y los
    terminos tambien: comparar 'Mitocondria' con 'mitocondria' daria cero acierto.

    Limitacion conocida: solo cuenta terminos de una palabra. Los terminos compuestos
    ("energia de activacion") requieren busqueda por n-gramas; queda pendiente si el
    dominio final lo exige.
    """
    conjunto = {t for t in terminos if " " not in t}
    c_ref = _contar(referencias, conjunto)
    c_hip = _contar(hipotesis, conjunto)

    total_ref = sum(c_ref.values())
    total_hip = sum(c_hip.values())
    # Aciertos = solapamiento de multiconjuntos: no se puede acertar mas veces de las
    # que el termino aparece realmente.
    aciertos = sum(min(c_ref[t], c_hip[t]) for t in conjunto)

    cobertura = aciertos / total_ref if total_ref else 0.0
    precision = aciertos / total_hip if total_hip else 0.0
    f1 = (2 * cobertura * precision / (cobertura + precision)
          if (cobertura + precision) else 0.0)

    perdidos = sorted(((t, c_ref[t], c_hip[t]) for t in conjunto if c_ref[t] > c_hip[t]),
                      key=lambda x: -(x[1] - x[2]))[:top_perdidos]

    return ResultadoTerminologia(
        cobertura=cobertura, precision=precision, f1=f1,
        ocurrencias_referencia=total_ref, ocurrencias_hipotesis=total_hip,
        aciertos=aciertos, n_terminos=len(conjunto), terminos_perdidos=perdidos)
