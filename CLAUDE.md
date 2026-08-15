# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es esto

TFM del Máster en IA de UNIR (modalidad individual). Dos núcleos que se evalúan por separado:

- **Núcleo investigador (Tipo 3)**: comparativa empírica de técnicas de adaptación de
  Whisper al dominio educativo en español. Vive en `research/`.
- **Núcleo aplicado (Tipo 2)**: aplicación .NET de subtitulado en vivo. Vive en `app/`.

### Convención de idioma

**Identificadores en inglés, comentarios y documentación en español.** Es la combinación
habitual en equipos hispanohablantes: el código se lee como código y la explicación en el
idioma del autor.

- `app/` (C#) y los endpoints ya siguen la convención: `IAsrEngine`, `AudioChunk`,
  `CaptionSession`, `/broadcast`, `/view`.
- `research/` (Python) **sigue en español** de forma deliberada: sus nombres aparecen en
  el `Makefile`, en los README de cada experimento y en las claves de los ~40 JSON de
  resultados ya generados. Renombrarlos rompería la reproducibilidad de resultados ya
  medidos a cambio de consistencia estética. Es una deuda declarada, no un descuido.
- La salida por consola y la interfaz van en español (el usuario final es un docente).
- En fuentes Python los comentarios van **sin tildes** (evita problemas de codificación en
  entornos mixtos); en C# y en Markdown sí se acentúa.

### Puntuación: nunca guiones largos en mitad de un párrafo

**No se usa el guión largo (`—`) como inciso dentro de la prosa.** Vale para la memoria, los
README, los comentarios de código y los mensajes de commit. En su lugar:

- **Dos puntos** cuando lo que sigue explica o desarrolla lo anterior.
- **Punto y coma** cuando son dos ideas completas relacionadas.
- **Comas** cuando el inciso es breve y encaja sin romper la frase.
- **Paréntesis** solo si el contenido es verdaderamente accesorio.

Antes de dar por buena la redacción, comprobar que no quedan: `grep -rn "—" memoria/`.

## Comandos

`make` sin argumentos lista todos los atajos. Los habituales:

```bash
make estado        # foto rápida: experimentos, corpus, ficheros sin confirmar
make gpu           # verifica que la GPU CALCULA y ENTRENA (no solo que se detecta)
make test          # pruebas de la aplicación
make app           # app con motor simulado (mide latencia del circuito)
make demo          # servicio ASR + app con Whisper real; limpia al salir
make parar         # mata servicios y experimentos sueltos
make tablas        # regenera TODAS las tablas y figuras de la memoria
```

Experimentos: `make baseline`, `make exp-001` … `make exp-104` (diez experimentos). `make` los lista todos con
la pregunta que responde cada uno.
Aceptan variables: `make baseline MODELO=openai/whisper-small CORPUS=tedx_es`.

Una sola prueba de .NET: `cd app && dotnet test --filter "FullyQualifiedName~Solapamiento"`.

El intérprete es `.venv/bin/python`, creado con `--system-site-packages` **a propósito**:
torch con ROCm está instalado a nivel de sistema y reinstalarlo en el venv rompe la GPU.

## Arquitectura

### Topología del sistema

Un emisor y muchos receptores, con **todo el cálculo en el servidor**:

- `/broadcast` — puesto del **docente**. Captura el micrófono y difunde. Protegido por
  `Aula:ClaveDocente` si está configurada.
- `/view` — pantalla del **alumnado**. Solo muestra; no captura, no ejecuta el modelo.
  Deliberadamente abierta: nadie debe pelearse con una contraseña para leer subtítulos.

`CaptionSession` (singleton) mantiene la clase en curso y difunde por los websockets que
Blazor ya tiene con cada cliente; no hace falta un hub de SignalR aparte. El modelo
transcribe **una vez para toda el aula**, con independencia del número de alumnos.

**Solo red local.** `LocalNetworkOnly` rechaza con 403 cualquier conexión que no venga de
una red privada. Se difunde audio de aula con voces identificables, así que no basta con
no abrir el puerto del router: la restricción la impone la propia aplicación.

### La frontera entre investigación y aplicación

`research/` y `app/` **no comparten código**. La aplicación depende solo de `IAsrEngine`
(`app/src/Accesibilidad.Core/AsrContract.cs`). Eso permite enseñar una demo mientras la
comparativa sigue en curso, y sustituir la técnica ganadora al final sin tocar la app.

`serving/servidor_asr.py` es el puente: un servicio HTTP mínimo que carga Whisper (PyTorch
con ROCm solo existe en Python; .NET no puede cargarlo). **Usa la misma configuración de
decodificación que los experimentos** — si la app decodificara distinto, los resultados
medidos no describirían el sistema desplegado.

Los motores se componen por decoración: `HighlightingAsrEngine` envuelve a cualquier
`IAsrEngine` para añadir el glosario. Así el resaltado no contamina la comparación entre
técnicas. **Cuidado**: eso hace que un `is TipoConcreto` desde `IAsrEngine` nunca se cumpla;
las capacidades opcionales van en interfaces propias que los decoradores reenvían.

### Numeración de experimentos

- `exp-000` a `exp-099`: núcleo investigador (técnicas de adaptación)
- `exp-100` en adelante: ingeniería del sistema en vivo

Cada carpeta tiene `run.py`, `README.md` con hipótesis/diseño/resultados, y `results/`
(gitignored salvo `.gitkeep`).

### Flujo de datos

```
corpus/manifests/*.jsonl  (en git: rutas, referencia, duración, metadatos)
        │                  corpus/raw/*.wav NUNCA entra en git
        ▼
experiments/*/run.py  ──►  results/metricas_*.json  (métricas + procedencia)
                                    │
                                    ▼
                    eval/report/*.py  ──►  memoria/tablas/*.tex
                                           memoria/figuras/*.pdf
```

## Invariantes metodológicos

Estas reglas se han pagado con errores reales. Romperlas invalida resultados de forma
silenciosa, que es lo peligroso.

**La identidad de un resultado incluye su configuración.** Los ficheros se nombran
`<modelo>__<corpus>__<decodificación>`. Dos ejecuciones con distinta decodificación **no
son comparables**: medido, la decodificación voraz frente al reintento por temperatura
cambia el WER hasta 13 puntos y provoca alucinaciones. Si añades un eje de variación
(solape, lote…), **añádelo al nombre del fichero**.

**Todo resultado registra su procedencia.** `research/src/trazabilidad.py` graba commit,
si el árbol estaba sucio, y el **hash SHA-256 del manifiesto**. Motivo: al ampliar un
corpus de 40 a 1200 clips se sobrescribió el manifiesto y los resultados anteriores
seguían apuntando a un fichero cuyo contenido ya era otro. Nada lo delataba.

**Los normalizadores se congelan antes de comparar** (`research/eval/normalizers/`).
Cambiarlos a mitad hace incomparables los experimentos entre sí.

**La eñe se protege ANTES de descomponer Unicode.** Este error se ha cometido dos veces,
una en Python y otra en C#: comprobar `c == 'ñ'` después de `NormalizationForm.FormD`
nunca se cumple, porque ya es `n` + tilde combinante. En español eso cambia la palabra.

**El glosario se extrae de clips disjuntos de los que se evalúan.** Construirlo con las
transcripciones de evaluación es fuga de información y cualquier mejora medida sería falsa.

**Una optimización que cambia los resultados no es una optimización.** El procesamiento
por lotes se validó con `tools/verificar_lote.py` comprobando que las transcripciones son
idénticas. Re-verificar si cambia el modelo, la decodificación o la versión de
`transformers`.

**Ninguna cifra se teclea a mano en el LaTeX.** Las tablas y figuras se generan desde
`research/eval/report/`. Los notebooks (`research/notebooks/`) **consumen** `results/`,
nunca los producen.

**Todo entrenamiento se verifica por la pérdida antes de evaluarlo.** Debe estar en el
rango esperado (<1 para Whisper) y **bajar entre épocas**. El primer ajuste con LoRA
terminó sin errores, guardó su adaptador y produjo métricas evaluables con la pérdida
estancada en 6,87 y subiendo: el colador descartaba `bos_token_id` (50257) en lugar de
`decoder_start_token_id` (50258), así que el token de inicio llegaba duplicado. Habría
concluido que LoRA destroza el modelo, con IC estrecho y p diminuto avalando el artefacto.

**Ajustar el modelo sobre referencias sucias optimiza hacia el error.** Entrenar con
CIEMPIESS, cuyas referencias omiten tildes, enseñaría al modelo a no acentuar — y medido
contra esas mismas referencias, el WER *mejoraría*. Por eso exp-003 usa VoxPopuli.

**El preprocesado del navegador no es neutro.** El control automático de ganancia
**sabotea la segmentación por silencios**: al callar el hablante sube la ganancia,
amplifica el ruido de fondo y la energía nunca baja. Medido en uso real, con AGC activo
casi todos los segmentos se cerraban por agotar el tope en vez de por pausa. Va
desactivado, y la interfaz muestra el recuento de cortes por pausa frente a por tope para
que el fallo sea visible.

**El enlace de configuración de .NET falla en silencio.** Es por nombre de propiedad: si la
clave del `appsettings.json` no coincide, la sección se ignora, el objeto se queda con sus
valores por defecto y **no hay excepción ni aviso**. Pasó con dos secciones a la vez, por un
renombrado de identificadores a inglés que no llegó al fichero: `Glosario:Terminos` frente a
`Glossary:Terms` dejó el glosario vacío en todos los despliegues, y `Asr:Segmentacion`
frente a `Segmentation` hacía que ajustar el umbral de silencio no tuviera ningún efecto.
Que los valores por defecto de C# coincidieran con los del fichero lo enmascaró del todo.
`ConfiguracionTests` lo cubre ahora: **toda sección nueva del appsettings necesita su prueba
de enlace**, porque leer el JSON no basta, era JSON válido.

**Un contador declarado no es un contador que cuente.** `CutsBySilence`, `CutsByTimeout` y
`DiscardedAsSilence` estaban declarados, documentados y expuestos en la interfaz sin que
nada los incrementara: el diagnóstico de segmentación que debe delatar el sabotaje del AGC
mostraba 0/0 indefinidamente. Y `ProporcionVozMinima` estaba escrita, justificada y sin
usar, de modo que la primera barrera anti-alucinación no existía. La comprobación barata es
`grep` de cada símbolo declarado: si solo aparece en su declaración, no hace nada.

**Los decoradores rompen las comprobaciones de tipo.** `HighlightingAsrEngine` envuelve al
motor real, así que un `is WhisperAsrEngine` desde `IAsrEngine` **nunca se cumple**. El
diagnóstico de segmentación estuvo devolviendo ceros por esto. Cualquier capacidad
opcional va en su propia interfaz (`ISegmentationDiagnostics`) que los decoradores
reenvían.

**El WER agregado esconde lo que importa en accesibilidad.** Cinco casos medidos lo
confirman: tildes ausentes en las referencias, alucinaciones fluidas, terminología del
dominio, duplicación por solapamiento, y dos modelos con WER indistinguible donde uno
pierde el 35% de las negaciones y el otro el 12% (exp-004). Por eso existen métricas aparte
(`eval/metrics/terminologia.py`, `eval/report/anomalias.py`). Al evaluar una técnica,
reportar también estas, no solo WER.

**Las anomalías se miden por longitud, así que la traducción es invisible.**
`anomalias.py` detecta truncamiento y expansión comparando el número de palabras; una
frase traducida al inglés tiene longitud normal y pasa de largo. El punto ciego apareció al
evaluar un modelo multilingüe sin control de idioma, que devolvió «Hello, what are you
talking about?» ante habla española. Para eso existe `eval/report/fuga_idioma.py`, que va
aparte porque detecta otra cosa.

**Al comparar arquitecturas, comprobar el estilo numérico antes de creerse la diferencia.**
El normalizador congelado no equipara «2010» con «dos mil diez», y como son una ficha
frente a tres, el alineamiento cuenta **tres errores por una cifra bien reconocida**. Entre
variantes del mismo modelo da igual porque comparten convención; entre arquitecturas
distintas infló un 18% la diferencia medida. Se comprueba con `eval/report/estilo_numerico.py`,
que repite el contraste sobre los clips sin numerales. **No tocar el normalizador**: está
congelado y cambiarlo invalida todo lo anterior.

## Contexto de decisiones

- `PLANNING.md` — planificación por fases y **16 riesgos** con mitigación. R11 (calidad de
  la referencia), R13 (variedad dialectal), R14 (decodificación), R15 (sin director) y R16
  (el modelo base envejece) se detectaron midiendo, no planificando.
- `research/MODELOS.md` — catálogo de modelos auditados, hermano de `corpus/FUENTES.md`.
  Todo candidato debe **poder recibir «transcribe en español» y obedecer**: exp-004 midió
  que un transductor multilingüe sin control de idioma traduce al inglés ante habla difícil.
- `docs/decisiones/` — una decisión por fichero, con la evidencia que la respalda.
- `docs/preguntas-director.md` — cola viva de decisiones bloqueadas. **No hay director
  asignado**; la norma es tomar decisiones provisionales documentadas y marcarlas
  revisables, no quedarse parado.
- `research/corpus/FUENTES.md` — candidatos auditados. El corpus objetivo (poliMedia, UPV)
  requiere solicitud: `docs/solicitud-polimedia.md`.

## Entorno

GPU AMD RX 9070 XT (gfx1201) con ROCm; funciona y entrena.

**Un núcleo entero se pierde en espera activa, siempre.** Medido: `torch.zeros(1,
device="cuda")` basta para que un hilo del runtime gire al 100% de un núcleo de forma
permanente, esté o no haciendo algo el proceso. Importar torch cuesta 0%; el salto está en
la creación del contexto de GPU, no en el modelo ni en el servidor. No lo desactivan
`HSA_ENABLE_INTERRUPT`, `GPU_MAX_HW_QUEUES`, `AMD_DIRECT_DISPATCH` ni `HSA_ENABLE_SDMA`
(los cuatro probados). Consecuencias prácticas:

- Al mirar `top`, **un núcleo al 100% en el servicio ASR en reposo es lo esperado**, no un
  fallo que investigar. Ya costó tiempo una vez.
- Hay que descontarlo antes de atribuir carga de CPU al trabajo real.
- No invalida ninguna medición: es un coste constante, idéntico en todas las condiciones.

Aparte de eso, la CPU se calienta más que la GPU durante los barridos: es normal y está
medido: el trabajo de CPU es el **despacho** de kernels desde Python, no el cálculo.
Mover el mel a GPU o limitar hilos **no ayuda**
(comprobado en `tools/bench_termico.py`); lo que ayuda es el procesamiento por lotes.

`app/` requiere el runtime de ASP.NET Core, que en Arch/CachyOS no viene con el SDK:
`sudo pacman -S aspnet-runtime-10.0 aspnet-targeting-pack-10.0`.

El servicio de `serving/` selecciona acelerador en este orden: `cuda` (NVIDIA y también
AMD, porque PyTorch expone ROCm con ese nombre), `mps` (Apple Silicon, forzando `float32`
porque Metal no cubre `float16` en todas las operaciones de Whisper) y `cpu`. Los scripts
de `research/` **siguen fijando cuda o cpu**: se ejecutan en el equipo de desarrollo y
añadir MPS ahí cambiaría resultados ya medidos.
