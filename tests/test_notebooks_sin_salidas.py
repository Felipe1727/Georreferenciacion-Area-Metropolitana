"""Los notebooks versionados no deben llevar salidas: podrían contener datos personales de original/."""
import json
from pathlib import Path

import pytest

NOTEBOOKS = sorted((Path(__file__).resolve().parent.parent / "notebooks").glob("*.ipynb"))


def celdas_con_salidas(ruta):
    """Devuelve los índices de las celdas de código con salidas o contador de ejecución."""
    notebook = json.loads(Path(ruta).read_text(encoding="utf-8"))
    return [
        i for i, celda in enumerate(notebook["cells"])
        if celda["cell_type"] == "code" and (celda.get("outputs") or celda.get("execution_count") is not None)
    ]


def test_hay_notebooks():
    assert NOTEBOOKS, "No se encontró ningún notebook en notebooks/"


@pytest.mark.parametrize("ruta", NOTEBOOKS, ids=lambda ruta: ruta.name)
def test_notebook_sin_salidas(ruta):
    assert celdas_con_salidas(ruta) == [], (
        f"{ruta.name} tiene salidas. Límpialo antes del commit:\n"
        f"  jupyter nbconvert --clear-output --inplace notebooks/{ruta.name}"
    )


def test_detecta_salidas(tmp_path):
    notebook = {
        "cells": [
            {"cell_type": "markdown", "source": "texto", "metadata": {}},
            {"cell_type": "code", "source": "1", "metadata": {}, "outputs": [], "execution_count": None},
            {"cell_type": "code", "source": "2", "metadata": {}, "execution_count": 3,
             "outputs": [{"output_type": "execute_result", "data": {"text/plain": "2"}}]},
        ],
        "metadata": {}, "nbformat": 4, "nbformat_minor": 5,
    }
    ruta = tmp_path / "con_salidas.ipynb"
    ruta.write_text(json.dumps(notebook), encoding="utf-8")
    assert celdas_con_salidas(ruta) == [2]
