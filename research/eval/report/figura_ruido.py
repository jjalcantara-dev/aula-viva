"""Figura: degradacion frente al ruido de aula (exp-104).

La tabla da los numeros; la figura ensena lo que la tabla esconde: el fallo NO es gradual.
Con murmullo, entre 5 y 0 dB el WER se triplica, mientras que el ruido blanco a la misma
energia apenas mueve la curva. Dos curvas y una zona sombreada bastan para que eso se vea
sin leer una sola cifra.

La zona segura se dibuja a partir de la propia medicion, el mayor SNR cuyo WER se mantiene
dentro de un margen del audio limpio, y no como una franja elegida a ojo.

Uso:  .venv/bin/python research/eval/report/figura_ruido.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from tabla_ruido import RAIZ, TIPOS, cargar  # noqa: E402

DESTINO = RAIZ / "memoria" / "figuras"
# Margen sobre el WER en limpio por debajo del cual la degradacion se considera
# despreciable. 1.5 pp no es arbitrario: es el ancho aproximado del intervalo de confianza
# del WER con el tamano de muestra de este barrido (40 clips), segun el calculo de potencia
# de la memoria. Por debajo de ese margen no se puede afirmar que haya degradacion.
MARGEN_PP = 1.5

ESTILOS = {"blanco": ("o", "-", "black"), "murmullo": ("s", "--", "crimson")}


def zona_segura(datos: dict) -> float | None:
    """Menor SNR a partir del cual NINGUN tipo de ruido degrada mas de MARGEN_PP.

    Se exige que todos los niveles por encima tambien lo cumplan, y no solo ese: la
    medicion no es perfectamente monotona (con 40 clips, 20 dB puede salir por encima de
    15 dB por ruido de muestreo), y un umbral leido de un unico punto seria un artefacto.
    """
    limpio = datos["limpio"]["wer"] * 100

    def seguro(snr: float) -> bool:
        return all(r["wer"] * 100 - limpio <= MARGEN_PP
                   for r in datos["por_snr"][snr].values())

    snrs = sorted(datos["por_snr"], reverse=True)     # de mas limpio a mas ruidoso
    umbral = None
    for snr in snrs:
        if not seguro(snr):
            break
        umbral = snr
    return umbral


def main():
    datos = cargar()
    limpio = datos["limpio"]["wer"] * 100
    snrs = sorted(datos["por_snr"], reverse=True)

    fig, ax = plt.subplots(figsize=(7.2, 4.4))

    umbral = zona_segura(datos)
    if umbral is not None:
        ax.axvspan(umbral, max(snrs) + 2, color="seagreen", alpha=0.10, zorder=0)
        # Alineada a la derecha: con el eje invertido, eso la deja DENTRO de la banda.
        ax.annotate(f"zona segura (≥ {umbral:.0f} dB)", xy=(umbral, 0.97),
                    xycoords=("data", "axes fraction"), ha="right", va="top",
                    fontsize=8, color="seagreen")

    for tipo in TIPOS:
        xs = [s for s in snrs if tipo in datos["por_snr"][s]]
        ys = [datos["por_snr"][s][tipo]["wer"] * 100 for s in xs]
        m, ls, c = ESTILOS.get(tipo, ("^", "-.", "gray"))
        ax.plot(xs, ys, marker=m, linestyle=ls, color=c, linewidth=1.7,
                label=f"ruido {tipo}", zorder=3)

    ax.axhline(limpio, color="gray", linestyle=":", linewidth=1.2, zorder=1)
    # A la derecha del panel, donde las curvas ya se han despegado de esta linea.
    ax.annotate(f"audio limpio: {limpio:.2f}%", xy=(0.98, limpio),
                xycoords=("axes fraction", "data"), ha="right", va="bottom",
                fontsize=8, color="gray")

    ax.invert_xaxis()                     # de mas limpio a mas ruidoso, como se degrada
    ax.set_xlabel("Relación señal-ruido (dB) — peor hacia la derecha")
    ax.set_ylabel("WER (%)")
    ax.set_title("Degradación frente al ruido: el tipo pesa más que la energía")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3, zorder=0)

    fig.tight_layout()
    DESTINO.mkdir(parents=True, exist_ok=True)
    base = DESTINO / "ruido"
    fig.savefig(base.with_suffix(".pdf"))
    fig.savefig(base.with_suffix(".png"), dpi=160)
    print(f"-> {base.with_suffix('.pdf').relative_to(RAIZ)}")
    print(f"-> {base.with_suffix('.png').relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
