"""Indice de barrios y comunas (georef.referencia) con el GeoJSON y las tablas reales del repositorio."""
from pathlib import Path

import pytest

from georef.referencia import ErrorReferencia, IndiceLugares, normalizar

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"


@pytest.fixture(scope="module")
def indice():
    return IndiceLugares(DATA / "limite_barrio_vereda_cata.geojson", DATA / "alias_barrios.csv",
                         DATA / "alias_comunas.csv")


def reconocer(indice, texto, zona=None):
    return indice.reconocer(texto.split(), zona)


# Escenarios de "Resolucion de nombres de barrio repetidos" (referencia-barrios)

def test_repetido_con_zona_urbana(indice):
    assert indice.resolver("LA FLORIDA", "URBANO") == "1417"  # El Poblado, U


def test_repetido_con_zona_rural(indice):
    assert indice.resolver("LA FLORIDA", "RURAL") == "8002"  # San Antonio de Prado, R


def test_ambiguedad_que_la_zona_no_resuelve(indice):
    assert indice.resolver("SUBURBANO EL LLANO", "RURAL") is None


def test_repetido_sin_zona(indice):
    assert indice.resolver("LA FLORIDA", None) is None


def test_nombre_unico(indice):
    assert indice.resolver("LAURELES", "RURAL") == "1108"
    assert indice.resolver("AREA DE EXPANSION PAJARITO", "URBANO") is not None


# Reconocimiento al final del texto

def test_barrio_con_complemento_delante(indice):
    lugar = reconocer(indice, "CASA 2 CALASANZ", "URBANO")
    assert (lugar.inicio, lugar.fin, lugar.barrio, lugar.codigo, lugar.comuna) == (2, 3, "Calasanz", "1202", "LA AMERICA")


def test_alias(indice):
    lugar = reconocer(indice, "CALAZANS")
    assert (lugar.barrio, lugar.codigo) == ("Calasanz", "1202")


def test_sufijo_mas_largo(indice):
    lugar = reconocer(indice, "SAN ANTONIO DE PRADO", "RURAL")
    assert (lugar.inicio, lugar.barrio, lugar.codigo, lugar.comuna) == (0, "", "", "SAN ANTONIO DE PRADO")


def test_variante_de_comuna(indice):
    lugar = reconocer(indice, "TORRE 3 POBLADO", "URBANO")
    assert (lugar.inicio, lugar.barrio, lugar.comuna) == (2, "", "EL POBLADO")


def test_el_poblado_es_barrio(indice):
    lugar = reconocer(indice, "EL POBLADO")
    assert (lugar.barrio, lugar.codigo, lugar.comuna) == ("El Poblado", "1418", "EL POBLADO")


def test_el_rodeo_es_barrio_de_guayabal(indice):
    lugar = reconocer(indice, "EL RODEO")
    assert (lugar.barrio, lugar.comuna) == ("El Rodeo", "GUAYABAL")


def test_numeros_finales(indice):
    lugar = reconocer(indice, "APTO 301 FATIMA 4")
    assert (lugar.inicio, lugar.fin, lugar.barrio) == (2, 3, "Fátima")  # el 4 queda en [3:]


def test_nombre_oficial_que_termina_en_numero(indice):
    lugar = reconocer(indice, "ASOMADERA NO. 1")
    assert (lugar.inicio, lugar.fin, lugar.barrio, lugar.codigo) == (0, 3, "Asomadera No. 1", "0914")


def test_repetido_sin_zona_conserva_el_nombre(indice):
    lugar = reconocer(indice, "LA FLORIDA")
    assert (lugar.barrio, lugar.codigo, lugar.comuna) == ("La Florida", "", "")


def test_nombre_con_espacio_final_en_el_geojson(indice):
    assert reconocer(indice, "EL SALADO", "URBANO").barrio == "El Salado"


def test_puntuacion_y_tildes(indice):
    assert reconocer(indice, "CARLOS E. RESTREPO").barrio == "Carlos E. Restrepo"
    assert reconocer(indice, "BELÉN").barrio == "Belén"


def test_sin_reconocimiento(indice):
    assert reconocer(indice, "TORRE 2 SENDEROS DEL MONTE") is None
    assert reconocer(indice, "") is None


def test_normalizar():
    assert normalizar("Área de Expansión Pajarito") == "AREA DE EXPANSION PAJARITO"
    assert normalizar(None) == ""


def test_archivo_inexistente(tmp_path):
    with pytest.raises(ErrorReferencia) as error:
        IndiceLugares(tmp_path / "no_existe.geojson", DATA / "alias_barrios.csv", DATA / "alias_comunas.csv")
    assert "no_existe.geojson" in str(error.value)


def test_tabla_sin_columnas(tmp_path):
    (tmp_path / "alias.csv").write_text("variante,destino\nX,Y\n", encoding="utf-8")
    with pytest.raises(ErrorReferencia) as error:
        IndiceLugares(DATA / "limite_barrio_vereda_cata.geojson", tmp_path / "alias.csv", DATA / "alias_comunas.csv")
    assert "alias.csv" in str(error.value)
