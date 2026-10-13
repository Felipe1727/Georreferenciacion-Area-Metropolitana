"""Escenarios de specs/consultas-proveedor: diagnostico de formatos de consulta (comparar-consultas)."""
from pathlib import Path

import pytest

from conftest import desplazado, resultado_api
from georef.geografia import Poligonos

COORDENADAS = Path("coordenadas") / "coordenadas_area_metropolitana.xlsx"
GEOJSON = Path(__file__).resolve().parent.parent / "data" / "limite_barrio_vereda_cata.geojson"
# Las tres direcciones de Medellin de los datos sinteticos con barrio declarado con codigo.
DIRECCIONES = ("CL 10 #20-30", "CL 45S #12-15", "TV 32B #75-20")


@pytest.fixture
def llave_falsa(monkeypatch):
    monkeypatch.setenv("OPENCAGE_API_KEY", "llave-falsa")


@pytest.fixture
def estandarizado(directorio_trabajo, ejecutar_main):
    ejecutar_main(argv=("estandarizar",))


def test_muestra_limitada(estandarizado, ejecutar_main, llave_falsa, cliente):
    ejecutar_main(argv=("comparar-consultas", "--muestra", "2"))
    assert len(cliente.consultas) == 4  # 2 direcciones x 2 formatos
    assert sum(c.startswith(("CL ", "TV ")) for c in cliente.consultas) == 2
    assert sum(c.startswith(("Calle ", "Transversal ")) for c in cliente.consultas) == 2


def test_muestra_de_50_con_menos_direcciones(estandarizado, ejecutar_main, llave_falsa, cliente):
    ejecutar_main(argv=("comparar-consultas", "--muestra", "50"))
    assert len(cliente.consultas) == 2 * len(DIRECCIONES)
    assert all("bounds" in parametros for _, parametros in cliente.llamadas)


def test_muestra_repetida(estandarizado, ejecutar_main, llave_falsa, cliente):
    ejecutar_main(argv=("comparar-consultas", "--muestra", "2"))
    primeras = list(cliente.consultas)
    ejecutar_main(argv=("comparar-consultas", "--muestra", "2"))
    assert cliente.consultas == primeras  # misma muestra, todo desde la cache


def test_informe_del_diagnostico(estandarizado, ejecutar_main, llave_falsa, cliente, capsys):
    poligonos = Poligonos.cargar(GEOJSON)
    laureles = [c for c in poligonos.codigos if poligonos.nombre_barrio(c)[0] == "Laureles"][0]
    # Abreviado: en el barrio declarado; expandido: a 2 km.
    cliente.respuestas["CL 10 #20-30, MEDELLIN, ANTIOQUIA, Colombia"] = [
        resultado_api(*poligonos.punto_barrio(laureles), tipo="building", confianza=9)]
    cliente.respuestas["Calle 10 # 20-30, MEDELLIN, ANTIOQUIA, Colombia"] = [
        resultado_api(*desplazado(poligonos, poligonos.geometria_barrio(laureles), 2000), tipo="road", confianza=8)]
    ejecutar_main(argv=("comparar-consultas", "--muestra", "50"))
    salida = capsys.readouterr().out
    abreviado, expandido = salida.split("Formato 'abreviado':")[1].split("Formato 'expandido':")
    assert "Con resultado: 1 (33.3 %)" in abreviado and "Dentro del barrio declarado: 1 (100.0 %)" in abreviado
    assert "Tipos de resultado: building 1" in abreviado and "Confidence mediana: 9" in abreviado
    assert "Aceptadas con la configuración actual: 1 (100.0 %)" in abreviado
    assert "A 250 m o menos del barrio declarado: 0 (0.0 %)" in expandido
    assert "Distancia mediana al barrio declarado: 2000 m" in expandido
    # Ninguna direccion ni barrio de la muestra aparece en la salida.
    assert not any(d in salida for d in DIRECCIONES + ("Calle 10", "LAURELES", "Laureles", "CALASANZ"))


def test_avance_del_diagnostico(estandarizado, ejecutar_main, llave_falsa, cliente, capsys):
    ejecutar_main(argv=("comparar-consultas", "--muestra", "50"))
    avance = capsys.readouterr().err
    assert "Dirección 3 de 3 · peticiones a OpenCage: 4" in avance
    assert not any(d in avance for d in DIRECCIONES)


def test_no_escribe_coordenadas(estandarizado, ejecutar_main, llave_falsa, cliente):
    ejecutar_main(argv=("comparar-consultas", "--muestra", "2"))
    assert not COORDENADAS.exists()


def test_sin_estandarizar(directorio_trabajo, ejecutar_main, llave_falsa, cliente):
    with pytest.raises(SystemExit) as salida:
        ejecutar_main(argv=("comparar-consultas", "--muestra", "2"))
    assert "estandarización" in salida.value.code
    assert cliente.consultas == []
