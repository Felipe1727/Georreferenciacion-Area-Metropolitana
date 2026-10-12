"""Caracterizacion de la estandarizacion y clasificacion por area.

Los valores esperados se obtuvieron ejecutando el codigo. Hasta `normalizacion-direcciones`
habia tests `*_defecto_conocido` que congelaban el reemplazo por subcadena (`URBANO` ->
`URBA#`); ese cambio los convirtio en tests del comportamiento corregido.
"""
import pandas as pd
import pytest

from conftest import RUTA_CONFIGURACION
from georef import direcciones
from georef.referencia import IndiceLugares

DIRECCION = "Direccion de residencia"
CIUDAD = "Ciudad Residencia"


@pytest.fixture
def vocabulario(configuracion):
    return configuracion.direcciones


@pytest.fixture
def equivalencias(vocabulario):
    return vocabulario.equivalencias


def _area_metropolitana_estandarizada(df, configuracion):
    """Reproduce la estandarizacion: normaliza, separa por area y clasifica."""
    raiz = RUTA_CONFIGURACION.parent.parent
    referencia = configuracion.referencia
    indice = IndiceLugares(raiz / referencia.geojson, raiz / referencia.alias_barrios, raiz / referencia.alias_comunas)
    normalizado, principal = direcciones.normalizar_direcciones(df, configuracion, indice)
    am, _ = direcciones.separar_por_area(normalizado, configuracion.area_metropolitana, CIUDAD)
    return am[principal[am.index]], am[~principal[am.index]]


def test_filtrar_area_metropolitana_separa_por_municipio(df_original, configuracion):
    am, fuera = direcciones.separar_por_area(df_original, configuracion.area_metropolitana, CIUDAD)
    assert list(am.index) == [0, 1, 2, 3, 4, 5, 8, 9]
    assert list(fuera.index) == [6, 7]


def test_reemplazar_equivalentes_convierte_a_mayusculas(equivalencias):
    s = pd.Series(["cl 10 20 30"])
    assert direcciones.reemplazar_equivalentes(s, equivalencias).tolist() == ["CL 10 20 30"]


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("CALLE 45 SUR 12 15", "CL 45 S 12 15"),
        ("CARRERA 43 A 1 50", "CR 43 A 1 50"),
        ("DIAGONAL 5 6 7", "DG 5 6 7"),
        ("TRANSVERSAL 5 6 7", "TV 5 6 7"),
    ],
)
def test_reemplazar_equivalentes_abrevia(entrada, esperado, equivalencias):
    assert direcciones.reemplazar_equivalentes(pd.Series([entrada]), equivalencias).tolist() == [esperado]


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        # Antes (reemplazo por subcadena): URBA#, BUE#S AIRES, LOS PI#S, CR 50 #RTE 30 20, SAMERICA.
        ("LAURELES -*- URBANO", "LAURELES -*- URBANO"),
        ("BUENOS AIRES", "BUENOS AIRES"),
        ("LOS PINOS", "LOS PINOS"),
        ("CR 50 NORTE 30 20", "CR 50 N 30 20"),
        ("SURAMERICA", "SURAMERICA"),
    ],
)
def test_reemplazo_por_palabra_completa(entrada, esperado, equivalencias):
    assert direcciones.reemplazar_equivalentes(pd.Series([entrada]), equivalencias).tolist() == [esperado]


def test_identificar_vias_principales(df_original, vocabulario):
    s = direcciones.reemplazar_equivalentes(df_original[DIRECCION], vocabulario.equivalencias)
    vias = direcciones.identificar_vias_principales(s, vocabulario.tipos_via)
    assert vias.tolist()[:4] == ["CL", "CL", "CR", "CR"]
    assert pd.isna(vias.iloc[4]) and pd.isna(vias.iloc[5])  # VEREDA, FINCA
    assert vias.tolist()[6:] == ["CL", "CR", "TV", "DG"]


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("CL 10 20 30 LAURELES", ["CL 10 20 30", "LAURELES"]),
        ("CR 43 A 1 50 UNIDAD LOS PINOS", ["CR 43 A 1 50", "UNIDAD LOS PINOS"]),
        ("TV 32 B 75 20 CASA 2", ["TV 32 B 75 20", "CASA 2"]),
        ("CL 10 20 30", ["CL 10 20 30", ""]),
    ],
)
def test_dividir_complemento(entrada, esperado, vocabulario):
    assert direcciones.dividir_complemento(entrada, vocabulario.palabras_clave_completas) == esperado


def test_dividir_complemento_con_norte_abreviado(vocabulario):
    # Antes, NORTE se convertia en #RTE y la direccion perdia sus numeros ("CR 50 #" | "RTE 30 20").
    assert direcciones.dividir_complemento("CR 50 N 30 20", vocabulario.palabras_clave_completas) == [
        "CR 50 N 30 20",
        "",
    ]


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("CL 10 20 30", "CL 10 #20-30"),
        ("CL 45 S 12 15", "CL 45S #12-15"),
        ("CR 43 A 1 50", "CR 43A #1-50"),
        ("TV 32 B 75 20", "TV 32B #75-20"),
        ("DG 50 A 35 12", "DG 50A #35-12"),
        ("CR 50 #", "CR 50"),
    ],
)
def test_format_dir(entrada, esperado, vocabulario):
    assert direcciones.format_dir(entrada, vocabulario) == esperado


def test_estandarizacion_completa(df_original, configuracion):
    principales, especiales = _area_metropolitana_estandarizada(df_original, configuracion)
    assert list(principales.columns) == [
        "CODIGO",
        "Programa Admision",
        "Ciudad Residencia",
        "Direccion de residencia",
        "Complemento",
        "Barrio",
        "Codigo barrio",
        "Comuna",
        "Zona",
    ]
    assert list(principales.index) == [0, 1, 2, 3, 8, 9]
    assert principales["Direccion de residencia"].tolist() == [
        "CL 10 #20-30",
        "CL 45S #12-15",
        "CR 43A #1-50",
        "CR 50N #30-20",  # antes "CR 50": NORTE se convertia en #RTE
        "TV 32B #75-20",
        "DG 50A #35-12",
    ]
    # Antes: "LAURELES -*- URBA#", "APARTAMENTO 301 BUE#S AIRES -*- URBA#", "UNIDAD LOS PI#S -*- URBA#",
    # "RTE 30 20 -*- URBA#", "CASA 2 CALASANZ -*- URBA#" y "SAMERICA -*- URBA#".
    assert principales["Complemento"].fillna("").tolist() == [
        "", "APARTAMENTO 301", "UNIDAD LOS PINOS", "", "CASA 2", "SURAMERICA",
    ]
    assert principales["Barrio"].fillna("").tolist() == ["Laureles", "Buenos Aires", "", "", "Calasanz", ""]
    assert principales["Codigo barrio"].fillna("").tolist() == ["1108", "0907", "", "", "1202", ""]
    assert principales["Zona"].tolist() == ["URBANO"] * 6
    assert list(especiales.index) == [4, 5]
    assert especiales.loc[4, "Barrio"] == "El Plan" and especiales.loc[5, "Complemento"] == "FINCA LA ESPERANZA"
