"""Escenarios de specs/normalizacion-direcciones con direcciones inventadas y los datos de referencia reales."""
from pathlib import Path

import pandas as pd
import pytest

from georef.direcciones import COLUMNAS_NORMALIZADAS, normalizar_direccion, normalizar_direcciones, reemplazar_equivalentes
from georef.referencia import IndiceLugares

DATA = Path(__file__).resolve().parent.parent / "data"
MEDELLIN = "MEDELLIN - ANTIOQUIA"


@pytest.fixture(scope="module")
def indice():
    return IndiceLugares(DATA / "limite_barrio_vereda_cata.geojson", DATA / "alias_barrios.csv",
                         DATA / "alias_comunas.csv")


@pytest.fixture
def medellin(configuracion, indice):
    """Normaliza una direccion de Medellin (con reconocimiento de lugares)."""
    return lambda texto: normalizar_direccion(texto, configuracion.direcciones, indice)


@pytest.fixture
def otro_municipio(configuracion):
    """Normaliza una direccion de un municipio sin poligonos."""
    return lambda texto: normalizar_direccion(texto, configuracion.direcciones, None)


def partes(resultado, *claves):
    return tuple(resultado[clave] for clave in claves)


# Columnas de la direccion normalizada

def test_direccion_completa_de_medellin(medellin):
    r = medellin("CALLE 45 SUR 12 15 APARTAMENTO 301 BUENOS AIRES -*- URBANO")
    assert partes(r, "direccion", "Complemento", "Barrio", "Codigo barrio", "Comuna", "Zona") == (
        "CL 45S #12-15", "APARTAMENTO 301", "Buenos Aires", "0907", "BUENOS AIRES", "URBANO"
    )


def test_columnas_e_indice_conservados(configuracion, indice):
    df = pd.DataFrame(
        {
            "CODIGO": ["E1", "E2"],
            "Ciudad Residencia": [MEDELLIN, "ENVIGADO - ANTIOQUIA"],
            "Direccion de residencia": ["CL 10 20 30 LAURELES -*- URBANO", "CR 1 2 3 -*- URBANO"],
            "Programa Admision": ["P1", "P2"],
        },
        index=[7, 42],
    )
    resultado, principal = normalizar_direcciones(df, configuracion, indice)
    assert list(resultado.columns) == [
        "CODIGO", "Ciudad Residencia", "Direccion de residencia", *COLUMNAS_NORMALIZADAS, "Programa Admision"
    ]
    assert list(resultado.index) == [7, 42]
    assert resultado["Programa Admision"].tolist() == ["P1", "P2"]
    assert resultado.loc[7, "Barrio"] == "Laureles" and pd.isna(resultado.loc[42, "Barrio"])
    assert principal.tolist() == [True, True]


# Equivalencias solo en la via y la numeracion

def test_palabras_que_contienen_una_equivalencia(otro_municipio):
    r = otro_municipio("CL 10 20 30 UNIDAD LOS PINOS -*- URBANO")
    assert partes(r, "Complemento", "Zona") == ("UNIDAD LOS PINOS", "URBANO")


def test_orientacion_de_la_via(medellin):
    assert medellin("CR 50 NORTE 30 20 -*- URBANO")["direccion"] == "CR 50N #30-20"


def test_nombre_oficial_con_una_palabra_de_las_equivalencias(medellin):
    r = medellin("CL 1 2 3 ASOMADERA NO 1 -*- URBANO")
    assert partes(r, "direccion", "Barrio") == ("CL 1 #2-3", "Asomadera No. 1")


def test_complemento_conserva_sus_palabras(otro_municipio):
    assert otro_municipio("CL 1 2 3 TORRE NORTE APTO NO 5")["Complemento"] == "TORRE NORTE APTO NO 5"


def test_reemplazar_equivalentes_por_palabra_completa(configuracion):
    equivalencias = configuracion.direcciones.equivalencias
    entrada = pd.Series(["laureles -*- urbano", "CALLE 45 SUR 12 15", "BUENOS AIRES", "SURAMERICA"])
    assert reemplazar_equivalentes(entrada, equivalencias).tolist() == [
        "LAURELES -*- URBANO", "CL 45 S 12 15", "BUENOS AIRES", "SURAMERICA"
    ]


# Zona

def test_zona_rural(medellin):
    assert medellin("VEREDA EL PLAN -*- RURAL")["Zona"] == "RURAL"


def test_sin_separador(medellin):
    assert partes(medellin("CL 50 40 30"), "Zona", "Complemento") == (None, None)


def test_texto_no_reconocido_tras_el_separador(otro_municipio):
    assert partes(otro_municipio("CR 1 2 3 CASA -*- OTRA COSA"), "Zona", "Complemento") == (None, "CASA OTRA COSA")


# Reconocimiento del barrio

def test_barrio_con_complemento_delante(medellin):
    assert partes(medellin("TV 32 B 75 20 CASA 2 CALASANZ -*- URBANO"), "Complemento", "Barrio") == ("CASA 2", "Calasanz")


def test_alias(medellin):
    assert partes(medellin("CL 1 2 3 CALAZANS -*- URBANO"), "Barrio", "Codigo barrio") == ("Calasanz", "1202")


def test_sufijo_mas_largo(medellin):
    r = medellin("CL 1 2 3 SAN ANTONIO DE PRADO -*- RURAL")
    assert partes(r, "Barrio", "Comuna") == (None, "SAN ANTONIO DE PRADO")


