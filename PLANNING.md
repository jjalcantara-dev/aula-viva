# PLANNING — TFM Máster en IA (UNIR)

**Título provisional:** Sistema de accesibilidad educativa en tiempo real con transcripción adaptativa: comparativa de técnicas sobre modelos ASR en español

**Modalidad:** individual · **Naturaleza:** doble núcleo (Tipo 3 investigador + Tipo 2 aplicado)

> **Estado de este documento:** esqueleto flexible. Todo lo marcado con 🔴 **DIRECTOR** son decisiones que NO deben cerrarse unilateralmente. Todo lo marcado con ⚠️ es un riesgo o una advertencia de realismo.

> **Nota sobre fechas:** este plan usa fases relativas (M0 = mes de arranque … M9 = entrega) en lugar de fechas absolutas, para no cerrar un cronograma antes de tiempo. Asume ~10 meses de calendario y un presupuesto realista de 12-15 h/semana. Ajustar el ancla temporal cuando esté confirmada la convocatoria.

---

## 1. Estructura de la memoria (impuesta por la plantilla UNIR)

Extraído de `Plantilla LATEX TFE TFM UNIR/plantilla.tex` y `estilo_unir-1.sty`. No hay nada añadido aquí que no esté en la plantilla.

### Preliminares (`\frontmatter`)
| Elemento | Notas de la plantilla |
|---|---|
| Portada | Autogenerada. Campos: `\titulacion`, `\title`, `\author`, `\director`, `\nombreciudad`, `\date` |
| Índice de Contenidos | `\tableofcontents` |
| Índice de Ilustraciones | `\listoffigures` |
| Índice de Tablas | `\listoftables` |
| **Resumen** | Máx. **150 palabras**. Debe incluir: objetivo/propósito, metodología, resultados, conclusiones. + **3-5 palabras clave** en español |
| **Abstract** | Mismo contenido y estructura, en inglés. + 3-5 keywords en inglés |

### Cuerpo (`\mainmatter`)
1. **Introducción** — la plantilla sugiere tres apartados: motivación/justificación del tema · planteamiento del trabajo · estructura del trabajo. La plantilla insiste en que este capítulo debe permitir entender por sí solo qué se pretendía, a qué conclusiones se llegó y con qué procedimiento.
2. **Contexto y Estado del Arte**
3. **Identificación de Requisitos**
4. **Objetivos**
5. **Desarrollo del trabajo**
6. **Conclusiones y Trabajo Futuro**

### Cierre
- **Referencias** — `\bibliographystyle{apacite}` (estilo APA), fuente `bibliografia.bib`
- **Apéndices** — `\appendix` + `\chapter{Apendices}`

### Formato impuesto por `estilo_unir-1.sty`
- Clase `book`, 11pt, A4, español (`babel`), `inputenc` utf8 (ya configurado para Linux)
- **Interlineado 1.5** (`\baselinestretch{1.5}`)
- Ecuaciones y figuras numeradas por capítulo; títulos de capítulo en azul UNIR
- Cabecera derecha: autor + titulación. Pie derecho: número de página
- Entornos de teorema predefinidos: `teo`, `prop`, `coro`, `lema`, `defi`, `obs`, `ex`

### Lo que la plantilla NO especifica
No inventar respuesta a esto; preguntar o consultar la normativa de la asignatura:
- Extensión total de la memoria (páginas / palabras)
- Profundidad de subsecciones permitida
- Si se exige declaración de originalidad, anexo de código, o anexo de uso de IA
- Si el orden de capítulos es rígido o adaptable

### 🔴 DIRECTOR — decisiones sobre la estructura
- **El orden Requisitos (cap. 3) → Objetivos (cap. 4) es contraintuitivo** y "Identificación de Requisitos" encaja mal en un trabajo de investigación. Propuesta a validar: usar el cap. 3 para requisitos *duales* (requisitos funcionales de la aplicación + requisitos del diseño experimental: qué debe cumplir el corpus, las métricas y el protocolo). Confirmar antes de escribir nada.
- **Dónde vive la comparativa empírica.** El cap. 5 "Desarrollo del trabajo" tendrá que albergar metodología experimental, ejecución, resultados y discusión *además* del desarrollo de la aplicación. Es mucho para un solo capítulo. Preguntar si se admite estructurarlo en secciones claramente separadas (5.1 Metodología experimental / 5.2 Resultados / 5.3 Desarrollo de la aplicación) o si se permite desdoblar en capítulos.
- **Peso relativo Tipo 2 vs Tipo 3** en la evaluación. Determina cuánto espacio y cuánto esfuerzo merece cada parte.

