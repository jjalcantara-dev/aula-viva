"""Figura: el coste de trocear el audio y por que conviene cortar en las pausas.

Dos paneles, porque son dos hallazgos distintos que la memoria narraba solo con texto:

  1. exp-100: cuanto WER cuesta cada segundo de latencia que se ahorra, y cuanto de ese
     coste era en realidad la duplicacion en las fronteras (defecto de implementacion, no
     coste del troceado). La curva con solape esta por encima del 100%: el sistema emitia
     mas errores que palabras tiene la referencia.
  2. exp-102: WER frente a latencia MEDIA, que es la comparacion honesta entre
     estrategias. Cortar por silencios domina a trocear por reloj en todo el rango.

Salida en PDF vectorial y legible en escala de grises: las series se distinguen por
marcador y por trazo, no por color.

Uso:  .venv/bin/python research/eval/report/figura_segmentacion.py
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
RES_VENTANA = RAIZ / "research" / "experiments" / "exp-100-ventana" / "results"
RES_VAD = RAIZ / "research" / "experiments" / "exp-102-vad" / "results"
DESTINO = RAIZ / "memoria" / "figuras"


def cargar_ventana(modelo: str, corpus: str, solape: str) -> tuple[list[float], list[float], float | None]:
    f = RES_VENTANA / f"metricas_{modelo}__{corpus}__solape{solape}.json"
    if not f.exists():
        raise SystemExit(f"falta {f.relative_to(RAIZ)}: ejecutar 'make exp-100'")
    d = json.loads(f.read_text(encoding="utf-8"))
    xs, ys, techo = [], [], None
    for r in sorted(d["resultados"], key=lambda r: r["ventana_s"]):
        if r["ventana_s"] == 0:          # 0 = fragmento entero
            techo = r["wer"] * 100
            continue
        xs.append(r["ventana_s"])
        ys.append(r["wer"] * 100)
    return xs, ys, techo


def cargar_vad(modelo: str, corpus: str) -> dict[str, list[tuple[float, float, float]]]:
    f = RES_VAD / f"metricas_{modelo}__{corpus}.json"
    if not f.exists():
        raise SystemExit(f"falta {f.relative_to(RAIZ)}: ejecutar 'make exp-102'")
    d = json.loads(f.read_text(encoding="utf-8"))
    series: dict[str, list[tuple[float, float, float]]] = {}
    for r in d["resultados"]:
        series.setdefault(r["estrategia"], []).append(
            (r["duracion_media_s"], r["wer"] * 100, r["tope_s"]))
    for k in series:
        series[k].sort()
    return series


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default="openai_whisper-medium")
    ap.add_argument("--corpus", default="voxpopuli_es")
    args = ap.parse_args()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2))

    # --- Panel 1: coste de trocear, y cuanto de el era duplicacion ---
    x0, y0, techo = cargar_ventana(args.modelo, args.corpus, "0")
    ax1.plot(x0, y0, marker="o", color="black", linewidth=1.6,
             label="troceado por reloj")
    try:
        x1, y1, _ = cargar_ventana(args.modelo, args.corpus, "1.0")
        ax1.plot(x1, y1, marker="s", color="crimson", linestyle="--", linewidth=1.4,
                 label="con solape de 1 s, sin fusionar")
    except SystemExit:
        pass                              # el barrido con solape es opcional
    if techo is not None:
        ax1.axhline(techo, color="gray", linestyle=":", linewidth=1.2)
        # A la izquierda: en este panel las curvas caen hacia la derecha y taparian la etiqueta.
        ax1.annotate(f"sin trocear: {techo:.2f}%", xy=(0.02, techo),
                     xycoords=("axes fraction", "data"), ha="left", va="bottom",
                     fontsize=8, color="gray")
    ax1.axhline(100, color="crimson", linewidth=0.8, alpha=0.4)
    ax1.annotate("más errores que palabras", xy=(0.02, 100),
                 xycoords=("axes fraction", "data"), ha="left", va="bottom",
                 fontsize=7.5, color="crimson", alpha=0.8)
    ax1.set_xlabel("Tamaño de ventana (s)")
    ax1.set_ylabel("WER (%)")
    ax1.set_title("Coste de trocear por reloj")
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.3)

    # --- Panel 2: WER frente a latencia media, por estrategia ---
    estilos = {"ventana fija": ("s", "--", "crimson"), "silencios": ("o", "-", "black")}
    for nombre, puntos in cargar_vad(args.modelo, args.corpus).items():
        m, ls, c = estilos.get(nombre, ("^", "-.", "gray"))
        xs = [p[0] for p in puntos]
        ys = [p[1] for p in puntos]
        ax2.plot(xs, ys, marker=m, linestyle=ls, color=c, linewidth=1.6, label=nombre)
        for x, y, tope in puntos:
            ax2.annotate(f"{tope:.0f} s", (x, y), textcoords="offset points",
                         xytext=(5, 5), fontsize=7.5, color=c)
    if techo is not None:
        ax2.axhline(techo, color="gray", linestyle=":", linewidth=1.2)
        ax2.annotate(f"sin trocear: {techo:.2f}%", xy=(0.98, techo),
                     xycoords=("axes fraction", "data"), ha="right", va="bottom",
                     fontsize=8, color="gray")
    ax2.margins(x=0.10)                   # sitio para la etiqueta del ultimo punto
    ax2.set_xlabel("Duración media del segmento (s) ≈ latencia")
    ax2.set_ylabel("WER (%)")
    ax2.set_title("A igual latencia, dónde se corta")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3)

    fig.tight_layout()
    DESTINO.mkdir(parents=True, exist_ok=True)
    base = DESTINO / "segmentacion"
    fig.savefig(base.with_suffix(".pdf"))
    fig.savefig(base.with_suffix(".png"), dpi=160)
    print(f"-> {base.with_suffix('.pdf').relative_to(RAIZ)}")
    print(f"-> {base.with_suffix('.png').relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
