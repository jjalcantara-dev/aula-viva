# exp-004 — ¿Es Whisper el modelo base correcto?

## Por qué existe este experimento

La comparativa de técnicas de adaptación (exp-001 a exp-003) se construyó entera sobre
Whisper, elegido en exp-000 entre seis variantes de su propia familia. Ese barrido
responde *qué Whisper*, no *por qué Whisper*.

La pregunta se volvió urgente por una razón externa: durante el desarrollo aparecieron
modelos multilingües de arquitectura distinta que declaran mejor calidad y un caudal muy
superior. Defender en 2027 una comparativa que nunca miró fuera de una familia de modelos
sería una debilidad evitable, y la respuesta honesta a *«¿por qué Whisper?»* no puede ser
*«porque fue lo primero que probé»*.

## Hipótesis

**H0:** el modelo base no cambia las conclusiones; un transductor reciente rinde igual que
`whisper-medium` sobre los mismos clips.

Lo que realmente se quiere saber no es solo quién gana en WER; son tres cosas:

1. ¿Cuánta calidad se dejó sobre la mesa al fijar Whisper?
2. ¿Se mantiene el hallazgo central del trabajo, que el WER agregado esconde los fallos
   que importan en accesibilidad, sobre una arquitectura distinta? Si se mantiene, deja de
   ser una peculiaridad de Whisper y pasa a ser una propiedad de la métrica.
3. ¿Cambia el margen de latencia lo suficiente como para replantear el diseño del sistema
   en vivo?

## Diseño

- **Pareado:** los mismos clips para los dos sistemas, del mismo manifiesto.
- **Corpus:** `voxpopuli_es_400` (400 clips, habla parlamentaria leída) y
  `teleconciencia_es_400` (400 clips, habla espontánea, que es donde exp-000
  encontró que escalar el modelo deja de ayudar).
- **Métricas:** WER y CER con los tres normalizadores congelados, tasa de error sobre
  tokens críticos (negaciones, numerales, cuantificadores) y factor de tiempo real.
- **Contraste:** test de signos sobre clips más intervalo de confianza al 95% por
  remuestreo de clips. Se exige que **ambos** coincidan para declarar diferencia.
- **Lote de 1 para los dos.** Whisper rellena toda entrada a 30 segundos, así que agrupar
  no le añade relleno; Parakeet procesa la duración real y agruparlo obligaría a rellenar
  hasta el clip más largo del lote, lo que puede alterar su salida. Además el coste medido
  dejaría de ser comparable entre arquitecturas.

## La asimetría que no se puede eliminar

Whisper se evalúa con reintento por temperatura, la decodificación congelada en R14.
Parakeet no admite nada equivalente: es un transductor, emite un símbolo por trama sin
bucle autorregresivo sobre el texto, de modo que no existen ni umbral de log-probabilidad
ni reintento con temperatura sobre los que igualar la configuración.

No hay forma de igualar la decodificación entre las dos arquitecturas, así que **la
comparación es entre sistemas completos**, cada uno en su configuración estándar, y no
entre codificadores con el resto controlado. Se declara aquí porque disimularlo sería
exactamente el tipo de factor de confusión que R14 obligó a documentar.

## Resultados

800 clips, 400 por corpus. Cifras generadas por `eval/report/tabla_arquitecturas.py`.

| Corpus | Modelo | WER | Crít. | Crít. sin num. | Velocidad | Veredicto |
|---|---|---:|---:|---:|---:|---|
| `voxpopuli_es_400` | `whisper-medium` | 9.63 | 17.52 | 7.74 | 8× | referencia |
| `voxpopuli_es_400` | `parakeet-tdt-0.6b-v3` | **6.83** | 4.46 | **4.33** | **44×** | mejora |
| `teleconciencia_es_400` | `whisper-medium` | **19.55** | 22.17 | 23.08 | 8× | referencia |
| `teleconciencia_es_400` | `parakeet-tdt-0.6b-v3` | 19.83 | 10.36 | **10.00** | **72×** | sin evidencia |

### 1. La ventaja en WER existe, pero solo en habla leída

En habla parlamentaria Parakeet gana 2.80 puntos (IC 95% [-3.48, -2.20]). En habla
espontánea la diferencia es de 0.28 puntos con el intervalo cruzando el cero: **no hay
evidencia de que ninguno sea mejor**.

