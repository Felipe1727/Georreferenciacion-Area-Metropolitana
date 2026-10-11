"""Escenarios de specs/configuracion y de la validación de subconjuntos (specs/areas-geograficas)."""
import dataclasses
from pathlib import Path

import pytest

from conftest import escribir_configuracion
from georef.config import ErrorConfiguracion, cargar_configuracion

RAIZ_REPO = Path(__file__).resolve().parent.parent
RUTA_INCLUIDA = RAIZ_REPO / "config" / "georef.toml"

# Copia literal de las constantes que tenía main.py antes de modularizacion-config.
# La configuración incluida debe reproducirlas exactamente, en el mismo orden.
AREA_METROPOLITANA_ANTERIOR = [
    "MEDELLIN - ANTIOQUIA",
    "ITAGUI - ANTIOQUIA",
    "BELLO - ANTIOQUIA",
    "GIRARDOTA - ANTIOQUIA",
    "BARBOSA - ANTIOQUIA",
    "COPACABANA - ANTIOQUIA",
    "ENVIGADO - ANTIOQUIA",
    "SABANETA - ANTIOQUIA",
    "CALDAS - ANTIOQUIA",
    "LA ESTRELLA - ANTIOQUIA"
    ]
TIPO_VIA_URBANA_ANTERIOR = ['CL', 'CR', 'AV', 'CIR', 'DG', 'TV']
KEYWORDS_ANTERIOR = TIPO_VIA_URBANA_ANTERIOR.copy() + ['BIS', 'KM']
EQUIVALENTE_ANTERIOR = {
    'CALLE' : 'CL',
    'CARRERA' : 'CR',
    'CRR' : 'CR',
    'CRA' : 'CR',
    'CLL' : 'CL',
    'NÚMERO' : '#',
    'NUMERO' : '#',
    'NO' : '#',
    'DIAGONAL' : 'DG',
    'CIRCULAR' : 'CIR',
    'TRANSVERSAL' : 'TV',
    'AVENIDA' : 'AV',
    'NO.' : '#',
    'NORTE' : 'N',
    'SUR' : 'S',
    'ESTE' : 'E',
    'ORIENTE' : 'E',
    'OESTE' : 'O',
    'OCCIDENTE' : 'O'
}


def configuracion_modificada(tmp_path, *reemplazos):
    return escribir_configuracion(tmp_path / "georef.toml", *reemplazos)


def errores_de(ruta):
    with pytest.raises(ErrorConfiguracion) as error:
        cargar_configuracion(ruta)
    return error.value.errores, str(error.value)


def test_configuracion_incluida_reproduce_las_constantes_anteriores():
    configuracion = cargar_configuracion(RUTA_INCLUIDA)
    assert list(configuracion.area_metropolitana) == AREA_METROPOLITANA_ANTERIOR
    assert list(configuracion.direcciones.tipos_via) == TIPO_VIA_URBANA_ANTERIOR
    assert list(configuracion.direcciones.palabras_clave_completas) == KEYWORDS_ANTERIOR
    assert list(configuracion.direcciones.equivalencias) == list(EQUIVALENTE_ANTERIOR.items())
    assert configuracion.columnas.ciudad == "Ciudad Residencia"
    assert configuracion.columnas.direccion == "Direccion de residencia"
    assert dict(configuracion.subconjuntos) == {"medellin": ("MEDELLIN - ANTIOQUIA",)}


def test_ruta_por_defecto_relativa_al_directorio_de_trabajo(monkeypatch):
    monkeypatch.chdir(RAIZ_REPO)
    assert cargar_configuracion().ruta == Path("config") / "georef.toml"


def test_valores_con_tildes_se_conservan():
    equivalencias = dict(cargar_configuracion(RUTA_INCLUIDA).direcciones.equivalencias)
    assert equivalencias["NÚMERO"] == "#"


def test_configuracion_inmutable():
    configuracion = cargar_configuracion(RUTA_INCLUIDA)
    with pytest.raises(dataclasses.FrozenInstanceError):
        configuracion.area_metropolitana = ()
    with pytest.raises(TypeError):
        configuracion.subconjuntos["otro"] = ()


def test_archivo_alternativo(tmp_path):
    ruta = configuracion_modificada(tmp_path, ('"BARBOSA - ANTIOQUIA",', '"BARBOSA - ANTIOQUIA",\n    "RIONEGRO - ANTIOQUIA",'))
    assert "RIONEGRO - ANTIOQUIA" in cargar_configuracion(ruta).area_metropolitana


def test_archivo_inexistente(tmp_path):
    errores, mensaje = errores_de(tmp_path / "no_existe.toml")
    assert "no_existe.toml" in mensaje
    assert errores == ["no existe el archivo"]


