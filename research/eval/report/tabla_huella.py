"""Tabla de huella de recursos, para el manual de despliegue.

Lee lo que midio `tools/huella_recursos.py`. Existe para que los requisitos de hardware del
apendice no sean cifras tecleadas a mano: un centro va a comprar equipamiento a partir de
ellas, asi que tienen que salir de una medicion y regenerarse si cambia el modelo.

Uso:  .venv/bin/python research/eval/report/tabla_huella.py
"""

import json
import math
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
RESULTADOS = RAIZ / "research" / "results"
DESTINO_TEX = RAIZ / "memoria" / "tablas"

# Orden de presentacion: de menor a mayor exigencia, que es como se lee un requisito.
ORDEN = ["openai/whisper-small", "openai/whisper-medium"]


def etiqueta(d: dict) -> str:
    nombre = d["modelo"].split("/")[-1]
    return nombre + (" + LoRA" if d.get("adaptador") else "")


def cargar() -> list[dict]:
    filas = [json.loads(f.read_text(encoding="utf-8"))
             for f in sorted(RESULTADOS.glob("huella_*.json"))]
    if not filas:
        raise SystemExit("sin mediciones: ejecutar tools/huella_recursos.py")

    def clave(d):
        base = d["modelo"]
        return (ORDEN.index(base) if base in ORDEN else len(ORDEN),
                bool(d.get("adaptador")))
    return sorted(filas, key=clave)


def markdown(filas: list[dict]) -> str:
    L = ["| Modelo | Disco (GB) | VRAM pico (GB) | RAM proceso (GB) |",
         "|---|---:|---:|---:|"]
    for d in filas:
        L.append(f"| `{etiqueta(d)}` | {d['disco_gb']:.2f} | "
                 f"{d['vram_pico_gb']:.2f} | {d['ram_proceso_gb']:.2f} |")
    ref = filas[0]["entorno"]
    L += ["", f"> Medido en {ref['gpu']} ({ref['vram_total_gb']:.1f} GB de VRAM), "
              f"precisión `float16`, sobre 30 s de audio (la ventana completa del modelo, "
              f"que es el caso peor)."]
    return "\n".join(L)


def latex(filas: list[dict]) -> str:
    cuerpo = "\n".join(
        f"    \\texttt{{{etiqueta(d)}}} & {d['disco_gb']:.2f} & {d['vram_pico_gb']:.2f} & "
        f"{d['ram_proceso_gb']:.2f} \\\\"
        for d in filas)
    ref = filas[0]["entorno"]
    # El requisito de compra se deriva del pico medido: se redondea HACIA ARRIBA al entero
    # (math.ceil, no int, que trunca) y se le suman 2 GB de margen. Con int(1.63)+2 salian
    # 3 GB y la tabla de requisitos decia 4: el pie y el requisito se contradecian.
    peor = max(d["vram_pico_gb"] for d in filas)
    holgura = math.ceil(peor) + 2
    return f"""% GENERADO AUTOMATICAMENTE por research/eval/report/tabla_huella.py
% No editar a mano.
\\begin{{table}}[H]
\\centering
\\small
\\begin{{tabular}}{{|l|r|r|r|}}
    \\hline
    \\textbf{{Modelo}} & \\textbf{{Disco (GB)}} & \\textbf{{VRAM pico (GB)}} &
    \\textbf{{RAM del proceso (GB)}} \\\\
    \\hline
{cuerpo}
    \\hline
\\end{{tabular}}
\\caption{{Huella de recursos del servicio de reconocimiento, medida sobre
{ref['gpu']} con precisión \\texttt{{float16}} y una ventana completa de 30~s de audio, que
es el caso peor. El pico de VRAM mayor observado es {peor:.2f}~GB, de donde sale el
requisito de {holgura}~GB de la tabla~\\ref{{tab:requisitos-despliegue}}: el margen cubre el
gestor de ventanas del propio equipo y la fragmentación de memoria.}}
\\label{{tab:huella}}
\\end{{table}}
"""


if __name__ == "__main__":
    filas = cargar()
    md = markdown(filas)
    print(md)

    DESTINO_TEX.mkdir(parents=True, exist_ok=True)
    (RESULTADOS / "huella.md").write_text(md + "\n", encoding="utf-8")
    (DESTINO_TEX / "huella.tex").write_text(latex(filas), encoding="utf-8")
    print(f"\n-> {(RESULTADOS / 'huella.md').relative_to(RAIZ)}")
    print(f"-> {(DESTINO_TEX / 'huella.tex').relative_to(RAIZ)}")