Parte de esa ventaja era ortográfica y hubo que descontarla. Las referencias escriben
todos los números en letra; Whisper produce 65 fichas con dígitos en `voxpopuli` y
Parakeet ninguna. Como «dos mil diez» son tres fichas y «2010» una sola, el alineamiento
cuenta **tres errores por una cifra bien reconocida**. Repitiendo el contraste solo sobre
los 240 clips sin numerales en la referencia, la ventaja baja de 2.80 a 2.31 puntos y
sigue siendo significativa: es real, pero un 18% de lo medido era convención de escritura.
Detalle en `research/results/estilo_numerico.md`.

### 2. El WER esconde una diferencia enorme en lo que importa

Es el resultado más interesante, y confirma la tesis central del trabajo sobre una
arquitectura distinta. En `teleconciencia_es_400` los dos modelos son **indistinguibles en
WER** y sin embargo:

| Categoría crítica | `whisper-medium` | `parakeet-tdt` |
|---|---:|---:|
| Negaciones perdidas | 48 / 138 (**35%**) | 16 / 138 (**12%**) |
| Cuantificadores | 12 / 122 | 10 / 122 |

Un evaluador que solo mirase el WER concluiría que da igual cuál se use. Uno de los dos
pierde el triple de negaciones que el otro, y en accesibilidad perder un «no» invierte el
significado de la frase.

### 3. Y aun así Parakeet no sirve para este sistema

El criterio que decidió el modelo base en `docs/decisiones/002-modelo-base.md` no fue el
WER sino el **modo de fallo**, y aplicado aquí sale en contra del ganador aparente:

| Sistema | Clips | Fuga de idioma | Salidas vacías |
|---|---:|---:|---:|
| `whisper-medium` | 800 | **0** | 0 |
| `parakeet-tdt-0.6b-v3` | 800 | **13** | 2 |

Parakeet no falla: **traduce**. Ante habla espontánea española produjo *«Hello, what are
you talking about?»*, *«Psychological that your wife will necessarily»*, y alternancias a
media frase como *«aumenta the number of adipositos. This is a signal of alarm»*.

Es exactamente el fallo que descartó a `large-v3-turbo`: salida fluida, verosímil y falsa,
que el alumno sordo no tiene forma de detectar. Un subtítulo ausente se nota; uno traducido
al inglés, tampoco se nota como error del sistema: se lee como si el docente hubiera
cambiado de idioma.

**Y no se puede arreglar por configuración.** Parakeet TDT no ofrece ningún mecanismo para
forzar el idioma: no tiene `forced_decoder_ids` ni `lang_id`, y su `generation_config` solo
declara tokens especiales. El idioma es implícito en el audio, y cuando el modelo duda,
deriva al inglés. Whisper, al que sí se le fuerza `language="es"`, no lo hizo ni una vez en
los mismos 800 clips.

Hizo falta un detector nuevo para verlo: el de anomalías mide **longitud**, y una frase
traducida tiene longitud normal. Ver `eval/report/fuga_idioma.py`.

### 4. La velocidad no rescata el diseño

Parakeet procesa entre 44 y 72 veces más rápido que el audio, frente a 8 de Whisper. Es
mucho, y no cambia nada: la latencia del sistema en vivo está dominada por la espera a que
se llene la ventana de audio, no por la inferencia. Aunque el modelo fuese instantáneo,
seguiría habiendo que esperar a que el docente termine la frase.

## Conclusión

**Se mantiene `whisper-medium` como modelo base**, ahora por una razón medida y no por
inercia. La respuesta a «¿por qué Whisper y no una arquitectura más reciente?» deja de ser
«porque fue lo primero que probé» y pasa a ser «porque la alternativa traduce al inglés
trece veces en ochocientos clips y no admite que se le imponga el idioma».

Nada de esto invalida la comparativa de técnicas de adaptación: se sostiene sobre el mismo
modelo base, que sigue siendo la elección correcta. Y el hallazgo 2 la **refuerza**, porque
demuestra que la insuficiencia del WER no era una peculiaridad de Whisper.

## Reproducir

```bash
make exp-004 CORPUS=voxpopuli_es_400
make exp-004 CORPUS=teleconciencia_es_400
.venv/bin/python research/eval/report/tabla_arquitecturas.py
.venv/bin/python research/eval/report/estilo_numerico.py
.venv/bin/python research/eval/report/fuga_idioma.py
```

## Reproducir

```bash
make exp-004 CORPUS=voxpopuli_es_400
make exp-004 CORPUS=teleconciencia_es_400
```
