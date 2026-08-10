"""Corrector de transcripciones con un LLM ligero local.

El riesgo dominante de esta tecnica NO es que corrija poco, sino que corrija de mas: un
modelo de lenguaje tiende a reescribir, completar y "mejorar" el texto. Cada palabra que
anada sin que estuviera en el audio es una insercion, y el WER lo penaliza igual que una
palabra perdida. Peor aun para accesibilidad: el alumno recibiria contenido que el docente
no dijo, redactado con total naturalidad.

De ahi que el prompt sea restrictivo hasta parecer paranoico, y que el experimento mida la
razon de longitud ademas del WER: si el texto crece, el modelo esta inventando.
"""

import re

SISTEMA = (
    "Eres un corrector de transcripciones automáticas en español. "
    "Tu única tarea es reparar errores de reconocimiento de voz."
)

# Las instrucciones llevan ejemplos por una razon medida: la primera version, solo con
# prohibiciones ("si dudas, no cambies nada"), dejo la tecnica INERTE -- 0 de 8 clips
# modificados a nivel de palabra, y errores obvios como "el Alco Parlamentario" (por
# "el arco parlamentario") sin tocar. Un modelo pequeno obedece la prohibicion al pie de
# la letra y se limita a cambiar mayusculas.
#
# Los ejemplos muestran QUE corregir, no solo que no hacer. Las prohibiciones se
# conservan porque el riesgo de reescritura sigue siendo real.
INSTRUCCIONES = """Corrige errores de reconocimiento de voz en una transcripción en español.

QUÉ SÍ debes corregir:
- Palabras que no existen en español y que por contexto son claramente otra palabra.
  Ejemplo: "el Alco Parlamentario" → "el arco parlamentario"
  Ejemplo: "el segundo acto del DAMA" → "el segundo acto del drama"
- Palabras reales pero imposibles en ese contexto, cuando la palabra correcta es evidente.
  Ejemplo: "la crisis se está grabando" → "la crisis se está agravando"

QUÉ NO debes tocar NUNCA:
- NO reformules ni mejores el estilo. NO resumas.
- NO completes frases que el hablante dejó a medias.
- NO añadas información que no esté en el texto.
- Mantén repeticiones, muletillas y titubeos: son habla real, no errores.
- Si una parte no tiene errores claros, déjala EXACTAMENTE igual.

Responde solo con la transcripción corregida, sin comentarios ni comillas.

TRANSCRIPCIÓN:
{texto}"""

INSTRUCCIONES_GLOSARIO = """Corrige errores de reconocimiento de voz en una transcripción en español.

Estos términos pertenecen al tema de la sesión y suelen reconocerse mal:
{glosario}

QUÉ SÍ debes corregir:
- Palabras que no existen en español y que por contexto son claramente otra palabra.
  Ejemplo: "el Alco Parlamentario" → "el arco parlamentario"
- Fragmentos que claramente intentaban decir uno de los términos de la lista.
- Palabras reales pero imposibles en ese contexto, cuando la correcta es evidente.

QUÉ NO debes tocar NUNCA:
- NO reformules ni mejores el estilo. NO resumas.
- NO completes frases que el hablante dejó a medias.
- NO metas términos de la lista donde el texto no los estaba intentando decir.
- Mantén repeticiones, muletillas y titubeos: son habla real.
- Si una parte no tiene errores claros, déjala EXACTAMENTE igual.

Responde solo con la transcripción corregida, sin comentarios ni comillas.

TRANSCRIPCIÓN:
{texto}"""

# El modelo a veces envuelve la respuesta pese a las instrucciones.
_ENVOLTORIOS = re.compile(r'^\s*(?:["\'«»]|```\w*)\s*|\s*(?:["\'«»]|```)\s*$')
_PREAMBULO = re.compile(
    r'^\s*(?:aquí (?:tienes|está)|la transcripción corregida|transcripción corregida)'
    r'[^:]*:\s*', re.IGNORECASE)


def construir_mensajes(texto: str, glosario: list[str] | None) -> list[dict]:
    plantilla = INSTRUCCIONES_GLOSARIO if glosario else INSTRUCCIONES
    contenido = plantilla.format(
        texto=texto,
        glosario=", ".join(glosario) if glosario else "")
    return [{"role": "system", "content": SISTEMA},
            {"role": "user", "content": contenido}]


def limpiar(respuesta: str, original: str, maximo_crecimiento: float = 1.5) -> tuple[str, str]:
    """Depura la respuesta del LLM y decide si es aceptable.

    Devuelve (texto, motivo). Si el motivo no es "ok", se descarta la correccion y se
    conserva el original: mas vale no corregir que degradar.
    """
    texto = _PREAMBULO.sub("", respuesta.strip())
    texto = _ENVOLTORIOS.sub("", texto).strip()

    if not texto:
        return original, "vacio"

    # Salvaguarda contra la reescritura: si el modelo alarga mucho el texto, ha
    # completado o inventado en lugar de corregir.
    n_orig, n_nuevo = len(original.split()), len(texto.split())
    if n_orig and n_nuevo > n_orig * maximo_crecimiento:
        return original, "demasiado largo"
    if n_orig and n_nuevo < n_orig / maximo_crecimiento:
        return original, "demasiado corto"
    # Una respuesta con saltos de linea suele ser una lista o un comentario anadido.
    if "\n" in texto and "\n" not in original:
        texto = texto.split("\n")[0].strip()

    return texto, "ok"
