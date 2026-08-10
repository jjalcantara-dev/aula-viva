# TFM — Sistema de accesibilidad educativa en tiempo real con transcripción adaptativa

Comparativa de técnicas de adaptación de modelos ASR (Whisper) al dominio educativo en
español, y aplicación cliente-servidor .NET de subtitulado en vivo.

Máster en Inteligencia Artificial · UNIR · modalidad individual

> Planificación, riesgos y alcance: **[PLANNING.md](PLANNING.md)**
> Decisiones tomadas: [`docs/decisiones/`](docs/decisiones/)
> Preguntas abiertas para el director: [`docs/preguntas-director.md`](docs/preguntas-director.md)

## Organización

| Carpeta | Qué contiene |
|---|---|
| `research/` | **Núcleo investigador (Tipo 3).** Corpus, experimentos, evaluación |
| `app/` | **Núcleo aplicado (Tipo 2).** ASP.NET Core + Blazor Server + SignalR |
| `serving/` | Servicio Python de transcripción: el puente entre `app/` y Whisper |
| `memoria/` | Memoria en LaTeX sobre la plantilla oficial de UNIR |
| `docs/` | Trazabilidad del proceso: decisiones, actas, preguntas |
| `tools/` | Verificación de entorno y bancos de pruebas |

**`research/` y `app/` no comparten código.** Se comunican por el contrato del servicio
ASR (`Accesibilidad.Core/ContratoAsr.cs`). Eso mantiene separables la contribución
investigadora y la ingeniería, tanto en el repositorio como en la defensa.

### Experimentos

| | Pregunta que responde |
|---|---|
| `exp-000-baseline` | Whisper sin adaptar: referencia de toda la comparativa |
| `exp-001-prompting` | ¿Ayuda un glosario del dominio como prompt contextual? |
| `exp-100-ventana` | ¿Cuánto WER cuesta cada segundo de latencia que se ahorra? |
| `exp-101-dispositivo` | ¿Cuánto aporta realmente la GPU? |

Numeración: `000-099` núcleo investigador, `100+` ingeniería del sistema en vivo.

## Entorno

```bash
python3 -m venv --system-site-packages .venv   # reutiliza el torch de ROCm del sistema
.venv/bin/pip install transformers accelerate peft jiwer soundfile librosa datasets matplotlib
.venv/bin/python tools/check_gpu.py            # verifica que la GPU CALCULA y ENTRENA
```

`--system-site-packages` es deliberado: torch con ROCm está instalado a nivel de sistema
y reinstalarlo en el venv rompería el soporte de la GPU.

## Reproducir el baseline

```bash
# 1. muestras con transcripción de referencia
.venv/bin/python research/src/data/fetch_sample.py --n 40 \
    --fuentes voxpopuli_es teleconciencia_es

# 2. Whisper sin adaptar = referencia de la comparativa
.venv/bin/python research/experiments/exp-000-baseline/run.py \
    --manifiesto research/corpus/manifests/voxpopuli_es.jsonl \
    --modelo openai/whisper-medium

# 3. tablas y figuras para la memoria (nunca se teclean cifras a mano)
.venv/bin/python research/eval/report/tabla_corpus.py   --decodificacion fallback
.venv/bin/python research/eval/report/figura_modelos.py --corpus voxpopuli_es
.venv/bin/python research/eval/report/anomalias.py      --decodificacion fallback
```

Resultados en `research/experiments/*/results/`, nombrados por `<modelo>__<corpus>__<decodificación>`.
Cada JSON registra métricas, configuración, semilla, commit, **hash del manifiesto** y entorno.

## Ejecutar la aplicación

Requiere el runtime de ASP.NET Core (en Arch/CachyOS no viene con el SDK):

```bash
sudo pacman -S aspnet-runtime-10.0 aspnet-targeting-pack-10.0   # una sola vez
cd app && dotnet run --project src/Accesibilidad.Web
```

Página de subtitulado: `http://localhost:5203/subtitulos` (el puerto lo fija
`Properties/launchSettings.json`, que tiene prioridad sobre `ASPNETCORE_URLS`).

El motor por defecto es `MotorAsrSimulado`: **no reconoce nada**. Devuelve texto fijo para
medir la latencia del circuito —micrófono, red, servidor, render— sin la contribución del
modelo. La página muestra mediana y p95. La captura del micrófono necesita un contexto
seguro; `localhost` cuenta como tal.

## Resultados de M0

WER (%) con normalización básica y **decodificación por reintento de temperatura**
(ver R14: con decodificación voraz estas cifras no son válidas). 40 clips por corpus.

