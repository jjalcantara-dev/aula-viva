"""Sonda de entorno GPU para el TFM.

Verifica no solo que la GPU se detecta, sino que calcula y entrena de verdad.
Cierra el riesgo R2 (ROCm/AMD) del PLANNING.md.

Uso:  python3 tools/check_gpu.py
"""

import sys
import time

FAIL = []


def check(nombre, fn):
    print(f"\n--- {nombre} ---")
    try:
        fn()
        print(f"[OK] {nombre}")
    except Exception as e:
        print(f"[FALLO] {nombre}: {type(e).__name__}: {e}")
        FAIL.append(nombre)


def entorno():
    import torch
    print(f"torch            : {torch.__version__}")
    print(f"version.hip      : {getattr(torch.version, 'hip', None)}")
    print(f"cuda.is_available: {torch.cuda.is_available()}")
    if not torch.cuda.is_available():
        raise RuntimeError("la GPU no se detecta")
    for i in range(torch.cuda.device_count()):
        p = torch.cuda.get_device_properties(i)
        print(f"  [{i}] {p.name}  arch={getattr(p, 'gcnArchName', '?')}  "
              f"VRAM={p.total_memory / 1024**3:.1f} GiB")


def computo_real():
    """is_available() puede mentir. Esto no."""
    import torch
    a = torch.randn(4096, 4096, device="cuda")
    b = torch.randn(4096, 4096, device="cuda")
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    for _ in range(10):
        c = a @ b
    torch.cuda.synchronize()
    dt = time.perf_counter() - t0
    tflops = (10 * 2 * 4096**3) / dt / 1e12
    print(f"matmul 4096^3 x10: {dt:.3f} s  ->  {tflops:.1f} TFLOP/s (fp32)")
    # verificar que el resultado es correcto, no solo que no peta
    err = (c - (a @ b)).abs().max().item()
    print(f"error maximo     : {err:.2e}")
    if err > 1e-3:
        raise RuntimeError("resultado numericamente incorrecto")


def precisiones():
    import torch
    for dtype in (torch.float16, torch.bfloat16):
        a = torch.randn(2048, 2048, device="cuda", dtype=dtype)
        c = a @ a
        torch.cuda.synchronize()
        print(f"{str(dtype):20s}: OK  (norma={c.float().norm().item():.1f})")


def entrenamiento():
    """LA prueba que importa: forward + backward + optimizer step."""
    import torch
    import torch.nn as nn

    modelo = nn.Sequential(
        nn.Linear(512, 1024), nn.ReLU(),
        nn.Linear(1024, 1024), nn.ReLU(),
        nn.Linear(1024, 10),
    ).cuda()
    opt = torch.optim.AdamW(modelo.parameters(), lr=1e-3)
    lossf = nn.CrossEntropyLoss()

    x = torch.randn(256, 512, device="cuda")
    y = torch.randint(0, 10, (256,), device="cuda")

    perdidas = []
    for paso in range(100):
        opt.zero_grad()
        loss = lossf(modelo(x), y)
        loss.backward()
        opt.step()
        if paso % 25 == 0:
            perdidas.append(loss.item())
            print(f"  paso {paso:3d}  loss={loss.item():.4f}")
    final = loss.item()
    print(f"  paso  99  loss={final:.4f}")
    if not (final < perdidas[0]):
        raise RuntimeError("la perdida no baja: el entrenamiento no converge")
    print(f"backward + AdamW funcionan (loss {perdidas[0]:.3f} -> {final:.4f})")


def entrenamiento_mixto():
    """Precision mixta: lo que se usara de verdad en un fine-tuning."""
    import torch
    import torch.nn as nn

    modelo = nn.Sequential(nn.Linear(512, 2048), nn.GELU(), nn.Linear(2048, 10)).cuda()
    opt = torch.optim.AdamW(modelo.parameters(), lr=1e-3)
    lossf = nn.CrossEntropyLoss()
    x = torch.randn(256, 512, device="cuda")
    y = torch.randint(0, 10, (256,), device="cuda")

    for _ in range(20):
        opt.zero_grad()
        with torch.autocast("cuda", dtype=torch.bfloat16):
            loss = lossf(modelo(x), y)
        loss.backward()
        opt.step()
    print(f"autocast bfloat16 + backward: OK (loss={loss.item():.4f})")


def memoria():
    import torch
    libre, total = torch.cuda.mem_get_info()
    print(f"VRAM libre/total : {libre / 1024**3:.1f} / {total / 1024**3:.1f} GiB")
    print(f"pico reservado   : {torch.cuda.max_memory_reserved() / 1024**3:.2f} GiB")


if __name__ == "__main__":
    print(f"python           : {sys.version.split()[0]}")
    check("entorno", entorno)
    check("computo real (matmul fp32)", computo_real)
    check("precisiones fp16/bf16", precisiones)
    check("entrenamiento (forward+backward+step)", entrenamiento)
    check("entrenamiento precision mixta", entrenamiento_mixto)
    check("memoria", memoria)

    print("\n" + "=" * 60)
    if FAIL:
        print(f"FALLOS: {', '.join(FAIL)}")
        print("-> R2 SIGUE ABIERTO. Revisar antes de comprometer LoRA.")
        sys.exit(1)
    print("TODO OK -> la GPU entrena. R2 mitigado, LoRA es viable a priori.")
