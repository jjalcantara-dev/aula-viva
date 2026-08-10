"""Descarga una muestra pequena de voz en espanol CON transcripcion de referencia.

Proposito: material minimo para validar el pipeline de evaluacion (WER) antes
de tener el corpus educativo definitivo. NO es el corpus del TFM.

Escribe:
  research/corpus/raw/<fuente>/*.wav        (gitignored)
  research/corpus/manifests/<fuente>.jsonl  (en git: id, ruta, referencia, duracion)

Uso:  .venv/bin/python research/src/data/fetch_sample.py --n 20
"""

import argparse
import io
import json
from pathlib import Path

import soundfile as sf
from datasets import Audio, load_dataset

RAIZ = Path(__file__).resolve().parents[3]
RAW = RAIZ / "research" / "corpus" / "raw"
MANIFESTS = RAIZ / "research" / "corpus" / "manifests"

# Fuentes de arranque. Ninguna es dominio educativo: sirven para validar el
# pipeline, no para responder la pregunta de investigacion.
FUENTES = {
    "fleurs_es": dict(
        ruta="google/fleurs", config="es_419", split="validation",
        campo_texto="transcription",
        nota="Voz leida 16 kHz, frases enciclopedicas. Dominio general.",
    ),
    "minds14_es": dict(
        ruta="PolyAI/minds14", config="es-ES", split="train",
        campo_texto="transcription",
        nota="Voz telefonica 8 kHz, dominio bancario. Peor calidad acustica.",
    ),
    # --- Candidatos con dominio cercano al educativo (ver corpus/FUENTES.md) ---
    "tedx_es": dict(
        ruta="ciempiess/tedx_spanish", config="tedx_spanish", split="train",
        campo_texto="normalized_text",
        nota="Charlas TEDx. Monologo expositivo espontaneo, el mas parecido a una clase.",
    ),
    "teleconciencia_es": dict(
        ruta="ciempiess/tele_con_ciencia", config="tele_con_ciencia", split="train",
        campo_texto="normalized_text",
        nota="Divulgacion cientifica en TV. Terminologia tecnica, habla planificada.",
    ),
    "mls_es": dict(
        ruta="facebook/multilingual_librispeech", config="spanish", split="test",
        campo_texto="transcript",
        nota="Audiolibros. Voz leida limpia; sirve de contraste con el dominio real.",
    ),
    # --- Espanol PENINSULAR (ver FUENTES.md: los anteriores son latinoamericanos) ---
    "voxpopuli_es": dict(
        ruta="facebook/voxpopuli", config="es", split="test",
        campo_texto="normalized_text",
        nota="Parlamento Europeo. Peninsular, espontaneo formal. Trae 'accent' y "
             "'is_gold_transcript' (referencia verificada a mano).",
    ),
    "mediaspeech_es": dict(
        ruta="ymoslem/MediaSpeech", config="es", split="train",
        campo_texto="sentence",
        nota="Medios espanoles. Peninsular, habla profesional de locucion.",
    ),
}


def descargar(nombre: str, n: int) -> int:
    cfg = FUENTES[nombre]
    destino = RAW / nombre
    destino.mkdir(parents=True, exist_ok=True)
    MANIFESTS.mkdir(parents=True, exist_ok=True)

    print(f"\n=== {nombre} ===  {cfg['nota']}")
    ds = load_dataset(cfg["ruta"], cfg["config"], split=cfg["split"], streaming=True)
    # Sin decodificar: evita depender de torchcodec (ata versiones de torch y
    # ffmpeg). Decodificamos nosotros con soundfile, que ya es dependencia.
    ds = ds.cast_column("audio", Audio(decode=False))

    filas, total_s = [], 0.0
    for i, ej in enumerate(ds):
        if i >= n:
            break
        crudo = ej["audio"]
        datos = crudo["bytes"] if crudo.get("bytes") else Path(crudo["path"]).read_bytes()
        arr, sr = sf.read(io.BytesIO(datos), dtype="float32")
        uid = f"{nombre}_{i:04d}"
        wav = destino / f"{uid}.wav"
        sf.write(wav, arr, sr)

        dur = len(arr) / sr
        total_s += dur
        fila = {
            "id": uid,
            "audio": str(wav.relative_to(RAIZ)),
            "referencia": ej[cfg["campo_texto"]],
            "duracion_s": round(dur, 2),
            "sr": sr,
            "fuente": cfg["ruta"],
            "split_origen": cfg["split"],
        }
        # Metadatos utiles cuando la fuente los trae: variedad dialectal, si la
        # transcripcion esta verificada a mano y quien habla. Sin esto no se puede
        # caracterizar el corpus en la memoria ni filtrar por acento.
        for extra in ("accent", "is_gold_transcript", "gender", "speaker_id"):
            if extra in ej and ej[extra] is not None:
                fila[extra] = ej[extra]
        filas.append(fila)
        print(f"  [{i + 1}/{n}] {uid}  {dur:5.1f}s  {ej[cfg['campo_texto']][:60]}...")

    manifiesto = MANIFESTS / f"{nombre}.jsonl"
    with manifiesto.open("w", encoding="utf-8") as f:
        for fila in filas:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")

    print(f"  -> {len(filas)} clips, {total_s / 60:.1f} min")
    print(f"  -> manifiesto: {manifiesto.relative_to(RAIZ)}")
    return len(filas)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20, help="clips por fuente")
    ap.add_argument("--fuentes", nargs="*", default=["fleurs_es"], choices=list(FUENTES))
    args = ap.parse_args()

    for nombre in args.fuentes:
        try:
            descargar(nombre, args.n)
        except Exception as e:
            print(f"  [FALLO] {nombre}: {type(e).__name__}: {e}")
