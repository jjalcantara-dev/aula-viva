"""Tabla comparativa de las tecnicas de adaptacion. Es la tabla central del TFM.

Agrega los resultados de los experimentos del nucleo investigador (exp-0XX) en una unica
tabla con la misma estructura para todos: linea base, tecnica, diferencia, intervalo de
confianza, analisis pareado y veredicto.

Cada experimento guarda sus metricas con nombres propios (sin_prompt/con_prompt,
sin_corregir/corregido...). El adaptador de cada uno los traduce a un esquema comun, en
lugar de forzar a los experimentos a compartir vocabulario: cada tecnica tiene su jerga y
oscurecerla en el codigo del experimento seria peor.

Uso:  .venv/bin/python research/eval/report/tabla_tecnicas.py
"""

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
EXPERIMENTOS = RAIZ / "research" / "experiments"
DESTINO_TEX = RAIZ / "memoria" / "tablas"
DESTINO_MD = RAIZ / "research" / "results"

# experimento -> (nombre legible, clave de la linea base, clave de la tecnica)
ADAPTADORES = {
    "exp-001-prompting": ("Prompting contextual", "sin_prompt", "con_prompt"),
    "exp-002-postcorreccion": ("Post-corrección con LLM", "sin_corregir", "corregido"),
    "exp-003-lora": ("Fine-tuning con LoRA", "sin_lora", "con_lora"),
}


def cargar() -> list[dict]:
    filas = []
    for carpeta, (nombre, clave_base, clave_tecnica) in ADAPTADORES.items():
        for f in sorted((EXPERIMENTOS / carpeta / "results").glob("metricas_*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            m = d.get("metricas", {})
            if clave_base not in m or clave_tecnica not in m:
                continue
            par = d.get("pareado", {})
            filas.append({
                "tecnica": nombre,
                "corpus": _corpus(d),
                "wer_base": m[clave_base]["wer"] * 100,
                "wer_tecnica": m[clave_tecnica]["wer"] * 100,
                "delta": par.get("delta_wer_pp"),
                "ic": par.get("ic95_pp"),
                "mejoran": par.get("mejoran"),
                "empeoran": par.get("empeoran"),
                "sin_cambio": par.get("sin_cambio"),
                "p": par.get("p_test_signos"),
                "concluyente": par.get("concluyente"),
                "palabras": m[clave_base].get("n_palabras_ref"),
            })
    return filas


def _corpus(d: dict) -> str:
    """El corpus se deduce de la entrada, que no es la misma en todos los experimentos."""
    cfg = d.get("config", {})
    origen = cfg.get("manifiesto") or cfg.get("transcripciones") or "?"
    tallo = Path(origen).stem
    for sufijo in ("__fallback", "__voraz"):
        tallo = tallo.replace(sufijo, "")
    return tallo.split("__")[-1] if "__" in tallo else tallo


#: Por debajo de esta cifra de palabras de referencia, el intervalo de confianza es tan
#: ancho que el experimento no puede detectar los efectos esperables (~0.5 pp). Medido en
#: M0: con ~600 palabras el IC alcanza +-2.4 pp. Ver corpus/FUENTES.md.
PALABRAS_MINIMAS = 5_000


def markdown(filas) -> str:
    L = ["| Técnica | Corpus | Palabras | WER base | WER técnica | Δ (pp) | IC 95% | Mejoran/Empeoran | p | Veredicto |",
         "|---|---|---:|---:|---:|---:|---|---|---:|---|"]
    hay_baja_potencia = False
    for r in filas:
        ic = f"[{r['ic'][0]:+.2f}, {r['ic'][1]:+.2f}]" if r["ic"] else "—"
        veredicto = "**significativa**" if r["concluyente"] else "no concluyente"
        n = r["palabras"] or 0
        # Marcar la potencia insuficiente en lugar de ocultarla: una fila "no
        # concluyente" por falta de muestra no dice lo mismo que una con muestra
        # suficiente, y en la misma tabla se confunden.
        if n and n < PALABRAS_MINIMAS:
            hay_baja_potencia = True
            veredicto = "⚠️ sin potencia"
        L.append(
            f"| {r['tecnica']} | `{r['corpus']}` | {n or '—'} | "
            f"{r['wer_base']:.2f} | {r['wer_tecnica']:.2f} | "
            f"{r['delta']:+.2f} | {ic} | {r['mejoran']}/{r['empeoran']} | "
            f"{r['p']:.4f} | {veredicto} |")
    if hay_baja_potencia:
        L.append("")
        L.append(f"> ⚠️ Menos de {PALABRAS_MINIMAS:,} palabras de referencia: el intervalo "
                 "de confianza es demasiado ancho para detectar los efectos esperables. "
                 "Esas filas **no permiten concluir nada**, ni a favor ni en contra.")
    return "\n".join(L)


def latex(filas) -> str:
    cuerpo = "\n".join(
        f"    {r['tecnica']} & \\texttt{{{r['corpus'].replace('_', '-')}}} & "
        f"{r['wer_base']:.2f} & {r['wer_tecnica']:.2f} & {r['delta']:+.2f} & "
        f"[{r['ic'][0]:+.2f}, {r['ic'][1]:+.2f}] & {r['p']:.3f} & "
        f"{'Sí' if r['concluyente'] else 'No'} \\\\" for r in filas if r["ic"])
    return f"""% GENERADO AUTOMATICAMENTE por research/eval/report/tabla_tecnicas.py
% No editar a mano.
\\begin{{table}}[h]
\\centering
\\small
\\begin{{tabular}}{{|l|l|r|r|r|c|r|c|}}
    \\hline
    \\textbf{{Técnica}} & \\textbf{{Corpus}} & \\textbf{{WER base}} &
    \\textbf{{WER téc.}} & \\textbf{{$\\Delta$ (pp)}} & \\textbf{{IC 95\\%}} &
    \\textbf{{$p$}} & \\textbf{{Signif.}} \\\\
    \\hline
{cuerpo}
    \\hline
\\end{{tabular}}
\\caption{{Efecto de cada técnica de adaptación sobre el WER (\\%), con diseño pareado.
$\\Delta$ negativo indica mejora. El intervalo de confianza se obtiene por bootstrap
remuestreando clips; $p$ corresponde al test de signos sobre los clips que cambian.}}
\\label{{tab:comparativa-tecnicas}}
\\end{{table}}
"""


if __name__ == "__main__":
    filas = cargar()
    if not filas:
        raise SystemExit("sin resultados de tecnicas todavia")

    md = markdown(filas)
    print(md)
    DESTINO_MD.mkdir(parents=True, exist_ok=True)
    DESTINO_TEX.mkdir(parents=True, exist_ok=True)
    (DESTINO_MD / "comparativa_tecnicas.md").write_text(md + "\n", encoding="utf-8")
    (DESTINO_TEX / "comparativa_tecnicas.tex").write_text(latex(filas), encoding="utf-8")
    print(f"\n-> {(DESTINO_MD / 'comparativa_tecnicas.md').relative_to(RAIZ)}")
    print(f"-> {(DESTINO_TEX / 'comparativa_tecnicas.tex').relative_to(RAIZ)}")
