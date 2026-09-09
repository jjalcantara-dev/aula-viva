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
| `docker/` | Imágenes para desplegar sobre GPU AMD o NVIDIA |

**`research/` y `app/` no comparten código.** Se comunican por el contrato del servicio
ASR (`Accesibilidad.Core/AsrContract.cs`). Eso mantiene separables la contribución
investigadora y la ingeniería, tanto en el repositorio como en la defensa.

### Experimentos

| | Pregunta que responde |
|---|---|
| `exp-000-baseline` | Whisper sin adaptar: referencia de toda la comparativa |
| `exp-001-prompting` | ¿Ayuda un glosario del dominio como prompt contextual? |
| `exp-002-postcorreccion` | ¿Puede un LLM local reparar los errores del ASR? |
| `exp-100-ventana` | ¿Cuánto WER cuesta cada segundo de latencia que se ahorra? |
| `exp-003-lora` | ¿Mejora el ajuste fino de los pesos del modelo? |
| `exp-004-arquitecturas` | ¿Es Whisper el modelo base correcto, o se eligió por inercia? |
| `exp-101-dispositivo` | ¿Cuánto aporta realmente la GPU? |
| `exp-102-vad` | ¿Conviene cortar por silencios en vez de por reloj? |
| `exp-103-contexto` | ¿Ayuda arrastrar la transcripción anterior entre ventanas? |
| `exp-104-ruido` | ¿Cuánto margen acústico necesita el sistema? |

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
make demo          # servicio ASR + app, con las direcciones impresas al arrancar
make demo-lora     # igual, pero con el adaptador de exp-003 (técnica ganadora)
make app           # solo la app, con motor simulado (mide la latencia del circuito)
```

### Topología: un emisor, muchos receptores

| Ruta | Quién | Qué hace |
|---|---|---|
| `/broadcast` | **Docente** | Captura el micrófono, fija el glosario, ve las métricas |
| `/view` | **Alumnado** | Solo muestra. No captura ni ejecuta el modelo |

El servidor transcribe **una vez para toda el aula**, con independencia del número de
alumnos conectados. Un diseño donde cada cliente transcribiera necesitaría una GPU por
alumno.

```
DOCENTE  http://localhost:5203/broadcast     ← el micrófono solo funciona en localhost sin HTTPS
ALUMNOS  http://<ip-del-equipo>:5203/view    ← desde el móvil, en la misma red
```

### Despliegue en contenedores

Para un centro que no quiera montar el entorno a mano, y para no atar el sistema a un
fabricante de GPU concreto:

```bash
make docker-amd      # ROCm
make docker-nvidia   # CUDA
make docker-parar
```

La única diferencia entre ambos es la imagen base del servicio de reconocimiento; el
código es idéntico porque PyTorch expone la misma interfaz sobre las dos plataformas. El
modelo se descarga una vez y queda en un volumen.

**Los contenedores NO se levantan solos al encender el equipo.** La política de reinicio es
`no` por defecto, porque en un equipo de desarrollo resucitar en cada arranque es una
molestia: el servicio de reconocimiento mantiene un núcleo en espera activa y ~4,7 GB de RAM
mientras vive. En un despliegue de aula se quiere lo contrario, y se activa en el `.env`:

```bash
REINICIO=unless-stopped
```

Si ya los tienes arrancando solos de un despliegue anterior, `make docker-parar` los elimina
y con eso dejan de reaparecer.

Requisitos del anfitrión: con AMD, pertenecer a los grupos `video` y `render`; con NVIDIA,
el conjunto de herramientas de contenedores del fabricante. Y el plugin `compose` de
Docker, que en Arch va en un paquete aparte (`docker-compose`).

**Ambos contenedores comparten la red del anfitrión.** Los kernels recientes de Arch y
derivadas no incluyen los módulos de compatibilidad de iptables que Docker necesita para
publicar puertos (`xt_nat`, `iptable_nat`), y su backend nativo de nftables falla al
inicializar. Compartir red lo evita, y en un despliegue de aula no se pierde aislamiento
real: el sistema sirve a la red local de todos modos.

### Apple Silicon

| Ejecución | Acelerador | Viable |
|---|---|---|
| Nativa (entorno de Python) | **MPS** | Sí |
| En contenedor | Solo CPU | No |

El servicio detecta MPS automáticamente y fuerza `float32`: Metal no implementa
`float16` para todas las operaciones de Whisper, y con precisión reducida la inferencia
falla o devuelve silencio.

En contenedor no hay alternativa: Docker en macOS ejecuta los contenedores dentro de una
máquina virtual Linux que no expone la GPU de Apple. Quedaría en CPU, y exp-101 midió que
eso da 1.6× tiempo real con `whisper-medium`, insuficiente para directo.

La aplicación .NET sí funciona en arm64 sin cambios, contenerizada o no.

> ✅ Construido y ejecutado sobre AMD: ambos contenedores arrancan y pasan su comprobación
> de salud. El perfil de NVIDIA sigue sin probar por falta de la tarjeta.
>
> ⚠️ **La imagen del reconocimiento ocupa 83,5 GB** según `docker system df -v` (su
> contenido real son 34 GiB; la diferencia es cómo contabiliza capas el snapshotter de
> containerd). No es el modelo, que son 2,85 GB: es la base `rocm/pytorch`, etiquetada
> `npi.amdgpu_family:device-all`, que transporta núcleos precompilados para **24
> arquitecturas de GPU**. De los 792 MB de `rocblas`, los de gfx1201 son **10 MB**; y hay 13
> `libMIOpenCKGroupedConv_gfx*.so` que suman 4,4 GB, de las que se usa una. Incluye además
> `_rocm_sdk_devel` (15 GB de compiladores) pese a anunciarse como imagen de runtime.
>
> A eso se suman 11,6 GB de núcleos compilados en el volumen de caché, porque ROCm no
> distribuye binarios para gfx1201. Total a efectos de planificación: **~100 GB**, frente a
> ~5 GB de la ejecución nativa.
>
> Dos mejoras pendientes: partir de una base restringida a una familia de GPU, y **fijar una
> versión estable**, porque `rocm/pytorch:latest` es una compilación *nightly*
> (`RELEASE_TYPE=nightly`) y dos construcciones separadas no dan el mismo sistema.

### Restricciones de acceso

- **Solo red local**: se rechaza con 403 cualquier conexión que no venga de una red
  privada. Se difunde audio de aula con voces identificables, así que la restricción la
  impone la aplicación y no la configuración del router (`Aula:SoloRedLocal`).
- **Clave del puesto docente** (`Aula:ClaveDocente`): protege `/broadcast`. Sin configurar,
  la propia página advierte de que cualquiera en la red puede emitir.
- El cortafuegos del equipo debe permitir el puerto:
  `sudo ufw allow from 192.168.1.0/24 to any port 5203 proto tcp`

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
   gana nada. El margen que queda está en la adaptación, no en el tamaño, que es
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

- [x] Entorno GPU verificado: entrena (R2 mitigado)
- [x] Pipeline de evaluación WER/CER con normalización configurable
- [x] Baseline reproducible, 6 modelos, trazabilidad de commit y semilla
- [x] Búsqueda de corpus y auditoría de calidad de referencia
- [x] Salto de dominio medido (efecto suelo descartado, R12)
- [x] Requisito de GPU justificado con medidas (exp-101)
- [x] Dos técnicas evaluadas con potencia estadística (exp-001, exp-002)
- [x] Troceado del audio resuelto con datos: exp-100 → exp-102 → exp-103
- [x] Robustez frente al ruido de aula caracterizada (exp-104)
- [x] Cuatro capas de evaluación: WER, terminología, anomalías, errores críticos
- [x] Aplicación .NET con segmentación por silencios y 88 pruebas
- [ ] **Solicitud de poliMedia enviada** (R1, camino crítico): borrador listo para
      enviar en `docs/solicitud-polimedia.md`. En paralelo, `docs/solicitud-albayzin-rtve.md`
      para español peninsular espontáneo, que es lo que hoy falta.
      **Mientras no salga, tres frases de la memoria dicen que sí se cursó**; el propio
      fichero indica qué revertir al enviarlo
- [ ] Protocolo de evaluación congelado (H2): bloqueado por R15 (sin director)
- [x] Fine-tuning con LoRA (tercera técnica): única que mejora
- [x] exp-002 replicado sobre referencias verificadas (`voxpopuli_es_400`)

## Licencia

**GNU AGPL-3.0** (`LICENSE`). Libre de usar, modificar y desplegar; quien lo modifique y lo
ofrezca como servicio en red debe publicar sus cambios. El razonamiento, incluida la razón
por la que «libre pero sin uso comercial» no existe como licencia de código abierto, está en
`docs/decisiones/006-licencia.md`.

La licencia cubre **el código**. El corpus no se redistribuye y mantiene las condiciones de
su procedencia (RL4).

## La comparativa de técnicas

Tres técnicas, el mismo corpus de referencias verificadas (`voxpopuli_es_400`, 12.951
palabras), diseño pareado y veredicto que exige que **coincidan** el intervalo de confianza
por bootstrap y el test de signos.

| Técnica | Δ WER (pp) | IC 95% | Veredicto |
|---|---:|---|---|
| Prompting contextual | −0.37 | [−0.76, −0.05] | **Sin efecto**: signos opuestos en dos corpus, pruebas discrepantes |
| Post-corrección con LLM | +1.18 | [+0.84, +1.54] | **Degrada**: replicado en dos corpus muy distintos |
| **Fine-tuning con LoRA** | **−1.23** | [−1.75, −0.77] | **Mejora**: única concluyente |

**Solo funciona la que modifica los pesos.** Las dos que actúan sin tocar el modelo no
aportan, y una perjudica.

Con un matiz que debe declararse: parte de la mejora de LoRA es **alineamiento con la forma
superficial de la referencia**, no mejor reconocimiento. VoxPopuli escribe los números en
letra y el ajuste fino aprendió esa convención (162 dígitos → 1). Descontando numerales, el
error crítico mejora de 7.7% a 6.2%: real, pero modesto.

### Lo que más mejora el sistema no es adaptar el modelo

Comparando las mejoras medidas en los dos núcleos:

| Intervención | Ganancia |
|---|---:|
| Cortar el audio por silencios en vez de por reloj (exp-102) | **−7.4 pp** |
| Ajuste fino con LoRA (exp-003) | −1.23 pp |
| Prompting contextual (exp-001) | ~0 |
| Post-corrección con LLM (exp-002) | +1.18 (empeora) |

**Segmentar bien el audio rinde seis veces más que adaptar el modelo**, y a coste de
cómputo prácticamente nulo. Es contraintuitivo para un trabajo que partía de la premisa de
que lo interesante estaba en la adaptación.

## Hallazgos que condicionan el diseño

Cuatro casos independientes muestran lo mismo: **el WER agregado esconde justo lo que
importa en accesibilidad**. Es el hilo argumental del trabajo.

| Hallazgo | Evidencia |
|---|---|
| Las referencias públicas están sucias | 5.1 pp del WER en CIEMPIESS son tildes ausentes |
| Los modelos alucinan de forma fluida | `turbo` emitió «Gracias, señora presidenta» por el contenido real |
| El sentido se pierde sin que el WER lo note | 18.61% de WER, pero **28% de las negaciones perdidas y 13 inventadas** |
| La post-corrección con LLM degrada | +1.18 pp de WER sobre referencias verificadas, replicado en dos corpus |

Y en el núcleo aplicado, tres decisiones tomadas con medidas y no por intuición:
la GPU es requisito (en CPU no llega a tiempo real), cortar por silencios gana 7.4 pp
sobre cortar por reloj a igual latencia, y arrastrar contexto entre ventanas no aporta.
