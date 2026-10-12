"""Etapas del proceso: separación por área (specs/areas-geograficas), columnas y municipios
configurables (specs/configuracion) y lectura de coordenadas por su nombre nuevo."""
from pathlib import Path

import pandas as pd
import pytest

from conftest import escribir_configuracion, resultado
from georef import archivos, etapas
from georef.config import cargar_configuracion

COORDENADAS = Path("coordenadas") / "coordenadas_area_metropolitana.xlsx"
COORDENADAS_ANTIGUO = Path("coordenadas") / "coordenadas.xlsx"


@pytest.fixture
def trabajo(directorio_trabajo):
    archivos.estructura_programa()
    return directorio_trabajo


@pytest.fixture
def llave_falsa(monkeypatch):
    monkeypatch.setenv("OPENCAGE_API_KEY", "llave-falsa")


def leer(ruta):
    return pd.read_excel(ruta, index_col=0)


def test_separacion_por_municipio(trabajo, configuracion):
    etapas.estandarizar(configuracion)
    fuera = leer(archivos.RUTA_FUERA_AM)
    assert list(fuera.index) == [6, 7]
    assert set(fuera["Ciudad Residencia"]) == {"RIONEGRO - ANTIOQUIA", "MONTERIA - CORDOBA"}
    assert list(leer(archivos.RUTA_TOTAL_AM).index) == [0, 1, 2, 3, 4, 5, 8, 9]


def test_registro_sin_municipio_queda_fuera(tmp_path, monkeypatch, configuracion):
    monkeypatch.chdir(tmp_path)
    archivos.estructura_programa()
    pd.DataFrame(
        {"Ciudad Residencia": ["MEDELLIN - ANTIOQUIA", None], "Direccion de residencia": ["CL 1 2 3", "CL 4 5 6"]}
    ).to_excel(Path("original") / "base.xlsx", index=False)
    etapas.estandarizar(configuracion)
    assert list(leer(archivos.RUTA_FUERA_AM).index) == [1]


def test_nuevo_municipio_en_la_configuracion(trabajo):
    ruta = escribir_configuracion(
        trabajo / "otra.toml", ('"BARBOSA - ANTIOQUIA",', '"BARBOSA - ANTIOQUIA",\n    "RIONEGRO - ANTIOQUIA",')
    )
    etapas.estandarizar(cargar_configuracion(ruta))
    assert list(leer(archivos.RUTA_FUERA_AM).index) == [7]
    assert 6 in leer(archivos.RUTA_TOTAL_AM).index


def test_columna_ausente_no_escribe_archivos(tmp_path, monkeypatch, configuracion):
    monkeypatch.chdir(tmp_path)
    archivos.estructura_programa()
    pd.DataFrame({"Direccion de residencia": ["CL 1 2 3"]}).to_excel(Path("original") / "base.xlsx", index=False)
    with pytest.raises(SystemExit) as salida:
        etapas.estandarizar(configuracion)
    assert "'Ciudad Residencia'" in salida.value.code
    assert list(Path("estandarizado").iterdir()) == []


def test_registros_de_fuera_no_se_geocodifican(trabajo, configuracion, llave_falsa, geocodificador):
    etapas.estandarizar(configuracion)
    geocodificador.por_defecto = resultado(6.2, -75.5)
    etapas.geocodificar(configuracion)
    assert geocodificador.consultas
    assert not any("RIONEGRO" in c or "MONTERIA" in c for c in geocodificador.consultas)
    assert list(leer(COORDENADAS).index) == [0, 1, 2, 3, 8, 9]


def test_conversion_reanudada_desde_el_archivo_nuevo(trabajo, configuracion, llave_falsa, geocodificador):
    pd.DataFrame(
        {
            "Ciudad Residencia": ["MEDELLIN - ANTIOQUIA"] * 2,
            "Direccion de residencia": ["CL 1 #2-3", "CL 4 #5-6"],
            "Latitud": [6.1, None],
            "Longitud": [-75.1, None],
        }
    ).to_excel(COORDENADAS)
    geocodificador.por_defecto = resultado(6.2, -75.5)
    etapas.geocodificar(configuracion)
    assert geocodificador.consultas == ["CL 4 #5-6, MEDELLIN, ANTIOQUIA, Antioquia, Colombia"]
    assert leer(COORDENADAS)["Latitud"].tolist() == [6.1, 6.2]


