# 005 — Modelos posteriores a la elección del modelo base

**Fecha:** agosto de 2026 · **Estado:** decidido con medición propia, revisable
**Complementa a:** `002-modelo-base.md`, que eligió `whisper-medium` entre seis variantes
de la misma familia

## Contexto

La comparativa de técnicas de adaptación se construyó entera sobre Whisper. El barrido de
exp-000 respondía *qué Whisper*, no *por qué Whisper*: las seis condiciones eran variantes
de un mismo modelo.

Durante el desarrollo aparecieron modelos multilingües de arquitectura distinta con
mejores cifras publicadas. Con la entrega prevista para enero o febrero de 2027, sostener
ante un tribunal una comparativa que nunca miró fuera de una familia, y responder «porque
fue lo primero que probé», era una debilidad evitable.

## Qué se auditó

| Modelo | Resultado |
|---|---|
| `nvidia/parakeet-tdt-0.6b-v3` | Medido en exp-004 sobre 800 clips |
| `Qwen/Qwen3-ASR-1.7B` | Reconocido por `transformers` 5.15; sin medir |
| `nvidia/canary-qwen-2.5b` | Descartado: solo se distribuye para NeMo, y esa cadena de dependencias sobre ROCm es un riesgo desproporcionado |

Catálogo completo en `research/MODELOS.md`.

## Lo que dijo la medición

Parakeet gana donde se le mira con la métrica habitual y pierde donde importa.

**Gana en WER, pero solo en habla leída.** 2.31 puntos en habla parlamentaria una vez
descontado el artefacto ortográfico de los numerales; en habla espontánea el intervalo de
confianza cruza el cero y no hay evidencia de diferencia.

**Gana con holgura en contenido crítico.** En `teleconciencia_es`, con un WER
indistinguible del de Whisper, pierde 16 de 138 negaciones frente a las 48 de Whisper. Un
evaluador que solo mirase el WER concluiría que da igual cuál usar.

**Y falla de la peor forma posible.** Trece clips de ochocientos traducidos al inglés, más
dos salidas vacías, frente a cero y cero de Whisper. No son truncamientos: son frases
fluidas en otro idioma, y alternancias a media frase del tipo *«aumenta the number of
adipositos»*.

## Decisión

**Se mantiene `whisper-medium` como modelo base.**

El criterio es el mismo que en la decisión 002, aplicado con coherencia: en un sistema de
accesibilidad el modo de fallo pesa más que unas décimas de WER. Allí descartó a
`large-v3-turbo` pese a su velocidad; aquí descarta a Parakeet pese a su ventaja en WER y
en contenido crítico.

Pesa además que **el fallo no es corregible por configuración**. Parakeet TDT no expone
ningún mecanismo para forzar el idioma: no tiene `forced_decoder_ids` ni `lang_id`, y su
`generation_config` solo declara tokens especiales. Whisper, al que sí se le impone
`language="es"`, no fugó ni una vez en los mismos clips. No es un parámetro mal puesto, es
una propiedad de la arquitectura tal y como se distribuye.

## Consecuencias

- La elección del modelo base pasa a estar respaldada por medición contra una arquitectura
  distinta, y no por inercia. Es una respuesta defendible a la pregunta previsible del
  tribunal.
- Aparece una métrica nueva en el protocolo: `eval/report/fuga_idioma.py`. El detector de
  anomalías existente mide **longitud** y es ciego a la traducción, porque una frase
  traducida tiene longitud normal. Ese punto ciego estuvo ahí todo el tiempo.
- La comparativa de técnicas de adaptación no se ve afectada: se sostiene sobre el modelo
  base, que sigue siendo el correcto.
- El hallazgo central del trabajo sale **reforzado**: que el WER esconde los fallos que
  importan en accesibilidad queda demostrado sobre dos arquitecturas distintas, y deja de
  ser atribuible a una peculiaridad de Whisper.
- Queda anotado que el veredicto es sobre `parakeet-tdt-0.6b-v3` tal como se distribuye
  hoy. Un ajuste fino sobre español, o una variante con control de idioma, cambiarían el
  cálculo; es trabajo futuro, no conclusión cerrada.

## Revisable si

- Aparece una variante de transductor multilingüe con forzado de idioma.
- Se consigue el corpus educativo real: repetir exp-004 sobre él tendría más valor que
  sobre corpus sustitutos, y la asimetría entre habla leída y espontánea que se ha medido
  sugiere que el resultado podría no trasladarse.
- 🟡 **DIRECTOR:** validar que se mantiene el criterio de priorizar el modo de fallo sobre
  el WER agregado, ahora que hacerlo implica descartar al modelo con mejor WER y mejor
  conservación de contenido crítico.
