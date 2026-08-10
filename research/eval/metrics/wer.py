"""Metricas de calidad de transcripcion.

WER (Word Error Rate) y CER (Character Error Rate), calculadas de forma agregada
sobre el corpus completo -- NO como media de los WER por clip.

Motivo: la media de ratios pondera igual un clip de 3 s y uno de 30 s, y con
clips cortos un solo error dispara el WER individual. El agregado (suma de
errores / suma de palabras) es el estandar en la literatura ASR y es el que
debe reportarse en la memoria.
"""

from dataclasses import dataclass, asdict

import jiwer


@dataclass
class Resultado:
    wer: float
    cer: float
    n_clips: int
    n_palabras_ref: int
    sustituciones: int
    inserciones: int
    borrados: int

    def como_dict(self):
        return asdict(self)

    def __str__(self):
        return (f"WER={self.wer:6.2%}  CER={self.cer:6.2%}  "
                f"(S={self.sustituciones} I={self.inserciones} D={self.borrados}, "
                f"{self.n_palabras_ref} palabras en {self.n_clips} clips)")


def evaluar(referencias: list[str], hipotesis: list[str]) -> Resultado:
    """WER/CER agregados. Descarta pares cuya referencia quede vacia."""
    pares = [(r, h) for r, h in zip(referencias, hipotesis) if r.strip()]
    if not pares:
        raise ValueError("no hay referencias no vacias que evaluar")
    refs, hips = map(list, zip(*pares))

    salida = jiwer.process_words(refs, hips)
    return Resultado(
        wer=salida.wer,
        cer=jiwer.process_characters(refs, hips).cer,
        n_clips=len(refs),
        n_palabras_ref=sum(len(r.split()) for r in refs),
        sustituciones=salida.substitutions,
        inserciones=salida.insertions,
        borrados=salida.deletions,
    )
