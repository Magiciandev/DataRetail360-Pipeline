"""Excepciones del pipeline.

Se distingue entre errores recuperables (se reintentan) y fatales (detienen la
ejecución), tal como pide la checklist de code review 2.3.4.
"""


class ErrorPipeline(Exception):
    """Base de todos los errores propios del pipeline."""


class ErrorFatal(ErrorPipeline):
    """Error no recuperable: el pipeline debe detenerse."""


class ErrorRecuperable(ErrorPipeline):
    """Error transitorio (ej. conexión caída): se puede reintentar."""


class ErrorConfiguracion(ErrorFatal):
    """Falta una variable de entorno o su valor es inválido."""
