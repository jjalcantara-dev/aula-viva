# exp-001 — Prompting contextual con glosario de dominio

## Hipótesis

Aportar al decodificador de Whisper un glosario del dominio, en forma de prompt, reduce
los errores sobre terminología específica de la clase.

## Diseño

**Pareado.** Las dos condiciones (sin prompt / con prompt) se ejecutan sobre exactamente
los mismos clips en la misma ejecución, con la misma decodificación. Permite comparar
clip a clip en vez de dos medias, que es lo único que da algo de poder estadístico con
corpus pequeños.

**Sin fuga de información.** Los clips se barajan con semilla fija y se parten en:

- **contexto** (40%): única fuente del glosario. Nunca se evalúa
- **evaluación** (60%): aquí se mide. Su texto no interviene en el prompt

Construir el glosario con las transcripciones de evaluación sería soplarle las respuestas
al modelo, y cualquier mejora medida sería falsa.

**Estadística.** Test de signos sobre los clips que cambian, e IC 95% de la diferencia de
WER por bootstrap **remuestreando clips, no palabras** — los errores se agrupan por clip y
hablante, y tratarlos como independientes estrecharía el intervalo artificialmente.

## Resultado principal (M0) — `teleconciencia_es` ampliado, 720 clips de evaluación

14.706 palabras de referencia. Es la única ejecución con potencia estadística suficiente;
las de la sección siguiente quedaron muy por debajo y solo sirven como historia.

| | Sin prompt | Con prompt | Δ |
|---|---:|---:|---:|
| **WER** | 18.79% | 19.14% | **+0.35** (peor) |
| CER | 8.66% | 9.32% | +0.66 |
| Sustituciones | 1470 | 1404 | **−66** |
| Inserciones | 241 | 284 | **+43** |
| Borrados | 1052 | 1126 | **+74** |
| **Cobertura de terminología** | 92.11% | 93.53% | **+1.42** |
| Precisión de terminología | 92.55% | 91.51% | **−1.04** |
| F1 de terminología | 92.33% | 92.51% | +0.18 |

- IC 95% de la diferencia de WER: **[−0.52, +1.42]** → cruza el cero, **no concluyente**
- Pareado: **129 mejoran, 91 empeoran**, 500 sin cambio · test de signos **p = 0.0124**

### Lectura: dos métricas que se contradicen solo en apariencia

El test de signos es **significativo** (más clips mejoran que empeoran) pero el WER global
**empeora**. No es una contradicción: significa que los clips que empeoran lo hacen con
más intensidad de la que mejoran los que mejoran. Un promedio agregado y un recuento de
clips responden a preguntas distintas, y aquí discrepan.

El desglose de errores explica el mecanismo, y es el hallazgo de verdad:

> **El prompt hace que el modelo elija mejor las palabras (−66 sustituciones) pero que
> añada e invente más (+43 inserciones, +74 borrados).** Es decir: acierta más veces
> *qué* palabra es, y falla más veces *si* la palabra estaba.

La métrica de terminología lo confirma desde el otro lado: la **cobertura sube 1.42
puntos**, porque el prompt sí recupera términos que antes se perdían, pero la **precisión baja
1.04**, porque empieza a colar términos del glosario donde no los hay. Es exactamente el efecto
adverso para el que se diseñó esa métrica, y sin ella habría pasado desapercibido bajo un
WER plano.

### Implicación para el TFM

El prompting contextual, tal como está montado, **no es una mejora neta en WER pero sí
recupera terminología**. Para un sistema de accesibilidad esa distinción importa: el WER
trata «de» y «mitocondria» como un error cada uno, y el alumno no.

Presentar esto como «el prompting no funciona» sería una lectura pobre. La lectura
defendible es que **mejora aquello para lo que se diseñó y degrada el resto**, y que la
decisión de usarlo depende de qué se quiera optimizar. 🔴 **DIRECTOR: decidir la métrica
principal antes de congelar el protocolo (H2).**

### Advertencia sobre la métrica de terminología

Los términos peor reproducidos delatan contaminación de **R11**, no fallos del modelo:

```
ciento (0/18)   -> la referencia escribe "ciento", el modelo escribe cifras
matematicas (0/10) -> la referencia omite la tilde, el modelo escribe "matemáticas"
```

