# 003 — Procesamiento por lotes en los experimentos

**Fecha:** M0 · **Estado:** verificado, adoptado para barridos

## Contexto

Los barridos de la comparativa tardan decenas de minutos y mantienen la CPU en torno a
85 °C durante todo ese tiempo. La causa medida: con lote de tamaño 1, la decodificación
autorregresiva lanza miles de kernels diminutos y el despacho desde Python satura ~3
núcleos, mientras la GPU trabaja muy por debajo de su capacidad.

## Verificación

`tools/verificar_lote.py`, `whisper-medium`, 16 clips (186 s de audio):

| Lote | Tiempo | Aceleración | Potencia GPU | Transcripciones idénticas |
|---:|---:|---:|---:|---|
| 1 | 23.6 s | 1.00× | 177 W | — |
| 4 | 13.9 s | 1.71× | 195 W | 16/16 |
| 8 | 13.3 s | 1.78× | 204 W | 16/16 |

## Decisión

**Adoptar lote 8 en los barridos.** Justificación:

1. **No altera los resultados.** Las 16 transcripciones coinciden exactamente con las de
   lote 1 en ambos tamaños. Esto era la condición indispensable: una optimización que
   cambiara las salidas sería un factor de confusión como la decodificación (R14), y
   habría que descartarla por rápida que fuese.
2. **1.78× más rápido**, lo que reduce a la mitad el tiempo de CPU a temperatura alta.
3. **Traslada trabajo a la GPU**: de 177 W a 204 W. Menos despachos por unidad de audio.
4. De 4 a 8 la ganancia ya es marginal; subir más solo consume VRAM sin beneficio.

## Consecuencias

- `exp-000-baseline` acepta `--lote`; el valor por defecto sigue siendo 1 por seguridad.
- **El lote debe re-verificarse si cambia el modelo, la decodificación o la versión de
  `transformers`.** La equivalencia comprobada aquí no es una garantía universal.
- **No aplica a la aplicación en vivo**: allí el audio llega de uno en uno y no hay nada
  que agrupar. La latencia por token sigue siendo el suelo irreducible.
- Los resultados existentes se generaron con lote 1 y siguen siendo válidos: la
  equivalencia está comprobada en ambos sentidos.
