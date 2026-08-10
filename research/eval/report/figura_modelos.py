"""Figura: compromiso calidad-coste de los modelos Whisper sin adaptar.

Salida en PDF (vectorial) para la memoria. Pensada para leerse tambien impresa en
escala de grises: los modelos se distinguen por marcador y etiqueta, no por color.

Uso:  .venv/bin/python research/eval/report/figura_modelos.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import NullFormatter, ScalarFormatter  # noqa: E402

from tabla_modelos import RAIZ, cargar  # noqa: E402

DESTINO = RAIZ / "memoria" / "figuras"
MARCADORES = ["o", "s", "^", "D", "v", "P", "X", "*"]


def desplazamientos(valores_x: list[float]) -> list[tuple[int, int]]:
    """Alterna la etiqueta arriba/abajo segun el orden en el eje X.

    Los modelos grandes se agrupan (764M, 809M, 1543M dan WER casi identico) y con
    un desplazamiento fijo las etiquetas se solapan y la figura queda inservible.
    """
    orden = sorted(range(len(valores_x)), key=lambda i: valores_x[i])
    salida: list[tuple[int, int]] = [(0, 0)] * len(valores_x)
    for puesto, i in enumerate(orden):
        salida[i] = (7, 7) if puesto % 2 == 0 else (7, -15)
    return salida


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="fleurs_es")
    ap.add_argument("--decodificacion", default="fallback", choices=["voraz", "fallback"])
    args = ap.parse_args()

    filas = cargar(args.corpus, args.decodificacion)
    if not filas:
        raise SystemExit(f"sin resultados para '{args.corpus}' / '{args.decodificacion}'")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2))

    # --- Panel 1: coste (veces tiempo real) frente a calidad (WER) ---
    desp1 = desplazamientos([r["veces"] for r in filas])
    for i, r in enumerate(filas):
        ax1.scatter(r["veces"], r["wer"], marker=MARCADORES[i % len(MARCADORES)],
                    s=90, edgecolor="black", linewidth=0.8, zorder=3)
        ax1.annotate(r["modelo"].replace("whisper-", ""),
                     (r["veces"], r["wer"]), textcoords="offset points",
                     xytext=desp1[i], fontsize=8)
    ax1.axvline(1.0, color="crimson", linestyle="--", linewidth=1.2, zorder=1)
    # Coordenadas mixtas (x en datos, y en fraccion de ejes): la etiqueta queda
    # bien colocada aunque luego cambien los limites del eje.
    ax1.annotate("límite de tiempo real", xy=(1.0, 0.97),
                 xycoords=("data", "axes fraction"), rotation=90,
                 va="top", ha="right", fontsize=8, color="crimson")
    ax1.set_xscale("log")
    ax1.set_xlabel("Velocidad frente al audio (×, escala log)")
    ax1.set_ylabel("WER (%)")
    ax1.set_title("Calidad frente a coste")
    ax1.grid(alpha=0.3, zorder=0)

    # --- Panel 2: tamano del modelo frente a calidad ---
    xs = [r["params"] for r in filas]
    ys = [r["wer"] for r in filas]
    ax2.plot(xs, ys, color="gray", linewidth=1, zorder=1)
    desp2 = desplazamientos(xs)
    for i, r in enumerate(filas):
        ax2.scatter(r["params"], r["wer"], marker=MARCADORES[i % len(MARCADORES)],
                    s=90, edgecolor="black", linewidth=0.8, zorder=3)
        ax2.annotate(r["modelo"].replace("whisper-", ""),
                     (r["params"], r["wer"]), textcoords="offset points",
                     xytext=desp2[i], fontsize=8)
    ax2.set_xscale("log")
    ax2.set_xlabel("Parámetros (millones, escala log)")
    ax2.set_ylabel("WER (%)")
    ax2.set_title("Rendimientos decrecientes por tamaño")
    ax2.grid(alpha=0.3, zorder=0)
    # Marcar el tamano real de cada modelo. Las marcas menores por defecto de la
    # escala log se solapan e impiden leer el eje.
    # Marcar el tamano de cada modelo, pero descartando las que caen demasiado
    # juntas en escala log (764M y 809M se solapan e impiden leer el eje).
    marcas: list[float] = []
    for x in sorted(xs):
        if not marcas or x / marcas[-1] > 1.3:
            marcas.append(x)
    ax2.set_xticks(marcas)
    ax2.xaxis.set_major_formatter(ScalarFormatter())
    ax2.xaxis.set_minor_formatter(NullFormatter())
    plt.setp(ax2.get_xticklabels(), rotation=45, ha="right")

    # Margen para que las etiquetas anotadas no se corten en los bordes.
    for ax in (ax1, ax2):
        ax.margins(x=0.18, y=0.15)

    fig.tight_layout()
    DESTINO.mkdir(parents=True, exist_ok=True)
    nombre = f"baseline_modelos_{args.corpus}_{args.decodificacion}"
    for ext in ("pdf", "png"):
        fig.savefig(DESTINO / f"{nombre}.{ext}", dpi=200, bbox_inches="tight")
    print(f"-> {(DESTINO / f'{nombre}.pdf').relative_to(RAIZ)}")
    print(f"-> {(DESTINO / f'{nombre}.png').relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