@pytest.mark.parametrize("etapa", ["geocodificar", "mejorar", "generar_mapas"])
def test_nombre_antiguo_detiene_la_etapa(trabajo, configuracion, llave_falsa, geocodificador, etapa):
    pd.DataFrame({"Latitud": [6.2], "Longitud": [-75.5], "Complemento": ["X"]}).to_excel(COORDENADAS_ANTIGUO)
    contenido = COORDENADAS_ANTIGUO.read_bytes()
    with pytest.raises(SystemExit) as salida:
        getattr(etapas, etapa)(configuracion)
    assert "coordenadas/coordenadas.xlsx" in salida.value.code
    assert geocodificador.consultas == []
    assert not COORDENADAS.exists()
    assert COORDENADAS_ANTIGUO.read_bytes() == contenido
    assert not (Path("mapas") / "area_metropolitana" / "individual.html").exists()


def test_mapas_sin_coordenadas(trabajo, configuracion):
    with pytest.raises(SystemExit) as salida:
        etapas.generar_mapas(configuracion)
    assert salida.value.code == etapas.MENSAJE_SIN_COORDENADAS


def test_mapas_del_area_metropolitana(trabajo, configuracion):
    pd.DataFrame({"Latitud": [6.2], "Longitud": [-75.5]}).to_excel(COORDENADAS)
    etapas.generar_mapas(configuracion)
    assert (Path("mapas") / "area_metropolitana" / "individual.html").exists()
    assert (Path("mapas") / "area_metropolitana" / "filtrados" / "clusters_filtrados.html").exists()


def test_archivo_de_referencia_inexistente(trabajo):
    ruta = escribir_configuracion(
        trabajo / "otra.toml", ('geojson = "data/limite_barrio_vereda_cata.geojson"', 'geojson = "no_existe.geojson"')
    )
    with pytest.raises(SystemExit) as salida:
        etapas.estandarizar(cargar_configuracion(ruta))
    assert salida.value.code not in (None, 0)
    assert "no_existe.geojson" in salida.value.code
    assert list(Path("estandarizado").iterdir()) == []


def test_normalizacion_de_un_registro_de_fuera(trabajo, configuracion):
    etapas.estandarizar(configuracion)
    monteria = leer(archivos.RUTA_FUERA_AM).loc[7]
    assert monteria["Direccion de residencia"] == "CR 5 #10-20"
    assert monteria["Complemento"] == "CENTRO"
    assert monteria[["Barrio", "Codigo barrio", "Comuna"]].isna().all()


def test_columnas_normalizadas_en_los_cuatro_archivos(trabajo, configuracion):
    etapas.estandarizar(configuracion)
    for ruta in (archivos.RUTA_TOTAL_AM, archivos.RUTA_PRINCIPALES_AM, archivos.RUTA_ESPECIALES_AM, archivos.RUTA_FUERA_AM):
        columnas = list(leer(ruta).columns)
        posicion = columnas.index("Direccion de residencia")
        assert columnas[posicion:posicion + 6] == [
            "Direccion de residencia", "Complemento", "Barrio", "Codigo barrio", "Comuna", "Zona"
        ]


def test_codigo_barrio_se_lee_como_texto(trabajo, configuracion):
    etapas.estandarizar(configuracion)
    # Buenos Aires (fila 1) tiene el codigo 0907: con dtype=str se conserva el cero.
    principales = pd.read_excel(archivos.RUTA_PRINCIPALES_AM, index_col=0, dtype={"Codigo barrio": str})
    assert principales.loc[1, "Codigo barrio"] == "0907"
    assert pd.read_excel(archivos.RUTA_PRINCIPALES_AM, index_col=0).loc[1, "Codigo barrio"] == 907
