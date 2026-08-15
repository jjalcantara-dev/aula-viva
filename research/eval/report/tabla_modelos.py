"""Agrega los resultados de exp-000-baseline en una tabla comparativa.

Genera a la vez la version legible (markdown, para revisar) y la version LaTeX
(para la memoria). La tabla de la memoria SIEMPRE se genera desde aqui: ninguna
cifra se teclea a mano en el .tex.

Uso:  .venv/bin/python research/eval/report/tabla_modelos.py
"""

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
RESULTADOS = RAIZ / "research" / "experiments" / "exp-000-baseline" / "results"
DESTINO_TEX = RAIZ / "memoria" / "tablas"
DESTINO_MD = RAIZ / "research" / "results"

NORMALIZADOR = "basico"  # metrica principal (ver docs/preguntas-director.md)


def cargar(corpus: str = "fleurs_es", decodificacion: str = "fallback") -> list[dict]:
    filas = []
    for f in sorted(RESULTADOS.glob(f"metricas_*__{corpus}__{decodificacion}.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        m = d["metricas"][NORMALIZADOR]
        filas.append({
            "modelo": d["modelo"]["nombre"].split("/")[-1],
            "params": d["modelo"]["parametros_M"],
            "wer": m["wer"] * 100,
            "cer": m["cer"] * 100,
            "rtf": d["coste"]["factor_tiempo_real"],
            "veces": 1 / d["coste"]["factor_tiempo_real"] if d["coste"]["factor_tiempo_real"] else 0,
            # Se arrastra POR FILA, no se lee de un fichero cualquiera: ver homogenea().
            "n_clips": m["n_clips"],
        })
    return sorted(filas, key=lambda r: r["params"])


def homogenea(filas: list[dict]) -> bool:
    """Comprueba que todas las filas se midieron sobre el mismo numero de fragmentos.

    Esta comprobacion existe porque el fallo ya ocurrio. La identidad de un resultado es
    <modelo>__<corpus>__<decodificacion>, y NO incluye el tamano de la muestra: al reevaluar
    un modelo sobre la ampliacion de un corpus, su fichero sobrescribe al de la muestra
    reducida y la tabla pasa a comparar 1.200 fragmentos contra 40 sin que nada lo delate.
    Las cifras siguen siendo correctas cada una por su lado; lo que deja de ser valido es
    ponerlas en la misma tabla.

    La solucion de fondo es que la muestra forme parte del nombre del corpus, como ya se
    hizo con `voxpopuli_es_400`—; mientras tanto, esto al menos lo hace visible.
    """
    return len({f["n_clips"] for f in filas}) <= 1


def markdown(filas) -> str:
    L = ["| Modelo | Parámetros (M) | Clips | WER (%) | CER (%) | RTF | Veces tiempo real |",
         "|---|---:|---:|---:|---:|---:|---:|"]
    for r in filas:
        L.append(f"| `{r['modelo']}` | {r['params']} | {r['n_clips']} | {r['wer']:.2f} | "
                 f"{r['cer']:.2f} | {r['rtf']:.3f} | {r['veces']:.1f}× |")
    if not homogenea(filas):
        L += ["",
              "> ⚠️ **Las filas NO comparten muestra.** Comparar sus WER entre sí no es "
              "válido: cada uno se midió sobre un material distinto. Ver `homogenea()`."]
    return "\n".join(L)


def latex(filas, n_clips, duracion_min, corpus: str) -> str:
    """El corpus entra en la ETIQUETA, no solo en el nombre del fichero.

    Antes todas las tablas por corpus compartian `tab:baseline-modelos`: incluir dos en la
    memoria daba etiquetas duplicadas y referencias cruzadas apuntando a la tabla
    equivocada, en silencio. Es el mismo principio que rige los nombres de resultado: la
    identidad incluye el corpus.
    """
    etiqueta = f"tab:baseline-modelos-{corpus.replace('_', '-')}"
    cuerpo = "\n".join(
        f"    \\texttt{{{r['modelo'].replace('_', '-')}}} & {r['params']} & {r['n_clips']} & "
        f"{r['wer']:.2f} & {r['cer']:.2f} & {r['rtf']:.3f} & {r['veces']:.1f} \\\\"
        for r in filas)
    # La advertencia viaja DENTRO del pie: si la tabla acaba en la memoria pese al aviso
    # de consola, el lector tiene que verla igual.
    aviso = "" if homogenea(filas) else (
        r" \textbf{Atención:} las filas no comparten muestra, de modo que sus tasas de "
        r"error no son comparables entre sí; ver la columna \emph{Clips}.")
    return f"""% GENERADO AUTOMATICAMENTE por research/eval/report/tabla_modelos.py
% No editar a mano: los cambios se pierden en la siguiente regeneracion.
\\begin{{table}}[h]
\\centering
\\small
\\setlength{{\\tabcolsep}}{{4pt}}
\\resizebox{{\\textwidth}}{{!}}{{%
\\begin{{tabular}}{{|l|r|r|r|r|r|r|}}
    \\hline
    \\textbf{{Modelo}} & \\textbf{{Par.\\ (M)}} & \\textbf{{Clips}} & \\textbf{{WER (\\%)}} &
    \\textbf{{CER (\\%)}} & \\textbf{{RTF}} & \\textbf{{$\\times$ tiempo real}} \\\\
    \\hline
{cuerpo}
    \\hline
\\end{{tabular}}}}
\\caption{{Rendimiento de los modelos Whisper sin adaptar sobre
\\texttt{{{corpus.replace('_', '-')}}} ({duracion_min:.1f} minutos de audio en la muestra de
referencia). Normalización \\texttt{{{NORMALIZADOR}}}. RTF: factor de tiempo real (menor es
mejor).{aviso}}}
\\label{{{etiqueta}}}
\\end{{table}}
"""


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="fleurs_es",
                    help="sufijo del manifiesto (fleurs_es, tedx_es, ...)")
    ap.add_argument("--decodificacion", default="fallback", choices=["voraz", "fallback"])
    args = ap.parse_args()

    filas = cargar(args.corpus, args.decodificacion)
    if not filas:
        raise SystemExit(
            f"sin resultados para '{args.corpus}' / '{args.decodificacion}' en {RESULTADOS}")

    muestra = json.loads(
        next(RESULTADOS.glob(f"metricas_*__{args.corpus}__{args.decodificacion}.json"))
        .read_text(encoding="utf-8"))
    n_clips = muestra["metricas"][NORMALIZADOR]["n_clips"]
    dur_min = muestra["coste"]["audio_s"] / 60

    if not homogenea(filas):
        reparto = ", ".join(f"{r['modelo']}={r['n_clips']}" for r in filas)
        print(f"AVISO: '{args.corpus}' mezcla tamanos de muestra ({reparto}).\n"
              f"       Las tasas de error de esta tabla NO son comparables entre filas.\n"
              f"       Causa habitual: un modelo reevaluado sobre la ampliacion del corpus\n"
              f"       sobrescribio su resultado anterior, que compartia nombre de fichero.")

    md = markdown(filas)
    print(md)

    DESTINO_MD.mkdir(parents=True, exist_ok=True)
    DESTINO_TEX.mkdir(parents=True, exist_ok=True)
    nombre = f"baseline_modelos_{args.corpus}_{args.decodificacion}"
    (DESTINO_MD / f"{nombre}.md").write_text(md + "\n", encoding="utf-8")
    (DESTINO_TEX / f"{nombre}.tex").write_text(
        latex(filas, n_clips, dur_min, args.corpus), encoding="utf-8")

    print(f"\n-> {(DESTINO_MD / f'{nombre}.md').relative_to(RAIZ)}")
    print(f"-> {(DESTINO_TEX / f'{nombre}.tex').relative_to(RAIZ)}")
