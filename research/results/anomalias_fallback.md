| Modelo | Corpus | Decod. | Clips | Truncados | Graves | Expandidos | Ratio med. |
|---|---|---|---:|---:|---:|---:|---:|
| `whisper-base` | `fleurs_es` | fallback | 20 | 0 | **0** | 0 | 1.00 |
| `whisper-large-v3-turbo` | `fleurs_es` | fallback | 20 | 0 | **0** | 0 | 1.00 |
| `whisper-large-v3-turbo` | `mediaspeech_es` | fallback | 40 | 1 | **1** ⚠️ | 0 | 1.00 |
| `whisper-large-v3-turbo` | `tedx_es` | fallback | 40 | 0 | **0** | 0 | 1.00 |
| `whisper-large-v3-turbo` | `teleconciencia_es` | fallback | 40 | 0 | **0** | 0 | 1.00 |
| `whisper-large-v3-turbo` | `voxpopuli_es` | fallback | 40 | 2 | **2** ⚠️ | 0 | 1.00 |
| `whisper-large-v3` | `fleurs_es` | fallback | 20 | 0 | **0** | 0 | 1.00 |
| `whisper-medium` | `fleurs_es` | fallback | 20 | 0 | **0** | 0 | 1.00 |
| `whisper-medium` | `mediaspeech_es` | fallback | 40 | 0 | **0** | 0 | 0.97 |
| `whisper-medium` | `tedx_es` | fallback | 40 | 0 | **0** | 0 | 1.00 |
| `whisper-medium` | `teleconciencia_es` | fallback | 1200 | 5 | **0** | 0 | 0.96 |
| `whisper-medium` | `voxpopuli_es_400` | fallback | 400 | 4 | **2** ⚠️ | 0 | 1.00 |
| `whisper-medium` | `voxpopuli_es` | fallback | 40 | 0 | **0** | 0 | 1.00 |
| `whisper-small` | `fleurs_es` | fallback | 20 | 0 | **0** | 0 | 1.00 |
| `whisper-small` | `mediaspeech_es` | fallback | 40 | 0 | **0** | 0 | 0.97 |
| `whisper-small` | `tedx_es` | fallback | 40 | 0 | **0** | 0 | 1.00 |
| `whisper-small` | `teleconciencia_es` | fallback | 40 | 0 | **0** | 0 | 0.96 |
| `whisper-small` | `voxpopuli_es` | fallback | 40 | 0 | **0** | 0 | 1.00 |
| `whisper-tiny` | `fleurs_es` | fallback | 20 | 0 | **0** | 0 | 1.00 |

## Salidas gravemente truncadas

Menos de un cuarto de las palabras de la referencia. Revisar a mano: una salida corta **y fluida** es una alucinación, no un truncamiento.

- `whisper-large-v3-turbo`/`mediaspeech_es`/fallback — mediaspeech_es_0031: «¡Gracias!»
- `whisper-large-v3-turbo`/`voxpopuli_es`/fallback — voxpopuli_es_0014: «Gracias, señora presidenta.»
- `whisper-large-v3-turbo`/`voxpopuli_es`/fallback — voxpopuli_es_0025: «Gracias, señora presidenta.»
- `whisper-medium`/`voxpopuli_es_400`/fallback — voxpopuli_es_400_0169: «Gracias.»
- `whisper-medium`/`voxpopuli_es_400`/fallback — voxpopuli_es_400_0392: «Gracias, señora presidenta.»

