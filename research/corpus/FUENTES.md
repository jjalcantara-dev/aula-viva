# Corpus candidatos — español con transcripción de referencia

Documento vivo. Riesgos asociados: **R1** (disponibilidad), **R11** (calidad de la
referencia), **R12** (efecto suelo).

**Estado de verificación:** ✅ comprobado en M0 · ❓ sin comprobar · ⛔ inaccesible ahora

## Cuánto corpus hace falta

Calculado a partir del barrido de M0. Con 499 palabras de referencia, el error estándar
del WER a ~3% ronda **0.8 puntos**, así que el intervalo de confianza al 95% es de unos
±1.5 puntos: con esa muestra `medium`, `large-v3-turbo` y `large-v3` son
**estadísticamente indistinguibles**.

Para detectar diferencias del orden de **0.5 puntos** —la escala en la que se moverán las
técnicas de adaptación— hacen falta del orden de **30.000 palabras de referencia**, que a
ritmo de habla normal son **3-4 horas de audio transcrito**.

> ⚠️ Es una cota **optimista**: supone errores independientes, cuando en realidad se
> agrupan por hablante y por grabación. Contar con más, y con variedad de ponentes.

---

## ⚠️ Sesgo dialectal de las mediciones de M0

**Los tres corpus medidos en M0 son latinoamericanos, sin excepción:**

| Corpus medido | Variedad | Origen |
|---|---|---|
| `fleurs_es` | Latinoamérica | Config `es_419` — **FLEURS no tiene español peninsular**; sus únicas variantes ibéricas son `ca_es` (catalán) y `gl_es` (gallego) |
| `tedx_es` | México | CIEMPIESS (UNAM) |
| `teleconciencia_es` | México | CIEMPIESS (UNAM) |

Si el sistema se destina a un centro educativo español, **ninguna cifra de M0 es
representativa del escenario de despliegue**. Las diferencias fonéticas relevantes para
ASR entre variedades (seseo/distinción, aspiración de /s/, /θ/, entonación) pueden mover
el WER de forma apreciable, y además interactúan con la adaptación al dominio: una técnica
que ayude en español mexicano no tiene por qué ayudar igual en peninsular.

**Consecuencia:** el conjunto de evaluación debe ser peninsular, o la comparativa debe
incluir la variedad como factor explícito. 🔴 **DIRECTOR: decidir cuál de las dos.**

### Candidatos peninsulares ✅

| Corpus | Ejemplos | Campo | Registro | Metadatos |
|---|---:|---|---|---|
| `facebook/voxpopuli` (`es`) | 50.922 / 1.631 / 1.528 | `normalized_text` | Parlamento Europeo | **`accent`, `is_gold_transcript`** |
| `ymoslem/MediaSpeech` (`es`) | 2.507 | `sentence` | Medios españoles, locución | — |
| `tj-solergibert/Europarl-ST` | 116.138 train | `transcriptions` | Parlamento Europeo | CC BY-NC 4.0 |
| Albayzin / RTVE | ~500 h | — | Radiotelevisión española | ⛔ Solicitud |

**`facebook/voxpopuli` (`es`) es el mejor candidato peninsular verificado.** Dos razones
que lo separan del resto:

- **`is_gold_transcript`** marca las transcripciones verificadas manualmente. Filtrando por
  ese campo se ataca directamente **R11**, que es el problema que arruina a CIEMPIESS
- **`accent`** permite caracterizar —o filtrar— la variedad de cada hablante, y por tanto
  documentar la composición dialectal del corpus en la memoria en vez de suponerla

Registro: discurso parlamentario, formal pero pronunciado en vivo con desviaciones del
guion. No es un aula, pero es monólogo expositivo peninsular espontáneo.

> **Albayzin/RTVE** sigue siendo el candidato peninsular más rico (~500 h de RTVE 2015-2018,
> con diversidad de acentos, habla solapada, espontánea y ruido de fondo), pero requiere
> solicitud al organizador del reto. Segunda petición a cursar después de poliMedia.

---

## Nivel 1 — Dominio educativo real (objetivo)

### poliMedia / transLectures (UPV) ❓ ⛔
Lo más parecido a lo que necesita este TFM: **más de 115 horas de clases universitarias
en español transcritas manualmente**, del repositorio poliMedia de la Universitat
Politècnica de València (>10.000 minilecciones, 1.373 docentes), transcritas en el marco
del proyecto europeo transLectures y descritas como disponibles para la comunidad
investigadora.

