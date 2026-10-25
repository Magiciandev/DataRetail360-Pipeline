"""Ejecuta el pipeline completo, notebook por notebook, y deja evidencia de cada corrida.

Orden (respeta las dependencias entre dimensiones):
    por cada snapshot (1 y 2):  01_dim_geografia → 02_dim_producto → 03_dim_cliente
    al final:                   04_fact_ventas_integracion

Uso:
    python run_pipeline.py                  # snapshots 1 y 2 + integración
    python run_pipeline.py --snapshots 1    # solo el primer snapshot
    python run_pipeline.py --solo 03        # un solo notebook (ej. mientras lo desarrollas)

Los notebooks ya ejecutados (con sus salidas) quedan en logs/ejecutados/ como evidencia.
Si un notebook falla, el pipeline SE DETIENE y sale con código 1 (nunca falla en silencio).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from src.config import get_settings  # noqa: E402
from src.logger import get_logger  # noqa: E402

log = get_logger("run_pipeline")
NOTEBOOKS = RAIZ / "notebooks"
DIMENSIONES = ["01_dim_geografia", "02_dim_producto", "03_dim_cliente"]
INTEGRACION = "04_fact_ventas_integracion"


def ejecutar(nombre: str, snapshot: int | None) -> None:
    ruta = NOTEBOOKS / f"{nombre}.ipynb"
    etiqueta = f"{nombre} (snapshot {snapshot})" if snapshot else nombre
    log.info("▶ Ejecutando %s", etiqueta)
    if snapshot:
        os.environ["SNAPSHOT"] = str(snapshot)          # el kernel hereda esta variable
    nb = nbformat.read(ruta, as_version=4)
    cliente = NotebookClient(nb, timeout=900, kernel_name="python3",
                             resources={"metadata": {"path": str(NOTEBOOKS)}})
    sufijo = f"_snapshot{snapshot}" if snapshot else ""
    salida = get_settings().log_dir / "ejecutados" / f"{nombre}{sufijo}.ipynb"
    salida.parent.mkdir(parents=True, exist_ok=True)
    try:
        cliente.execute()
    except CellExecutionError as exc:
        nbformat.write(nb, salida)                       # se guarda hasta donde llegó, para depurar
        log.error("✖ Falló %s. Revisa %s", etiqueta, salida.relative_to(RAIZ))
        sin_color = re.sub(r"\x1b\[[0-9;]*m", "", str(exc))     # quita los códigos de color de Jupyter
        log.error("Detalle: %s", sin_color.strip().splitlines()[-1] if sin_color.strip() else "sin detalle")
        raise SystemExit(1)
    nbformat.write(nb, salida)
    log.info("✔ %s OK", etiqueta)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecuta el pipeline ETL de DataRetail 360")
    parser.add_argument("--snapshots", type=int, default=2, help="cuántos snapshots procesar (por defecto 2)")
    parser.add_argument("--solo", help="ejecutar solo un notebook por prefijo (ej. 01, 03, 04)")
    args = parser.parse_args()

    if not os.getenv("RUT_SALT") and not get_settings().rut_salt:
        log.error("Falta RUT_SALT en el entorno o en .env (ver .env.example).")
        raise SystemExit(1)

    if args.solo:
        todos = [*DIMENSIONES, INTEGRACION]
        elegidos = [n for n in todos if n.startswith(args.solo)]
        if not elegidos:
            log.error("No hay un notebook que empiece con '%s'", args.solo)
            raise SystemExit(1)
        for nombre in elegidos:
            ejecutar(nombre, None if nombre == INTEGRACION else args.snapshots)
        return

    for snapshot in range(1, args.snapshots + 1):
        for nombre in DIMENSIONES:
            ejecutar(nombre, snapshot)
    ejecutar(INTEGRACION, None)
    log.info("Pipeline completo OK")


if __name__ == "__main__":
    main()
