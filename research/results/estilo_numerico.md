# Estilo numérico: ¿cuánta de la ventaja de exp-004 es ortografía?

## `teleconciencia_es_400`

### Fichas escritas con dígitos

| Sistema | Referencia | Hipótesis | Desviación |
|---|---:|---:|---:|
| `nvidia_parakeet-tdt-0.6b-v3` | 0 | 5 | +5 |
| `openai_whisper-medium` | 0 | 31 | +31 |

### Contraste sobre los 294 de 400 clips cuya referencia no contiene numerales

| Sistema | WER (sin numerales) | Δ (pp) | IC 95% | p | Veredicto |
|---|---:|---:|---|---:|---|
| `openai_whisper-medium` | 19.48 | — | — | — | referencia |
| `nvidia_parakeet-tdt-0.6b-v3` | 19.70 | +0.22 | [-1.42, +2.18] | 0.0016 | sin evidencia |

## `voxpopuli_es_400`

### Fichas escritas con dígitos

| Sistema | Referencia | Hipótesis | Desviación |
|---|---:|---:|---:|
| `nvidia_parakeet-tdt-0.6b-v3` | 0 | 0 | +0 |
| `openai_whisper-medium` | 0 | 65 | +65 |

### Contraste sobre los 240 de 400 clips cuya referencia no contiene numerales

| Sistema | WER (sin numerales) | Δ (pp) | IC 95% | p | Veredicto |
|---|---:|---:|---|---:|---|
| `openai_whisper-medium` | 9.45 | — | — | — | referencia |
| `nvidia_parakeet-tdt-0.6b-v3` | 7.14 | -2.31 | [-3.29, -1.48] | 2.1e-08 | mejora |

