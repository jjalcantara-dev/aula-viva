# 004 — Arquitectura de aula: un emisor, muchos receptores

**Fecha:** M0 · **Estado:** implementado y probado (47 pruebas)

## Contexto

El sistema debe servir a una clase: un docente hablando y varios alumnos leyendo. La
primera versión solo contemplaba al emisor — cada navegador capturaba su propio audio y
recibía sus propios subtítulos —, lo que no permitía que un alumno simplemente se conectara
a mirar.

## Decisiones

### 1. Todo el cálculo en el servidor

`/broadcast` (docente) captura el micrófono; `/view` (alumnado) **solo muestra**.

El motivo no es comodidad sino viabilidad: el modelo se carga y ejecuta **una vez para toda
el aula**, con independencia de que haya tres alumnos o treinta. Un diseño donde cada
cliente transcribiera necesitaría una GPU por alumno, lo que contradice el objetivo de que
un centro pueda desplegarlo.

### 2. Difusión en memoria, sin hub de SignalR aparte

`CaptionSession` es un singleton que mantiene la clase en curso y emite un evento por
segmento. Como todos los clientes son circuitos de Blazor Server sobre el mismo proceso,
Blazor ya mantiene un websocket con cada uno y por ahí viajan las actualizaciones.

**Limitación conocida**: esto ata el sistema a un único servidor. Escalar a varios exigiría
un backplane (Redis o Azure SignalR), que es la objeción habitual a Blazor Server en
producción. Para un aula —un servidor, decenas de clientes— no aplica, pero debe declararse.

### 3. Solo red local, impuesto por la aplicación

`LocalNetworkOnly` rechaza con 403 toda conexión que no venga de una red privada
(RFC 1918, bucle o enlace local).

Se difunde **audio de aula transcrito: voces identificables, a menudo de menores**.
Exponerlo a internet es un problema de protección de datos antes que técnico, y no se
resolvería añadiendo una contraseña. Que la restricción la imponga la propia aplicación la
hace verificable, en lugar de depender de que nadie configure mal un reenvío de puertos.

Si algún día hiciera falta acceso remoto, la vía es una VPN al centro: el dispositivo entra
en la red local y la comprobación lo acepta sin cambiar nada.

### 4. Clave solo para el puesto docente

`/view` queda abierta a propósito: en un aula nadie debe pelearse con una contraseña para
poder leer los subtítulos. `/broadcast` activa el micrófono y difunde, así que va protegida
por clave compartida (`Aula:ClaveDocente`), con comparación de tiempo constante.

Sin clave configurada la emisión queda abierta y **la propia página lo advierte**, para que
no se despliegue así por descuido.

### 5. Control automático de ganancia desactivado

El AGC del navegador **sabotea la segmentación por silencios**: al callar el hablante sube
la ganancia, amplifica el ruido de fondo y la energía nunca baja lo suficiente para
detectar la pausa.

Medido con micrófono real: con AGC activo, prácticamente todos los segmentos se cerraban
por agotar el tope de 8 s en lugar de por pausa, dando latencias de 8,2 s. La supresión de
ruido y la cancelación de eco siguen activas; solo se separó el AGC.

## Consecuencias

- La interfaz muestra **cortes por pausa frente a cortes por tope**. Si domina el segundo,
  el detector no funciona y el sistema degenera en troceado por reloj — la peor opción
  según exp-102. El fallo era invisible antes de instrumentarlo.
- Las capacidades opcionales van en interfaces propias (`ISegmentationDiagnostics`) que los
  decoradores reenvían: un `is TipoConcreto` desde `IAsrEngine` nunca se cumple porque
  `HighlightingAsrEngine` envuelve al motor real. El diagnóstico estuvo devolviendo ceros
  por esto.
- El límite de mensaje de SignalR se elevó a 128 KB: un fragmento de 500 ms ocupa 16 KB y
  el valor por defecto son 32 KB, así que subir el tamaño de fragmento habría roto la
  captura con un error de conexión sin relación aparente con la causa.

## Pendiente

- 🔴 **DIRECTOR**: confirmar que el alcance del núcleo aplicado incluye la difusión
  multiusuario, o si basta con demostrar el puesto docente.
- HTTPS para que el docente pueda emitir desde un equipo distinto al servidor (el micrófono
  exige contexto seguro).
- VAD entrenado (Silero) en lugar del detector de energía.
