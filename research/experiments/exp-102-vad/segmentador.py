"""Segmentacion de audio por silencios, sin dependencias externas.

exp-100 midio que trocear por tiempo fijo es caro: a 3 s de ventana el WER casi se
duplica frente a transcribir el fragmento entero. La hipotesis es que el problema son
los cortes: caen en mitad de una palabra o una frase, justo donde el modelo necesita
contexto. Cortar en los silencios deberia dar unidades completas.

El detector es de energia, deliberadamente simple. No pretende competir con un VAD
entrenado (Silero, WebRTC): sirve para comprobar si la hipotesis se sostiene antes de
introducir una dependencia nueva. Si el efecto aparece con esto, un VAD de verdad solo
puede mejorarlo; si no aparece, nos hemos ahorrado la dependencia.
"""

import numpy as np


def energia_por_trama(audio: np.ndarray, sr: int, ms_trama: int = 20) -> tuple[np.ndarray, int]:
    """Energia RMS por trama. Devuelve (energias, muestras_por_trama)."""
    n = max(1, int(sr * ms_trama / 1000))
    sobrante = len(audio) % n
    recortado = audio[:len(audio) - sobrante] if sobrante else audio
    tramas = recortado.reshape(-1, n)
    return np.sqrt((tramas ** 2).mean(axis=1)), n


def segmentar(audio: np.ndarray, sr: int, *,
              percentil_silencio: float = 25.0,
              factor_umbral: float = 1.5,
              ms_silencio_minimo: int = 300,
              s_maximo: float = 10.0,
              s_minimo: float = 1.0) -> list[np.ndarray]:
    """Divide el audio en segmentos cortando por silencios.

    :param percentil_silencio: el umbral se calcula sobre la propia grabacion, no como
        constante absoluta: el nivel de ruido de un aula no es el de un estudio.
    :param factor_umbral: margen sobre el nivel de fondo estimado.
    :param ms_silencio_minimo: una pausa mas corta que esto es respiracion o una oclusiva,
        no una frontera de frase.
    :param s_maximo: tope de duracion. Sin el, un hablante sin pausas produciria un unico
        segmento gigantesco y la latencia se dispararia.
    :param s_minimo: evita segmentos tan cortos que el modelo se quede sin contexto, que
        es justo el fallo que exp-100 encontro con ventanas de 1 s.
    """
    if len(audio) < sr * s_minimo:
        return [audio]

    energias, n_trama = energia_por_trama(audio, sr)
    if energias.size == 0:
        return [audio]

    umbral = np.percentile(energias, percentil_silencio) * factor_umbral
    es_silencio = energias < umbral

    tramas_silencio_min = max(1, int(ms_silencio_minimo / 20))
    tramas_max = int(s_maximo * sr / n_trama)
    tramas_min = int(s_minimo * sr / n_trama)

    cortes: list[int] = []          # en indices de trama
    inicio_segmento = 0
    racha = 0

    for i, silencio in enumerate(es_silencio):
        racha = racha + 1 if silencio else 0
        largo = i - inicio_segmento

        # Se corta en MITAD de la pausa: asi ninguno de los dos segmentos pierde el
        # ataque de la primera palabra ni la cola de la ultima.
        if racha >= tramas_silencio_min and largo >= tramas_min:
            corte = i - racha // 2
            cortes.append(corte)
            inicio_segmento = corte
            racha = 0
        elif largo >= tramas_max:
            # Sin pausa a la vista: se corta por el tope para no romper la latencia.
            cortes.append(i)
            inicio_segmento = i
            racha = 0

    limites = [0, *cortes, len(es_silencio)]
    segmentos = []
    for a, b in zip(limites, limites[1:]):
        trozo = audio[a * n_trama:b * n_trama]
        if len(trozo) > sr * 0.2:
            segmentos.append(trozo)
    return segmentos or [audio]
