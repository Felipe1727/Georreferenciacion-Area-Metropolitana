"""Escenarios de specs/archivos-de-salida: estructura, archivo de entrada y nombre antiguo de coordenadas."""
from pathlib import Path

import pandas as pd
import pytest

from georef import archivos
from georef.config import Columnas

COORDENADAS_NUEVO = Path("coordenadas") / "coordenadas_area_metropolitana.xlsx"
COORDENADAS_ANTIGUO = Path("coordenadas") / "coordenadas.xlsx"


@pytest.fixture
def en_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def original(en_tmp):
    carpeta = en_tmp / "original"
    carpeta.mkdir()
    return carpeta


def excel(ruta, filas=1):
    pd.DataFrame({"Ciudad Residencia": ["MEDELLIN - ANTIOQUIA"] * filas}).to_excel(ruta, index=False)


def test_nombres_por_area():
    assert archivos.ruta_coordenadas("area_metropolitana") == COORDENADAS_NUEVO
    assert archivos.ruta_coordenadas("medellin") == Path("coordenadas") / "coordenadas_medellin.xlsx"
    assert archivos.carpeta_mapas("medellin") == Path("mapas") / "medellin"
    assert archivos.RUTA_PRINCIPALES_AM == Path("estandarizado") / "principales_area_metropolitana.xlsx"


def test_estructura_en_directorio_limpio(en_tmp):
    archivos.estructura_programa()
    for directorio in ("original", "estandarizado", "coordenadas", "mapas/area_metropolitana"):
        assert Path(directorio).is_dir()
    assert not Path("llave").exists()
    assert not Path("mapas/area_metropolitana/filtrados").exists()


@pytest.mark.parametrize("bloqueo", [".~lock.base.xlsx#", "~$base.xlsx", ".oculto"])
def test_archivos_de_bloqueo_se_ignoran(original, bloqueo):
    excel(original / "base.xlsx", filas=3)
    (original / bloqueo).write_text("bloqueo")
    (original / "subcarpeta").mkdir()
    assert len(archivos.leer_archivo_original()) == 3


def test_mas_de_un_archivo(original):
    excel(original / "a.xlsx")
    excel(original / "b.xlsx")
    with pytest.raises(SystemExit) as salida:
        archivos.leer_archivo_original()
    assert "más de un archivo" in salida.value.code


def test_ningun_archivo_visible(original):
    (original / ".~lock.base.xlsx#").write_text("bloqueo")
    with pytest.raises(SystemExit) as salida:
        archivos.leer_archivo_original()
    assert "No hay ningún archivo en la carpeta 'original'" in salida.value.code


def test_dialogo_cancelado_termina_con_mensaje(original, monkeypatch):
    abiertos = []

    class TkFalso:
        def withdraw(self):
            abiertos.append(True)

    monkeypatch.setattr(archivos.tk, "Tk", TkFalso)
    monkeypatch.setattr(archivos.filedialog, "askopenfilename", lambda **kwargs: "")
    (original / ".~lock.base.xlsx#").write_text("bloqueo")
    archivos.verificar_y_copiar_archivo_original()
    assert abiertos == [True]
    with pytest.raises(SystemExit) as salida:
        archivos.leer_archivo_original()
    assert "original" in salida.value.code


def test_columna_configurada_ausente():
    df = pd.DataFrame({"Direccion de residencia": ["CL 1 2 3"]})
    with pytest.raises(SystemExit) as salida:
        archivos.verificar_columnas(df, Columnas(ciudad="Ciudad Residencia", direccion="Direccion de residencia"))
    assert "'Ciudad Residencia'" in salida.value.code


def test_solo_archivo_de_coordenadas_antiguo(en_tmp):
    COORDENADAS_ANTIGUO.parent.mkdir()
    excel(COORDENADAS_ANTIGUO)
    with pytest.raises(SystemExit) as salida:
        archivos.verificar_nombre_antiguo_coordenadas()
    assert salida.value.code not in (None, 0)
    assert "coordenadas/coordenadas.xlsx" in salida.value.code
    assert "coordenadas/coordenadas_area_metropolitana.xlsx" in salida.value.code


def test_los_dos_archivos_de_coordenadas(en_tmp):
    COORDENADAS_ANTIGUO.parent.mkdir()
    excel(COORDENADAS_ANTIGUO)
    excel(COORDENADAS_NUEVO)
    contenido = COORDENADAS_ANTIGUO.read_bytes()
    archivos.verificar_nombre_antiguo_coordenadas()
    assert COORDENADAS_ANTIGUO.read_bytes() == contenido
