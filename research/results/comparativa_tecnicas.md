| Técnica | Corpus | Palabras | WER base | WER técnica | Δ (pp) | IC 95% | Mejoran/Empeoran | p | Veredicto |
|---|---|---:|---:|---:|---:|---|---|---:|---|
| Prompting contextual | `tedx_es` | 532 | 10.15 | 9.96 | -0.19 | [-0.61, +0.00] | 1/0 | 1.0000 | ⚠️ sin potencia |
| Prompting contextual | `teleconciencia_es` | 14706 | 18.79 | 19.14 | +0.35 | [-0.52, +1.42] | 129/91 | 0.0124 | en el límite |
| Prompting contextual | `voxpopuli_es` | 771 | 9.99 | 9.60 | -0.39 | [-1.14, +0.45] | 4/1 | 0.3750 | ⚠️ sin potencia |
| Prompting contextual | `voxpopuli_es_400` | 7551 | 9.51 | 9.14 | -0.37 | [-0.76, -0.05] | 16/9 | 0.2295 | en el límite |
| Post-corrección con LLM | `teleconciencia_es` | 8186 | 19.55 | 22.77 | +3.23 | [+2.66, +3.84] | 12/164 | 0.0000 | **significativa** |
| Post-corrección con LLM | `voxpopuli_es_400` | 12951 | 9.63 | 10.81 | +1.18 | [+0.84, +1.54] | 39/130 | 0.0000 | **significativa** |
| Post-corrección con LLM | `voxpopuli_es` | 288 | 12.50 | 12.15 | -0.35 | [-1.69, +1.12] | 1/1 | 1.0000 | ⚠️ sin potencia |
| Fine-tuning con LoRA | `voxpopuli_es_400` | 12951 | 9.63 | 8.40 | -1.23 | [-1.75, -0.77] | 112/54 | 0.0000 | **significativa** |

> ⚠️ Menos de 5,000 palabras de referencia: el intervalo de confianza es demasiado ancho para detectar los efectos esperables. Esas filas **no permiten concluir nada**, ni a favor ni en contra.
