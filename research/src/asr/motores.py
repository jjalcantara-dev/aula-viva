"""Motores de reconocimiento para los experimentos, tras una interfaz comun.

Existe porque la comparativa dejo de ser "Whisper frente a Whisper". Whisper es un
codificador-decodificador autorregresivo y Parakeet es un transductor: no comparten ni la
forma de la entrada, ni el bucle de decodificacion, ni los tokens especiales. Sin esta
capa, cada experimento que quisiera contrastar arquitecturas tendria que ramificar por
tipo de modelo, y esa ramificacion acabaria divergiendo entre experimentos.

Es el equivalente en investigacion de lo que IMotorAsr es en la aplicacion: la frontera
que permite cambiar el modelo sin tocar quien lo mide.
"""

from dataclasses import dataclass, field

import numpy as np
import torch

# Reintento con temperatura, como en la implementacion de referencia de Whisper. NO es un
# detalle de implementacion sino un FACTOR DE CONFUSION (R14): medido sobre voxpopuli_es,
# la decodificacion voraz hace que large-v3-turbo trunque 6 de 40 clips e invente frases
# plausibles del dominio, con el WER pasando de ~10% a 24.22%.
#
# Vive AQUI y no en cada experimento para que haya un unico sitio donde este congelada.
DECODIFICACION_WHISPER = {
    "voraz": {},
    "fallback": dict(
        temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
        logprob_threshold=-1.0,
        compression_ratio_threshold=1.35,
        no_speech_threshold=0.6,
        return_timestamps=True,
    ),
}


@dataclass
class Motor:
    """Un modelo cargado y listo para transcribir.

    `decodificacion` entra en la identidad del resultado y por eso se expone: dos
    ejecuciones del mismo modelo con distinta decodificacion no son comparables.
    """

    nombre: str
    decodificacion: str
    parametros_M: int
    carga_s: float
    _transcribir: object = field(repr=False)

    def transcribir(self, audios: list[np.ndarray], sr: int) -> list[str]:
        return self._transcribir(audios, sr)


def _cargar_whisper(nombre, decodificacion, idioma, dispositivo, dtype):
    from transformers import AutoProcessor, WhisperForConditionalGeneration

    proc = AutoProcessor.from_pretrained(nombre)
    modelo = WhisperForConditionalGeneration.from_pretrained(
        nombre, dtype=dtype).to(dispositivo).eval()

    def transcribir(audios, sr):
        # Whisper rellena toda entrada a 30 s, asi que los ejemplos de un lote tienen
        # forma identica y agruparlos no requiere relleno adicional.
        ent = proc(audios, sampling_rate=sr, return_tensors="pt")
        feats = ent.input_features.to(dispositivo, dtype=dtype)
        with torch.no_grad():
            ids = modelo.generate(feats, language=idioma, task="transcribe",
                                  **DECODIFICACION_WHISPER[decodificacion])
        return [t.strip() for t in proc.batch_decode(ids, skip_special_tokens=True)]

    return proc, modelo, transcribir


def _cargar_parakeet(nombre, decodificacion, idioma, dispositivo, dtype):
    # AutoModel y no AutoModelForCTC: pese al nombre de la familia, la variante TDT es un
    # transductor y su configuracion no esta registrada en la cabeza de CTC.
    from transformers import AutoModel, AutoProcessor

    # `idioma` SE IGNORA, y no por descuido. Parakeet TDT no ofrece ninguna forma de
    # forzarlo: no tiene forced_decoder_ids ni lang_id, y su generation_config solo
    # declara tokens especiales. El idioma es implicito en el audio.
    #
    # No es un detalle: medido en exp-004 sobre habla espontanea espanola, el modelo
    # TRADUJO al ingles en 12 de 400 clips ("Hello, what are you talking about?") y
    # alterno idioma a media frase ("aumenta the number of adipositos"). Whisper, al que
    # SI se le fuerza language="es", no lo hizo ni una vez en los mismos 800 clips.
    #
    # Se acepta el parametro para que la interfaz sea comun, pero quien lo pase debe saber
    # que no surte efecto. Silenciarlo sin decirlo seria peor.
    del idioma

    if decodificacion != "tdt":
        raise SystemExit(
            f"parakeet no admite '{decodificacion}'. Es un transductor: emite un simbolo "
            "por trama sin bucle autorregresivo sobre el texto, asi que no existe "
            "reintento con temperatura ni umbral de logprob. Su unica decodificacion es "
            "'tdt', y esa asimetria hay que declararla al comparar, no disimularla.")

    proc = AutoProcessor.from_pretrained(nombre)
    modelo = AutoModel.from_pretrained(nombre, dtype=dtype).to(dispositivo).eval()

    def transcribir(audios, sr):
        ent = proc(audios, sampling_rate=sr, return_tensors="pt").to(dispositivo, dtype=dtype)
        with torch.no_grad():
            salida = modelo.generate(**ent)
        # generate devuelve ParakeetRNNTGenerateOutput, no un tensor. Y sin
        # skip_special_tokens el texto sale sembrado de <blank>: el simbolo que el
        # transductor emite en las tramas donde decide no producir nada.
        return [t.strip() for t in
                proc.batch_decode(salida.sequences, skip_special_tokens=True)]

    return proc, modelo, transcribir


FAMILIAS = {
    "whisper": (_cargar_whisper, "fallback"),
    "parakeet": (_cargar_parakeet, "tdt"),
}


def familia(nombre: str) -> str:
    for clave in FAMILIAS:
        if clave in nombre.lower():
            return clave
    raise SystemExit(f"no se reconoce la familia de '{nombre}'. Conocidas: {list(FAMILIAS)}")


def decodificacion_por_defecto(nombre: str) -> str:
    return FAMILIAS[familia(nombre)][1]


def cargar(nombre: str, decodificacion: str | None = None, idioma: str = "es",
           dispositivo: str = "cuda", dtype: torch.dtype = torch.float16) -> Motor:
    import time

    fam = familia(nombre)
    constructor, por_defecto = FAMILIAS[fam]
    decodificacion = decodificacion or por_defecto

    t0 = time.perf_counter()
    _, modelo, transcribir = constructor(nombre, decodificacion, idioma, dispositivo, dtype)
    carga_s = time.perf_counter() - t0

    return Motor(
        nombre=nombre,
        decodificacion=decodificacion,
        parametros_M=round(sum(p.numel() for p in modelo.parameters()) / 1e6),
        carga_s=round(carga_s, 1),
        _transcribir=transcribir,
    )
