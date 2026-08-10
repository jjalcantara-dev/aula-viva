# exp-103 — ¿Ayuda arrastrar la transcripción anterior como contexto?

## Motivación

En el sistema en vivo cada ventana se transcribe **a ciegas**: Whisper no sabe nada de lo
dicho en los segundos previos. Observado con micrófono real, «encantado de conoceros»
partido entre dos ventanas salió como «Es encantado hacer».

Whisper admite un prompt que actúa como contexto ya transcrito, y la implementación de
referencia de OpenAI lo usa (`condition_on_previous_text`). ¿Cuánto aporta aquí?

## Hipótesis (refutada)

*El contexto ayudará más cuando los cortes sean arbitrarios (ventana fija) que cuando
caigan en pausas naturales (silencios), porque es ahí donde falta información.*

## Diseño

`whisper-medium`, 40 clips de `voxpopuli_es`. Cruce de dos factores: estrategia de
troceado (ventana fija de 5 s / silencios con tope de 8 s) × contexto (no / sí).

El contexto son las **últimas 30 palabras que el propio sistema ya transcribió en ese
clip**. Nunca la referencia ni nada posterior: es exactamente la información que tendría
la aplicación en vivo. Pasarle la transcripción correcta sería hacer trampa.

Se limita a 30 palabras a propósito: arrastrar todo el clip aumentaría la propagación de
errores y diluiría la parte relevante, que es el final.

## Resultados

| Troceado | Contexto | WER | CER | Segmentos |
|---|---|---:|---:|---:|
| ventana fija | no | 17.12% | 12.18% | 121 |
| ventana fija | sí | 17.26% | 11.87% | 121 |
| silencios | no | **12.48%** | 8.14% | 176 |
| silencios | sí | 13.10% | 8.87% | 176 |

**Aporte del contexto:** ventana fija **+0.14 pp**, silencios **+0.61 pp**. En ambos casos
el WER empeora ligeramente.

## Lectura

**El contexto no aporta mejora**, y la hipótesis queda refutada al revés de lo esperado:
estorba **más** con segmentación por silencios, no menos.

La explicación encaja con lo que ya sabíamos. Cuando los cortes caen en pausas naturales,
cada segmento **ya es una unidad coherente**: el contexto no añade información que falte,
pero sí arrastra los errores de la ventana anterior. Whisper tiende a mantener coherencia
con lo que cree que ya se dijo, así que un error de una ventana se propaga a la siguiente.

El CER se comporta distinto del WER en ventana fija (mejora de 12.18% a 11.87% mientras el
WER empeora): el contexto homogeneiza ortografía y puntuación, pero no corrige errores de
palabra. Es coherente con la idea de que aporta estilo, no información.

### Advertencia sobre la magnitud

Las diferencias son **pequeñas** (0.14 y 0.61 puntos) y **no se han calculado intervalos
de confianza** en este experimento. La afirmación defendible es *«el contexto no aporta
mejora»*, no *«el contexto empeora significativamente»*. Si se quisiera afirmar lo segundo,
habría que repetirlo con el diseño pareado de exp-001/exp-002.

## Consecuencia para la aplicación

**No implementar el arrastre de contexto.** No aporta, añade complejidad y crea un canal de
propagación de errores. La complejidad debe ir a la segmentación por silencios (exp-102),
que sí está medida y sí mejora.

## Comprobación de reproducibilidad (no buscada)

Las filas sin contexto dan 17.12% (ventana fija 5 s) y 12.48% (silencios tope 8 s),
**idénticas** a las medidas por exp-100 y exp-102 en ejecuciones independientes. El
pipeline es determinista con la semilla fijada.

## Reproducir

```bash
make exp-103
```
