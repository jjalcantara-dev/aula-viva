# Modelos ASR candidatos — auditoría

Documento vivo, hermano de `corpus/FUENTES.md`. Registra qué modelos se han considerado
como base de la comparativa, cuáles se han medido y por qué se descartaron los demás.

**Estado:** ✅ medido en este repositorio · 🔬 verificado que carga y transcribe · ❓ sin
comprobar · ⛔ no viable en esta plataforma

## Por qué existe

La comparativa de técnicas de adaptación se construyó sobre Whisper, elegido en exp-000
entre seis variantes de su propia familia (ver `docs/decisiones/002-modelo-base.md`). Ese
barrido responde *qué Whisper*, no *por qué Whisper*.

Durante el desarrollo aparecieron modelos de arquitectura distinta con mejores cifras
publicadas. Defender un trabajo que nunca miró fuera de una familia sería una debilidad
evitable, así que la elección pasa a estar respaldada por medición propia (exp-004) y no
por inercia.

## Auditado en agosto de 2026

| Modelo | Estado | Arquitectura | Español | Notas |
|---|---|---|---|---|
| `openai/whisper-medium` | ✅ | Codificador-decodificador autorregresivo | Sí | Base de toda la comparativa. Cero salidas anómalas en cinco corpus |
| `openai/whisper-large-v3-turbo` | ✅ | Íd. | Sí | Segunda condición del barrido. Tres truncamientos graves |
| `openai/whisper-small` | ✅ | Íd. | Sí | |
| `nvidia/parakeet-tdt-0.6b-v3` | ✅ | Transductor (TDT) | Sí, 25 idiomas europeos | Medido en exp-004 sobre 800 clips. Mejor WER en habla leída y mucho mejor en contenido crítico, pero **traduce al inglés en 13 clips** y no admite forzar idioma. Descartado como base |
| `Qwen/Qwen3-ASR-1.7B` | ❓ | Condicional generativa sobre LLM | Sí, 52 idiomas | Reconocido por `transformers` 5.15. Sin comprobar aquí |
| `nvidia/canary-qwen-2.5b` | ⛔ | — | — | Se distribuye para NeMo, no para `transformers`. Introducir esa cadena de dependencias sobre ROCm es un riesgo desproporcionado para lo que aporta |

### Lo que cambia y lo que no

Las cifras publicadas de los modelos recientes se mueven en un margen estrecho de calidad
y uno amplísimo de caudal: entre los mejores sistemas la diferencia de WER ronda el punto
porcentual, mientras que el rendimiento por unidad de tiempo varía en más de un orden de
magnitud. Para un sistema en vivo eso importa mucho más de lo que parece al mirar solo la
tabla de precisión.

**Lo que la comparación midió, en una línea:** Parakeet gana en WER sobre habla leída,
empata sobre habla espontánea, conserva mucho mejor el contenido crítico, corre entre
cinco y nueve veces más rápido, y aun así queda descartado porque traduce al inglés y no
hay forma de impedírselo (`docs/decisiones/005-modelos-posteriores.md`).

**El control de idioma es un requisito, no una comodidad.** Cualquier candidato debe poder
recibir «transcribe en español» y obedecer. Un modelo multilingüe con detección automática
derivará a otro idioma cuando el audio sea difícil, que es justo cuando un sistema de
accesibilidad no puede permitírselo. Se comprueba mirando si expone `forced_decoder_ids`,
`lang_id` o equivalente; Parakeet TDT no expone ninguno.

**Aun así, un modelo más rápido no rescata el diseño del sistema en vivo.** La latencia
medida está dominada por la espera a que se llene la ventana de audio, no por la
inferencia; aunque el modelo fuese cien veces más rápido, seguiría habiendo que esperar a
que el docente termine de hablar. El hallazgo de exp-102, que segmentar por silencios rinde
más que cualquier técnica de adaptación, no depende del modelo.

### La asimetría de decodificación

Whisper admite reintento con temperatura, y esa decodificación está congelada por R14
porque cambiarla mueve el WER hasta trece puntos. Parakeet no admite nada equivalente: es
un transductor, emite un símbolo por trama y no tiene bucle autorregresivo sobre el texto
sobre el que aplicar umbrales ni reintentos.

No hay forma de igualar la decodificación entre ambas arquitecturas. La comparación de
exp-004 es entre **sistemas completos**, cada uno en su configuración estándar, y así queda
declarado en lugar de disimulado.

## Cómo añadir un modelo

`research/src/asr/motores.py` concentra la carga y la decodificación de cada familia. Un
modelo nuevo necesita una función de carga y una entrada en `FAMILIAS`; el resto de los
experimentos lo recibe ya envuelto en la misma interfaz.

Dos cosas que costaron tiempo con Parakeet y que conviene comprobar en cualquier familia
nueva:

- `AutoModelForCTC` **no** vale para la variante TDT pese al nombre de la familia; su
  configuración no está registrada en esa cabeza. Se carga con `AutoModel`.
- `generate` no devuelve un tensor sino un objeto con `.sequences`, y sin
  `skip_special_tokens` el texto sale sembrado de `<blank>`, el símbolo que el transductor
  emite en las tramas donde decide no producir nada. Sin eso el WER medido es basura: 48%
  en lugar de 6.6% sobre los mismos ocho clips.
