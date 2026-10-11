"""Pruebas de humo en subproceso: `python -m georef` y el envoltorio `python main.py`."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ_REPO = Path(__file__).resolve().parent.parent
FORMAS = {
    "modulo": [sys.executable, "-m", "georef"],
    "main.py": [sys.executable, str(RAIZ_REPO / "main.py")],
}


def ejecutar(forma, argumentos, cwd, entrada=None):
    entorno = {**os.environ, "PYTHONPATH": str(RAIZ_REPO)}
    entorno.pop("OPENCAGE_API_KEY", None)
    return subprocess.run(FORMAS[forma] + argumentos, cwd=cwd, input=entrada, capture_output=True,
                          text=True, env=entorno, timeout=120)


@pytest.mark.parametrize("forma", FORMAS)
def test_ayuda(forma):
    resultado = ejecutar(forma, ["--help"], cwd=RAIZ_REPO)
    assert resultado.returncode == 0
    for subcomando in ("estandarizar", "geocodificar", "mejorar", "mapas", "subconjunto"):
        assert subcomando in resultado.stdout


@pytest.mark.parametrize("forma", FORMAS)
def test_menu_sin_argumentos(forma, tmp_path):
    # Sin archivo de coordenadas, la opcion 4 termina con un mensaje (sin tocar la API ni original/).
    (tmp_path / "config").mkdir()
    shutil.copy(RAIZ_REPO / "config" / "georef.toml", tmp_path / "config" / "georef.toml")
    resultado = ejecutar(forma, [], cwd=tmp_path, entrada="4\n")
    assert "5. Extracción de un subconjunto" in resultado.stdout
    assert resultado.returncode == 1
    assert "Necesitas primero procesar las coordenadas" in resultado.stderr
