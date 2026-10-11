"""Caracterizacion de la mejora de coordenadas por barrio (sin red)."""
import pandas as pd

from georef.geocodificacion import rellenar_por_barrio
from conftest import CENTROIDE_MEDELLIN, resultado


def _df(filas):
    """filas: lista de (latitud, longitud, complemento)."""
    return pd.DataFrame(
        {
            "Latitud": [f[0] for f in filas],
            "Longitud": [f[1] for f in filas],
            "Complemento": [f[2] for f in filas],
        }
    )


def test_reconsulta_centroide_con_barrio_de_la_lista(geocodificador):
    geocodificador.respuestas = {"CALASANZ, MEDELLIN": resultado(6.26, -75.6)}
    salida = rellenar_por_barrio(
        _df([(*CENTROIDE_MEDELLIN, "CASA 2 CALASANZ -*- URBA#")]), api_key="llave-falsa"
    )
    assert (salida.loc[0, "Latitud"], salida.loc[0, "Longitud"]) == (6.26, -75.6)
    assert geocodificador.consultas == ["CALASANZ, MEDELLIN"]
    assert geocodificador.llaves == ["llave-falsa"]


def test_ignora_barrio_fuera_de_la_lista(geocodificador):
    # LAURELES no figura en la lista fija de barrios.
    salida = rellenar_por_barrio(_df([(*CENTROIDE_MEDELLIN, "LAURELES -*- URBA#")]), api_key="k")
    assert geocodificador.consultas == []
    assert (salida.loc[0, "Latitud"], salida.loc[0, "Longitud"]) == CENTROIDE_MEDELLIN


def test_ignora_filas_fuera_del_centroide(geocodificador):
    rellenar_por_barrio(_df([(6.2, -75.5, "CASA 2 CALASANZ -*- URBA#")]), api_key="k")
    assert geocodificador.consultas == []


def test_sin_resultado_conserva_coordenadas(geocodificador):
    salida = rellenar_por_barrio(_df([(*CENTROIDE_MEDELLIN, "CALASANZ")]), api_key="k")
    assert geocodificador.consultas == ["CALASANZ, MEDELLIN"]
    assert (salida.loc[0, "Latitud"], salida.loc[0, "Longitud"]) == CENTROIDE_MEDELLIN


def test_tope_n_limita_llamadas(geocodificador):
    geocodificador.por_defecto = resultado(6.26, -75.6)
    filas = [(*CENTROIDE_MEDELLIN, "CALASANZ"), (*CENTROIDE_MEDELLIN, "CALASANZ")]
    salida = rellenar_por_barrio(_df(filas), api_key="k", n=1)
    assert len(geocodificador.consultas) == 1
    assert salida["Latitud"].tolist() == [6.26, CENTROIDE_MEDELLIN[0]]
