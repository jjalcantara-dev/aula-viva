# Servicio de transcripción. La imagen base decide el fabricante de GPU.
#
# El trabajo se desarrolló sobre AMD con ROCm, pero atar el despliegue a un fabricante
# concreto limitaría su utilidad para un centro educativo, que tendrá el equipo que tenga.
# La única diferencia entre ambas variantes es la imagen base: el código del servicio es
# idéntico porque PyTorch expone la misma interfaz sobre CUDA y sobre ROCm.
#
#   AMD     docker build --build-arg BASE=rocm/pytorch:latest        -f docker/asr.Dockerfile .
#   NVIDIA  docker build --build-arg BASE=pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime \
#                        -f docker/asr.Dockerfile .
#
# La versión concreta de la imagen base se fija fuera y no aquí a propósito: cada
# combinación de tarjeta y controlador exige una, y codificarla obligaría a editar el
# fichero en cada despliegue.

ARG BASE=rocm/pytorch:latest
FROM ${BASE}

LABEL org.opencontainers.image.title="TFM ASR" \
      org.opencontainers.image.description="Servicio de transcripción para subtitulado educativo"

WORKDIR /app

# Las dependencias van antes que el código para que un cambio en el servicio no invalide
# la capa de instalación, que es la cara.
COPY docker/requirements-asr.txt .
RUN pip install --no-cache-dir -r requirements-asr.txt

COPY serving/ ./serving/

# El modelo se descarga en el primer arranque y se cachea en un volumen; incluirlo en la
# imagen la haría crecer varios gigabytes y obligaría a reconstruirla para cambiarlo.
ENV HF_HOME=/cache/huggingface \
    MODELO=openai/whisper-medium \
    PUERTO=5601

VOLUME ["/cache/huggingface"]
EXPOSE 5601

# Comprobación de salud: el servicio tarda en cargar el modelo, así que un arranque lento
# no debe confundirse con un arranque fallido.
HEALTHCHECK --interval=15s --timeout=5s --start-period=300s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5601/salud').status==200 else 1)"

# El adaptador LoRA es opcional: si ADAPTADOR está vacío, se sirve el modelo base.
CMD ["sh", "-c", "python serving/servidor_asr.py --modelo $MODELO --puerto $PUERTO ${ADAPTADOR:+--adaptador $ADAPTADOR}"]