### Detalle técnico menor
En `plantilla.tex:8` se aplica `\numberwithin` a figuras y ecuaciones, pero la línea equivalente para tablas está comentada (líneas 12, 15, 18). Las tablas saldrán con numeración corrida en lugar de por capítulo. Decidir y dejarlo coherente.

---

## 2. Estructura de repositorio

Principio rector: **`research/` y `app/` no comparten código.** Se comunican por un contrato documentado (la interfaz del servicio ASR). Si mañana hay que recortar la aplicación o cambiar de técnica ganadora, ninguna de las dos partes arrastra a la otra. Esto también es lo que te permite defender ante el tribunal qué es contribución investigadora y qué es ingeniería.

```
TFM-IA/
├── README.md                    # qué es esto, cómo se arranca cada parte
├── PLANNING.md                  # este archivo
├── .gitignore
│
├── docs/                        # trazabilidad del proceso (no es la memoria)
│   ├── reuniones/               # acta breve por reunión con el director: acuerdos y decisiones
│   ├── decisiones/              # una decisión por archivo: contexto, opciones, elección, motivo
│   └── preguntas-director.md    # cola viva de preguntas pendientes
│
├── memoria/                     # PARTE ESCRITA (LaTeX)
│   ├── template-original/       # copia intacta de la plantilla UNIR, nunca se toca
│   ├── main.tex
│   ├── estilo_unir-1.sty
│   ├── capitulos/               # 01-introduccion.tex … 06-conclusiones.tex
│   ├── apendices/
│   ├── figuras/                 # SOLO figuras generadas o finales
│   ├── tablas/                  # tablas .tex generadas desde research/results/
│   ├── bibliografia.bib
│   └── Makefile                 # compilación reproducible
│
├── research/                    # ══ NÚCLEO INVESTIGADOR (Tipo 3) ══
│   ├── README.md                # cómo reproducir cualquier experimento
│   ├── corpus/
│   │   ├── raw/                 # audio original — GITIGNORED
│   │   ├── processed/           # audio normalizado — GITIGNORED
│   │   ├── manifests/           # ✔ EN GIT: jsonl/csv con id, ruta, duración,
│   │   │                        #   transcripción de referencia, split, licencia, procedencia
│   │   └── FUENTES.md           # ✔ EN GIT: origen, licencia y condiciones de uso de cada fuente
│   ├── src/                     # código compartido entre experimentos
│   │   ├── data/                # carga de corpus, splits, normalización de audio
│   │   ├── asr/                 # envoltorio de inferencia (base y variantes)
│   │   └── text/                # normalización de texto previa a métricas
│   ├── experiments/             # un experimento = una carpeta = una config = un resultado
│   │   ├── exp-000-baseline/
│   │   ├── exp-001-prompting/
│   │   ├── exp-002-postcorreccion-llm/
│   │   └── exp-003-lora/
│   │       ├── README.md        # hipótesis, qué se compara, cómo se lanza
│   │       ├── config.*         # TODOS los hiperparámetros, incluida la semilla
│   │       └── results/         # salida cruda: transcripciones, métricas, logs
│   ├── eval/                    # ══ evaluación, aislada y estable ══
│   │   ├── metrics/             # WER, CER, y las que se acuerden
│   │   ├── normalizers/         # reglas de normalización (mayúsculas, puntuación, números)
│   │   ├── stats/               # variabilidad, intervalos, tests si se exigen
│   │   └── report/              # genera las tablas/figuras que consume memoria/
│   └── results/                 # ══ ÚNICO PUENTE research → memoria ══
│       └── (tablas .tex y figuras versionadas, siempre regenerables)
│
├── app/                         # ══ NÚCLEO APLICADO (Tipo 2) — .NET ══
│   ├── src/
│   │   ├── <Proyecto>.Web/      # ASP.NET Core + Blazor Server + SignalR
│   │   ├── <Proyecto>.Core/     # dominio: sesión, transcripción, conceptos clave
│   │   └── <Proyecto>.Asr/      # adaptador al motor ASR — LA FRONTERA
│   ├── tests/
│   └── deploy/                  # despliegue en red local del centro
│
└── tools/                       # scripts de entorno, arranque, verificación de GPU
```

### Reglas que hacen que esto funcione

1. **Nunca audio en git.** Solo manifiestos + un script que reconstruye `corpus/` desde las fuentes. Si el corpus se pierde, se regenera; si no está documentado en `FUENTES.md`, no existe.
2. **Todo resultado es regenerable con un comando** desde su `config.*` + el commit correspondiente. Anota el hash del commit en la salida.
3. **`research/results/` es la única entrada a la memoria.** Ninguna cifra se copia a mano al LaTeX; se genera. Evita la clase de error que destroza un TFM: una tabla que no coincide con los datos.
4. **`eval/` se congela antes de empezar la comparativa.** Si cambias el normalizador de texto a mitad, los experimentos dejan de ser comparables entre sí.
5. **La plantilla original se conserva intacta** en `memoria/template-original/`. Trabajas sobre la copia.
6. **`app/` no importa nada de `research/`.** La aplicación consume un servicio ASR a través de `<Proyecto>.Asr`, cuyo contrato está documentado. Es lo que te permite enseñar una demo con la técnica base aunque la comparativa aún no haya concluido.

