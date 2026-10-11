"""Caracterizacion de la geocodificacion de direcciones (sin red)."""
import pandas as pd
import pytest

from georef.geocodificacion import geocodificar_direcciones
from conftest import CENTROIDE_MEDELLIN, resultado

CIUDAD = "MEDELLIN - ANTIOQUIA"
CONSULTA_CIUDAD = "MEDELLIN, ANTIOQUIA"


def consulta(direccion):
    return f"{direccion}, MEDELLIN, ANTIOQUIA, Antioquia, Colombia"


@pytest.fixture
def geocodificar(configuracion):
    """geocodificar_direcciones con las columnas de la configuracion incluida."""
    return lambda df, **kwargs: geocodificar_direcciones(df, columnas=configuracion.columnas, **kwargs)


def _df(direcciones, **coordenadas):
    df = pd.DataFrame(
        {
            "Ciudad Residencia": [CIUDAD] * len(direcciones),
            "Direccion de residencia": direcciones,
            "Complemento": [f"COMP {i}" for i in range(len(direcciones))],
            "Estrato": list(range(len(direcciones))),
        }
    )
    for columna, valores in coordenadas.items():
        df[columna] = valores
    return df


def test_resultado_encontrado_asigna_coordenadas(geocodificador, geocodificar):
    geocodificador.respuestas = {consulta("CL 10 #20-30"): resultado(6.2, -75.5)}
    salida = geocodificar(_df(["CL 10 #20-30"]), api_key="llave-falsa")
    assert salida.loc[0, "Latitud"] == 6.2
    assert salida.loc[0, "Longitud"] == -75.5
    assert geocodificador.llaves == ["llave-falsa"]


def test_sin_resultado_usa_ciudad_con_dos_consultas_extra(geocodificador, geocodificar):
    geocodificador.respuestas = {CONSULTA_CIUDAD: resultado(*CENTROIDE_MEDELLIN)}
    salida = geocodificar(_df(["CR 1 #2-3"]), api_key="k")
    assert (salida.loc[0, "Latitud"], salida.loc[0, "Longitud"]) == CENTROIDE_MEDELLIN
    assert geocodificador.consultas == [consulta("CR 1 #2-3"), CONSULTA_CIUDAD, CONSULTA_CIUDAD]


def test_excepcion_deja_registro_vacio_y_continua(geocodificador, capsys, geocodificar):
    geocodificador.respuestas = {
        consulta("CL 5 #6-7"): RuntimeError("fallo"),
        consulta("CL 8 #9-10"): resultado(6.3, -75.6),
    }
    salida = geocodificar(_df(["CL 5 #6-7", "CL 8 #9-10"]), api_key="k")
    assert pd.isna(salida.loc[0, "Latitud"]) and pd.isna(salida.loc[0, "Longitud"])
    assert salida.loc[1, "Latitud"] == 6.3
    assert "Error al consultar idx=0: fallo" in capsys.readouterr().out


def test_tope_n_limita_registros_procesados(geocodificador, geocodificar):
    geocodificador.por_defecto = resultado(6.2, -75.5)
    salida = geocodificar(_df(["CL 1 #1-1", "CL 2 #2-2", "CL 3 #3-3"]), api_key="k", n=2)
    assert salida["Latitud"].notna().tolist() == [True, True, False]
    assert len(geocodificador.consultas) == 2


def test_excepcion_no_cuenta_para_el_tope(geocodificador, geocodificar):
    geocodificador.por_defecto = resultado(6.2, -75.5)
    geocodificador.respuestas = {consulta("CL 1 #1-1"): RuntimeError("fallo")}
    salida = geocodificar(_df(["CL 1 #1-1", "CL 2 #2-2", "CL 3 #3-3"]), api_key="k", n=1)
    assert salida["Latitud"].notna().tolist() == [False, True, False]


def test_inicia_en_primera_fila_sin_coordenadas(geocodificador, geocodificar):
    geocodificador.por_defecto = resultado(6.2, -75.5)
    df = _df(["CL 1 #1-1", "CL 2 #2-2"], Latitud=[6.1, None], Longitud=[-75.1, None])
    salida = geocodificar(df, api_key="k")
    assert geocodificador.consultas == [consulta("CL 2 #2-2")]
    assert salida.loc[0, "Latitud"] == 6.1


def test_reordena_columnas_tras_complemento(geocodificador, geocodificar):
    geocodificador.por_defecto = resultado(6.2, -75.5)
    salida = geocodificar(_df(["CL 1 #1-1"]), api_key="k")
    assert list(salida.columns) == [
        "Ciudad Residencia",
        "Direccion de residencia",
        "Complemento",
        "Latitud",
        "Longitud",
        "Estrato",
    ]


def test_todas_completas_no_consulta(geocodificador, capsys, geocodificar):
    df = _df(["CL 1 #1-1"], Latitud=[6.1], Longitud=[-75.1])
    salida = geocodificar(df, api_key="k")
    assert geocodificador.consultas == []
    assert salida.equals(df)
    assert "Todas las coordenadas ya están completas" in capsys.readouterr().out