def test_sintaxis_invalida_indica_la_linea(tmp_path):
    ruta = configuracion_modificada(tmp_path, ('ciudad = "Ciudad Residencia"', 'ciudad = "Ciudad Residencia'))
    _, mensaje = errores_de(ruta)
    assert "georef.toml" in mensaje
    assert "line" in mensaje


def test_clave_desconocida(tmp_path):
    ruta = configuracion_modificada(tmp_path, ("[area_metropolitana]\nmunicipios", "[area_metropolitana]\nmunicipio"))
    errores, _ = errores_de(ruta)
    assert "area_metropolitana.municipio: clave desconocida" in errores
    assert "area_metropolitana.municipios: falta esta clave" in errores


def test_seccion_ausente(tmp_path):
    ruta = configuracion_modificada(
        tmp_path, ('[columnas]\nciudad = "Ciudad Residencia"\ndireccion = "Direccion de residencia"\n', "")
    )
    errores, _ = errores_de(ruta)
    assert errores == ["columnas: falta esta sección"]


def test_lista_vacia(tmp_path):
    ruta = configuracion_modificada(tmp_path, ('tipos_via = ["CL", "CR", "AV", "CIR", "DG", "TV"]', "tipos_via = []"))
    errores, _ = errores_de(ruta)
    assert errores == ["direcciones.tipos_via: la lista está vacía"]


def test_municipio_repetido(tmp_path):
    ruta = configuracion_modificada(tmp_path, ('"BARBOSA - ANTIOQUIA",', '"BARBOSA - ANTIOQUIA",\n    "BELLO - ANTIOQUIA",'))
    errores, _ = errores_de(ruta)
    assert errores == ["area_metropolitana.municipios: 'BELLO - ANTIOQUIA' está repetido"]


def test_equivalencia_repetida(tmp_path):
    ruta = configuracion_modificada(tmp_path, ('["SUR", "S"],', '["SUR", "S"],\n    ["CALLE", "C"],'))
    errores, _ = errores_de(ruta)
    assert errores == ["direcciones.equivalencias: 'CALLE' tiene más de una equivalencia"]


def test_equivalencia_mal_formada(tmp_path):
    ruta = configuracion_modificada(tmp_path, ('["SUR", "S"],', '["SUR"],'))
    errores, _ = errores_de(ruta)
    assert errores[0].startswith("direcciones.equivalencias[14]: debe ser un par")


def test_texto_vacio(tmp_path):
    ruta = configuracion_modificada(tmp_path, ('ciudad = "Ciudad Residencia"', 'ciudad = ""'))
    errores, _ = errores_de(ruta)
    assert errores == ["columnas.ciudad: debe ser un texto no vacío"]


def test_varios_errores_a_la_vez(tmp_path):
    ruta = configuracion_modificada(
        tmp_path,
        ("[columnas]\n", "[columnas]\ncolumna_extra = 1\n"),
        ('tipos_via = ["CL", "CR", "AV", "CIR", "DG", "TV"]', "tipos_via = []"),
    )
    errores, mensaje = errores_de(ruta)
    assert errores == ["columnas.columna_extra: clave desconocida", "direcciones.tipos_via: la lista está vacía"]
    assert all(error in mensaje for error in errores)


@pytest.mark.parametrize("nombre", ['"Medellín"', "area_metropolitana", '"valle sur"'])
def test_nombre_de_subconjunto_no_valido(tmp_path, nombre):
    ruta = configuracion_modificada(tmp_path, ("[subconjuntos.medellin]", f"[subconjuntos.{nombre}]"))
    errores, _ = errores_de(ruta)
    assert len(errores) == 1 and "nombre no válido" in errores[0]


def test_municipio_de_subconjunto_fuera_del_area(tmp_path):
    ruta = configuracion_modificada(
        tmp_path, ('municipios = ["MEDELLIN - ANTIOQUIA"]', 'municipios = ["MEDELLIN - ANTIOQUIA", "RIONEGRO - ANTIOQUIA"]')
    )
    errores, _ = errores_de(ruta)
    assert errores == ["subconjuntos.medellin.municipios: 'RIONEGRO - ANTIOQUIA' no pertenece al área metropolitana"]


def test_subconjunto_sin_municipios(tmp_path):
    ruta = configuracion_modificada(tmp_path, ('municipios = ["MEDELLIN - ANTIOQUIA"]', "municipios = []"))
    errores, _ = errores_de(ruta)
    assert errores == ["subconjuntos.medellin.municipios: la lista está vacía"]


def test_nuevo_subconjunto_solo_con_configuracion(tmp_path):
    ruta = configuracion_modificada(
        tmp_path,
        ("[columnas]", '[subconjuntos.sur]\nmunicipios = ["ENVIGADO - ANTIOQUIA", "SABANETA - ANTIOQUIA"]\n\n[columnas]'),
    )
    assert cargar_configuracion(ruta).subconjuntos["sur"] == ("ENVIGADO - ANTIOQUIA", "SABANETA - ANTIOQUIA")