### 🔴 DIRECTOR — decisiones sobre el repositorio
- Si el corpus tiene restricciones de licencia o contiene voces reales, **si el repositorio puede ser público**.
- Si se exige entregar el código como anexo, en qué formato y con qué nivel de documentación.

### Decisión abierta (no urgente)
Versionado de datos: git-lfs, una herramienta de versionado de datasets, o simplemente manifiestos + script de reconstrucción. **Empieza por lo último**, que es lo más barato, y solo escala si el corpus crece. No introduzcas herramienta nueva hasta que duela.

---

## 3. Planning por fases

Fases relativas, con solapamiento deliberado. **No son estancos**: la redacción y la aplicación corren en paralelo a la investigación desde el principio.

```
M0    M1    M2    M3    M4    M5    M6    M7    M8    M9
│                                                       │
├─F0──┤
      ├─────F1─────┤
                   ├──F2──┤
                          ├───────F3────────┤
            ├────────────F4 (app)───────────┤
      ├──────────────F5 (redacción)──────────────────┤
                                              ├──F6───┤
```

### F0 · Arranque y cierre de alcance (M0 → M1)
Objetivo: eliminar incertidumbre técnica y metodológica **antes** de comprometerse a nada.

- Entorno funcionando: GPU AMD reconocida, Whisper transcribiendo audio real de extremo a extremo
- Primera medición propia de WER, aunque sea sobre 5 minutos transcritos a mano
- Barrido de corpus candidatos con licencia, horas y disponibilidad de transcripción de referencia
- Esqueleto .NET que mueve audio del navegador al servidor y devuelve texto por SignalR (con texto simulado, sin ASR real)
- Reunión de cierre de alcance con el director

🔴 **DIRECTOR — a cerrar en F0:**
- **Qué técnicas entran finalmente.** Prompting contextual / post-corrección con LLM / LoRA. Recomendación: comprometerse a **dos**, con la tercera declarada explícitamente como opcional.
- **Qué corpus se acepta.** ¿Corpus público con referencia? ¿Vídeo educativo con subtítulos verificados manualmente? ¿Grabación propia con transcripción manual? ¿Mezcla?
- **Qué métricas.** ¿Basta WER/CER, o se exige alguna métrica orientada a accesibilidad (p. ej. acierto sobre terminología del dominio, que es lo que de verdad importa a un alumno con discapacidad auditiva)?
- **Si se exige análisis de significancia estadística** o basta con reportar variabilidad.
- **Si la aplicación debe evaluarse formalmente** (usuarios, evaluación heurística de accesibilidad) o basta demo funcional. ⚠️ Esto puede duplicar el trabajo del núcleo Tipo 2.

🎯 **HITO CRÍTICO H1 — corpus confirmado.** Si al final de F1 no hay corpus con transcripción de referencia, no hay comparativa posible y hay que replantear el TFM. Es el punto de no retorno.

### F1 · Estado del arte y construcción del corpus (M1 → M3)
- Revisión bibliográfica: ASR en español, adaptación a dominio, las técnicas seleccionadas
- Corpus definitivo: recogida, normalización, splits, documentación de procedencia y licencias
- **Protocolo de evaluación escrito y congelado** antes de ejecutar nada
- Redacción en marcha del cap. 2 (Estado del Arte)

🎯 **HITO CRÍTICO H2 — protocolo de evaluación congelado.** Escrito, versionado, acordado con el director. Definir *antes* de ver resultados qué se mide y cómo evita el sesgo de ajustar el criterio a lo que salió.

### F2 · Baseline reproducible (M3 → M4)
- Whisper sin adaptar sobre el corpus completo
- Pipeline de evaluación automatizado de punta a punta
- Caracterización del baseline por condiciones (ponente, ruido, terminología)

🎯 **HITO CRÍTICO H3 — baseline reproducible con un comando.** Si esto no está sólido, todo lo que venga después es ruido.

### F3 · Comparativa — el núcleo del TFM (M4 → M7)
Ejecutar las técnicas **en orden de coste creciente**, para que el recorte por retraso sea automático:

1. **Prompting contextual** — la más barata. Sin entrenamiento
2. **Post-corrección con LLM ligero local** — coste medio. Sin entrenamiento
3. **Fine-tuning con LoRA** — la más cara. Requiere entrenamiento funcionando en la GPU y datos suficientes

