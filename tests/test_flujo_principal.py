"""Caracterizacion de extremo a extremo de main() en un directorio temporal."""
from pathlib import Path

import pandas as pd
import pytest

ESTANDARIZADO = Path("estandarizado")
COORDENADAS = Path("coordenadas") / "coordenadas_area_metropolitana.xlsx"
MAPAS = Path("mapas") / "area_metropolitana"
ARCHIVOS_ESTANDARIZADOS = {
    "total": ESTANDARIZADO / "total_area_metropolitana.xlsx",
    "principales": ESTANDARIZADO / "principales_area_metropolitana.xlsx",
    "especiales": ESTANDARIZADO / "especiales_area_metropolitana.xlsx",
    "fuera": ESTANDARIZADO / "fuera_area_metropolitana.xlsx",
}


@pytest.fixture
def llave_falsa(monkeypatch):
    monkeypatch.setenv("OPENCAGE_API_KEY", "llave-falsa")


def test_opcion_1_genera_archivos_estandarizados(directorio_trabajo, ejecutar_main):
    ejecutar_main(1)
    filas = {n: len(pd.read_excel(r, index_col=0)) for n, r in ARCHIVOS_ESTANDARIZADOS.items()}
    assert filas == {"total": 8, "principales": 6, "especiales": 2, "fuera": 2}
    principales = pd.read_excel(ARCHIVOS_ESTANDARIZADOS["principales"], index_col=0)
    assert list(principales.index) == [0, 1, 2, 3, 8, 9]
    assert principales.loc[0, "Direccion de residencia"] == "CL 10 #20-30"
    assert (principales.loc[0, "Barrio"], principales.loc[0, "Zona"]) == ("Laureles", "URBANO")
    generados = sorted(p.name for p in ESTANDARIZADO.iterdir())
    assert generados == sorted(r.name for r in ARCHIVOS_ESTANDARIZADOS.values())
    assert all(nombre.isascii() for nombre in generados)


def test_ubicacion_con_solo_archivos_de_nombre_antiguo_termina(directorio_trabajo, ejecutar_main, llave_falsa,
                                                                cliente):
    ESTANDARIZADO.mkdir(exist_ok=True)
    pd.DataFrame({"Direccion de residencia": ["CL 10 #20-30"]}).to_excel(
        ESTANDARIZADO / "principales_área_metropolitana.xlsx"
    )
    with pytest.raises(SystemExit) as salida:
        ejecutar_main(2)
    assert "principales_area_metropolitana.xlsx" in salida.value.code
    assert "estandarización" in salida.value.code
    assert cliente.consultas == []
    assert not COORDENADAS.exists()


def test_opcion_2_ubica_el_area_metropolitana(con_puntos, ejecutar_main, llave_falsa, cliente):
    ejecutar_main(1)
    ejecutar_main(2)
    coordenadas = pd.read_excel(COORDENADAS, index_col=0)
    assert list(coordenadas.index) == [0, 1, 2, 3, 4, 5, 8, 9]
    assert coordenadas[["Latitud", "Longitud", "Nivel ubicacion"]].notna().all().all()
    assert cliente.llaves == ["llave-falsa"]


def test_opcion_3_sin_coordenadas_termina(directorio_trabajo, ejecutar_main):
    with pytest.raises(SystemExit) as salida:
        ejecutar_main(3)
    assert salida.value.code == "Error: Necesitas primero procesar las coordenadas."


def test_opcion_3_genera_mapas(directorio_trabajo, ejecutar_main):
    Path("coordenadas").mkdir(exist_ok=True)
    pd.DataFrame({"Latitud": [6.2], "Longitud": [-75.5], "Nivel ubicacion": ["BARRIO"]}).to_excel(COORDENADAS)
    ejecutar_main(3)
    assert (MAPAS / "individual.html").exists()
    assert (MAPAS / "filtrados" / "clusters_filtrados.html").exists()


def test_modo_c_ubica_con_llave_del_entorno(con_puntos, ejecutar_main, llave_falsa, cliente):
    ejecutar_main(1)
    ejecutar_main(argv=("c",))
    assert cliente.llaves == ["llave-falsa"]
    assert COORDENADAS.exists()
    assert not Path("llave").exists()


def test_modo_c_no_agrega_columna_unnamed(con_puntos, ejecutar_main, llave_falsa, cliente):
    ejecutar_main(1)
    ejecutar_main(argv=("c",))
    ejecutar_main(argv=("c",))
    assert not any(str(c).startswith("Unnamed") for c in pd.read_excel(COORDENADAS, index_col=0).columns)
