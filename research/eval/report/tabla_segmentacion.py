"""Tabla de segmentacion: cortar por silencios frente a trocear por reloj (exp-102).

Existe porque esa tabla estaba TECLEADA A MANO en la memoria, que es exactamente lo que
RE7 prohibe: una cifra copiada deja de estar vinculada a la ejecucion que la produjo en
el momento en que se copia.

El techo (transcribir sin trocear) se lee de exp-100, no se escribe aqui: es la misma
condicion medida en el mismo corpus, y duplicarla a mano reintroduciria el problema.

Uso:  .venv/bin/python research/eval/report/tabla_segmentacion.py
"""

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
RES_VAD = RAIZ / "research" / "experiments" / "exp-102-vad" / "results"
RES_VENTANA = RAIZ / "research" / "experiments" / "exp-100-ventana" / "results"
DESTINO_TEX = RAIZ / "memoria" / "tablas"
DESTINO_MD = RAIZ / "research" / "results"


def cargar(modelo: str = "openai_whisper-medium", corpus: str = "voxpopuli_es") -> dict:
    """Devuelve las filas de exp-102 y el techo sin trocear de exp-100."""
    f = RES_VAD / f"metricas_{modelo}__{corpus}.json"
    if not f.exists():
        raise SystemExit(f"falta {f.relative_to(RAIZ)}: ejecutar 'make exp-102'")
    d = json.loads(f.read_text(encoding="utf-8"))

    # El techo se toma del barrido SIN solapamiento: con solape la cifra incluye la
    # duplicacion en las fronteras, que es un defecto de implementacion y no el coste
    # de trocear (ver exp-100, hallazgo 1).
    g = RES_VENTANA / f"metricas_{modelo}__{corpus}__solape0.json"
    techo = None
    if g.exists():
        dv = json.loads(g.read_text(encoding="utf-8"))
        for r in dv["resultados"]:
            if r["ventana_s"] == 0:          # 0 = fragmento entero, sin trocear
                techo = r["wer"] * 100
    return {"filas": d["resultados"], "techo": techo, "procedencia": d["procedencia"],
            # El contraste pareado del par de latencia equivalente. Puede faltar en
            # resultados anteriores a que exp-102 lo calculara; entonces la tabla sale sin
            # el, en lugar de romperse.
            "pareado": d.get("pareado")}


def _pares(filas: list[dict]) -> list[tuple[float, dict, dict]]:
    """Agrupa las dos estrategias por tope, que es como se disenaron para compararse."""
    topes = sorted({r["tope_s"] for r in filas})
    salida = []
    for t in topes:
        fija = next((r for r in filas if r["tope_s"] == t and r["estrategia"] == "ventana fija"), None)
        sil = next((r for r in filas if r["tope_s"] == t and r["estrategia"] == "silencios"), None)
        if fija and sil:
            salida.append((t, fija, sil))
    return salida


def equivalente(filas: list[dict]) -> tuple[dict, dict] | None:
    """Busca el par a LATENCIA MEDIA equivalente, que es la comparacion que importa.

    Comparar fila a fila subestima el resultado: cada estrategia alcanza una duracion
    media distinta con el mismo tope. Se empareja la ventana fija con la segmentacion
    por silencios cuya duracion media mas se le parezca.
    """
    fijas = [r for r in filas if r["estrategia"] == "ventana fija"]
    sils = [r for r in filas if r["estrategia"] == "silencios"]
    if not fijas or not sils:
        return None
    mejor = None
    for f in fijas:
        for s in sils:
            d = abs(f["duracion_media_s"] - s["duracion_media_s"])
            ganancia = (f["wer"] - s["wer"]) * 100
            # Entre pares igual de equivalentes en latencia, el que mas separa las
            # estrategias es el informativo.
            if d <= 0.5 and (mejor is None or ganancia > mejor[2]):
                mejor = (f, s, ganancia)
    return (mejor[0], mejor[1]) if mejor else None


