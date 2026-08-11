| Modelo | Corpus | WER | **Error crítico** | Negaciones | Numerales | Cuantif. |
|---|---|---:|---:|---:|---:|---:|
| `whisper-base` | `fleurs_es` | 11.42% | **3.70%** | 0/6 | 0/14 | 1/7 |
| `whisper-large-v3-turbo` | `fleurs_es` | 3.41% | **0.00%** | 0/6 | 0/14 | 0/7 |
| `whisper-large-v3-turbo` | `mediaspeech_es` | 15.60% | **19.32%** | 6/23 | 11/41 | 0/24 |
| `whisper-large-v3-turbo` | `tedx_es` | 11.12% | **14.55%** | 2/16 | 6/26 | 0/13 |
| `whisper-large-v3-turbo` | `teleconciencia_es` | 22.26% | **18.46%** | 8/34 | 2/16 | 2/15 |
| `whisper-large-v3-turbo` | `voxpopuli_es` | 11.53% | **7.25%** | 1/21 | 2/29 | 2/19 |
| `whisper-large-v3` | `fleurs_es` | 3.01% | **0.00%** | 0/6 | 0/14 | 0/7 |
| `whisper-medium` | `fleurs_es` | 3.21% | **0.00%** | 0/6 | 0/14 | 0/7 |
| `whisper-medium` | `mediaspeech_es` | 14.72% | **18.18%** | 6/23 | 10/41 | 0/24 |
| `whisper-medium` | `tedx_es` | 10.22% | **12.73%** | 2/16 | 5/26 | 0/13 |
| `whisper-medium` | `teleconciencia_es` | 18.61% | **20.23%** | 134/477 | 99/459 | 34/384 |
| `whisper-medium` | `voxpopuli_es_400` | 9.63% | **17.52%** | 11/168 | 81/282 | 14/155 |
| `whisper-medium` | `voxpopuli_es` | 10.44% | **4.35%** | 0/21 | 2/29 | 1/19 |
| `whisper-small` | `fleurs_es` | 6.61% | **3.70%** | 0/6 | 0/14 | 1/7 |
| `whisper-small` | `mediaspeech_es` | 15.94% | **18.18%** | 5/23 | 11/41 | 0/24 |
| `whisper-small` | `tedx_es` | 12.13% | **12.73%** | 2/16 | 5/26 | 0/13 |
| `whisper-small` | `teleconciencia_es` | 23.42% | **29.23%** | 15/34 | 2/16 | 2/15 |
| `whisper-small` | `voxpopuli_es` | 12.01% | **7.25%** | 0/21 | 3/29 | 2/19 |
| `whisper-tiny` | `fleurs_es` | 19.44% | **3.70%** | 0/6 | 0/14 | 1/7 |

> **Error crítico**: proporción de negaciones, numerales y cuantificadores de la referencia que el sistema no reproduce correctamente. Un error aquí cambia el sentido; un error de WER corriente suele reconstruirse por contexto.

### Negaciones inventadas

El fallo más grave posible: el sistema introduce una negación que nadie dijo, invirtiendo la afirmación.

- `whisper-large-v3-turbo`/`teleconciencia_es`: **2 negaciones inventadas** (el sistema niega algo que no se negó)
- `whisper-medium`/`mediaspeech_es`: **2 negaciones inventadas** (el sistema niega algo que no se negó)
- `whisper-medium`/`teleconciencia_es`: **13 negaciones inventadas** (el sistema niega algo que no se negó)
- `whisper-medium`/`voxpopuli_es_400`: **1 negaciones inventadas** (el sistema niega algo que no se negó)
- `whisper-tiny`/`fleurs_es`: **1 negaciones inventadas** (el sistema niega algo que no se negó)