Cada técnica produce: resultados crudos, tabla comparativa, análisis de errores cualitativo.

🎯 **HITO CRÍTICO H4 — primera técnica completa con resultados frente al baseline.** A partir de aquí ya tienes un TFM defendible aunque todo lo demás se caiga.

### F4 · Aplicación .NET (M2 → M7, en paralelo)
- MVP: audio en vivo → ASR → subtítulos en tiempo real vía SignalR
- Integración del motor ASR real detrás del adaptador
- Resaltado visual de conceptos clave
- Despliegue en red local + medición de latencia

⚠️ **"Tiempo real" hay que definirlo con un número.** Fija un umbral de latencia medible (p. ej. retardo extremo a extremo por debajo de X segundos) y mídelo. Sin umbral declarado, la afirmación es indefendible ante el tribunal.

### F5 · Redacción (M1 → M8, continua)
No es una fase final. Se escribe en paralelo desde F1. Orden natural: cap. 2 durante F1 → caps. 3 y 4 tras cerrar alcance → cap. 5 a medida que salen resultados → caps. 1 y 6 al final, cuando ya sabes qué has hecho.

🎯 **HITO CRÍTICO H5 — borrador completo al director con margen para DOS iteraciones de revisión.** Trabaja hacia atrás desde la fecha de entrega. Este hito es el que más gente falla.

### F6 · Cierre (M8 → M9)
- Congelación de resultados: nada de experimentos nuevos
- Revisión de coherencia entre cifras del texto y `research/results/`
- Formato, referencias, índices, resumen/abstract (se escriben **los últimos**)
- Preparación de la defensa

---

## 4. Puntos de recorte de alcance

**Si vas con retraso, recorta EN ESTE ORDEN.** Decidirlo ahora, en frío, evita que a mitad de camino recortes lo que no debías.

| # | Qué se recorta | Cómo | Se justifica en la memoria como |
|---|---|---|---|
| 1 | Detección semántica de conceptos clave | Lista estática de terminología por asignatura | Trabajo futuro |
| 2 | **LoRA** | Fuera si no ha arrancado al final de M6 | Limitación reconocida + trabajo futuro |
| 3 | Post-corrección con LLM | Reducir a un solo modelo y una configuración | Alcance acotado |
| 4 | Tiempo real estricto | Pasar a casi-tiempo-real por bloques | Decisión de diseño justificada por latencia medida |
| 5 | Multiusuario / multi-aula | Un único emisor y varios receptores pasivos | Alcance acotado |
| 6 | Tamaño del corpus | Menos horas o menos condiciones, mejor caracterizadas | Limitación con impacto declarado en la validez |

**Núcleo intocable — nunca recortes esto:**
> Baseline reproducible + **al menos una** técnica de adaptación evaluada rigurosamente + análisis honesto de resultados.
>
> Eso es un TFM tipo 3 completo. Tres técnicas mal medidas valen menos que una bien medida.

---

## 5. Riesgos y mitigaciones

### ⚠️ R1 — Corpus educativo en español con transcripción de referencia (RIESGO Nº 1)
Sin transcripción de referencia no hay WER, y sin WER no hay comparativa. Ya lo has identificado tú, y tienes razón en que es el riesgo dominante.

**Mitigación, en tres planes simultáneos desde M0:**
- **Plan A:** corpus públicos en español con transcripción verificada. Aunque no sean estrictamente educativos, sirven si documentas el desajuste de dominio
- **Plan B:** material educativo con subtítulos existentes, **verificados manualmente** sobre una muestra antes de fiarte de ellos. Los subtítulos automáticos no valen como referencia
- **Plan C:** grabación propia con transcripción manual de un subconjunto
- **Acción concreta esta semana:** transcribe a mano 30 minutos de audio educativo real y cronométralo. Sabrás cuántas horas de referencia puedes permitirte, y esa cifra decide el diseño experimental completo

### ⚠️ R11 — Calidad de la transcripción de referencia (hermano de R1, detectado en M0)
Riesgo no previsto en la propuesta. Si la referencia tiene errores, se mide el ruido de
la referencia y no el del modelo — y el error se propaga a toda la comparativa sin dar
la cara, porque el WER sigue saliendo con dos decimales muy convincentes.

**Evidencia (M0):** en la muestra de FLEURS, `whisper-medium` produce `'mayorca' → 'mallorca'`
y `'velásquez' → 'velázquez'`. **El modelo escribe mejor que la referencia** y se le penaliza.
Además, el 43% de las sustituciones son numerales (`'ocho' → '8'`) y expansión correcta de
abreviaturas (`'ee','uu' → 'estados','unidos'`), que no son errores acústicos.

**Mitigación:**
- Auditar a mano una muestra de cualquier corpus candidato **antes** de adoptarlo. Que
  "tenga transcripción" no basta: hay que mirarla.
