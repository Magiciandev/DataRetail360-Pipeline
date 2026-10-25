"""Lectura de fuentes (CSV / JSON) con trazabilidad de origen.

Todas las columnas se leen como texto para no perder información en la capa
bronce; la conversión de tipos ocurre en la transformación.
Cada fila queda marcada con `origen_archivo` y `fila_origen`, que permiten
registrar rechazos sin guardar datos personales.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .errores import ErrorFatal
from .logger import get_logger

log = get_logger("extract")


def _verificar(ruta: Path) -> Path:
    ruta = Path(ruta)
    if not ruta.exists():
        log.error("Fuente no encontrada: %s", ruta.name)
        raise ErrorFatal(f"No existe el archivo de origen: {ruta}")
    return ruta


def leer_csv(ruta, **kwargs) -> pd.DataFrame:
    """Lee un CSV como texto y agrega `origen_archivo` y `fila_origen` (línea del archivo)."""
    ruta = _verificar(ruta)
    df = pd.read_csv(ruta, dtype="string", **kwargs)
    df["origen_archivo"] = ruta.name
    df["fila_origen"] = range(2, len(df) + 2)   # la línea 1 es el encabezado
    log.info("Extraídas %s filas desde %s", len(df), ruta.name)
    return df


def leer_json(ruta, record_path=None, meta=None) -> pd.DataFrame:
    """Lee un JSON (posiblemente anidado) y lo aplana con `json_normalize`.

    Si se usa `record_path` (ej. los `items` de cada orden), agrega la columna `_registro`:
    la posición del registro padre dentro del archivo. Sirve para numerar líneas dentro de
    cada aparición de una orden y así detectar órdenes repetidas.
    """
    ruta = _verificar(ruta)
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    if record_path is not None and isinstance(datos, list):
        for posicion, registro in enumerate(datos):
            if isinstance(registro, dict):
                registro.setdefault("_registro", posicion)
        meta = [*(meta or []), "_registro"]
    df = pd.json_normalize(datos, record_path=record_path, meta=meta, sep="_")
    df = df.astype("string")
    df["origen_archivo"] = ruta.name
    df["fila_origen"] = range(1, len(df) + 1)
    log.info("Extraídas %s filas desde %s", len(df), ruta.name)
    return df