| Corpus | Variedad | Registro | small | medium | turbo | Δ tildes |
|---|---|---|---:|---:|---:|---:|
| `fleurs_es` | Latinoamérica | Leída | 6.61 | 3.21 | 3.41 | — |
| `tedx_es` | México | Charla espontánea | 12.13 | 10.22 | 11.12 | −3.48 |
| `teleconciencia_es` | México | Divulgación | 23.42 | 22.65 | 22.26 | −8.54 |
| `mediaspeech_es` | Peninsular | Medios | 15.94 | 14.72 | 15.60 | −1.70 |
| `voxpopuli_es` | Peninsular | Parlamentario | 12.01 | **10.44** | 11.53 | **−0.07** |

Cuatro hallazgos que condicionan el diseño de la comparativa:

1. **Manda el registro, no el dialecto.** A registro equivalente, peninsular y mexicano
   son casi idénticos (`voxpopuli` 10.44 vs `tedx` 10.22). Lo que lleva el WER de 3% a
   23% es leer un texto frente a hablar de forma espontánea.
2. **En dominio real, escalar el modelo deja de servir.** De `medium` a `turbo` no se
   gana nada. El margen que queda está en la adaptación, no en el tamaño — que es
   justamente la premisa de este trabajo.
3. **Δ tildes mide la calidad de la referencia.** Cuanto más negativo, más sucia: las
   transcripciones de CIEMPIESS omiten tildes y traen erratas; las de VoxPopuli están
   verificadas a mano (`is_gold_transcript`) y el artefacto es nulo.
4. **La decodificación es un factor de confusión (R14).** Sin reintento por temperatura,
   `turbo` truncaba y llegaba a inventar frases plausibles del dominio.

**Modelo base recomendado: `whisper-medium`** — cero salidas anómalas en 180 clips,
frente a 3 de `turbo`. Ver `docs/decisiones/002-modelo-base.md`.

### Requisito de hardware, medido (exp-101)

| Modelo | GPU | CPU | Aceleración |
|---|---:|---:|---:|
| `whisper-small` | 18.0× tiempo real | 4.8× | 3.7× |
| `whisper-medium` | 8.1× tiempo real | **1.6×** | **5.0×** |

**La GPU no es una comodidad, es un requisito.** Con `whisper-medium` en CPU el sistema
va a 1.6× tiempo real: una vez descontado el troceado y el solapamiento del subtitulado
en vivo, no llega. En GPU hay 8.1× de margen.

> Nota sobre el reparto de carga: durante los barridos la CPU alcanza ~85 °C mientras la
> GPU se queda en ~50 °C, lo que hace dudar de si el modelo corre realmente en GPU. Corre.
> Lo que ocupa la CPU es el **despacho** de kernels desde el bucle de Python, un token
> cada vez; la GPU marca 99% de uso pero solo consume el 45% de su potencia porque cada
> kernel es diminuto. Es propio de la decodificación autorregresiva con lote de tamaño 1,
> no del hardware AMD. La vía para reducirlo es procesar por lotes, no reconfigurar
> (comprobado en `tools/bench_termico.py`: mover el mel a GPU y limitar hilos no cambia nada).

> ⚠️ Ninguno de estos corpus es aula real. El objetivo sigue siendo **poliMedia** (UPV):
> ver `docs/solicitud-polimedia.md`. Mejor alternativa verificada: `voxpopuli_es`.

## Estado

- [x] Entorno GPU verificado — entrena (R2 mitigado)
- [x] Pipeline de evaluación WER/CER con normalización configurable
- [x] Baseline reproducible, 6 modelos, trazabilidad de commit y semilla
- [x] Búsqueda de corpus y auditoría de calidad de referencia
- [x] Salto de dominio medido (efecto suelo descartado, R12)
- [x] Requisito de GPU justificado con medidas (exp-101)
- [x] Prompting contextual evaluado con potencia estadística (exp-001)
- [x] Compromiso latencia-calidad medido (exp-100) y deduplicación implementada
- [x] Aplicación .NET: contrato, motor real, glosario, pruebas
- [ ] **Solicitud de poliMedia enviada** (R1, camino crítico) — `docs/solicitud-polimedia.md`
- [ ] **Prueba de latencia con micrófono real** — requiere navegador
- [ ] Protocolo de evaluación congelado (H2) — bloqueado por R15 (sin director)
- [ ] Post-corrección con LLM y LoRA
- [ ] Segmentación por silencios (VAD) en la aplicación
