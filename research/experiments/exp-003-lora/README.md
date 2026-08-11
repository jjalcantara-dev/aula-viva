# exp-003 — Ajuste fino con LoRA

## Hipótesis

Adaptar los pesos del modelo al dominio mejora el reconocimiento más que las técnicas que
actúan sin tocarlo (prompting, post-corrección).

## Diseño

**Sin fuga por construcción**: se entrena con la partición `train` de VoxPopuli y se evalúa
con `test`. La separación la garantiza el propio dataset, no una división nuestra.

- Entrenamiento: 1.500 clips, 4,64 h · `whisper-medium` · LoRA r=16 sobre `q_proj`/`v_proj`
- 4,72 M parámetros entrenables (0,6% del total) · 2 épocas · 15,8 min · adaptador de 18,9 MB
- Evaluación: 400 clips, 12.951 palabras, diseño pareado

El adaptador se **activa y desactiva sobre el mismo modelo cargado**
(`enable_adapter_layers` / `disable_adapter_layers`), de modo que la única diferencia entre
condiciones es LoRA.

### Por qué VoxPopuli y no CIEMPIESS, que tiene más clips

Las referencias de CIEMPIESS omiten tildes sistemáticamente (R11). Ajustar el modelo sobre
ellas le enseñaría a **no acentuar**, y al medirlo contra esas mismas referencias sucias el
WER *mejoraría*. Habríamos optimizado hacia el error con la métrica dándonos la razón.

Es la trampa más peligrosa del trabajo, porque el resultado sería excelente sobre el papel.

## Resultado: la única técnica que mejora

| | Sin LoRA | Con LoRA | Δ |
|---|---:|---:|---:|
| **WER** | 9.63% | **8.40%** | **−1.23** |
| CER | 6.64% | 5.30% | −1.34 |
| Sustituciones | 565 | 527 | −38 |
| Borrados | 456 | 342 | **−114** |
| Error crítico | 17.52% | 6.12% | −11.40 |

- IC 95%: **[−1.75, −0.77]** · pareado **112 mejoran / 54 empeoran** · p < 0.0001
- **Significativa por ambos criterios** (IC y test de signos coinciden)

Es la única de las tres técnicas que mejora de forma concluyente, y tiene sentido: es la
única que modifica los pesos del modelo.

## El matiz que hay que declarar: aprende la convención, no solo a reconocer

La caída del error crítico (17.52% → 6.12%) es engañosa. Viene casi toda de los numerales
(81 → 17 errores), y el motivo se ve contando dígitos:

```
dígitos totales →  referencia: 0    sin LoRA: 162    con LoRA: 1
```

VoxPopuli escribe los números **en letra**; Whisper los escribía en cifra. El ajuste fino
ha aprendido esa convención de transcripción. **Es adaptación real al corpus, pero es
adaptación de estilo, no de reconocimiento acústico.**

El caso que lo demuestra:

```
REF     : los uno seiscientos ochenta y seis millones de euros
sin LoRA: los 1 686 millones de euros            ← valor correcto, formato distinto
con LoRA: los cero cero seis millones de euros   ← formato correcto, valor MAL
```

El modelo ajustado acertó el estilo y **falló el número**, y las dos métricas lo premian
porque ambas comparan contra una referencia escrita en letra.

**Descontando los numerales, la mejora del error crítico es real pero modesta: 7.7% → 6.2%**
(negaciones 11→7, cuantificadores 14→13).

Lectura honesta: LoRA mejora el WER de forma significativa, pero **parte de la mejora es
alineamiento con la forma superficial de la referencia**, no mejor comprensión del audio.
En un despliegue real esa distinción importa: si el corpus de ajuste escribe de una manera
y el docente espera otra, la "mejora" no se traslada.

## Incidente: el primer entrenamiento estaba roto y no daba error

La primera ejecución terminó sin fallos, guardó su adaptador y produjo métricas evaluables.
Pero la pérdida se quedó en **6,87 y subía entre épocas** (5,77 → 6,87).

Causa: el colador descartaba el token inicial comparando con `bos_token_id`, que en Whisper
es `<|endoftext|>` (50257), cuando las etiquetas empiezan por `<|startoftranscript|>`
(50258). La comprobación nunca se cumplía, el modelo anteponía **otro** token de inicio al
desplazar las etiquetas, y todo quedaba desalineado una posición.

Con el token correcto la pérdida cae a **0,21** y baja entre épocas (0,3231 → 0,2056).

**Si no se hubiera detectado**, la evaluación habría mostrado que LoRA destroza el modelo,
con intervalo de confianza estrecho y p diminuto respaldando un artefacto.

> **Regla adoptada**: antes de evaluar ningún entrenamiento, comprobar que la pérdida esté
> en el rango esperado y que **baje entre épocas**. Treinta segundos que separan un
> resultado de un artefacto.

## Limitaciones

- 1.500 clips y 2 épocas: es un ajuste modesto. Con más datos el efecto podría crecer.
- Dominio parlamentario, no educativo. El objetivo sigue siendo poliMedia.
- Sin barrido de hiperparámetros (rango, tasa, módulos objetivo). El resultado corresponde
  a una configuración razonable, no a la mejor posible.
- No se ha medido el coste en latencia de aplicar el adaptador en producción.

## Reproducir

```bash
make exp-003            # entrena y evalúa
make exp-003 EPOCAS=4   # más épocas
```
