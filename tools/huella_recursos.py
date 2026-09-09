"""Mide la huella de recursos del servicio de reconocimiento: VRAM, RAM y disco.

Por que hace falta: el manual de despliegue tiene que decirle a un centro que tarjeta
grafica necesita comprar, y esa cifra no se puede estimar de memoria. El tamano en disco
del modelo NO es la VRAM que ocupa al ejecutarse, y la VRAM en reposo no es la del pico
durante una transcripcion: hay que medir las tres cosas por separado.

Lo que mide, y por que cada una:

  disco   Lo que hay que descargar y conservar. Determina el requisito de almacenamiento
          del equipo servidor.
  VRAM    Pico durante una transcripcion real, no solo tras cargar los pesos. Es la cifra
          que decide si una tarjeta concreta sirve o no.
  RAM     Memoria residente del proceso. En un equipo compartido con otras tareas es lo
          que determina si el sistema convive con ellas.

El audio de prueba se sintetiza en el propio script y no sale de ningun corpus: aqui no se
mide calidad, solo consumo, y depender de un manifiesto ataria esta medicion a un corpus
concreto sin necesidad.

Uso:  .venv/bin/python tools/huella_recursos.py --modelo openai/whisper-medium
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "research"))

DESTINO = RAIZ / "research" / "results"
FRECUENCIA = 16000
SEGUNDOS_PRUEBA = 30.0          # ventana completa de Whisper: es el caso peor


def tamano_en_disco(modelo: str) -> float | None:
    """Gigabytes que ocupa el modelo en la cache local, si esta descargado."""
    cache = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"
    carpeta = cache / ("models--" + modelo.replace("/", "--"))
    if not carpeta.exists():
        return None
    # Se EXCLUYEN los enlaces simbolicos: la cache guarda los pesos una sola vez en
    # `blobs/` y `snapshots/` apunta a ellos. Contar ambos duplica el tamano, y aqui la
    # cifra acaba siendo un requisito de almacenamiento en el manual de despliegue.
    total = sum(f.stat().st_size for f in carpeta.rglob("*")
                if f.is_file() and not f.is_symlink())
    return total / 1024**3


def ram_residente_gb() -> float | None:
    """Memoria residente del proceso, leida de /proc (solo Linux)."""
    try:
        with open("/proc/self/statm", encoding="utf-8") as f:
            paginas = int(f.read().split()[1])
        return paginas * os.sysconf("SC_PAGE_SIZE") / 1024**3
    except (OSError, IndexError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default="openai/whisper-medium")
    ap.add_argument("--adaptador", default=None,
                    help="ruta a un adaptador LoRA, para medir su coste adicional")
    args = ap.parse_args()

    from transformers import WhisperForConditionalGeneration, WhisperProcessor

    hay_gpu = torch.cuda.is_available()
    dispositivo = "cuda" if hay_gpu else "cpu"
    dtype = torch.float16 if hay_gpu else torch.float32

    disco_gb = tamano_en_disco(args.modelo)
    ram_antes = ram_residente_gb()
    if hay_gpu:
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()

    print(f"cargando {args.modelo} en {dispositivo}...")
    procesador = WhisperProcessor.from_pretrained(args.modelo)
    modelo = WhisperForConditionalGeneration.from_pretrained(
        args.modelo, dtype=dtype).to(dispositivo).eval()

    if args.adaptador:
        from peft import PeftModel
        modelo = PeftModel.from_pretrained(modelo, args.adaptador).eval()

    vram_pesos = torch.cuda.memory_allocated() / 1024**3 if hay_gpu else None

    # Ruido rosa suave: irrelevante para la calidad, suficiente para que el modelo recorra
    # el codificador y el decodificador completos, que es donde esta el pico de memoria.
    generador = np.random.default_rng(42)
    audio = generador.normal(0, 0.05, int(FRECUENCIA * SEGUNDOS_PRUEBA)).astype(np.float32)

    entradas = procesador(audio, sampling_rate=FRECUENCIA, return_tensors="pt")
    feats = entradas.input_features.to(dispositivo, dtype=dtype)
    print("transcribiendo 30 s de audio para medir el pico...")
    with torch.no_grad():
        modelo.generate(feats, language="es", task="transcribe", max_new_tokens=440)

    vram_pico = torch.cuda.max_memory_allocated() / 1024**3 if hay_gpu else None
    ram_despues = ram_residente_gb()

    salida = {
        "herramienta": "huella_recursos",
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "modelo": args.modelo,
        "adaptador": args.adaptador,
        "dispositivo": dispositivo,
        "dtype": str(dtype).replace("torch.", ""),
        "disco_gb": None if disco_gb is None else round(disco_gb, 2),
        "vram_pesos_gb": None if vram_pesos is None else round(vram_pesos, 2),
        "vram_pico_gb": None if vram_pico is None else round(vram_pico, 2),
        "ram_proceso_gb": None if ram_despues is None else round(ram_despues, 2),
        "ram_incremento_gb": (None if None in (ram_antes, ram_despues)
                              else round(ram_despues - ram_antes, 2)),
        "segundos_audio_prueba": SEGUNDOS_PRUEBA,
        "entorno": {
            "python": sys.version.split()[0],
            "torch": torch.__version__,
            "gpu": torch.cuda.get_device_name(0) if hay_gpu else None,
            "vram_total_gb": (round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2)
                              if hay_gpu else None),
        },
    }

    DESTINO.mkdir(parents=True, exist_ok=True)
    nombre = args.modelo.replace("/", "_") + ("+lora" if args.adaptador else "")
    destino = DESTINO / f"huella_{nombre}.json"
    destino.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")

    print(json.dumps(salida, ensure_ascii=False, indent=2))
    print(f"\n-> {destino.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
