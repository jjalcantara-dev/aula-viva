# Fuga de idioma y salidas vacías

Casos en que el sistema traduce en lugar de transcribir, o no devuelve nada.
El detector de anomalías por longitud no ve los primeros: una frase traducida
tiene longitud normal.

| Sistema | Clips | Fuga de idioma | Vacías |
|---|---:|---:|---:|
| `nvidia_parakeet-tdt-0.6b-v3__teleconciencia_es_400__tdt` | 400 | **12** ⚠️ | 1 |
| `nvidia_parakeet-tdt-0.6b-v3__voxpopuli_es_400__tdt` | 400 | **1** ⚠️ | 1 |
| `openai_whisper-medium__teleconciencia_es_400__fallback` | 400 | **0** | 0 |
| `openai_whisper-medium__voxpopuli_es_400__fallback` | 400 | **0** | 0 |

### `nvidia_parakeet-tdt-0.6b-v3__teleconciencia_es_400__tdt`

- [teleconciencia_es_0002] «and the platinum orientación. Andamos toda esta information and los cu…» (and, the, and, the)
- [teleconciencia_es_0015] «Psychological that your wife will necessarily. And for sure, many does…» (that, your, will, and)
- [teleconciencia_es_0020] «Sobre este proceso de duelo and. ¿Por qué? Because you no le puedes de…» (and, because, you)
- [teleconciencia_es_0048] «With the school. No vas a travers de manera conjunta in the adequation…» (with, the, the, that)
- [teleconciencia_es_0051] «Porque llegan siempre my hijo de ahí, what do you want to do for my hi…» (what, you)
- [teleconciencia_es_0086] «aumenta the number of adipositos. This is a signal of alarm, in which …» (the, of, this, is)
- [teleconciencia_es_0119] «And when they cohabitan in an ambiente of much dimension, and estimula…» (and, when, they, of)
- [teleconciencia_es_0120] (salida vacía) ← «entonces partiendo de esa premisa nosotros en laboratorio mo…»

### `nvidia_parakeet-tdt-0.6b-v3__voxpopuli_es_400__tdt`

- [voxpopuli_es_400_0169] (salida vacía) ← «para mí todas las personas que estamos aquí todos los eurodi…»
- [voxpopuli_es_400_0341] «There are innocents on all sides.…» (there, are)
