# exp-102 — Segmentar por silencios frente a trocear por tiempo fijo

## Pregunta

exp-100 midió que trocear cada N segundos degrada mucho la transcripción, y dejó planteada
la hipótesis de que la causa son los cortes arbitrarios en mitad de palabra o de frase.
**¿Se sostiene?**

## Diseño

`whisper-medium`, 40 clips de `voxpopuli_es`, decodificación con reintento.

**Comparación justa por construcción.** Cada tope de duración enfrenta ventana fija contra
segmentación por silencios *con el mismo límite*, de modo que ambas produzcan segmentos de
duración comparable. Comparar segmentos de 2 s contra segmentos de 8 s solo diría algo
sobre la duración, no sobre la estrategia de corte.

**Detector de energía, sin dependencias nuevas.** Umbral calculado sobre la propia
grabación (percentil 25 × 1.5), pausa mínima de 300 ms, y corte **en mitad de la pausa**
para que ningún segmento pierda el ataque de la primera palabra ni la cola de la última.
Es deliberadamente simple: si la hipótesis se sostiene con esto, un VAD entrenado
(Silero, WebRTC) solo puede mejorarlo; si no se sostuviera, nos habríamos ahorrado la
dependencia.

## Resultados

| Estrategia | Tope | WER | Dur. media | Dur. p95 | Segmentos |
|---|---:|---:|---:|---:|---:|
| ventana fija | 2 s | 23.19% | 1.87 s | 2.00 s | 277 |
| **silencios** | 2 s | **20.87%** | 1.69 s | 2.00 s | 306 |
| ventana fija | 3 s | 19.85% | 2.68 s | 3.00 s | 193 |
| **silencios** | 3 s | **17.33%** | 2.22 s | 3.00 s | 232 |
| ventana fija | 5 s | 17.12% | 4.27 s | 5.00 s | 121 |
| **silencios** | 5 s | **14.53%** | 2.78 s | 5.00 s | 186 |
| ventana fija | 8 s | 13.92% | 6.30 s | 8.00 s | 82 |
| **silencios** | 8 s | **12.48%** | 2.93 s | 5.92 s | 176 |

Referencia sin trocear (exp-100): **10.44%**.

## Hallazgo: no es un compromiso, es una mejora estricta

La lectura por filas subestima el resultado. La comparación que importa es **a latencia
equivalente**:

| Estrategia | WER | Dur. media | Dur. p95 |
|---|---:|---:|---:|
| Ventana fija, tope 3 s | 19.85% | 2.68 s | 3.00 s |
| **Silencios, tope 8 s** | **12.48%** | **2.93 s** | 5.92 s |

**Con una latencia media prácticamente idéntica, segmentar por silencios reduce el WER en
7.4 puntos** y se queda a solo 2 puntos de transcribir el fragmento entero sin trocear.

El mecanismo se ve en las duraciones: con tope de 8 s, la segmentación por silencios
produce segmentos de 2.93 s de media. El tope casi nunca se alcanza porque el detector
encuentra pausas naturales mucho antes. Resultado: segmentos **cortos y completos**, en
lugar de cortos y partidos.

## El pero: la latencia deja de ser predecible

El p95 pasa de 3.00 s (ventana fija, tope 3 s) a **5.92 s**. La latencia media mejora, pero
el peor caso empeora: si el docente encadena una parrafada sin pausas, el subtítulo tarda
hasta que se alcanza el tope.

Para accesibilidad la previsibilidad también cuenta, así que **ambas cifras deben
reportarse en la memoria**, no solo la media. Mitigación posible: bajar el tope para acotar
el peor caso, aceptando algo más de WER — el barrido da la curva para elegir con datos.

## Recomendación

Adoptar **segmentación por silencios con tope de 5-8 s** en la aplicación. La elección
exacta depende de qué se priorice:

- **tope 8 s**: mejor WER (12.48%), p95 de 5.92 s
- **tope 5 s**: WER 14.53%, p95 acotado a 5.00 s — peor caso garantizado

🔴 **DIRECTOR: confirmar que la segmentación por silencios entra en el alcance del núcleo
aplicado, y si el criterio es la latencia media o el peor caso.**

## Limitaciones

- Detector de energía, no entrenado. Con ruido de aula real (proyector, sillas, murmullo)
  el umbral por percentil puede fallar; un VAD entrenado sería más robusto. Esta medición
  justifica introducirlo, ya no es una suposición.
- Un solo corpus y un solo modelo.
- No se ha medido la latencia real de extremo a extremo, solo la duración de segmento como
  aproximación.

## Reproducir

```bash
.venv/bin/python research/experiments/exp-102-vad/run.py --limite 40
```
