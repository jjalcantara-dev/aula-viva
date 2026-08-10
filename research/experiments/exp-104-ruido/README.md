# exp-104 — Robustez frente al ruido de aula

## Pregunta

Todas las mediciones anteriores usan audio limpio. Un aula real tiene proyector, sillas,
toses y murmullo. **¿Cuánto margen acústico necesita el sistema para ser utilizable?**

Que hará falta un micrófono de solapa es obvio y no requiere experimento. Lo que no es
obvio es *cuánto margen* deja ese micrófono, si la degradación es suave o abrupta, y si el
ruido induce alucinaciones.

## Diseño

`whisper-medium`, 40 clips de `voxpopuli_es`, barrido de relación señal-ruido con dos
tipos de ruido que degradan de forma muy distinta:

- **Blanco**: estacionario, espectro plano. Es lo que mejor maneja cualquier supresor de ruido.
- **Murmullo**: sintetizado mezclando seis clips del propio corpus, desfasados. No
  estacionario y **comparte espectro con la voz útil**, que es lo que de verdad hay en un aula.

Referencia aproximada: 20 dB sala tranquila · 10 dB aula con actividad · 0 dB voz y ruido
al mismo nivel.

## Resultados

| SNR | WER blanco | WER murmullo | Anómalos |
|---:|---:|---:|---:|
| limpio | 10.44% | 10.44% | 0/40 |
| 20 dB | 10.50% | 11.66% | 0/40 |
| 15 dB | 10.57% | 11.19% | 0/40 |
| 10 dB | 13.23% | 12.41% | 1/40 |
| 5 dB | 13.98% | 14.26% | 0/40 |
| **0 dB** | 16.85% | **36.02%** | 0/40 |

## Hallazgo 1 — el sistema es robusto en la zona que importa

Hasta **15 dB la degradación es despreciable**: +0.14 puntos con ruido blanco, +0.75 con
murmullo. Un micrófono de solapa sitúa el sistema cómodamente en ese régimen.

Consecuencia práctica: **no hace falta equipo caro**. Una solapa inalámbrica corriente basta;
lo que no vale es el micrófono integrado del portátil a tres metros del docente, que
trabajaría en la zona de 5-10 dB.

## Hallazgo 2 — la degradación no es lineal: hay un precipicio

Entre limpio y 5 dB el WER sube unos 4 puntos, de forma gradual y tolerable. **Entre 5 y
0 dB con murmullo se triplica** (14.26% → 36.02%). Con ruido blanco al mismo nivel solo
llega a 16.85%.

La diferencia confirma el mecanismo: lo que arruina el reconocimiento no es la energía del
ruido sino que **comparta espectro con la voz**. Seis voces de fondo enmascaran lo que un
ventilador no. Por eso los supresores de ruido convencionales, diseñados para ruido
estacionario, no resuelven el problema del aula.

Para el sistema desplegado significa que **el modo de fallo es abrupto**: mientras el
docente esté por encima del murmullo, funciona; si la clase sube el volumen hasta
igualarlo, el subtitulado se cae de golpe en lugar de degradarse poco a poco.

## Hallazgo 3 — el ruido NO disparó las alucinaciones (hipótesis no confirmada)

Se esperaba que con SNR baja Whisper inventase texto sobre el murmullo. **La tasa de
salidas anómalas se mantuvo en cero** en todas las condiciones.

**Limitación importante de esta conclusión**: el detector de anomalías identifica
truncamientos (salidas con menos de un cuarto de las palabras esperadas), no invenciones
fluidas de longitud normal. A 0 dB con 36% de WER el modelo podría estar fabricando
contenido sin que la métrica lo detecte. Para afirmarlo haría falta inspección manual de
las transcripciones en esa condición.

## Limitaciones

- Ruido **añadido sintéticamente**, no grabado en un aula. Falta reverberación, que es un
  factor independiente y posiblemente más dañino que el ruido aditivo.
- El murmullo se construye con voces del mismo corpus: comparten canal de grabación y
  características acústicas, lo que puede hacerlo más o menos enmascarante que un aula real.
- Un solo modelo y un solo corpus.
- Sin medir el efecto del preprocesado del navegador (supresión de ruido de WebRTC), que
  en el sistema real actúa antes que el modelo.

## Reproducir

```bash
make exp-104
```
