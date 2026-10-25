import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import schema  # noqa: E402


@pytest.fixture()
def engine(tmp_path, monkeypatch):
    """Base SQLite temporal con el esquema completo y los miembros desconocidos."""
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("LAKE_DIR", str(tmp_path / "lake"))
    motor = create_engine(f"sqlite:///{tmp_path / 'test.db'}")

    @event.listens_for(motor, "connect")
    def _fk(conexion, _):
        conexion.execute("PRAGMA foreign_keys=ON")

    schema.crear_esquema(motor)
    schema.sembrar_miembros_desconocidos(motor)
    return motor
