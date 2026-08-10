"""Errores que cambian el significado, no solo la forma.

El WER trata igual perder "de" que perder "no". Para un alumno con discapacidad auditiva
no son lo mismo ni de lejos: confundir una preposicion se reconstruye por contexto,
perder una negacion **invierte la frase**.

  referencia: "el resultado no es significativo"
  hipotesis : "el resultado es significativo"
  WER 20% -- un error de cinco palabras. Y el alumno entiende lo contrario.

Esta metrica cuenta aparte tres categorias donde un error destruye el contenido:

  NEGACIONES : invierten el sentido. Es la mas grave.
  NUMERALES  : fechas, cantidades, referencias a normativa o a paginas.
  CUANTIFICADORES : "todos"/"algunos"/"ninguno" cambian el alcance de una afirmacion.

Complementa a eval/metrics/terminologia.py: aquella mide si el vocabulario del dominio
sobrevive; esta mide si el SENTIDO sobrevive. Ninguna de las dos se ve en el WER agregado.
"""

import re
from collections import Counter
from dataclasses import asdict, dataclass

import jiwer

NEGACIONES = {
    "no", "ni", "nunca", "jamas", "jamás", "tampoco", "nada", "nadie", "ninguno",
    "ninguna", "ningun", "ningún", "sin",
}

CUANTIFICADORES = {
    "todo", "toda", "todos", "todas", "algun", "algún", "alguna", "algunos", "algunas",
    "poco", "poca", "pocos", "pocas", "mucho", "mucha", "muchos", "muchas",
    "siempre", "solo", "sólo", "unicamente", "únicamente", "mayoria", "mayoría",
    "minoria", "minoría", "cada", "ambos", "ambas",
}

NUMEROS_PALABRA = {
    "cero", "uno", "una", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho",
    "nueve", "diez", "once", "doce", "trece", "catorce", "quince", "veinte", "treinta",
    "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa", "cien",
    "ciento", "mil", "millon", "millón", "millones", "primero", "segundo", "tercero",
    "mitad", "doble", "triple", "por ciento", "porciento",
}

_DIGITO = re.compile(r"\d")

#: Valor numerico de las palabras-numero de una sola pieza. Permite comparar 'cuarenta'
#: con '40' y no contarlo como error: el modelo escribe cifra donde la referencia escribe
#: letra, pero acerto el numero. Sin esto la categoria "numeral" mide formato, no errores
#: (mismo artefacto que R11 con las tildes).
_VALORES = {
    "cero": 0, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12,
    "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16, "diecisiete": 17,
    "dieciocho": 18, "diecinueve": 19, "veinte": 20, "treinta": 30, "cuarenta": 40,
    "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90,
    "cien": 100, "ciento": 100, "mil": 1000, "millon": 1_000_000, "millón": 1_000_000,
}


def valor_numerico(palabra: str) -> int | None:
    """Valor de un numeral escrito en cifra o en letra. None si no lo es."""
    p = palabra.lower()
    if p in _VALORES:
        return _VALORES[p]
    solo_digitos = re.sub(r"\D", "", p)
    return int(solo_digitos) if solo_digitos and p.replace(".", "").replace(",", "").isdigit() else None


def equivalentes(ref: str, hip: str) -> bool:
    """True si ambas palabras son el mismo numero escrito de forma distinta."""
    va, vb = valor_numerico(ref), valor_numerico(hip)
    return va is not None and va == vb


def categoria(palabra: str) -> str | None:
    """Categoria critica de una palabra, o None si no lo es."""
    p = palabra.lower()
    if p in NEGACIONES:
        return "negacion"
    if _DIGITO.search(p) or p in NUMEROS_PALABRA:
        return "numeral"
    if p in CUANTIFICADORES:
        return "cuantificador"
    return None


@dataclass
class ResultadoCriticos:
    tasa_error: float
    tokens_criticos: int
    errores: int
    por_categoria: dict[str, dict[str, int]]
    ejemplos: list[str]

    def como_dict(self):
        return asdict(self)

    def __str__(self):
        partes = " · ".join(
            f"{c}: {d['errores']}/{d['total']}" for c, d in sorted(self.por_categoria.items()))
        return f"tasa de error crítico={self.tasa_error:6.2%}  ({partes})"


def evaluar(referencias: list[str], hipotesis: list[str],
            max_ejemplos: int = 12) -> ResultadoCriticos:
    """Errores sobre tokens criticos, usando el alineamiento palabra a palabra.

    Los textos deben venir normalizados con el mismo normalizador que el WER.

    La tasa se calcula sobre los tokens criticos de la REFERENCIA: responde a "¿que
    proporcion del contenido critico que se dijo llega mal o no llega?". Las inserciones
    (contenido critico que el sistema anade sin que se dijera) se cuentan aparte, porque
    son un fallo distinto: no es perdida de informacion, es invencion.
    """
    total = Counter()
    fallos = Counter()
    inventados = Counter()
    ejemplos: list[str] = []

    salida = jiwer.process_words(referencias, hipotesis)

    for ref, hip, trozos in zip(salida.references, salida.hypotheses, salida.alignments):
        for palabra in ref:
            if (c := categoria(palabra)) is not None:
                total[c] += 1

        for t in trozos:
            if t.type == "equal":
                continue
            palabras_ref = ref[t.ref_start_idx:t.ref_end_idx]
            palabras_hip = hip[t.hyp_start_idx:t.hyp_end_idx]

            for i, palabra in enumerate(palabras_ref):
                if (c := categoria(palabra)) is None:
                    continue
                # "cuarenta" -> "40" no es un error de reconocimiento sino de formato.
                if (c == "numeral" and i < len(palabras_hip)
                        and equivalentes(palabra, palabras_hip[i])):
                    continue
                fallos[c] += 1
                if len(ejemplos) < max_ejemplos:
                    destino = palabras_hip[i] if i < len(palabras_hip) else "(omitido)"
                    ejemplos.append(f"[{c}] {palabra!r} -> {destino!r}")

            # Contenido critico que aparece en la hipotesis sin estar en la referencia.
            if t.type == "insert":
                for palabra in palabras_hip:
                    if (c := categoria(palabra)) is not None:
                        inventados[c] += 1

    n_total = sum(total.values())
    n_fallos = sum(fallos.values())
    por_categoria = {
        c: {"total": total[c], "errores": fallos[c], "inventados": inventados[c]}
        for c in set(total) | set(fallos) | set(inventados)
    }
    return ResultadoCriticos(
        tasa_error=n_fallos / n_total if n_total else 0.0,
        tokens_criticos=n_total, errores=n_fallos,
        por_categoria=por_categoria, ejemplos=ejemplos)
