| Estrategia | Tope | WER (%) | Dur. media (s) | Dur. p95 (s) | Segmentos |
|---|---:|---:|---:|---:|---:|
| ventana fija | 2 s | 23.19 | 1.87 | 2.00 | 277 |
| **silencios** | 2 s | 20.87 | 1.69 | 2.00 | 306 |
| ventana fija | 3 s | 19.85 | 2.68 | 3.00 | 193 |
| **silencios** | 3 s | 17.33 | 2.22 | 3.00 | 232 |
| ventana fija | 5 s | 17.12 | 4.27 | 5.00 | 121 |
| **silencios** | 5 s | 14.53 | 2.78 | 5.00 | 186 |
| ventana fija | 8 s | 13.92 | 6.30 | 8.00 | 82 |
| **silencios** | 8 s | 12.48 | 2.93 | 5.92 | 176 |
| sin trocear (techo) | — | 10.44 | — | — | — |

## A latencia media equivalente

| Estrategia | Tope | WER (%) | Dur. media (s) | Dur. p95 (s) |
|---|---:|---:|---:|---:|
| ventana fija | 3 s | 19.85 | 2.68 | 3.00 |
| **silencios** | 8 s | **12.48** | 2.93 | 5.92 |

Diferencia: **7.37 pp** de WER con 0.26 s de diferencia en latencia media, a costa de que el p95 suba de 3.00 a 5.92 s.

Contraste pareado sobre los mismos clips: IC 95% [-9.76, -5.04] pp, 30 clips mejoran y 2 empeoran (p=2.5e-07), 1466 palabras de referencia. Veredicto: **mejora**.
