"""Escenarios de specs/consultas-proveedor: consulta unica de los puntos de los municipios."""
from pathlib import Path

import pytest

from conftest import resultado_api, seccion_puntos
from georef.config import cargar_configuracion

CONFIGURACION = Path("config") / "georef.toml"


@pytest.fixture
def llave_falsa(monkeypatch):
    monkeypatch.setenv("OPENCAGE_API_KEY", "llave-falsa")


@pytest.fixture
def municipios(directorio_trabajo):
    return cargar_configuracion(CONFIGURACION).area_metropolitana


def consulta(municipio):
    return municipio.replace(" - ", ", ") + ", Colombia"


def responder_todos(cliente, municipios):
    for i, municipio in enumerate(municipios):
        cliente.respuestas[consulta(municipio)] = [resultado_api(6.1 + i / 100, -75.6, tipo="city", confianza=7,
                                                                 texto=f"{municipio} (sintetico)")]


def test_peticion_de_un_municipio(municipios, ejecutar_main, llave_falsa, cliente):
    ejecutar_main(argv=("consultar-municipios",))
    assert "BELLO, ANTIOQUIA, Colombia" in cliente.consultas
    assert all("bounds" not in parametros for _, parametros in cliente.llamadas)
    assert all(parametros["countrycode"] == "co" and parametros["limit"] == 1 for _, parametros in cliente.llamadas)


def test_primera_consulta(municipios, ejecutar_main, llave_falsa, cliente, capsys):
    original = CONFIGURACION.read_text(encoding="utf-8")
    responder_todos(cliente, municipios)
    ejecutar_main(argv=("consultar-municipios",))
    assert len(cliente.consultas) == 10
    nuevo = CONFIGURACION.read_text(encoding="utf-8")
    assert nuevo.startswith(original)  # el resto del archivo no cambia
    puntos = cargar_configuracion(CONFIGURACION).puntos_municipios
    assert set(puntos) == set(municipios)
    assert puntos["MEDELLIN - ANTIOQUIA"].latitud == 6.1 and puntos["MEDELLIN - ANTIOQUIA"].fuente == "OpenCage"
    salida = capsys.readouterr().out
    assert "BELLO - ANTIOQUIA (sintetico)" in salida and "tipo city" in salida  # para revisarlos


def test_todos_los_puntos_presentes(con_puntos, ejecutar_main, cliente, capsys):
    original = CONFIGURACION.read_text(encoding="utf-8")
    ejecutar_main(argv=("consultar-municipios",))  # sin llave: no hace falta
    assert cliente.consultas == []
    assert "ya tienen punto" in capsys.readouterr().out
    assert CONFIGURACION.read_text(encoding="utf-8") == original


def test_municipio_sin_resultado(municipios, ejecutar_main, llave_falsa, cliente, capsys):
    responder_todos(cliente, municipios)
    del cliente.respuestas[consulta("CALDAS - ANTIOQUIA")]
    ejecutar_main(argv=("consultar-municipios",))
    puntos = cargar_configuracion(CONFIGURACION).puntos_municipios
    assert "CALDAS - ANTIOQUIA" not in puntos and len(puntos) == 9
    salida = capsys.readouterr().out
    assert "a mano" in salida and "CALDAS - ANTIOQUIA" in salida.split("a mano")[1]


def test_seccion_ya_existente_con_un_municipio_nuevo(municipios, ejecutar_main, llave_falsa, cliente, capsys):
    with open(CONFIGURACION, "a", encoding="utf-8") as archivo:
        archivo.write(seccion_puntos([m for m in municipios if m != "BARBOSA - ANTIOQUIA"]))
    original = CONFIGURACION.read_text(encoding="utf-8")
    responder_todos(cliente, municipios)
    ejecutar_main(argv=("consultar-municipios",))
    assert cliente.consultas == ["BARBOSA, ANTIOQUIA, Colombia"]
    assert CONFIGURACION.read_text(encoding="utf-8") == original
    assert '"BARBOSA - ANTIOQUIA" = { latitud = ' in capsys.readouterr().out


def test_resultado_no_valido_restaura_el_archivo(municipios, ejecutar_main, llave_falsa, cliente):
    original = CONFIGURACION.read_text(encoding="utf-8")
    responder_todos(cliente, municipios)
    cliente.respuestas[consulta("BELLO - ANTIOQUIA")] = [resultado_api(95, -75.5)]  # latitud imposible
    with pytest.raises(SystemExit) as salida:
        ejecutar_main(argv=("consultar-municipios",))
    assert "no se guardaron" in salida.value.code
    assert CONFIGURACION.read_text(encoding="utf-8") == original


def test_sin_llave(municipios, ejecutar_main, cliente):
    original = CONFIGURACION.read_text(encoding="utf-8")
    with pytest.raises(SystemExit) as salida:
        ejecutar_main(argv=("consultar-municipios",))
    assert "OPENCAGE_API_KEY" in salida.value.code
    assert cliente.consultas == [] and CONFIGURACION.read_text(encoding="utf-8") == original


def test_registro_de_las_peticiones(municipios, ejecutar_main, llave_falsa, cliente):
    responder_todos(cliente, municipios)
    ejecutar_main(argv=("consultar-municipios",))
    registro = (Path("coordenadas") / "registro_consultas.csv").read_text(encoding="utf-8")
    assert registro.count(",municipios,") == 10
    assert not (Path("coordenadas") / "cache_consultas.csv").exists()
