# 001 — Stack ASR para la parte de investigación

**Fecha:** M0, sesión de arranque · **Estado:** decidido (revisable) · 🔴 pendiente de comunicar al director

## Contexto

La comparativa exige tres técnicas sobre Whisper: prompting contextual, post-corrección
con LLM y fine-tuning con LoRA. La app .NET exige inferencia en tiempo real. Son dos
perfiles de uso distintos y no tienen por qué compartir motor.

## Opciones

| Opción | Baseline | Prompting | LoRA | Tiempo real |
|---|---|---|---|---|
| `transformers` + `peft` | sí | sí | **sí** | aceptable |
| `openai-whisper` | sí | sí | no | no |
| `faster-whisper` (CTranslate2) | sí | limitado | no | **excelente** |

## Decisión

**`transformers` + `peft` para `research/`.** Es la única que cubre las tres técnicas
con una sola base de código, y evita un cambio de stack a mitad del TFM (que caería
justo en M5-M6, la fase peor para eso).

El motor de la app queda **sin decidir** y se elegirá con datos de latencia medidos.
`faster-whisper` es la candidata natural, pero la medición de esta sesión (RTF 0.056
con `whisper-small`) sugiere que puede no hacer falta.

## Consecuencias

- `research/` y `app/` pueden usar motores distintos. La frontera es `<Proyecto>.Asr`.
- Se evita `torchcodec` como dependencia (ata versiones de torch y ffmpeg): el audio
  se decodifica con `soundfile`, que ya era dependencia.

## Entorno verificado

```
GPU        AMD RX 9070 XT (gfx1201, RDNA4), 15.9 GiB VRAM
ROCm       7.2.4          torch 2.13.0 (HIP 7.2.53211)
Python     3.14.6         venv con --system-site-packages (reutiliza el torch de ROCm)
transformers 5.15.0 · peft 0.20.0 · datasets 5.0.1 · jiwer · librosa · soundfile
```

Verificado con `tools/check_gpu.py`: matmul correcto (8.2 TFLOP/s fp32), backward +
AdamW convergiendo, autocast bf16 funcionando. **R2 mitigado: LoRA es viable.**
