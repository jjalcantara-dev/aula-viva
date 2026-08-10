#!/usr/bin/env bash
# Barrido de tamanos de modelo sobre el mismo manifiesto.
# Objetivo: curva calidad (WER) vs coste (factor de tiempo real) para elegir el
# modelo base de la comparativa con datos, no por intuicion.
#
# Uso: bash research/experiments/exp-000-baseline/barrido_modelos.sh [manifiesto]

set -u
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
MANIFIESTO="${1:-research/corpus/manifests/fleurs_es.jsonl}"
LOG="$RAIZ/research/experiments/exp-000-baseline/results/barrido.log"

mkdir -p "$(dirname "$LOG")"
: > "$LOG"

MODELOS=(
  openai/whisper-tiny
  openai/whisper-base
  openai/whisper-small
  openai/whisper-medium
  openai/whisper-large-v3-turbo
  openai/whisper-large-v3
)

cd "$RAIZ" || exit 1
for M in "${MODELOS[@]}"; do
  echo "=================== $M ===================" | tee -a "$LOG"
  if .venv/bin/python research/experiments/exp-000-baseline/run.py \
        --manifiesto "$MANIFIESTO" --modelo "$M" >>"$LOG" 2>&1; then
    echo "[OK] $M" | tee -a "$LOG"
  else
    # Un modelo que no cabe en VRAM o no se descarga no debe abortar el barrido.
    echo "[FALLO] $M (ver $LOG)" | tee -a "$LOG"
  fi
done

echo "BARRIDO TERMINADO" | tee -a "$LOG"