- Fijar la normalización de numerales y abreviaturas en el protocolo (H2) y justificarla.
- Reportar en la memoria el WER con y sin esas normalizaciones, como cota superior e
  inferior honesta de la calidad real.

### 🔴 R15 — Sin director asignado (situación en M0)
No hay director asignado todavía. Es un riesgo de **proceso**, no técnico, y por eso es
fácil de subestimar: no impide trabajar, pero bloquea el cierre de alcance.

**Qué bloquea concretamente:** las ~14 decisiones marcadas 🔴 en
`docs/preguntas-director.md`, entre ellas qué técnicas se comprometen, qué corpus se
acepta, si la variedad dialectal entra como factor, y si se admite una métrica de
terminología además del WER. Esa última puede decidir si las técnicas parecen funcionar.
También impide el hito de cierre de alcance de F0 y debilita la solicitud a la UPV.

**Mitigación:**
- **Seguir avanzando en lo que no depende de nadie**: infraestructura experimental,
  ampliación de corpus, integración del ASR en la aplicación, barrido de ventana. En M0
  esto ya ha producido resultados aprovechables sin ninguna decisión de dirección.
- **Mantener `docs/preguntas-director.md` como cola viva**, con datos medidos en lugar de
  intuiciones. Cuando llegue el director, la primera reunión será mucho más productiva.
- **Tomar decisiones provisionales documentadas**, no quedarse parado: elegir por defecto
  razonable, dejar registro del porqué en `docs/decisiones/` y marcar como revisable.
- **Reclamar la asignación a la universidad.** Es el único punto donde conviene insistir:
  cada semana sin director es una semana de decisiones acumuladas.

### ⚠️ R14 — La configuración de decodificación es un factor de confusión (detectado en M0)
El WER de un modelo Whisper **no depende solo del modelo**: depende de cómo se decodifica.
Comparar técnicas de adaptación sin fijar la decodificación mide artefactos de
decodificación en lugar del efecto de la adaptación, y el resultado sería invalidable.

**Evidencia (M0), `large-v3-turbo` sobre `voxpopuli_es`:**

| Decodificación | WER | Clips truncados |
|---|---:|---:|
| Voraz (greedy simple) | 24.22% | 6 / 40 |
| Con reintento por temperatura | **11.53%** | **2 / 40** |

Efecto sobre los 15 experimentos (3 modelos × 5 corpus): el reintento **cuesta entre 0.2
y 0.4 puntos** en los corpus limpios —a veces sustituye una hipótesis voraz que ya era
buena— y **ahorra entre 4 y 13 puntos** en los difíciles. Las salidas gravemente anómalas
bajan de 15 a 3 en total, y las 3 restantes son todas de `turbo`.

Con decodificación voraz el modelo no solo trunca: **inventa frases plausibles del
dominio**. En varios clips emitió `"Gracias, señora presidenta."` en lugar del contenido
real — fluido, verosímil y falso. En otro produjo `"Sorry."`, es decir **fuga de idioma
pese a forzar `language="es"`**.

Recuento de salidas gravemente truncadas (<25% de las palabras de la referencia), con
decodificación voraz sobre los cinco corpus:

| Modelo | Total graves | Dónde |
|---|---:|---|
| `large-v3-turbo` | **10** | `voxpopuli_es` (6), `mediaspeech_es` (4) |
| `medium` | 3 | `mediaspeech_es` (3) |
| `small` | 2 | `mediaspeech_es` (2) |

**No es un problema exclusivo de `turbo`**: aparece en los tres modelos y solo en los dos
corpus peninsulares, que son los de clips más largos. Pero `turbo` lo sufre tres veces más
y es el único al que le cambia la conclusión: sin corregir la decodificación, se le
habría descartado por motivos equivocados.

Al activar el reintento con temperatura, cuatro de los seis clips se recuperan; uno pasa
de **100% a 4.5%** de WER.

**Por qué importa para accesibilidad, más allá de la métrica:** una alucinación fluida es
el peor modo de fallo posible en un subtítulo. Un alumno con discapacidad auditiva no
tiene forma de detectar que la frase es inventada, porque suena perfectamente razonable.
Esto merece medición explícita en la comparativa, no solo WER agregado.

**Mitigación:**
- `run.py` expone `--decodificacion {voraz, fallback}` y **la incluye en el nombre del
  resultado**: dos ejecuciones con distinta decodificación no se pueden confundir
- Congelar la configuración en H2 junto con el normalizador
- Añadir a la evaluación una métrica de truncamiento/alucinación (proporción de clips con
  salida anómalamente corta), no solo WER

