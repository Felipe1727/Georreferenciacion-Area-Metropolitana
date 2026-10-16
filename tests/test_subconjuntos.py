"""Extraccion de subconjuntos (specs/areas-geograficas y specs/archivos-de-salida)."""
import os
from pathlib import Path

import pandas as pd
import pytest

from conftest import escribir_configuracion
from georef import archivos, etapas
from georef.config import cargar_configuracion

COORDENADAS_AM = Path("coordenadas") / "coordenadas_area_metropolitana.xlsx"
COORDENADAS_MEDELLIN = Path("coordenadas") / "coordenadas_medellin.xlsx"
MAPAS_MEDELLIN = [Path("mapas") / "medellin" / "mapa.html"]


@pytest.fixture
def trabajo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    archivos.estructura_programa()
    return tmp_path


@pytest.fixture
def coordenadas_am(trabajo):
    df = pd.DataFrame(
        {
            "CODIGO": ["E1", "E2", "E3"],
            "Ciudad Residencia": ["MEDELLIN - ANTIOQUIA", "BELLO - ANTIOQUIA", "MEDELLIN - ANTIOQUIA"],
            "Direccion de residencia": ["CL 1 #2-3", "CR 4 #5-6", "CL 7 #8-9"],
            "Latitud": [6.2, 6.33, 6.25],
            "Longitud": [-75.5, -75.55, -75.6],
            "Nivel ubicacion": ["BARRIO", "MUNICIPIO", "DIRECCION"],
        },
        index=[3, 10, 42],
    )
    df.to_excel(COORDENADAS_AM)
    return df


def test_subconjunto_de_medellin(coordenadas_am, configuracion):
    etapas.extraer_subconjunto(configuracion, "medellin")
    medellin = pd.read_excel(COORDENADAS_MEDELLIN, index_col=0)
    assert list(medellin.index) == [3, 42]
    assert list(medellin.columns) == list(coordenadas_am.columns)
    assert set(medellin["Ciudad Residencia"]) == {"MEDELLIN - ANTIOQUIA"}


def test_mapas_del_subconjunto(coordenadas_am, configuracion):
    etapas.extraer_subconjunto(configuracion, "medellin")
    assert all(ruta.exists() for ruta in MAPAS_MEDELLIN)
    assert MAPAS_MEDELLIN[0].read_text().count("L.divIcon(") == 2


def test_sin_llave_ni_llamadas_al_proveedor(coordenadas_am, configuracion):
    # La fixture automatica ya prohibe OpenCageGeocode y elimina OPENCAGE_API_KEY.
    assert "OPENCAGE_API_KEY" not in os.environ
    etapas.extraer_subconjunto(configuracion, "medellin")
    assert COORDENADAS_MEDELLIN.exists()


def test_el_archivo_del_area_no_cambia(coordenadas_am, configuracion):
    contenido = COORDENADAS_AM.read_bytes()
    etapas.extraer_subconjunto(configuracion, "medellin")
    assert COORDENADAS_AM.read_bytes() == contenido


def test_subconjunto_definido_solo_en_la_configuracion(coordenadas_am, trabajo):
    ruta = escribir_configuracion(
        trabajo / "otra.toml", ("[columnas]", '[subconjuntos.norte]\nmunicipios = ["BELLO - ANTIOQUIA"]\n\n[columnas]')
    )
    etapas.extraer_subconjunto(cargar_configuracion(ruta), "norte")
    assert list(pd.read_excel(Path("coordenadas") / "coordenadas_norte.xlsx", index_col=0).index) == [10]
    assert (Path("mapas") / "norte" / "mapa.html").exists()


def test_subconjunto_desconocido(coordenadas_am, configuracion):
    with pytest.raises(SystemExit) as salida:
        etapas.extraer_subconjunto(configuracion, "norte")
    assert salida.value.code not in (None, 0)
    assert "'norte'" in salida.value.code and "medellin" in salida.value.code
    assert not (Path("mapas") / "norte").exists()


