"""Capas Bronze y Silver en Parquet (arquitectura Medallion).

- bronze: dato crudo tal como llegó (sin limpiar).
- silver: dato limpio y validado.
- gold: esquema estrella en la base de datos (ver `schema.py`).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from .config import get_settings
from .logger import get_logger

log = get_logger("medallion")
CAPAS = ("bronze", "silver")


def ruta_capa(capa: str, nombre: str) -> Path:
    if capa not in CAPAS:
        raise ValueError(f"Capa inválida '{capa}'. Usa una de {CAPAS}.")
    return get_settings().lake_dir / capa / f"{nombre}.parquet"


def guardar_capa(df: pd.DataFrame, capa: str, nombre: str) -> Path:
    """Guarda `df` en Parquet dentro de la capa indicada (sobrescribe: idempotente)."""
    ruta = ruta_capa(capa, nombre)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    salida = df.copy()
    if "_ingestado_en" not in salida.columns:
        salida["_ingestado_en"] = datetime.now()
    salida.to_parquet(ruta, index=False)
    log.info("Capa %s: %s filas guardadas en %s", capa, len(salida), ruta.name)
    return ruta


def leer_capa(capa: str, nombre: str) -> pd.DataFrame:
    return pd.read_parquet(ruta_capa(capa, nombre))
