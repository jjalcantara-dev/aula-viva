# Servicio de transcripción. La imagen base decide el fabricante de GPU.
#
# El trabajo se desarrolló sobre AMD con ROCm, pero atar el despliegue a un fabricante
# concreto limitaría su utilidad para un centro educativo, que tendrá el equipo que tenga.
# La única diferencia entre ambas variantes es la imagen base: el código del servicio es
# idéntico porque PyTorch expone la misma interfaz sobre CUDA y sobre ROCm.
#
#   AMD     docker build -f docker/asr.Dockerfile .          (usa el BASE anclado por defecto)
#   NVIDIA  docker build --build-arg BASE=pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime \
#                        -f docker/asr.Dockerfile .
#
# La versión concreta de la imagen base se fija fuera y no aquí a propósito: cada
# combinación de tarjeta y controlador exige una, y codificarla obligaría a editar el
# fichero en cada despliegue.
#
# El valor por defecto SÍ va anclado, y no a «latest». Una imagen publicada cuya base se
# mueve sola deja de ser reproducible: dos construcciones del mismo commit dan artefactos
# distintos, que es el mismo fallo que este trabajo persigue en los resultados
# experimentales. Quien necesite otra versión la pasa por --build-arg, que es justo para
# lo que está el argumento.

ARG BASE=rocm/pytorch:rocm6.4.1_ubuntu24.04_py3.12_pytorch_release_2.6.0
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
