"""Contraste estadistico para diseños pareados: mismos clips, dos sistemas.

Estaba duplicado en exp-001, exp-002 y exp-003, con tres versiones que solo diferian en
los comentarios. Al añadir un cuarto experimento que lo necesitaba, copiarlo otra vez
habria sido la cuarta oportunidad de que una de las copias divergiera sin que nada lo
delatara; que es justo el fallo que este proyecto ya ha pagado con el manifiesto.

Los experimentos anteriores conservan su copia: reescribirlos no cambiaria ninguna cifra
ya medida y si abriria la posibilidad de introducir un error en resultados cerrados.
"""

import math
import random

import jiwer


def prueba_signos(mejoras: int, empeoramientos: int) -> float:
    """p-valor bilateral del test de signos. Sin dependencias externas.

    Hipotesis nula: la tecnica no cambia nada, asi que cada clip que cambia tiene la
    misma probabilidad de mejorar que de empeorar. Los empates no cuentan, que es
    precisamente lo que hace apropiado el test: no asume ninguna distribucion sobre la
    magnitud de la diferencia, solo sobre su signo.
    """
    n = mejoras + empeoramientos
    if n == 0:
        return 1.0
    k = min(mejoras, empeoramientos)
    cola = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * cola)


def errores_por_clip(refs: list[str], hips: list[str]) -> list[tuple[int, int]]:
    """(errores, palabras_de_referencia) por clip. Se calcula UNA vez."""
    salida = []
    for r, h in zip(refs, hips):
        o = jiwer.process_words([r], [h])
        salida.append((o.substitutions + o.deletions + o.insertions, len(r.split())))
    return salida


def ic_bootstrap(refs: list[str], hip_a: list[str], hip_b: list[str],
                 repeticiones: int = 2000, semilla: int = 42) -> tuple[float, float]:
    """IC 95% de la diferencia de WER (b - a) remuestreando CLIPS.

    Remuestrear clips y no palabras es lo correcto: los errores se agrupan dentro de un
    mismo clip y hablante, y tratarlos como independientes estrecharia el intervalo de
    forma artificial.

    Los alineamientos se calculan una sola vez y cada replica solo suma conteos: con 700
    clips y 2000 replicas, realinear en cada una supondria millones de alineamientos.
    """
    ea, eb = errores_por_clip(refs, hip_a), errores_por_clip(refs, hip_b)
    rng = random.Random(semilla)
    n = len(refs)
    difs = []
    for _ in range(repeticiones):
        idx = [rng.randrange(n) for _ in range(n)]
        palabras = sum(ea[i][1] for i in idx)
        err_a = sum(ea[i][0] for i in idx)
        err_b = sum(eb[i][0] for i in idx)
        if palabras:
            difs.append(err_b / palabras - err_a / palabras)
    difs.sort()
    return difs[int(0.025 * len(difs))], difs[int(0.975 * len(difs))]


def conteo_signos(refs: list[str], hip_a: list[str], hip_b: list[str]) -> tuple[int, int, int]:
    """Clips donde b mejora, empeora o empata frente a a, en tasa de error por clip."""
    ea, eb = errores_por_clip(refs, hip_a), errores_por_clip(refs, hip_b)
    mejoras = empeoramientos = empates = 0
    for (err_a, pal), (err_b, _) in zip(ea, eb):
        if pal == 0:
            empates += 1
        elif err_b < err_a:
            mejoras += 1
        elif err_b > err_a:
            empeoramientos += 1
        else:
            empates += 1
    return mejoras, empeoramientos, empates


def veredicto(ic: tuple[float, float], p: float, alfa: float = 0.05) -> str:
    """Resume el contraste exigiendo que AMBOS criterios coincidan.

    Declarar significativo cuando el intervalo apenas excluye el cero y el test de signos
    dice lo contrario es como se fabrican hallazgos que no se replican; ya estuvo a punto
    de ocurrir en este proyecto.
    """
    bajo, alto = ic
    if bajo < 0 < alto or p >= alfa:
        return "sin evidencia"
    return "mejora" if alto < 0 else "empeora"
