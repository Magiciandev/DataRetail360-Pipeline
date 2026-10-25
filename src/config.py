"""Configuración central del pipeline.

Todo valor sensible se lee desde variables de entorno (archivo `.env`, que NO se
versiona). Ver `.env.example` para la lista de variables.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .errores import ErrorConfiguracion

try:  # python-dotenv es opcional: si no está, se usan las variables del sistema
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent.parent
if load_dotenv:
    load_dotenv(BASE_DIR / ".env", override=True)

# --- Convenciones compartidas por los 3 notebooks (ver docs/acuerdos_tecnicos.md)
FECHA_INICIO_DEFECTO = date(1900, 1, 1)   # valido_desde de la primera versión de cada registro
FECHA_FIN_VIGENTE = date(9999, 12, 31)    # valido_hasta de la versión vigente
CLAVE_DESCONOCIDA = -1                    # miembro "No informado" de cada dimensión


@dataclass(frozen=True)
class Settings:
    db_engine: str          # "sqlite" | "sqlserver"
    db_host: str
    db_name: str
    db_driver: str
    db_trusted: bool        # autenticación de Windows (SQL Server)
    db_user: str | None
    db_password: str | None
    sqlite_path: Path
    data_dir: Path          # datos de entrada (CSV/JSON)
    lake_dir: Path          # capas bronze/silver en Parquet
    log_dir: Path
    rut_salt: str | None    # sal para anonimizar RUT (nunca se guarda en el código)


def _bool(valor: str | None, defecto: bool) -> bool:
    if valor is None:
        return defecto
    return valor.strip().lower() in {"1", "true", "yes", "si", "sí"}


def get_settings() -> Settings:
    """Lee la configuración en el momento de la llamada (útil para pruebas)."""
    def ruta(nombre: str, defecto: str) -> Path:
        p = Path(os.getenv(nombre, defecto))
        return p if p.is_absolute() else BASE_DIR / p

    return Settings(
        db_engine=os.getenv("DB_ENGINE", "sqlite").strip().lower(),
        db_host=os.getenv("DB_HOST", "localhost"),
        db_name=os.getenv("DB_NAME", "DataRetail360_DW"),
        db_driver=os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server"),
        db_trusted=_bool(os.getenv("DB_TRUSTED_CONNECTION"), True),
        db_user=os.getenv("DB_USER") or None,
        db_password=os.getenv("DB_PASSWORD") or None,
        sqlite_path=ruta("DB_SQLITE_PATH", "data/datarretail360_dw.db"),
        data_dir=ruta("DATA_DIR", "data/sample"),
        lake_dir=ruta("LAKE_DIR", "data/lake"),
        log_dir=ruta("LOG_DIR", "logs"),
        rut_salt=os.getenv("RUT_SALT") or None,
    )


def exigir_rut_salt(settings: Settings | None = None) -> str:
    """Devuelve la sal para anonimizar RUT o falla con un mensaje claro."""
    s = (settings or get_settings()).rut_salt
    if not s:
        raise ErrorConfiguracion(
            "Falta la variable de entorno RUT_SALT (ver .env.example). "
            "Se necesita para anonimizar el RUT de los clientes."
        )
    return s
