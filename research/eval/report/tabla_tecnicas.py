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
                # El veredicto se DERIVA aqui de las cifras guardadas, no se lee del
                # JSON: los resultados anteriores al endurecimiento del criterio traen la
                # marca antigua, que bastaba con que el IC excluyera el cero. Recalcularlo
                # mantiene toda la tabla bajo el mismo criterio sin relanzar experimentos.
                "palabras": m[clave_base].get("n_palabras_ref"),
            })
    for f in filas:
        ic = f["ic"]
        f["ic_excluye_cero"] = bool(ic) and (ic[1] < 0 or ic[0] > 0)
        f["signos_confirma"] = f["p"] is not None and f["p"] < 0.05
        f["concluyente"] = f["ic_excluye_cero"] and f["signos_confirma"]
        f["discrepan"] = f["ic_excluye_cero"] != f["signos_confirma"]
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
        if r["concluyente"]:
            veredicto = "**significativa**"
        elif r.get("discrepan"):
            # Una prueba dice que sí y la otra que no: el efecto está en el límite de
            # detección y afirmar cualquiera de las dos cosas sería forzar el dato.
            veredicto = "en el límite"
        else:
            veredicto = "no concluyente"
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


def veredicto_corto(r: dict) -> str:
    """Mismo vocabulario que el Markdown. La distincion que importa es entre «no» y «sin
    potencia»: la primera dice que no hay efecto, la segunda que esta medicion no puede
    saberlo. Presentarlas igual, como se hacia antes en el LaTeX, convierte una carencia
    de muestra en un resultado negativo."""
    n = r["palabras"] or 0
    if n and n < PALABRAS_MINIMAS:
        return "Sin potencia"
    if r["concluyente"]:
        return "Sí"
    if r.get("discrepan"):
        return "En el límite"
    return "No"


def _miles(n: int) -> str:
    """Separador de millar espanol, que es el punto. Se formatea aparte para no tocar las
    comas del intervalo de confianza, que van en la misma fila."""
    return f"{n:,}".replace(",", ".")


def latex(filas) -> str:
    usables = [r for r in filas if r["ic"]]
    cuerpo = "\n".join(
        f"    {r['tecnica']} & \\texttt{{{r['corpus'].replace('_', '-')}}} & "
        f"{_miles(r['palabras'] or 0)} & "
        f"{r['wer_base']:.2f} & {r['wer_tecnica']:.2f} & {r['delta']:+.2f} & "
        f"[{r['ic'][0]:+.2f}, {r['ic'][1]:+.2f}] & {r['p']:.3f} & "
        f"{veredicto_corto(r)} \\\\"
        for r in usables)
    sin_potencia = sum(1 for r in usables if veredicto_corto(r) == "Sin potencia")
    return f"""% GENERADO AUTOMATICAMENTE por research/eval/report/tabla_tecnicas.py
% No editar a mano.
%
% {sin_potencia} de {len(usables)} filas quedan marcadas «Sin potencia». Si esta cuenta
% cambia, hay que revisar la cifra que da el capitulo de conclusiones al verificar el
% objetivo 3.
\\begin{{table}}[h]
\\centering
\\footnotesize
\\setlength{{\\tabcolsep}}{{4pt}}
\\resizebox{{\\textwidth}}{{!}}{{%
\\begin{{tabular}}{{|l|l|r|r|r|r|c|r|c|}}
    \\hline
    \\textbf{{Técnica}} & \\textbf{{Corpus}} & \\textbf{{Palabras}} & \\textbf{{WER base}} &
    \\textbf{{WER téc.}} & \\textbf{{$\\Delta$ (pp)}} & \\textbf{{IC 95\\%}} &
    \\textbf{{$p$}} & \\textbf{{Signif.}} \\\\
    \\hline
{cuerpo}
    \\hline
\\end{{tabular}}}}
\\caption{{Efecto de cada técnica de adaptación sobre el WER (\\%), con diseño pareado.
$\\Delta$ negativo indica mejora. El intervalo de confianza se obtiene por bootstrap
remuestreando clips; $p$ corresponde al test de signos sobre los clips que cambian.
La columna de significación distingue tres situaciones que no deben confundirse:
\\emph{{Sí}} cuando ambos criterios coinciden, \\emph{{En el límite}} cuando discrepan
entre sí, y \\textbf{{\\emph{{Sin potencia}}}} cuando la muestra no alcanza las
{_miles(PALABRAS_MINIMAS)} palabras de referencia que exige la sección~\\ref{{sec:potencia}}.
Estas últimas no dicen que la técnica no funcione: dicen que con ese material no se puede
saber, y por eso no se interpretan.}}
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
