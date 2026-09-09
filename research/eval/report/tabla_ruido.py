"""Tabla de degradacion frente al ruido de aula (exp-104).

Misma razon que `tabla_segmentacion.py`: esta tabla estaba tecleada a mano en la memoria.

La tabla cruza relacion senal-ruido con tipo de ruido. Se generan las dos columnas por
separado y no una media, porque el hallazgo del experimento es justamente que el tipo de
ruido importa mas que su energia: el murmullo comparte espectro con la voz y el ruido
blanco no.

Uso:  .venv/bin/python research/eval/report/tabla_ruido.py
"""

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
RESULTADOS = RAIZ / "research" / "experiments" / "exp-104-ruido" / "results"
DESTINO_TEX = RAIZ / "memoria" / "tablas"
DESTINO_MD = RAIZ / "research" / "results"

TIPOS = ["blanco", "murmullo"]


def cargar(modelo: str = "openai_whisper-medium", corpus: str = "voxpopuli_es") -> dict:
    f = RESULTADOS / f"metricas_{modelo}__{corpus}.json"
    if not f.exists():
        raise SystemExit(f"falta {f.relative_to(RAIZ)}: ejecutar 'make exp-104'")
    d = json.loads(f.read_text(encoding="utf-8"))

    limpio = next(r for r in d["resultados"] if r["ruido"] == "limpio")
    por_snr: dict[float, dict[str, dict]] = {}
    for r in d["resultados"]:
        if r["ruido"] == "limpio":
            continue
        por_snr.setdefault(r["snr_db"], {})[r["ruido"]] = r
    return {"limpio": limpio, "por_snr": por_snr, "procedencia": d["procedencia"]}


def _salto_maximo(datos: dict, tipo: str) -> tuple[float, float, float]:
    """Mayor degradacion entre dos niveles consecutivos: donde el fallo deja de ser gradual."""
    snrs = sorted(datos["por_snr"], reverse=True)
    peor = (0.0, 0.0, 0.0)
    for a, b in zip(snrs, snrs[1:]):
        ra, rb = datos["por_snr"][a].get(tipo), datos["por_snr"][b].get(tipo)
        if ra and rb:
            salto = (rb["wer"] - ra["wer"]) * 100
            if salto > peor[0]:
                peor = (salto, a, b)
    return peor


def markdown(datos: dict) -> str:
    L = ["| Relación señal-ruido | Ruido blanco (WER %) | Murmullo (WER %) |",
         "|---|---:|---:|",
         f"| Audio limpio | {datos['limpio']['wer'] * 100:.2f} | "
         f"{datos['limpio']['wer'] * 100:.2f} |"]
    for snr in sorted(datos["por_snr"], reverse=True):
        fila = datos["por_snr"][snr]
        celdas = []
        for t in TIPOS:
            r = fila.get(t)
            celdas.append(f"{r['wer'] * 100:.2f}" if r else "—")
        L.append(f"| {snr:.0f} dB | " + " | ".join(celdas) + " |")

    L.append("")
    for t in TIPOS:
        salto, a, b = _salto_maximo(datos, t)
        L.append(f"- Mayor degradación con **{t}**: {salto:.2f} pp entre "
                 f"{a:.0f} y {b:.0f} dB.")
    return "\n".join(L)


def latex(datos: dict) -> str:
    filas = [f"    Audio limpio & {datos['limpio']['wer'] * 100:.2f} & "
             f"{datos['limpio']['wer'] * 100:.2f} \\\\"]
    peor_murmullo = max(
        (datos["por_snr"][s]["murmullo"]["wer"] for s in datos["por_snr"]
         if "murmullo" in datos["por_snr"][s]), default=None)
    for snr in sorted(datos["por_snr"], reverse=True):
        fila = datos["por_snr"][snr]
        celdas = []
        for t in TIPOS:
            r = fila.get(t)
            if not r:
                celdas.append("---")
            elif t == "murmullo" and peor_murmullo is not None and r["wer"] == peor_murmullo:
                celdas.append(f"\\textbf{{{r['wer'] * 100:.2f}}}")
            else:
                celdas.append(f"{r['wer'] * 100:.2f}")
        filas.append(f"    {snr:.0f}~dB & " + " & ".join(celdas) + " \\\\")
    cuerpo = "\n".join(filas)

    salto_m, a_m, b_m = _salto_maximo(datos, "murmullo")
    salto_b, _, _ = _salto_maximo(datos, "blanco")

    return f"""% GENERADO AUTOMATICAMENTE por research/eval/report/tabla_ruido.py
% No editar a mano.
\\begin{{table}}[h]
\\centering
\\small
\\begin{{tabular}}{{|l|r|r|}}
    \\hline
    \\textbf{{Relación señal-ruido}} & \\textbf{{Ruido blanco}} & \\textbf{{Murmullo}} \\\\
    \\hline
{cuerpo}
    \\hline
\\end{{tabular}}
\\caption{{WER (\\%) según relación señal-ruido y tipo de ruido añadido. La mayor
degradación con murmullo son {salto_m:.2f} puntos entre {a_m:.0f} y {b_m:.0f}~dB, frente a
{salto_b:.2f} puntos como peor salto con ruido blanco: el fallo no es gradual y depende
del espectro del ruido, no solo de su energía.}}
\\label{{tab:ruido}}
\\end{{table}}
"""


if __name__ == "__main__":
    datos = cargar()
    md = markdown(datos)
    print(md)

    DESTINO_MD.mkdir(parents=True, exist_ok=True)
    DESTINO_TEX.mkdir(parents=True, exist_ok=True)
    (DESTINO_MD / "ruido.md").write_text(md + "\n", encoding="utf-8")
    (DESTINO_TEX / "ruido.tex").write_text(latex(datos), encoding="utf-8")
    print(f"\n-> {(DESTINO_MD / 'ruido.md').relative_to(RAIZ)}")
    print(f"-> {(DESTINO_TEX / 'ruido.tex').relative_to(RAIZ)}")
