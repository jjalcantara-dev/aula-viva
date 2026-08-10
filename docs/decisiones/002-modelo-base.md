# 002 — Modelo base de la comparativa

**Fecha:** M0 · **Estado:** recomendación, pendiente de validar con el director
**Sustituye a:** una recomendación anterior de `large-v3-turbo` basada solo en WER y velocidad

## Contexto

Barrido de seis modelos sobre cinco corpus, con decodificación por reintento de
temperatura fijada (ver R14). Métricas: WER, factor de tiempo real y **tasa de salidas
anómalas**.

## Lo que cambió la decisión

La primera lectura recomendaba `large-v3-turbo`: igualaba a `medium` en WER y era el
doble de rápido. Esa lectura **ignoraba el modo de fallo**.

Salidas gravemente truncadas (<25% de las palabras de la referencia), con la
decodificación ya corregida, sobre 180 clips:

| Modelo | Anomalías | Dónde |
|---|---:|---|
| `large-v3-turbo` | **3** | `voxpopuli_es` (2), `mediaspeech_es` (1) |
| `medium` | **0** | — |
| `small` | **0** | — |

Y no son truncamientos inocuos: con decodificación voraz, `turbo` llegó a emitir
`"Gracias, señora presidenta."` —frase fluida, plausible en el dominio y completamente
falsa— y `"Sorry."`, con fuga de idioma pese a forzar `language="es"`.

## Decisión

**`whisper-medium` como modelo base de la comparativa.**

Justificación, en orden de peso:

1. **Cero alucinaciones** en los cinco corpus. En un sistema de accesibilidad este
   criterio pesa más que unas décimas de WER: un subtítulo ausente se nota, uno inventado
   no. El alumno con discapacidad auditiva no tiene forma de detectarlo
2. **Mejor o igual WER** que `turbo` en cuatro de los cinco corpus
3. **La velocidad no es una restricción**: `medium` va ~12 veces más rápido que el audio.
   El margen de latencia sobra incluso para añadir post-corrección con LLM encima

`large-v3-turbo` se conserva como **segunda condición** del barrido: la comparación
medium/turbo es en sí misma un resultado sobre el compromiso velocidad-fiabilidad.

## Consecuencias

- La aplicación puede usar `turbo` si el perfil de latencia lo exigiera, pero **entonces
  hay que medir alucinación explícitamente**, no solo WER
- La métrica de anomalías (`research/eval/report/anomalias.py`) entra en el protocolo de
  evaluación junto a WER/CER, y debe congelarse en H2
- 🔴 **DIRECTOR:** validar que se acepta priorizar fiabilidad sobre velocidad, y que la
  tasa de alucinación entra como métrica de la comparativa
