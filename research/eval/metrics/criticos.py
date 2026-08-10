"""Errores que cambian el SIGNIFICADO, no solo la forma.

El WER trata todos los errores por igual: confundir "de" por "del" cuenta lo mismo que
perder una negacion. Para un alumno con discapacidad auditiva no es lo mismo en absoluto.
Leer "el examen no es el martes" cuando el profesor dijo "el examen es el martes" no es
un error de transcripcion: es informacion falsa que el alumno no puede detectar.

Se miden tres categorias, elegidas porque un fallo en ellas invierte o destruye el
contenido en lugar de degradarlo:

  NEGACION   : "no", "nunca", "ningun"... Perder o anadir una invierte el sentido.
  NUMEROS    : fechas, cantidades, notas. Un digito mal es un dato falso, no una errata.
  NOMBRES    : personas, lugares, terminos propios. Ya se vio un caso real en exp-002,
               donde el modelo sustituyo el nombre de una persona por el de una enfermedad.

Esta metrica NO sustituye al WER: lo complementa. Un sistema puede tener buen WER y ser
inservible si falla justo en estas tres cosas.
"""

import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass

NEGACIONES = {
    "no", "ni", "nunca", "jamas", "jamás", "nada", "nadie", "ningun", "ningún",
    "ninguna", "ninguno", "tampoco", "sin",
}

_DIGITOS = re.compile(r"\d+")
_PALABRA = re.compile(r"[\wáéíóúüñ]+", re.IGNORECASE | re.UNICODE)


@dataclass
class ResultadoCriticos:
    negaciones_ref: int
    negaciones_perdidas: int
    negaciones_anadidas: int
    numeros_ref: int
    numeros_perdidos: int
    nombres_ref: int
    nombres_perdidos: int
    ejemplos: list[str]

    @property
    def tasa_negacion(self) -> float:
        """Proporcion de negaciones de la referencia que NO se reproducen."""
        return self.negaciones_perdidas / self.negaciones_ref if self.negaciones_ref else 0.0

    @property
    def tasa_numeros(self) -> float:
        return self.numeros_perdidos / self.numeros_ref if self.numeros_ref else 0.0

    @property
    def tasa_nombres(self) -> float:
        return self.nombres_perdidos / self.nombres_ref if self.nombres_ref else 0.0

    def como_dict(self):
        d = asdict(self)
        d |= {"tasa_negacion": self.tasa_negacion, "tasa_numeros": self.tasa_numeros,
              "tasa_nombres": self.tasa_nombres}
        return d

    def __str__(self):
        return (f"negaciones perdidas={self.tasa_negacion:6.2%} "
                f"({self.negaciones_perdidas}/{self.negaciones_ref}, "
                f"+{self.negaciones_anadidas} inventadas)  "
                f"numeros={self.tasa_numeros:6.2%} ({self.numeros_perdidos}/{self.numeros_ref})  "
                f"nombres={self.tasa_nombres:6.2%} ({self.nombres_perdidos}/{self.nombres_ref})")


def _sin_tildes(t: str) -> str:
    d = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in d if unicodedata.category(c) != "Mn")


def _nombres_propios(texto_original: str) -> Counter:
    """Palabras capitalizadas que no abren frase. Heuristica, no analisis morfologico.

    Se aplica al texto SIN normalizar, porque la mayuscula es justo la senal que se usa.
    Limitacion: no distingue un nombre propio de una palabra capitalizada por error.
    """
    cuenta: Counter[str] = Counter()
    for frase in re.split(r"[.!?]+", texto_original):
        palabras = _PALABRA.findall(frase.strip())
        for p in palabras[1:]:            # se salta la primera: siempre va en mayuscula
            if p[0].isupper() and not p.isupper():
                cuenta[_sin_tildes(p)] += 1
    return cuenta


def evaluar(referencias: list[str], hipotesis: list[str],
            referencias_crudas: list[str] | None = None,
            hipotesis_crudas: list[str] | None = None,
            top_ejemplos: int = 10) -> ResultadoCriticos:
    """Compara referencia e hipotesis en las tres categorias criticas.

    `referencias` e `hipotesis` deben venir normalizadas (mismo normalizador que el WER).
    Las versiones *crudas*, si se pasan, se usan solo para detectar nombres propios por
    capitalizacion; sin ellas esa categoria queda a cero.
    """
    neg_ref = neg_perdidas = neg_anadidas = 0
    num_ref = num_perdidos = 0
    nom_ref = nom_perdidos = 0
    ejemplos: list[str] = []

    for i, (r, h) in enumerate(zip(referencias, hipotesis)):
        pr, ph = Counter(r.split()), Counter(h.split())

        for termino in NEGACIONES:
            en_ref, en_hip = pr[termino], ph[termino]
            neg_ref += en_ref
            if en_hip < en_ref:
                neg_perdidas += en_ref - en_hip
                if len(ejemplos) < top_ejemplos:
                    ejemplos.append(f"negación «{termino}» perdida: «{r[:70]}»")
            elif en_hip > en_ref:
                neg_anadidas += en_hip - en_ref

        cr, ch = Counter(_DIGITOS.findall(r)), Counter(_DIGITOS.findall(h))
        num_ref += sum(cr.values())
        for d, n in cr.items():
            if ch[d] < n:
                num_perdidos += n - ch[d]
                if len(ejemplos) < top_ejemplos:
                    ejemplos.append(f"número «{d}» perdido: «{r[:70]}»")

        if referencias_crudas and hipotesis_crudas:
            nr = _nombres_propios(referencias_crudas[i])
            nh = _nombres_propios(hipotesis_crudas[i])
            nom_ref += sum(nr.values())
            for nombre, n in nr.items():
                if nh[nombre] < n:
                    nom_perdidos += n - nh[nombre]
                    if len(ejemplos) < top_ejemplos:
                        ejemplos.append(f"nombre «{nombre}» perdido")

    return ResultadoCriticos(
        negaciones_ref=neg_ref, negaciones_perdidas=neg_perdidas,
        negaciones_anadidas=neg_anadidas,
        numeros_ref=num_ref, numeros_perdidos=num_perdidos,
        nombres_ref=nom_ref, nombres_perdidos=nom_perdidos,
        ejemplos=ejemplos)
