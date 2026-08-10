# exp-002 — Post-corrección de la transcripción con un LLM ligero local

## Hipótesis

Un modelo de lenguaje local puede reparar errores de reconocimiento usando el contexto,
sin necesidad de reentrenar el sistema ASR.

## Diseño

`Qwen2.5-3B-Instruct` corrige las transcripciones que ya produjo exp-000 con
`whisper-medium`. **No se vuelve a ejecutar Whisper**: la salida del ASR queda fija y la
única variable es la corrección, lo que aísla el efecto por completo.

400 clips de `teleconciencia_es` · 8.186 palabras de referencia · diseño pareado ·
test de signos e IC 95% por bootstrap sobre clips.

Salvaguardas del corrector: se descarta la corrección y se conserva el original si el
texto crece o encoge más de un 50%, si viene vacío, o si el modelo añade comentarios.

## Resultado: la técnica degrada, y de forma significativa

| | Sin corregir | Corregido | Δ |
|---|---:|---:|---:|
| **WER** | 19.55% | **22.77%** | **+3.23** |
| WER sin tildes | 14.19% | 17.52% | +3.32 |
| CER | 9.06% | 11.56% | +2.50 |
| Sustituciones | 822 | 951 | +129 |
| Inserciones | 123 | 144 | +21 |
| Borrados | 655 | 769 | +114 |

- IC 95%: **[+2.66, +3.84]** — no cruza el cero, **diferencia significativa**
- Pareado: **12 mejoran, 164 empeoran**, 224 sin cambio · test de signos **p < 0.0001**
- Razón de longitud: 0.988 → **no es reescritura por inflado**
- Descartes por las salvaguardas: 1 de 400

**No es un artefacto de tildes** (R11): la degradación se mantiene igual con normalización
insensible a acentos (+3.32 frente a +3.23).

## Mecanismo: el LLM mejora el texto, no la transcripción

Los peores casos muestran qué está haciendo exactamente:

```
"cirugía"                             → "quirófano"
"Ramón de la Fuente Muñez"            → "Fibromialgia"
"Instituto de Tecnología de la UNAM"  → "Universidad Nacional Autónoma de México (UNAM)"
"atiendan a como un tipo terapia"     → "atiendan cómo un tipo de terapia"
```

Sustituye palabras por sinónimos más precisos, expande siglas, corrige la gramática del
hablante y completa lo que interpreta como intención. **Cada una de esas ediciones mejora
el texto como pieza escrita y lo empeora como transcripción.** Son objetivos en conflicto,
y un modelo entrenado para generar lenguaje natural optimiza el primero.

### El caso que debe aparecer en la memoria

`teleconciencia_es_0278`: el modelo sustituyó **el nombre de una persona por el nombre de
una enfermedad** («Ramón de la Fuente Muñez» → «Fibromialgia»), quedándose con el tema del
programa. El resultado es fluido, gramatical y completamente falso.

Para un sistema de accesibilidad esto es el peor modo de fallo posible: el alumno con
discapacidad auditiva no tiene forma de detectarlo, porque el subtítulo se lee
perfectamente bien. Un subtítulo ausente se nota; uno inventado, no.

## El prompt es determinante, y esto limita la generalidad del resultado

La **primera versión** de las instrucciones era puramente prohibitiva («si dudas, no
cambies nada»). Con ella la técnica quedó **inerte**: 0 de 8 clips modificados a nivel de
palabra, y errores obvios como «el Alco Parlamentario» (por «el arco parlamentario») sin
tocar. Sus únicos cambios fueron poner mayúsculas.

Añadir **ejemplos de qué sí corregir**, manteniendo las prohibiciones, activó la técnica.

Consecuencia honesta: **este experimento no mide "la post-corrección con LLM" en abstracto,
sino una implementación concreta.** Un prompt distinto, un modelo mayor o ejemplos few-shot
adaptados podrían dar otro resultado. Debe declararse como limitación.

## Conclusión

Con esta configuración, la post-corrección con LLM ligero **no es recomendable** para
subtitulado educativo: degrada el WER de forma significativa y su modo de fallo es
precisamente el más peligroso para el usuario final.

Es el primer resultado **concluyente** de la comparativa, y es negativo. Eso no lo hace
menos valioso: un resultado negativo bien medido, con mecanismo explicado y con las
salvaguardas documentadas, es una contribución legítima — sobre todo cuando la intuición
del campo diría lo contrario.

## Qué probar antes de descartarla del todo

1. **Restringir la corrección a la terminología del glosario**, en lugar de dar libertad
   sobre todo el texto. Reduce la superficie donde el modelo puede "mejorar".
2. **Modelo mayor o específico de español** (`BSC-LT/salamandra-2b-instruct`). Comparar un
   modelo español con uno multilingüe sería un resultado en sí mismo.
3. **Aceptar la corrección solo cuando el modelo esté seguro**, usando la probabilidad de
   la secuencia como umbral.
4. **Medir sobre referencias limpias** (`voxpopuli_es`), para descartar del todo la
   contaminación de CIEMPIESS.

## Reproducir

```bash
.venv/bin/python research/experiments/exp-002-postcorreccion/run.py \
    --transcripciones research/experiments/exp-000-baseline/results/\
transcripciones_openai_whisper-medium__teleconciencia_es__fallback.jsonl --limite 400
```
