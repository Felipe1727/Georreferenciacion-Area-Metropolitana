"""Caracterizacion de la estandarizacion y clasificacion por area.

Los valores esperados se obtuvieron ejecutando el codigo actual. Los tests con
`defecto_conocido` en el nombre congelan defectos a proposito: el cambio que
los corrija (`ubicacion-por-niveles`) debe actualizarlos explicitamente.
"""
import pandas as pd
import pytest

from georef import direcciones

DIRECCION = "Direccion de residencia"
CIUDAD = "Ciudad Residencia"


@pytest.fixture
def vocabulario(configuracion):
    return configuracion.direcciones


@pytest.fixture
def equivalencias(vocabulario):
    return vocabulario.equivalencias


def _area_metropolitana_estandarizada(df, configuracion):
    """Reproduce la opcion 1 del menu hasta la estandarizacion."""
    vocabulario = configuracion.direcciones
    am, _ = direcciones.separar_por_area(df, configuracion.area_metropolitana, CIUDAD)
    am = pd.DataFrame(am)
    am.loc[:, DIRECCION] = direcciones.reemplazar_equivalentes(am.loc[:, DIRECCION], vocabulario.equivalencias)
    principales, especiales = direcciones.filtrar_vias_principales(am.copy(), DIRECCION, vocabulario.tipos_via)
    return direcciones.estandarizar(principales, vocabulario, DIRECCION), especiales


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
        # Correcto seria conservar las palabras: el reemplazo es por subcadena.
        ("LAURELES -*- URBANO", "LAURELES -*- URBA#"),
        ("BUENOS AIRES", "BUE#S AIRES"),
        ("LOS PINOS", "LOS PI#S"),
        ("CR 50 NORTE 30 20", "CR 50 #RTE 30 20"),
        ("SURAMERICA", "SAMERICA"),
    ],
)
def test_reemplazo_por_subcadena_defecto_conocido(entrada, esperado, equivalencias):
    assert direcciones.reemplazar_equivalentes(pd.Series([entrada]), equivalencias).tolist() == [esperado]


def test_identificar_vias_principales(df_original, vocabulario):
    s = direcciones.reemplazar_equivalentes(df_original[DIRECCION], vocabulario.equivalencias)
    vias = direcciones.identificar_vias_principales(s, vocabulario.tipos_via)
    assert vias.tolist()[:4] == ["CL", "CL", "CR", "CR"]
    assert pd.isna(vias.iloc[4]) and pd.isna(vias.iloc[5])  # VEREDA, FINCA
    assert vias.tolist()[6:] == ["CL", "CR", "TV", "DG"]


def test_filtrar_vias_principales_separa_especiales(df_original, configuracion):
    vocabulario = configuracion.direcciones
    am, _ = direcciones.separar_por_area(df_original, configuracion.area_metropolitana, CIUDAD)
    am = pd.DataFrame(am)
    am.loc[:, DIRECCION] = direcciones.reemplazar_equivalentes(am.loc[:, DIRECCION], vocabulario.equivalencias)
    principales, especiales = direcciones.filtrar_vias_principales(am.copy(), DIRECCION, vocabulario.tipos_via)
    assert list(principales.index) == [0, 1, 2, 3, 8, 9]
    assert list(especiales.index) == [4, 5]


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("CL 10 20 30 LAURELES -*- URBA#", ["CL 10 20 30", "LAURELES -*- URBA#"]),
        ("CR 43 A 1 50 UNIDAD LOS PI#S -*- URBA#", ["CR 43 A 1 50", "UNIDAD LOS PI#S -*- URBA#"]),
        ("TV 32 B 75 20 CASA 2 CALASANZ -*- URBA#", ["TV 32 B 75 20", "CASA 2 CALASANZ -*- URBA#"]),
        ("CL 10 20 30", ["CL 10 20 30", ""]),
    ],
)
def test_dividir_complemento(entrada, esperado, vocabulario):
    assert direcciones.dividir_complemento(entrada, vocabulario.palabras_clave_completas) == esperado


def test_dividir_complemento_corta_direccion_con_norte_defecto_conocido(vocabulario):
    # Tras convertir NORTE en #RTE, la direccion pierde sus numeros.
    assert direcciones.dividir_complemento("CR 50 #RTE 30 20 -*- URBA#", vocabulario.palabras_clave_completas) == [
        "CR 50 #",
        "RTE 30 20 -*- URBA#",
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
    estandarizado, especiales = _area_metropolitana_estandarizada(df_original, configuracion)
    assert list(estandarizado.columns) == [
        "CODIGO",
        "Programa Admision",
        "Ciudad Residencia",
        "Direccion de residencia",
        "Complemento",
    ]
    assert estandarizado["Direccion de residencia"].tolist() == [
        "CL 10 #20-30",
        "CL 45S #12-15",
        "CR 43A #1-50",
        "CR 50",
        "TV 32B #75-20",
        "DG 50A #35-12",
    ]
    assert estandarizado["Complemento"].tolist() == [
        "LAURELES -*- URBA#",
        "APARTAMENTO 301 BUE#S AIRES -*- URBA#",
        "UNIDAD LOS PI#S -*- URBA#",
        "RTE 30 20 -*- URBA#",
        "CASA 2 CALASANZ -*- URBA#",
        "SAMERICA -*- URBA#",
    ]
    assert list(especiales.index) == [4, 5]