def test_numeros_finales(medellin):
    r = medellin("CL 1 2 3 APTO 4 FATIMA 4")
    assert partes(r, "Barrio", "Complemento") == ("Fátima", "APTO 4 4")


# Barrio resuelto a un poligono

def test_repetido_resuelto_por_la_zona(medellin):
    assert partes(medellin("CL 1 2 3 LA FLORIDA -*- URBANO"), "Codigo barrio", "Comuna") == ("1417", "EL POBLADO")


def test_repetido_sin_zona(medellin):
    r = medellin("CL 1 2 3 LA FLORIDA")
    assert partes(r, "Barrio", "Codigo barrio", "Comuna") == ("La Florida", None, None)


def test_codigo_con_cero_a_la_izquierda(medellin):
    assert medellin("CL 1 2 3 BARRIOS DE JESUS -*- URBANO")["Codigo barrio"] == "0902"


# Registros que solo nombran una comuna

def test_corregimiento(medellin):
    r = medellin("SAN ANTONIO DE PRADO -*- RURAL")
    assert partes(r, "Comuna", "Barrio", "Codigo barrio") == ("SAN ANTONIO DE PRADO", None, None)


def test_variante_de_comuna(medellin):
    r = medellin("TORRE 3 POBLADO -*- URBANO")
    assert partes(r, "Comuna", "Barrio", "Complemento") == ("EL POBLADO", None, "TORRE 3")


def test_nombre_de_barrio_con_articulo(medellin):
    assert partes(medellin("CL 1 2 3 EL POBLADO"), "Barrio", "Codigo barrio") == ("El Poblado", "1418")


# Regla sin perdida

def test_barrio_no_reconocido(medellin):
    r = medellin("CL 10 20 30 TORRE 2 SENDEROS DEL MONTE -*- URBANO")
    assert partes(r, "Complemento", "Barrio", "Codigo barrio", "Comuna") == ("TORRE 2 SENDEROS DEL MONTE", None, None, None)


def test_registro_sin_via(otro_municipio):
    r = otro_municipio("FINCA LA ESPERANZA -*- RURAL")
    assert partes(r, "direccion", "Complemento", "Zona") == (None, "FINCA LA ESPERANZA", "RURAL")


@pytest.mark.parametrize("texto", [
    "CALLE 45 SUR 12 15 APARTAMENTO 301 BUENOS AIRES -*- URBANO",
    "TV 32 B 75 20 CASA 2 CALASANZ -*- URBANO",
    "CL 10 20 30 TORRE 2 SENDEROS DEL MONTE -*- URBANO",
    "CL 1 2 3 APTO 4 FATIMA 4",
    "VEREDA EL PLAN -*- RURAL",
])
def test_ninguna_palabra_se_pierde(medellin, texto):
    # Las palabras del complemento, el lugar y la zona estan en el texto; la via solo cambia de formato.
    r = medellin(texto)
    complemento = (r["Complemento"] or "").split()
    originales = texto.split()
    assert all(palabra in originales for palabra in complemento)
    if r["Zona"]:
        assert r["Zona"] in originales


# Otros municipios sin barrio

def test_registro_de_envigado(otro_municipio):
    r = otro_municipio("CARRERA 43 A 1 50 UNIDAD LOS PINOS -*- URBANO")
    assert partes(r, "direccion", "Complemento", "Zona", "Barrio") == ("CR 43A #1-50", "UNIDAD LOS PINOS", "URBANO", None)


def test_otros_municipios_sin_reconocimiento(configuracion, indice):
    df = pd.DataFrame({"Ciudad Residencia": ["ENVIGADO - ANTIOQUIA"], "Direccion de residencia": ["CL 1 2 3 LAURELES"]})
    resultado, _ = normalizar_direcciones(df, configuracion, indice)
    assert resultado.loc[0, "Complemento"] == "LAURELES" and pd.isna(resultado.loc[0, "Barrio"])


# Clasificacion en vias principales y especiales

def test_via_expresada_con_la_palabra_completa(medellin):
    assert medellin("CALLE 45 12 15")["principal"] is True


def test_vereda(medellin):
    r = medellin("VEREDA EL PLAN -*- RURAL")
    assert r["principal"] is False
    assert partes(r, "Barrio", "Complemento", "Zona") == ("El Plan", "VEREDA", "RURAL")


# Casos encontrados en la verificacion con los datos reales (formas inventadas)

@pytest.mark.parametrize("texto, direccion", [
    ("CALLE31A 45 12", "CL 31A #45-12"),   # abreviatura pegada a numeros
    ("CL 9 9ESTE 123", "CL 9 #9E-123"),     # orientacion pegada a numeros
    ("CRRA 45 12 30", "CR 45 #12-30"),       # variante CRRA de la configuracion
])
def test_abreviatura_pegada_a_numeros_o_signos(otro_municipio, texto, direccion):
    r = otro_municipio(texto)
    assert r["direccion"] == direccion and r["principal"] is True


def test_palabra_de_dos_letras_al_final(otro_municipio):
    # Sin el espacio final, dividir_complemento fallaba y devolvia todo como direccion.
    assert partes(otro_municipio("CARRERA 45 12 30 NA"), "direccion", "Complemento") == ("CR 45 #12-30", "NA")
