| Corpus | Modelo | Params | Decod. | WER | CER | Crít. | Crít. sin num. | × tiempo real | Δ WER (pp) | IC 95% | p | Veredicto |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|---:|---|
| `teleconciencia_es_400` | `whisper-medium` | 764M | fallback | 19.55 | 9.06 | 22.17 | 23.08 | 8× | — | — | — | referencia |
| `teleconciencia_es_400` | `parakeet-tdt-0.6b-v3` | 627M | tdt | 19.83 | 8.56 | 10.36 | 10.00 | 106× | +0.28 | [-1.28, +2.03] | 0.00011 | sin evidencia |
| `voxpopuli_es_400` | `whisper-medium` | 764M | fallback | 9.63 | 6.64 | 17.52 | 7.74 | 8× | — | — | — | referencia |
| `voxpopuli_es_400` | `parakeet-tdt-0.6b-v3` | 627M | tdt | 6.83 | 4.47 | 4.46 | 4.33 | 44× | -2.80 | [-3.48, -2.20] | 0 | mejora |

> **Crít. sin num.** excluye los numerales: su recuento mide en parte la convención de escritura y no el reconocimiento, porque la referencia escribe «dos mil diez» donde Whisper escribe «2010» y el alineamiento cuenta tres errores por una cifra bien reconocida. Negaciones y cuantificadores no tienen ese sesgo. Ver `estilo_numerico.md`.
