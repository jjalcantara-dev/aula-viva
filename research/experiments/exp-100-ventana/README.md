# exp-100 — Latencia frente a calidad al trocear el audio en vivo

## Pregunta

La aplicación no puede esperar a que el docente termine la frase: debe trocear el audio en
ventanas y transcribir cada una. Ventanas cortas bajan la latencia pero dan al modelo menos
contexto acústico. **¿Cuánto WER cuesta cada segundo de latencia que se ahorra?**

Sin este barrido, el tamaño de ventana de la aplicación sería un número elegido a ojo.

## Diseño

`whisper-medium`, 40 clips de `voxpopuli_es` (peninsular, transcripción verificada),
decodificación con reintento de temperatura. Cada ventana se transcribe por separado y los
textos se concatenan; se compara con la referencia completa.

Latencia estimada = ventana + inferencia por ventana. Es una **cota inferior**: no incluye
red ni renderizado, que se miden aparte en la aplicación.

Se ejecutaron dos condiciones para separar dos efectos que se confunden:

- **con solapamiento de 1 s** — como lo hacía la aplicación inicialmente
- **sin solapamiento** — aísla el efecto de la pérdida de contexto

## Resultados

| Ventana | WER con solape 1 s | **WER sin solape** | Latencia est. | Trozos |
|---:|---:|---:|---:|---:|
| 1 s | 105.32% | **35.81%** | 1.51 s | 530 |
| 2 s | 104.09% | **23.12%** | 2.55 s | 277 |
| 3 s | 54.43% | **19.85%** | 3.61 s | 193 |
| 5 s | 33.22% | **17.12%** | 5.77 s | 121 |
| 8 s | 22.71% | **13.92%** | 8.98 s | 82 |
| sin trocear | 10.44% | 10.44% | — | 40 |

## Hallazgo 1 — la duplicación por solapamiento era casi todo el problema

Un WER **por encima del 100%** significa que el sistema emite más errores que palabras
tiene la referencia: está insertando texto masivamente. La causa no era el modelo sino la
implementación: cada ventana repetía el final de la anterior y ese texto se concatenaba
dos veces. Con ventana de 1 s y solape de 0,5 s, la mitad del contenido estaba duplicado.

Aislado el efecto, el coste real de trocear es mucho menor: **35.81% en lugar de 105.32%**
con ventanas de 1 segundo.

**Corregido** con `Solapamiento.Fusionar` en `Accesibilidad.Core`, que recorta el mayor
solape entre el final del texto ya emitido y el principio del nuevo. Cubierto por pruebas
en `app/tests/`. Gracias a eso la aplicación puede conservar el solapamiento —que evita
partir palabras en la frontera— sin pagar su coste.

## Hallazgo 2 — el troceado sigue siendo caro, y la latencia utilizable es peor de lo esperado

Incluso sin duplicación, trocear degrada de forma sustancial:

| Ventana | WER | Frente al ideal (10.44%) |
|---:|---:|---|
| 8 s | 13.92% | ×1.33 |
| 5 s | 17.12% | ×1.64 |
| 3 s | 19.85% | ×1.90 |
| 2 s | 23.12% | ×2.21 |
| 1 s | 35.81% | ×3.43 |

En un aula, un retardo por encima de 3-4 segundos incomoda. Pero a 3 segundos de ventana
el WER **casi se duplica** respecto a transcribir el fragmento completo. El compromiso es
mucho más duro de lo que sugiere la intuición.

## Conclusión: el troceado por tiempo fijo es una mala estrategia

Cortar cada N segundos parte palabras y frases por la mitad, precisamente donde el modelo
más necesita contexto. La alternativa es **cortar por silencios** (detección de actividad
de voz): las fronteras caen entre frases, el modelo recibe unidades completas y la latencia
percibida mejora porque el subtítulo aparece cuando el docente hace una pausa natural.

Es la línea de trabajo con más recorrido del núcleo aplicado, y este barrido es la
justificación medida de por qué hace falta. 🔴 **DIRECTOR: confirmar que entra en alcance.**

## Limitaciones

- Un solo modelo y un solo corpus. Habría que confirmar en el corpus definitivo.
- La latencia estimada no incluye red ni renderizado.
- La concatenación es ingenua incluso sin solapamiento: no reconstruye palabras partidas
  por la frontera.

## Reproducir

```bash
.venv/bin/python research/experiments/exp-100-ventana/run.py \
    --manifiesto research/corpus/manifests/voxpopuli_es.jsonl \
    --modelo openai/whisper-medium --limite 40 --solape 0
```

Los resultados se nombran por `<modelo>__<corpus>__solape<N>`: dos barridos con solapes
distintos no son comparables y no deben compartir fichero.