### ⚠️ R13 — Desajuste de variedad dialectal (detectado en M0)
El sistema se destina a un centro educativo **español**, pero **el 100% de los corpus
medidos en M0 son latinoamericanos**: `fleurs_es` usa la configuración `es_419`
(Latinoamérica — FLEURS no ofrece español peninsular, solo catalán y gallego), y los dos
corpus de CIEMPIESS son mexicanos (UNAM).

**Por qué importa más de lo que parece:** las diferencias fonéticas entre variedades
(seseo/distinción, aspiración de /s/, /θ/, entonación) mueven el WER de forma apreciable,
y además **interactúan con la adaptación al dominio**. Una técnica que mejore el
reconocimiento en español mexicano no tiene por qué mejorarlo igual en peninsular, así que
un resultado obtenido sobre CIEMPIESS no se transfiere sin más al escenario de despliegue.
Es un riesgo de **validez externa**: los resultados podrían ser correctos y aun así no
responder la pregunta que importa.

**Medición (M0, posterior al registro de este riesgo):** a **registro equivalente**, la
diferencia dialectal resulta **pequeña**: `voxpopuli_es` (peninsular, parlamentario) da
10.44% y `tedx_es` (mexicano, charla espontánea) 10.22% con `whisper-medium`. Lo que
domina el WER no es la variedad sino el registro — de voz leída (3.21%) a divulgación
espontánea (22.65%) hay un factor de 7.

Eso **rebaja la severidad** de este riesgo pero no lo elimina: el conjunto de evaluación
debe ser peninsular por **representatividad del escenario de despliegue**, no porque el
WER vaya a ser muy distinto. Y queda sin medir si las técnicas de adaptación transfieren
igual entre variedades, que es la parte del riesgo que sigue viva.

**Mitigación:**
- Conjunto de evaluación **peninsular**. Recomendado tras M0: **`voxpopuli_es`**, único
  candidato peninsular con transcripción verificada (`is_gold_transcript`) y artefacto de
  acentuación nulo (Δ tildes −0.07). Resuelve R11 y R13 a la vez. Otros candidatos:
  `facebook/voxpopuli` (`es`) —con `is_gold_transcript` y `accent`, lo que ataca de paso
  R11—, `ymoslem/MediaSpeech` (`es`), `tj-solergibert/Europarl-ST`
- Alternativa: incluir la variedad como **factor explícito** de la comparativa (peninsular
  vs. latinoamericano), lo que convierte el problema en un resultado publicable
- Solicitar **Albayzin/RTVE** (~500 h de radiotelevisión española, acentos diversos, habla
  solapada y ruido real). Segunda petición, después de poliMedia
- 🔴 **DIRECTOR:** decidir entre conjunto peninsular único o variedad como factor

### ⚠️ R12 — Efecto suelo: el baseline es demasiado bueno (detectado en M0)
Si el modelo sin adaptar ya acierta casi todo, **no queda margen donde las técnicas de
adaptación puedan demostrar nada**, y la comparativa sale sin diferencias significativas
por construcción. Es R6 pero por una causa concreta y medible.

**Evidencia (M0):** `whisper-medium` da 3.01% de WER sobre FLEURS, y descontando los
artefactos de medición de R11 el WER real ronda el 1.7%.

**Mitigación:** es un artefacto del material, no del diseño. FLEURS es voz leída, limpia y
bien articulada. El corpus educativo real (habla espontánea, muletillas, solapamientos,
ruido de aula, acentos, terminología técnica) subirá el WER base y devolverá margen a las
técnicas. **Esto convierte R1 en un riesgo de validez, no solo de disponibilidad:** sin
corpus realista no es que los resultados sean peores, es que no hay fenómeno que medir.
Argumento a llevar explícitamente a la reunión de F0.

### ✅ R2 — GPU AMD + entorno Linux para entrenamiento — **MITIGADO (M0)**
> Verificado con `tools/check_gpu.py`: RX 9070 XT (gfx1201) + ROCm 7.2.4 + torch 2.13
> calcula correctamente y **entrena** (backward + AdamW convergiendo, autocast bf16 OK),
> con 15.9 GiB de VRAM. LoRA es técnicamente viable. Lo que queda de este riesgo es de
> datos y de calendario, no de entorno. Se conserva el análisis original abajo.

### ⚠️ R2 (análisis original) — GPU AMD + entorno Linux para entrenamiento
La inferencia con Whisper suele resolverse. **El entrenamiento (LoRA) sobre GPU AMD es donde se pierden semanas enteras**, y es un riesgo silencioso porque no aparece hasta que ya has comprometido el alcance.

**Mitigación:** valida que la GPU **entrena algo, lo que sea**, en M0-M1. Un entrenamiento mínimo de juguete, no Whisper. Hasta que eso funcione, LoRA es "opcional" en toda comunicación con el director. Fallback: inferencia en CPU para prompting y post-corrección (no necesitan entrenamiento) + cómputo externo puntual para LoRA 🔴 **DIRECTOR: ¿se acepta usar cómputo externo?**