- **Dominio:** exactamente el del TFM — clase universitaria grabada, en español
- **Problema:** `mllp.upv.es` **rechazó la conexión** de forma repetida en M0 (posible
  bloqueo geográfico o caída). No se ha podido confirmar procedimiento ni licencia
- **Verificado por otra vía (M0):** el GitHub público del grupo (`github.com/mllpresearch`)
  distribuye **Europarl-ASR**, **ESO-dataset** y **LHCP-ASR**, todos en inglés.
  **poliMedia NO está publicado ahí**, así que el único camino es la solicitud directa
- **Acción:** escribir al grupo MLLP-VRAIN de la UPV solicitando acceso con fines
  académicos. Borrador preparado en `docs/solicitud-polimedia.md`. **Hacerlo ya**: una
  petición institucional puede tardar semanas y es el camino crítico del proyecto
- 🔴 **DIRECTOR:** una petición avalada por el director pesa más que una individual

### Albayzin / RTVE Speech-to-Text ❓
Datos de radiotelevisión española usados en los retos Albayzin-RTVE (2018, 2020), con
transcripción. Dominio informativo, no educativo, pero español peninsular real y
espontáneo. Acceso mediante solicitud al organizador del reto.

---

## Nivel 2 — Proxies cercanos, accesibles ya ✅

Verificados accesibles en M0 vía Hugging Face.

| Corpus | Ejemplos | Tamaño | Campo de referencia | Dominio | Variedad |
|---|---:|---:|---|---|---|
| `ciempiess/tedx_spanish` | 11.243 | 1,71 GB | `normalized_text` | Charlas TEDx | México |
| `ciempiess/tele_con_ciencia` | 12.073 | 2,03 GB | `normalized_text` | Divulgación científica en TV | México |
| `tj-solergibert/Europarl-ST` | 116.138 train | — | `transcriptions` | Debate parlamentario | **Peninsular** |

**`Europarl-ST`** (del propio grupo MLLP de la UPV) ✅ — audio fuente en nueve idiomas,
español incluido, con transcripción. Licencia **CC BY-NC 4.0**, derechos de la Unión
Europea; el uso académico encaja, pero **hay que declararla** y descarta cualquier
explotación comercial de la app.

Registro: discurso formal preparado pero pronunciado en vivo, con desviaciones del guion.
No es una clase, pero es **español peninsular espontáneo de monólogo expositivo**, que
resuelve el desajuste dialectal de CIEMPIESS. Buen candidato para conjunto de contraste
o incluso como material de adaptación.

**`tedx_spanish`** es el mejor sustituto disponible sin trámites: monólogo expositivo ante
público, habla espontánea con muletillas y autocorrecciones, terminología variada. Es la
estructura discursiva de una clase magistral.

**`tele_con_ciencia`** aporta lo que a TEDx le falta: densidad de terminología técnica
sostenida, que es justo donde se espera que actúe la adaptación al dominio.

> ⚠️ Ambos son español de México (CIEMPIESS es de la UNAM). Si el sistema se destina a un
> centro español, hay desajuste de variedad dialectal. **Declararlo como limitación**, o
> compensar con material peninsular. 🔴 **DIRECTOR: ¿es aceptable?**

### 🔬 Auditoría de referencia (M0) — resultado

Aplicado el protocolo de admisión con `whisper-medium` y decodificación por reintento de
temperatura, 40 clips por corpus:

| Corpus | Variedad | WER básico | WER sin tildes | Δ por tildes |
|---|---|---:|---:|---:|
| `voxpopuli_es` | Peninsular | 10.44% | 10.37% | **−0.07** ✅ |
| `fleurs_es` | Latinoamérica | 3.21% | 3.21% | **0.00** ✅ |
| `mediaspeech_es` | Peninsular | 14.72% | 13.03% | −1.70 |
| `tedx_es` | México | 10.22% | 6.74% | **−3.48** ⚠️ |
| `teleconciencia_es` | México | 22.65% | 14.11% | **−8.54** ⚠️ |

**Δ por tildes funciona como termómetro de la calidad de la referencia.** Cuanto más
negativo, más errores de acentuación tiene la transcripción de referencia y menos fiable
es la medición. `voxpopuli_es` (transcripción verificada, `is_gold_transcript`) es el
único candidato peninsular con artefacto prácticamente nulo.

**Hallazgo:** en FLEURS las tildes no cuestan nada (referencia correcta). En los dos
corpus de CIEMPIESS **la referencia omite tildes de forma sistemática y contiene erratas**:

```
'galerias'  -> 'galerías'      'excepcion'    -> 'excepción'       'vivia' -> 'vivía'
'peridendo' -> 'perdiendo'     'rencontrarnos'-> 'reencontrarnos'  'vesido'-> 'vestido'
```

En todos esos casos **el modelo escribe bien y la referencia mal**. Entre un tercio y un
40% del WER medido sobre CIEMPIESS es ruido de la referencia, no error de reconocimiento.

**Consecuencia metodológica — 🔴 DIRECTOR, decisión antes de H2:**
Si se adopta CIEMPIESS hay que elegir, y ninguna opción es gratis:

1. **Usar `sin_tildes` como métrica principal.** Barato, pero pierde errores de acentuación
   que en español sí son léxicos (*papa*/*papá*, *marco*/*marcó* — este último aparece
   literalmente en la muestra). Contradice el criterio inicial de tratar `sin_tildes`
   solo como análisis de sensibilidad
2. **Corregir la referencia a mano** en el subconjunto de evaluación. Metodológicamente
   lo mejor, y coste asumible si el subconjunto es pequeño. Debe documentarse
3. **Restaurar tildes automáticamente** y verificar una muestra. Riesgo de introducir
   sesgo a favor del modelo

**Recomendación:** opción 2 sobre el conjunto de evaluación, y reportar siempre las dos
cifras (con y sin tildes) como cota superior e inferior.

### Dificultad relativa: dónde hay margen para las técnicas

`teleconciencia_es` es, con diferencia, el material más difícil (13.63% incluso ignorando
tildes, frente a 6.74% de TEDx y 3.01% de FLEURS). **Es donde las técnicas de adaptación
tienen más margen para demostrar efecto** y por tanto el candidato más informativo para
la comparativa, pese a no ser aula real.

---

## Nivel 3 — Contraste y control ✅

Sirven para caracterizar el efecto suelo (R12), no para responder la pregunta.

| Corpus | Ejemplos | Dominio | Uso previsto |
|---|---:|---|---|
| `google/fleurs` (`es_419`) | 408 val | Frases enciclopédicas leídas | **Ya usado en exp-000.** Techo de calidad |
| `facebook/multilingual_librispeech` (`spanish`) | 2.385 test / 220.701 train | Audiolibros | Contraste voz leída; volumen para LoRA |
| `ciempiess/librivox_spanish` | 36.338 | Audiolibros | Alternativa de volumen |
| `PolyAI/minds14` (`es-ES`) | — | Banca telefónica 8 kHz | Suelo de calidad acústica |

**Nota sobre MLS español:** 220.701 ejemplos de entrenamiento. Es el único candidato
verificado con volumen suficiente para un fine-tuning con LoRA de verdad. Dominio
equivocado, pero resuelve el problema de cantidad si el corpus educativo se queda corto.

---

## Inaccesibles / con trámite

| Corpus | Estado |
|---|---|
| `mozilla-foundation/common_voice_*` | ⛔ Requiere autenticación y aceptar términos en HF. Trámite trivial, pendiente |
| OpenSLR SLR67 (TEDx Spanish) | Fuente original de `ciempiess/tedx_spanish`; usar la copia en HF |
| OpenSLR SLR61/71-75 | Español rioplatense, chileno, colombiano, peruano, puertorriqueño, venezolano. Frases cortas leídas, no educativo |
| OpenSLR SLR39 (Heroico) | Espejo de LDC |

---

## Nivel 4 — Grabación propia

Plan de respaldo si nada de lo anterior encaja. Cubre el dominio exacto y la variedad
dialectal correcta, a cambio de coste de transcripción y de trámite de protección de datos.

- **Antes de comprometerse:** cronometrar la transcripción manual de 30 minutos. Ese dato
  decide si 3-4 horas son alcanzables
- Consentimiento informado, anonimización de nombres, y decidir de antemano si el corpus
  podrá publicarse (**R9**)
- Combinable: grabación propia como conjunto de evaluación + corpus público para adaptación

---

## Protocolo de admisión de un corpus

Antes de adoptar cualquier candidato, y por **R11**:

1. Escuchar y revisar a mano una muestra (≥20 clips) contra su transcripción
2. Contar cuántas referencias tienen errores reales. Si es apreciable, descartar o corregir
3. Comprobar si la referencia está normalizada (minúsculas, sin puntuación, numerales) y
   registrarlo — condiciona el normalizador del protocolo (H2)
4. Anotar licencia y condiciones de redistribución **antes** de meter nada en el repositorio
5. Registrar variedad dialectal, número de hablantes y condiciones acústicas