def test_sin_coordenadas_del_area(trabajo, configuracion):
    with pytest.raises(SystemExit) as salida:
        etapas.extraer_subconjunto(configuracion, "medellin")
    assert salida.value.code == etapas.MENSAJE_SIN_COORDENADAS
    assert not COORDENADAS_MEDELLIN.exists()


def test_subconjunto_sin_registros(trabajo, configuracion):
    pd.DataFrame(
        {"Ciudad Residencia": ["BELLO - ANTIOQUIA"], "Latitud": [6.33], "Longitud": [-75.55],
         "Nivel ubicacion": ["MUNICIPIO"]}
    ).to_excel(COORDENADAS_AM)
    with pytest.raises(SystemExit) as salida:
        etapas.extraer_subconjunto(configuracion, "medellin")
    assert "Ningún registro" in salida.value.code
    assert not COORDENADAS_MEDELLIN.exists()
    assert not (Path("mapas") / "medellin").exists()


def test_archivo_antiguo(trabajo, configuracion):
    pd.DataFrame({"Ciudad Residencia": ["MEDELLIN - ANTIOQUIA"]}).to_excel(Path("coordenadas") / "coordenadas.xlsx")
    with pytest.raises(SystemExit) as salida:
        etapas.extraer_subconjunto(configuracion, "medellin")
    assert "coordenadas/coordenadas.xlsx" in salida.value.code
    assert not COORDENADAS_MEDELLIN.exists()


def test_coordenadas_sin_nivel(trabajo, configuracion):
    pd.DataFrame({"Ciudad Residencia": ["MEDELLIN - ANTIOQUIA"], "Latitud": [6.2], "Longitud": [-75.5]}).to_excel(
        COORDENADAS_AM)
    with pytest.raises(SystemExit) as salida:
        etapas.extraer_subconjunto(configuracion, "medellin")
    assert salida.value.code == etapas.MENSAJE_SIN_NIVEL
    assert not COORDENADAS_MEDELLIN.exists() and not any(ruta.exists() for ruta in MAPAS_MEDELLIN)


NORTE = ("[columnas]", '[subconjuntos.norte]\nmunicipios = ["BELLO - ANTIOQUIA"]\n\n[columnas]')


def test_mapas_del_subconjunto_con_poligonos(coordenadas_am, configuracion):
    etapas.extraer_subconjunto(configuracion, "medellin")
    assert "Contorno de comunas" in MAPAS_MEDELLIN[0].read_text(encoding="utf-8")


def test_separados_del_subconjunto(coordenadas_am, configuracion):
    etapas.extraer_subconjunto(configuracion, "medellin", ["puntos"])
    assert (Path("mapas") / "medellin" / "separados" / "puntos.html").exists()


def test_subconjunto_sin_medellin_sin_poligonos(coordenadas_am, trabajo):
    etapas.extraer_subconjunto(cargar_configuracion(escribir_configuracion(trabajo / "otra.toml", NORTE)), "norte")
    assert "Contorno de comunas" not in (Path("mapas") / "norte" / "mapa.html").read_text(encoding="utf-8")


def test_vista_coloreada_pedida_para_otra_area(coordenadas_am, trabajo):
    configuracion = cargar_configuracion(escribir_configuracion(trabajo / "otra.toml", NORTE))
    with pytest.raises(SystemExit) as salida:
        etapas.extraer_subconjunto(configuracion, "norte", ["barrios_cantidad"])
    assert "barrios_cantidad" in salida.value.code and "MEDELLIN - ANTIOQUIA" in salida.value.code
    assert not (Path("coordenadas") / "coordenadas_norte.xlsx").exists()
    assert not (Path("mapas") / "norte").exists()


def test_todos_en_un_area_sin_poligonos(coordenadas_am, trabajo, capsys):
    configuracion = cargar_configuracion(escribir_configuracion(trabajo / "otra.toml", NORTE))
    etapas.extraer_subconjunto(configuracion, "norte", ["todos"])
    separados = Path("mapas") / "norte" / "separados"
    assert sorted(p.name for p in separados.iterdir()) == ["clusters.html", "puntos.html"]
    assert "no se generaron" in capsys.readouterr().out