### ✅ R3 — Datos insuficientes para fine-tuning — **RESUELTO (M0)**
> exp-003 entrenó LoRA con 1.500 clips (4,64 h) de la partición `train` de VoxPopuli en
> 15,8 minutos, produciendo un adaptador de 18,9 MB. Es la **única técnica de las tres que
> mejora de forma concluyente**: −1.23 pp de WER, IC [−1.75, −0.77], p < 0.0001.
> La restricción de datos no se materializó. Se conserva el análisis original abajo.

### ⚠️ R3 (análisis original) — Datos insuficientes para fine-tuning
LoRA necesita bastante más material anotado que las otras dos técnicas. Si el corpus se queda corto (R1), LoRA cae por dependencia, no por tiempo.
**Mitigación:** es la última en el orden de ejecución y la segunda en el orden de recorte. No la anuncies como comprometida hasta que R1 y R2 estén resueltos.

### ⚠️ R4 — Latencia insuficiente para "tiempo real"
**Mitigación:** define el umbral en F0, instrumenta la medición desde el primer MVP, y reporta la latencia real aunque no cumpla. Un sistema con latencia medida y justificada es defendible; uno que dice "tiempo real" sin número, no.

### ⚠️ R5 — Doble núcleo (Tipo 2 + Tipo 3) = doble trabajo
**Mitigación:** acuerda con el director, **por escrito**, que la aplicación se evalúa como *vehículo de demostración* de la técnica ganadora, no como contribución independiente con su propia validación. La diferencia entre esas dos lecturas son ~6 semanas.

### ⚠️ R6 — La comparativa no da diferencias concluyentes
Es un resultado perfectamente posible: las técnicas quedan dentro del ruido de medición.
**Mitigación:** un resultado negativo bien medido es defendible — pero **solo si el método es sólido y estaba fijado de antemano**. De ahí H2 (protocolo congelado). Reporta variabilidad, no solo medias. Y prepara el análisis cualitativo de errores: aunque el WER agregado no se mueva, puede haber mejoras claras en terminología del dominio, que es precisamente lo que importa para accesibilidad.

### ⚠️ R7 — Redacción tardía
El fallo más común y el más evitable.
**Mitigación:** F5 arranca en M1. Entrega borradores parciales al director en lugar de un bloque final. H5 protege el margen de revisión.

### ⚠️ R8 — Resultados no reproducibles
Descubrir en M8 que una cifra de la tabla no se puede regenerar.
**Mitigación:** una config por experimento, semillas fijadas, hash de commit en cada salida, tablas generadas y no copiadas a mano.

### ⚠️ R9 — Datos personales (RGPD)
Si grabas clases reales, hay voz de personas identificables.
**Mitigación:** consentimiento informado por escrito, anonimización de nombres en las transcripciones, y decidir **antes de grabar** si el corpus podrá publicarse. 🔴 **DIRECTOR: ¿requiere el trabajo aprobación ética o consentimiento formalizado?**

### ⚠️ R10 — Disponibilidad personal
**Mitigación:** el plan en fases relativas absorbe desfases sin rehacerse. Los puntos de recorte de la sección 4 son la válvula. Revisa el plan al final de cada fase, no cada semana.

---

## 5 bis. Estado de la comparativa (M0)

Las tres técnicas comprometidas están medidas sobre el mismo corpus de referencias
verificadas, con diseño pareado y veredicto que exige coincidencia entre el IC por
bootstrap y el test de signos.

| Técnica | Δ WER | Veredicto |
|---|---:|---|
| Prompting contextual | −0.37 / +0.35 | Sin efecto (signos opuestos en dos corpus) |
| Post-corrección con LLM | +1.18 | Degrada (replicado) |
| Fine-tuning con LoRA | **−1.23** | **Mejora** (única concluyente) |

**Solo funciona la que modifica los pesos.** Y una conclusión que reordena el trabajo:
segmentar el audio por silencios (exp-102, −7.4 pp) rinde **seis veces más** que la mejor
técnica de adaptación, a coste de cómputo nulo. El margen no estaba donde la propuesta
suponía.

La técnica ganadora ya está en el sistema desplegado (`make demo-lora`) **sin haber tocado
la aplicación .NET**, que era la promesa arquitectónica del proyecto.

## 6. Valoración crítica del alcance

Me pediste que fuera crítico. Lo soy:

**El alcance actual es demasiado para una modalidad individual sin experiencia previa en NLP/ML.** Tres técnicas de adaptación + corpus propio + aplicación .NET en tiempo real con resaltado semántico son, cómodamente, dos TFM.

