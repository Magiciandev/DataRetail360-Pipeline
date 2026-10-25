"""Revisa que los notebooks sigan la plantilla común y que su código sea válido."""
import ast
from pathlib import Path

import nbformat
import pytest

NOTEBOOKS = sorted((Path(__file__).resolve().parent.parent / "notebooks").glob("*.ipynb"))
SECCIONES = ["Extract", "Transform", "Load", "Validación", "Evidencia"]


def test_hay_cuatro_notebooks():
    assert len(NOTEBOOKS) == 4


@pytest.mark.parametrize("ruta", NOTEBOOKS, ids=lambda p: p.name)
def test_notebook_tiene_las_secciones_de_la_plantilla(ruta):
    nb = nbformat.read(ruta, as_version=4)
    texto = " ".join(c.source for c in nb.cells if c.cell_type == "markdown")
    faltan = [s for s in SECCIONES if s not in texto]
    assert not faltan, f"{ruta.name}: faltan secciones {faltan}"


@pytest.mark.parametrize("ruta", NOTEBOOKS, ids=lambda p: p.name)
def test_codigo_del_notebook_es_python_valido(ruta):
    nb = nbformat.read(ruta, as_version=4)
    for i, celda in enumerate(c for c in nb.cells if c.cell_type == "code"):
        ast.parse(celda.source, filename=f"{ruta.name}[celda {i}]")


@pytest.mark.parametrize("ruta", NOTEBOOKS, ids=lambda p: p.name)
def test_notebook_no_incluye_credenciales(ruta):
    nb = nbformat.read(ruta, as_version=4)
    codigo = " ".join(c.source.lower() for c in nb.cells if c.cell_type == "code")
    assert "password" not in codigo and "pwd=" not in codigo