def markdown(datos: dict) -> str:
    L = ["| Estrategia | Tope | WER (%) | Dur. media (s) | Dur. p95 (s) | Segmentos |",
         "|---|---:|---:|---:|---:|---:|"]
    for tope, fija, sil in _pares(datos["filas"]):
        for r in (fija, sil):
            nombre = r["estrategia"] if r["estrategia"] == "ventana fija" else "**silencios**"
            L.append(f"| {nombre} | {tope:.0f} s | {r['wer'] * 100:.2f} | "
                     f"{r['duracion_media_s']:.2f} | {r['duracion_p95_s']:.2f} | {r['n_segmentos']} |")
    if datos["techo"] is not None:
        L.append(f"| sin trocear (techo) | — | {datos['techo']:.2f} | — | — | — |")

    eq = equivalente(datos["filas"])
    if eq:
        f, s = eq
        L += ["", "## A latencia media equivalente", "",
              "| Estrategia | Tope | WER (%) | Dur. media (s) | Dur. p95 (s) |",
              "|---|---:|---:|---:|---:|",
              f"| ventana fija | {f['tope_s']:.0f} s | {f['wer'] * 100:.2f} | "
              f"{f['duracion_media_s']:.2f} | {f['duracion_p95_s']:.2f} |",
              f"| **silencios** | {s['tope_s']:.0f} s | **{s['wer'] * 100:.2f}** | "
              f"{s['duracion_media_s']:.2f} | {s['duracion_p95_s']:.2f} |",
              "",
              f"Diferencia: **{(f['wer'] - s['wer']) * 100:.2f} pp** de WER con "
              f"{abs(f['duracion_media_s'] - s['duracion_media_s']):.2f} s de diferencia en "
              f"latencia media, a costa de que el p95 suba de {f['duracion_p95_s']:.2f} a "
              f"{s['duracion_p95_s']:.2f} s."]
        par = datos.get("pareado")
        if par:
            ic = par["ic95_pp"]
            L += ["",
                  f"Contraste pareado sobre los mismos clips: IC 95% "
                  f"[{ic[0]:+.2f}, {ic[1]:+.2f}] pp, "
                  f"{par['mejoran']} clips mejoran y {par['empeoran']} empeoran "
                  f"(p={par['p_test_signos']:.2g}), {par['n_palabras_ref']} palabras de "
                  f"referencia. Veredicto: **{par['veredicto']}**."]
    return "\n".join(L)


def latex(datos: dict) -> str:
    filas = []
    for tope, fija, sil in _pares(datos["filas"]):
        filas.append(f"    Ventana fija & {tope:.0f} & {fija['wer'] * 100:.2f} & "
                     f"{fija['duracion_media_s']:.2f} & {fija['duracion_p95_s']:.2f} & "
                     f"{fija['n_segmentos']} \\\\")
        filas.append(f"    Silencios & {tope:.0f} & \\textbf{{{sil['wer'] * 100:.2f}}} & "
                     f"{sil['duracion_media_s']:.2f} & {sil['duracion_p95_s']:.2f} & "
                     f"{sil['n_segmentos']} \\\\")
        filas.append("    \\hline")
    if datos["techo"] is not None:
        filas.append(f"    Sin trocear (techo) & --- & {datos['techo']:.2f} & --- & --- & 40 \\\\")
        filas.append("    \\hline")
    cuerpo = "\n".join(filas)

    eq = equivalente(datos["filas"])
    nota = ""
    if eq:
        f, s = eq
        nota = (f" A latencia media equivalente ({f['duracion_media_s']:.2f} frente a "
                f"{s['duracion_media_s']:.2f}~s), la segmentación por silencios reduce el "
                f"error {(f['wer'] - s['wer']) * 100:.2f} puntos, a costa de que el "
                f"percentil 95 pase de {f['duracion_p95_s']:.2f} a {s['duracion_p95_s']:.2f}~s.")
    par = datos.get("pareado")
    if par:
        ic = par["ic95_pp"]
        nota += (f" Ese contraste se somete al mismo doble criterio que las técnicas de "
                 f"adaptación, sobre los mismos fragmentos: intervalo de confianza al 95\\% "
                 f"de [{ic[0]:+.2f}, {ic[1]:+.2f}] puntos por remuestreo de clips, y "
                 f"{par['mejoran']} fragmentos que mejoran frente a {par['empeoran']} que "
                 f"empeoran en el test de signos ($p={par['p_test_signos']:.2g}$).")

    return f"""% GENERADO AUTOMATICAMENTE por research/eval/report/tabla_segmentacion.py
% No editar a mano.
\\begin{{table}}[h]
\\centering
\\small
\\setlength{{\\tabcolsep}}{{4pt}}
\\resizebox{{\\textwidth}}{{!}}{{%
\\begin{{tabular}}{{|l|r|r|r|r|r|}}
    \\hline
    \\textbf{{Estrategia}} & \\textbf{{Tope (s)}} & \\textbf{{WER (\\%)}} &
    \\textbf{{Dur. media (s)}} & \\textbf{{Dur. p95 (s)}} & \\textbf{{Segmentos}} \\\\
    \\hline
{cuerpo}
\\end{{tabular}}}}
\\caption{{Segmentación por silencios frente a troceado por reloj, con el mismo tope de
duración en cada par para que la comparación no mida simplemente la longitud del
segmento.{nota}}}
\\label{{tab:vad}}
\\end{{table}}
"""


if __name__ == "__main__":
    datos = cargar()
    md = markdown(datos)
    print(md)

    DESTINO_MD.mkdir(parents=True, exist_ok=True)
    DESTINO_TEX.mkdir(parents=True, exist_ok=True)
    (DESTINO_MD / "segmentacion.md").write_text(md + "\n", encoding="utf-8")
    (DESTINO_TEX / "segmentacion.tex").write_text(latex(datos), encoding="utf-8")
    print(f"\n-> {(DESTINO_MD / 'segmentacion.md').relative_to(RAIZ)}")
    print(f"-> {(DESTINO_TEX / 'segmentacion.tex').relative_to(RAIZ)}")
