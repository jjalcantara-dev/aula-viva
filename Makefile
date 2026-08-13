# Atajos del TFM. Ejecuta `make` sin argumentos para ver la lista.
#
# Todo lo que aparece aquí se ha ejecutado antes a mano; esto solo evita recordar rutas
# y banderas. Cada objetivo es una línea que puedes copiar si prefieres lanzarla suelta.

PY      := .venv/bin/python
APP     := app/src/Accesibilidad.Web
MODELO  := openai/whisper-medium
CORPUS  := voxpopuli_es
MANIF   := research/corpus/manifests/$(CORPUS).jsonl
RESULT  := research/experiments/exp-000-baseline/results
# Evita que el equipo se suspenda durante operaciones largas. Una descarga de 19 GB o un
# barrido de una hora se pierden enteros si la sesion se duerme a la mitad; ya ocurrio.
DESPIERTO := systemd-inhibit --what=idle:sleep:shutdown --why="TFM en curso"

PUERTO_ASR := 5601
PUERTO_APP := 5203
# IP de la interfaz por la que sale el tráfico: la que deben teclear los alumnos.
IP_LOCAL := $(shell ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \K[\d.]+' | head -1)

.DEFAULT_GOAL := ayuda
.PHONY: ayuda entorno gpu test app asr demo parar corpus baseline \
        direcciones demo-lora docker-amd docker-nvidia docker-parar exp-001 exp-002 exp-003 exp-100 exp-102 exp-103 exp-104 tablas estado limpiar

ayuda:  ## Muestra esta ayuda
	@echo "TFM — atajos disponibles:"
	@echo
	@grep -E '^[a-z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "Variables: MODELO=$(MODELO)  CORPUS=$(CORPUS)"
	@echo "Ejemplo:   make baseline MODELO=openai/whisper-small CORPUS=tedx_es"

# ---------------------------------------------------------------- entorno --

entorno:  ## Crea el venv y instala dependencias (una sola vez)
	python3 -m venv --system-site-packages .venv
	$(PY) -m pip install -q transformers accelerate peft jiwer soundfile \
	    librosa datasets matplotlib
	@echo "Listo. Comprueba la GPU con: make gpu"

gpu:  ## Verifica que la GPU calcula Y entrena
	$(PY) tools/check_gpu.py

# ----------------------------------------------------------- aplicación --

test:  ## Ejecuta las pruebas de la aplicación
	cd app && dotnet test

app:  ## Arranca la app con motor SIMULADO (mide latencia del circuito)
	@$(MAKE) --no-print-directory direcciones
	cd app && dotnet run --project src/Accesibilidad.Web --urls http://0.0.0.0:$(PUERTO_APP)

direcciones:  ## Muestra por dónde entran el docente y el alumnado
	@echo
	@echo "  DOCENTE  http://localhost:$(PUERTO_APP)/broadcast"
	@echo "           (el micrófono solo funciona en localhost sin HTTPS)"
	@echo "  ALUMNOS  http://$(IP_LOCAL):$(PUERTO_APP)/view"
	@echo

asr:  ## Arranca solo el servicio de transcripción (Whisper)
	$(PY) serving/servidor_asr.py --modelo $(MODELO) --puerto $(PUERTO_ASR) $(ADAPTADOR)

demo-lora:  ## Como `demo`, pero con el adaptador LoRA de exp-003 (técnica ganadora)
	@$(MAKE) demo ADAPTADOR="--adaptador research/experiments/exp-003-lora/adaptador"

demo:  ## Arranca servicio ASR + app con Whisper REAL, y limpia al salir
	@echo "Arrancando servicio ASR ($(MODELO))..."
	@$(PY) serving/servidor_asr.py --modelo $(MODELO) --puerto $(PUERTO_ASR) $(ADAPTADOR) \
	    > /tmp/tfm-asr.log 2>&1 & echo $$! > /tmp/tfm-asr.pid
	@echo "Esperando a que cargue el modelo (puede tardar)..."
	@until curl -sf -o /dev/null http://localhost:$(PUERTO_ASR)/salud; do sleep 2; done
	@echo "Servicio listo."
	@$(MAKE) --no-print-directory direcciones
	@trap 'kill $$(cat /tmp/tfm-asr.pid) 2>/dev/null; rm -f /tmp/tfm-asr.pid' EXIT; \
	  cd app && Asr__Motor=whisper dotnet run --project src/Accesibilidad.Web \
	    --urls http://0.0.0.0:$(PUERTO_APP)

parar:  ## Detiene servicios y experimentos que hayan quedado sueltos
	-@pkill -f servidor_asr.py 2>/dev/null && echo "servicio ASR detenido" || true
	-@pkill -f "Accesibilidad.Web" 2>/dev/null && echo "app detenida" || true
	-@pkill -f "research/experiments" 2>/dev/null && echo "experimentos detenidos" || true
	-@rm -f /tmp/tfm-asr.pid
	@echo "Todo parado."

# ------------------------------------------------------------ corpus --

corpus:  ## Descarga muestras de corpus (N=40 por defecto)
	$(PY) research/src/data/fetch_sample.py --n $(or $(N),40) \
	    --fuentes $(or $(FUENTES),voxpopuli_es teleconciencia_es)

# ------------------------------------------------------- experimentos --

baseline:  ## exp-000: Whisper sin adaptar (usa MODELO y CORPUS)
	$(DESPIERTO) $(PY) research/experiments/exp-000-baseline/run.py \
	    --manifiesto $(MANIF) --modelo $(MODELO) --lote 8 --decodificacion fallback

exp-001:  ## Prompting contextual con glosario de dominio
	$(DESPIERTO) $(PY) research/experiments/exp-001-prompting/run.py \
	    --manifiesto $(MANIF) --modelo $(MODELO)

exp-002:  ## Post-corrección con LLM (requiere transcripciones de baseline)
	$(DESPIERTO) $(PY) research/experiments/exp-002-postcorreccion/run.py \
	    --transcripciones $(RESULT)/transcripciones_$(subst /,_,$(MODELO))__$(CORPUS)__fallback.jsonl \
	    --limite $(or $(N),400)

exp-003:  ## Ajuste fino con LoRA: entrena el adaptador y lo evalúa
	$(DESPIERTO) $(PY) research/experiments/exp-003-lora/entrenar.py --epocas $(or $(EPOCAS),2)
	$(DESPIERTO) $(PY) research/experiments/exp-003-lora/run.py

exp-100:  ## Barrido de tamaño de ventana (latencia frente a calidad)
	$(DESPIERTO) $(PY) research/experiments/exp-100-ventana/run.py \
	    --manifiesto $(MANIF) --modelo $(MODELO) --limite 40 --solape 0

exp-102:  ## Segmentación por silencios frente a ventana fija
	$(DESPIERTO) $(PY) research/experiments/exp-102-vad/run.py \
	    --manifiesto $(MANIF) --modelo $(MODELO) --limite 40

exp-103:  ## ¿Ayuda arrastrar la transcripción anterior como contexto?
	$(DESPIERTO) $(PY) research/experiments/exp-103-contexto/run.py \
	    --manifiesto $(MANIF) --modelo $(MODELO) --limite 40

exp-104:  ## Robustez frente al ruido de aula (barrido de SNR)
	$(DESPIERTO) $(PY) research/experiments/exp-104-ruido/run.py \
	    --manifiesto $(MANIF) --modelo $(MODELO) --limite 40

# ------------------------------------------------------ contenedores --

docker-amd:  ## Levanta el sistema en contenedores sobre GPU AMD (ROCm)
	@$(MAKE) --no-print-directory direcciones
	$(DESPIERTO) docker compose --profile amd up --build

docker-nvidia:  ## Levanta el sistema en contenedores sobre GPU NVIDIA (CUDA)
	@$(MAKE) --no-print-directory direcciones
	$(DESPIERTO) docker compose --profile nvidia up --build

docker-parar:  ## Detiene los contenedores sin borrar el modelo descargado
	-docker compose --profile amd --profile nvidia down

# --------------------------------------------------------- informes --

tablas:  ## Regenera TODAS las tablas y figuras de la memoria
	-$(PY) research/eval/report/tabla_corpus.py --decodificacion fallback
	-$(PY) research/eval/report/tabla_tecnicas.py
	-$(PY) research/eval/report/anomalias.py --decodificacion fallback
	-$(PY) research/eval/report/tabla_criticos.py --decodificacion fallback
	-$(PY) research/eval/report/figura_modelos.py --corpus fleurs_es --decodificacion fallback
	@echo "Tablas en memoria/tablas/ y figuras en memoria/figuras/"

estado:  ## Resumen rápido del proyecto
	@echo "Experimentos con resultados:"
	@for d in research/experiments/*/; do \
	  n=$$(ls $$d/results/*.json 2>/dev/null | wc -l); \
	  printf "  %-26s %s ficheros\n" "$$(basename $$d)" "$$n"; done
	@echo "Corpus descargados:"
	@for m in research/corpus/manifests/*.jsonl; do \
	  printf "  %-26s %s clips\n" "$$(basename $$m .jsonl)" "$$(wc -l < $$m)"; done
	@echo "Git: $$(git status --short 2>/dev/null | wc -l) ficheros sin confirmar"

limpiar:  ## Borra artefactos de compilación (NO toca resultados ni corpus)
	rm -rf app/**/bin app/**/obj
	find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "Artefactos eliminados. Resultados y corpus intactos."
