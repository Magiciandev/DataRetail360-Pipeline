"""Logging común a todo el pipeline.

- Escribe en consola y en `logs/pipeline_AAAAMMDD.log` (rotativo).
- Redacta RUT y correos de cualquier mensaje o traceback, para no dejar datos
  personales en los logs (Ley 21.719 / checklist 2.3.4, sección 3).
"""
from __future__ import annotations

import logging
import re
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

from .config import get_settings

_PATRONES_PII = [
    (re.compile(r"\b\d{1,2}(?:\.\d{3}){2}-[\dkK]\b|\b\d{7,8}-[\dkK]\b"), "[RUT]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
]

_FORMATO = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_RAIZ = "datarretail360"


def redactar_pii(texto: str) -> str:
    """Reemplaza RUT y correos por marcadores."""
    for patron, reemplazo in _PATRONES_PII:
        texto = patron.sub(reemplazo, texto)
    return texto


class _FormatterSeguro(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redactar_pii(super().format(record))


def _configurar_raiz() -> logging.Logger:
    raiz = logging.getLogger(_RAIZ)
    if raiz.handlers:          # ya configurado: idempotente
        return raiz
    raiz.setLevel(logging.INFO)
    raiz.propagate = False
    formatter = _FormatterSeguro(_FORMATO)

    consola = logging.StreamHandler(sys.stdout)
    consola.setFormatter(formatter)
    raiz.addHandler(consola)

    log_dir = get_settings().log_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    archivo = RotatingFileHandler(
        log_dir / f"pipeline_{datetime.now():%Y%m%d}.log",
        maxBytes=1_000_000, backupCount=5, encoding="utf-8",
    )
    archivo.setFormatter(formatter)
    raiz.addHandler(archivo)
    return raiz


def get_logger(nombre: str = "pipeline") -> logging.Logger:
    """Logger hijo del logger raíz del proyecto, listo para usar."""
    _configurar_raiz()
    return logging.getLogger(f"{_RAIZ}.{nombre}")
