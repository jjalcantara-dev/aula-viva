# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es esto

TFM del Máster en IA de UNIR (modalidad individual). Dos núcleos que se evalúan por separado:

- **Núcleo investigador (Tipo 3)**: comparativa empírica de técnicas de adaptación de
  Whisper al dominio educativo en español. Vive en `research/`.
- **Núcleo aplicado (Tipo 2)**: aplicación .NET de subtitulado en vivo. Vive en `app/`.

El idioma del proyecto es el **español**: identificadores, comentarios, documentación y
salida por consola. En fuentes Python los comentarios van **sin tildes** (evita problemas
de codificación en entornos mixtos); en C# y en Markdown sí se acentúa.

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

Experimentos: `make baseline`, `make exp-001`, `make exp-002`, `make exp-100`, `make exp-102`.
Aceptan variables: `make baseline MODELO=openai/whisper-small CORPUS=tedx_es`.

Una sola prueba de .NET: `cd app && dotnet test --filter "FullyQualifiedName~Solapamiento"`.

El intérprete es `.venv/bin/python`, creado con `--system-site-packages` **a propósito**:
torch con ROCm está instalado a nivel de sistema y reinstalarlo en el venv rompe la GPU.

## Arquitectura

### La frontera entre investigación y aplicación

`research/` y `app/` **no comparten código**. La aplicación depende solo de `IMotorAsr`
(`app/src/Accesibilidad.Core/ContratoAsr.cs`). Eso permite enseñar una demo mientras la
comparativa sigue en curso, y sustituir la técnica ganadora al final sin tocar la app.

`serving/servidor_asr.py` es el puente: un servicio HTTP mínimo que carga Whisper (PyTorch
con ROCm solo existe en Python; .NET no puede cargarlo). **Usa la misma configuración de
decodificación que los experimentos** — si la app decodificara distinto, los resultados
medidos no describirían el sistema desplegado.

Los motores se componen por decoración: `MotorConResaltado` envuelve a cualquier `IMotorAsr`
para añadir el glosario. Así el resaltado no contamina la comparación entre técnicas.

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

**El WER agregado esconde lo que importa en accesibilidad.** Cuatro casos medidos lo
confirman: tildes ausentes en las referencias, alucinaciones fluidas, terminología del
dominio, y duplicación por solapamiento. Por eso existen métricas aparte
(`eval/metrics/terminologia.py`, `eval/report/anomalias.py`). Al evaluar una técnica,
reportar también estas, no solo WER.

## Contexto de decisiones

- `PLANNING.md` — planificación por fases y **15 riesgos** con mitigación. R11 (calidad de
  la referencia), R13 (variedad dialectal), R14 (decodificación) y R15 (sin director) se
  detectaron midiendo, no planificando.
- `docs/decisiones/` — una decisión por fichero, con la evidencia que la respalda.
- `docs/preguntas-director.md` — cola viva de decisiones bloqueadas. **No hay director
  asignado**; la norma es tomar decisiones provisionales documentadas y marcarlas
  revisables, no quedarse parado.
- `research/corpus/FUENTES.md` — candidatos auditados. El corpus objetivo (poliMedia, UPV)
  requiere solicitud: `docs/solicitud-polimedia.md`.

## Entorno

GPU AMD RX 9070 XT (gfx1201) con ROCm; funciona y entrena. La CPU se calienta más que la
GPU durante los barridos: es normal y está medido — el trabajo de CPU es el **despacho**
de kernels desde Python, no el cálculo. Mover el mel a GPU o limitar hilos **no ayuda**
(comprobado en `tools/bench_termico.py`); lo que ayuda es el procesamiento por lotes.

`app/` requiere el runtime de ASP.NET Core, que en Arch/CachyOS no viene con el SDK:
`sudo pacman -S aspnet-runtime-10.0 aspnet-targeting-pack-10.0`.