Lo que recomiendo negociar con el director:

1. **Dos técnicas comprometidas, no tres.** Prompting contextual y post-corrección con LLM son las dos que no requieren entrenamiento — es decir, las dos que sobreviven a que ROCm te dé problemas. LoRA queda declarada como línea opcional/trabajo futuro desde el minuto uno. Si sale, es un extra; si no sale, no arrastra al TFM.

2. **El resaltado de conceptos clave, en su versión simple.** Una lista de terminología por asignatura resuelve el 80% del valor de accesibilidad con el 10% del trabajo. La detección semántica es un problema de PLN completo metido de contrabando en el capítulo de desarrollo.

3. **La aplicación como demostrador, no como objeto de evaluación.** Que exista, funcione y se despliegue. No que se valide con usuarios.

Dicho eso: **el planteamiento de fondo es bueno**. El núcleo investigador está bien definido, la pregunta es respondible empíricamente, y tu perfil backend/DevOps hace que la parte Tipo 2 sea la zona de bajo riesgo del proyecto — que es exactamente al revés de lo habitual. El riesgo está todo concentrado en corpus y entorno de GPU, y eso se ataca en las primeras semanas o no se ataca.

Y una observación sobre el orden del riesgo: la tentación natural, viniendo de .NET, va a ser empezar por la aplicación, porque es donde te sientes cómodo. **No lo hagas.** La aplicación es el trabajo que sabes que sabes hacer; el corpus es el que puede matar el TFM. Ataca primero lo que puede fallar.

---

## 7. Checklist de arranque

### Entorno
- [ ] Verificar que la GPU AMD es visible desde el entorno de trabajo
- [ ] Entorno Python aislado y reproducible (fijar el mecanismo, no las versiones aún)
- [ ] Whisper ejecutándose e infiriendo sobre un audio real
- [ ] **Prueba crítica:** entrenar *algo* mínimo en la GPU (no Whisper, cualquier cosa). Si esto falla, LoRA es inviable y hay que saberlo YA → R2
- [ ] SDK .NET instalado y proyecto Blazor Server vacío que arranca

### Repositorio
- [ ] `git init` (⚠️ el directorio **aún no es un repositorio git**)
- [ ] Crear el árbol de carpetas de la sección 2
- [ ] `.gitignore`: audio, modelos, artefactos LaTeX (`*.aux`, `*.log`, `*.toc`, `*.out`, `*.bbl`, `*.blg`, `*.synctex.gz`), `bin/`, `obj/`
- [ ] Copiar la plantilla a `memoria/template-original/` (intacta) y crear la copia de trabajo
- [ ] **Compilar la plantilla en limpio** y confirmar que el PDF sale bien en Linux
- [ ] Actualizar portada: titulación real (la plantilla trae "Máster en Ingeniería Matemática y Computación"), título, autor, director, ciudad, fecha
- [ ] Primer commit

### Primeras pruebas de Whisper
- [ ] Transcribir 10 min de clase real en español y **escuchar el resultado leyendo la transcripción**. Anotar cualitativamente qué falla: ¿terminología? ¿nombres propios? ¿solapamiento de voces? ¿ruido de aula? Esto orienta toda la comparativa
- [ ] Medir el tiempo de inferencia frente a la duración del audio (factor de tiempo real)
- [ ] Probar dos tamaños de modelo distintos y comparar calidad contra velocidad
- [ ] Calcular un primer WER a mano sobre 5 minutos — tu primera cifra propia

### Corpus
- [ ] Crear `research/corpus/FUENTES.md`
- [ ] Listar candidatos con: horas · idioma · dominio · ¿transcripción de referencia? · licencia · accesibilidad real
- [ ] Verificar manualmente la calidad de referencia de al menos un candidato (no fiarse de subtítulos automáticos)
- [ ] **Cronometrar la transcripción manual de 30 min** → cuántas horas de referencia puedes permitirte
- [ ] Redactar la recomendación de corpus para llevar al director con datos, no con intuiciones

### Aplicación (esqueleto, sin ASR real)
- [ ] Blazor Server + SignalR: audio del micro del navegador → servidor → texto simulado de vuelta al cliente
- [ ] Medir la latencia de ese circuito vacío. Es tu presupuesto de latencia antes de meter el ASR

### Dirección
- [ ] Crear `docs/preguntas-director.md` con todas las 🔴 de este documento
- [ ] Preparar la reunión de cierre de alcance de F0 con: recomendación de corpus, resultado de la prueba de entrenamiento en GPU, y propuesta de dos técnicas + una opcional
- [ ] Acordar cadencia de reuniones y formato de entrega de borradores
- [ ] Confirmar normativa: extensión, formato de entrega, anexos exigidos, y **fecha real de la convocatoria**
```
