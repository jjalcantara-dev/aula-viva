"""Servicio HTTP de transcripcion. Puente entre la aplicacion .NET y Whisper.

Por que un servicio y no una libreria: PyTorch con ROCm solo existe en Python, y .NET no
puede cargarlo. Un proceso aparte con una interfaz HTTP minima es la solucion mas simple
que funciona, y ademas mantiene la frontera del PLANNING: la aplicacion depende de
`IMotorAsr`, y una implementacion concreta habla con este servicio.

Punto importante para la validez del TFM: este servicio usa **la misma configuracion de
decodificacion que los experimentos** (reintento por temperatura, ver R14). Si la
aplicacion decodificara distinto que la comparativa, los resultados medidos no
describirian el sistema desplegado.

Sin dependencias nuevas: servidor de la biblioteca estandar.

Uso:
  .venv/bin/python serving/servidor_asr.py --modelo openai/whisper-medium --puerto 5601
"""

import argparse
import io
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock

import numpy as np
import torch

# Misma configuracion que research/experiments/exp-000-baseline/run.py.
DECODIFICACION = dict(
    temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
    logprob_threshold=-1.0,
    compression_ratio_threshold=1.35,
    no_speech_threshold=0.6,
    return_timestamps=True,
)

ESTADO: dict = {}
CERROJO = Lock()  # la GPU no se comparte bien entre peticiones simultaneas


def transcribir(pcm: bytes, frecuencia: int, prompt: str | None) -> tuple[str, float]:
    procesador, modelo = ESTADO["procesador"], ESTADO["modelo"]
    dispositivo, dtype = ESTADO["dispositivo"], ESTADO["dtype"]

    # PCM 16 bits con signo -> float32 en [-1, 1], que es lo que espera el extractor.
    muestras = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
    if muestras.size == 0:
        return "", 0.0

    t0 = time.perf_counter()
    with CERROJO:
        entradas = procesador(muestras, sampling_rate=frecuencia, return_tensors="pt")
        feats = entradas.input_features.to(dispositivo, dtype=dtype)
        extra = {}
        if prompt:
            extra["prompt_ids"] = procesador.get_prompt_ids(
                prompt, return_tensors="pt").to(dispositivo)
        with torch.no_grad():
            ids = modelo.generate(feats, language=ESTADO["idioma"], task="transcribe",
                                  **DECODIFICACION, **extra)
        texto = procesador.batch_decode(ids, skip_special_tokens=True)[0].strip()
    if prompt and texto.startswith(prompt):
        texto = texto[len(prompt):].strip()
    return texto, (time.perf_counter() - t0) * 1000


class Manejador(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _responder(self, codigo: int, cuerpo: dict):
        datos = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def do_GET(self):
        if self.path == "/salud":
            self._responder(200, {"estado": "listo", "modelo": ESTADO["nombre"],
                                  "dispositivo": ESTADO["dispositivo"]})
        else:
            self._responder(404, {"error": "ruta desconocida"})

    def do_POST(self):
        if self.path != "/transcribir":
            self._responder(404, {"error": "ruta desconocida"})
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            pcm = self.rfile.read(n)
            frecuencia = int(self.headers.get("X-Frecuencia", 16000))
            prompt = self.headers.get("X-Prompt") or None
            texto, ms = transcribir(pcm, frecuencia, prompt)
            self._responder(200, {"texto": texto, "ms_inferencia": round(ms, 1),
                                  "muestras": len(pcm) // 2})
        except Exception as e:  # que un fragmento malo no tumbe el servicio
            self._responder(500, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, formato, *args):
        pass  # el registro por peticion satura la consola con audio en vivo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default="openai/whisper-medium")
    ap.add_argument("--puerto", type=int, default=5601)
    ap.add_argument("--idioma", default="es")
    ap.add_argument("--dtype", default="float16")
    args = ap.parse_args()

    from transformers import AutoProcessor, WhisperForConditionalGeneration

    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = getattr(torch, args.dtype) if dispositivo == "cuda" else torch.float32

    print(f"cargando {args.modelo} en {dispositivo}...")
    ESTADO.update(
        nombre=args.modelo, idioma=args.idioma, dispositivo=dispositivo, dtype=dtype,
        procesador=AutoProcessor.from_pretrained(args.modelo),
        modelo=WhisperForConditionalGeneration.from_pretrained(
            args.modelo, dtype=dtype).to(dispositivo).eval())

    # Calentamiento: la primera inferencia paga compilacion de kernels. Sin esto, el
    # primer subtitulo de cada sesion llegaria con varios segundos de retraso.
    transcribir(np.zeros(16000, dtype="<i2").tobytes(), 16000, None)
    print(f"listo en http://localhost:{args.puerto}  (GET /salud, POST /transcribir)")

    ThreadingHTTPServer(("127.0.0.1", args.puerto), Manejador).serve_forever()


if __name__ == "__main__":
    main()
