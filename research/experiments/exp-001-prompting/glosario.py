"""Extraccion de glosario de dominio a partir de un subconjunto de CONTEXTO.

REGLA CRITICA (evitar fuga de informacion): el glosario se extrae SIEMPRE de clips
disjuntos de los que se evaluan. Construirlo con las transcripciones de evaluacion
equivaldria a soplarle al modelo las respuestas, y cualquier mejora medida seria falsa.

El metodo es deliberadamente simple: palabras de contenido frecuentes en el dominio y
ausentes de una lista de palabras vacias. No pretende ser una aportacion del TFM, sino
una linea base honesta de "informacion de dominio disponible antes de la clase" --
que es exactamente lo que un profesor podria aportar: el temario, un glosario, las
transparencias.
"""

import re
from collections import Counter

# Palabras vacias del espanol. Lista corta y explicita: preferible a una dependencia
# externa que ate el resultado a la version de una libreria.
VACIAS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al", "a", "ante",
    "bajo", "con", "contra", "desde", "en", "entre", "hacia", "hasta", "para", "por",
    "segun", "según", "sin", "sobre", "tras", "y", "e", "o", "u", "ni", "que", "qué",
    "como", "cómo", "cuando", "cuándo", "donde", "dónde", "porque", "pues", "si", "sí",
    "no", "es", "son", "era", "eran", "fue", "fueron", "ser", "estar", "esta", "está",
    "estan", "están", "este", "esta", "esto", "estos", "estas", "ese", "esa", "eso",
    "esos", "esas", "aquel", "se", "le", "les", "lo", "me", "te", "nos", "os", "mi",
    "tu", "su", "sus", "mis", "tus", "nuestro", "nuestra", "yo", "el", "ella", "ellos",
    "ellas", "usted", "ustedes", "hay", "han", "ha", "he", "hemos", "habia", "había",
    "muy", "mas", "más", "menos", "tambien", "también", "tampoco", "ya", "todo", "toda",
    "todos", "todas", "otro", "otra", "otros", "otras", "mismo", "misma", "cada", "algun",
    "algún", "alguna", "alguno", "algunos", "algunas", "ningun", "ningún", "ninguna",
    "poco", "pocos", "mucho", "muchos", "muchas", "tanto", "tan", "asi", "así", "aqui",
    "aquí", "alli", "allí", "ahora", "entonces", "despues", "después", "antes", "bien",
    "puede", "pueden", "hacer", "hace", "tiene", "tienen", "tener", "vamos", "va", "van",
    "señor", "señora", "presidente", "presidenta", "gracias", "bueno", "pero", "aunque",
}

_PALABRA = re.compile(r"[a-záéíóúüñ]+", re.IGNORECASE)


def extraer(textos: list[str], maximo: int = 40, minima_frecuencia: int = 2,
            longitud_minima: int = 6) -> list[str]:
    """Terminos candidatos a glosario, ordenados por frecuencia descendente.

    :param maximo: el prompt de Whisper esta limitado (~224 tokens); no tiene sentido
        pasar cientos de terminos.
    :param minima_frecuencia: un termino que aparece una sola vez puede ser una errata
        de la transcripcion, no vocabulario del dominio.
    :param longitud_minima: filtra palabras funcionales cortas que la lista de vacias
        no cubra.
    """
    cuenta: Counter[str] = Counter()
    for t in textos:
        for p in _PALABRA.findall(t.lower()):
            if len(p) >= longitud_minima and p not in VACIAS:
                cuenta[p] += 1

    return [p for p, n in cuenta.most_common() if n >= minima_frecuencia][:maximo]


def construir_prompt(terminos: list[str]) -> str:
    """Prompt en el estilo que Whisper espera: texto corrido, no una lista con vinetas.

    El prompt condiciona el decodificador como si fuera contexto previo ya transcrito,
    asi que debe parecerse a texto natural del dominio.
    """
    return "Glosario de la sesión: " + ", ".join(terminos) + "."