Cero aciertos en ambos casos, y en ambos el modelo tiene razón. **La métrica de
terminología hereda el problema de las referencias de CIEMPIESS** y debería usar
comparación insensible a tildes sobre este corpus, o medirse sobre `voxpopuli_es`, cuya
referencia está verificada. Pendiente.

## Resultados preliminares con muestras insuficientes (24 clips)

| Corpus | WER sin | WER con | Δ (pp) | IC 95% | Mejoran/Empeoran/Igual | p | Veredicto |
|---|---:|---:|---:|---|---|---:|---|
| `voxpopuli_es` | 9.99 | 9.60 | −0.39 | [−1.14, +0.45] | 4 / 1 / 19 | 0.375 | No concluyente |
| `teleconciencia_es` | 22.41 | 22.24 | −0.16 | [−2.40, +2.31] | 5 / 5 / 14 | 1.000 | No concluyente |
| `tedx_es` | 10.15 | 9.96 | −0.19 | [−0.61, +0.00] | 1 / 0 / 23 | 1.000 | No concluyente |

Todas las diferencias son negativas (el prompt ayuda ligeramente) y ninguna es
distinguible del ruido.

## Interpretación

**Esto NO es evidencia de que el prompting no funcione. Es evidencia de que este montaje
experimental no puede detectarlo.** Dos causas, y ambas son corregibles:

### 1. La muestra es demasiado pequeña, por diseño

Tras reservar el 40% para el glosario quedan **24 clips y 500-770 palabras** por corpus.
El cálculo de potencia (ver `corpus/FUENTES.md`) estimaba **~30.000 palabras** para
detectar diferencias de 0.5 puntos. Estamos dos órdenes de magnitud por debajo.

El IC observado lo confirma: en `teleconciencia_es` mide ±2.4 puntos. Solo detectaríamos
efectos mayores que eso, cuando lo esperable en adaptación por prompting es bastante menor.
**El experimento estaba condenado a no concluir antes de ejecutarse.**

### 2. El glosario no contiene terminología

Extraído por frecuencia sobre 16 clips, produce entre 8 y 25 términos, y son palabras
corrientes del registro, no vocabulario especializado:

```
voxpopuli      : estamos, estados, miembros, derechos, acuerdo, criterio, crisis...
teleconciencia : diagnostico, cursos, tenemos, escuela, fundacion, sospecha, padres...
tedx           : corredor, trabajo, cultural, condesa, proyecto, canina, acciones...
```

Whisper ya conoce esas palabras, así que el prompt no aporta nada. Que 19-23 de 24 clips
queden **sin cambio alguno** lo confirma: la técnica está prácticamente inerte.

## Qué hacer

1. ✅ **Corpus mayor.** Hecho: `teleconciencia_es` ampliado de 40 a 1200 clips (2,73 h,
   24.407 palabras). El IC pasó de ±2.4 puntos a ±0.95. Con esto el experimento ya
   discrimina.
2. ✅ **Métrica de terminología.** Hecha (`research/eval/metrics/terminologia.py`), y ha
   resultado ser la que aporta la información útil: sin ella el resultado habría parecido
   un empate plano.
3. **Glosario de fuente externa, no de transcripciones.** Sigue pendiente y es la mejora
   con más recorrido. Un docente aportaría el temario, las transparencias o el glosario
   de la asignatura; extraer términos por frecuencia del propio audio produce vocabulario
   corriente que el modelo ya conoce, y además obliga a sacrificar el 40% del corpus.
4. **Corregir la contaminación de la métrica de terminología** por tildes y numerales
   (ver advertencia arriba), o repetir sobre `voxpopuli_es`, con referencia verificada.
5. **Investigar el aumento de borrados e inserciones.** Es el efecto que arruina el WER.
   Hipótesis a comprobar: el prompt ocupa contexto del decodificador y desplaza audio, o
   induce a completar frases que el hablante dejó a medias.

## Reproducir

```bash
.venv/bin/python research/experiments/exp-001-prompting/run.py \
    --manifiesto research/corpus/manifests/voxpopuli_es.jsonl \
    --modelo openai/whisper-medium
```
