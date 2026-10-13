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
    # Se conservan todas las equivalencias anteriores; normalizacion-direcciones añadió CRRA.
    assert set(configuracion.direcciones.equivalencias) == set(EQUIVALENTE_ANTERIOR.items()) | {("CRRA", "CR")}
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
    assert errores[0].startswith("direcciones.equivalencias[15]: debe ser un par")  # SUR, tras añadir CRRA


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


def test_referencias_incluidas():
    referencia = cargar_configuracion(RUTA_INCLUIDA).referencia
    assert referencia.geojson == Path("data/limite_barrio_vereda_cata.geojson")
    assert referencia.alias_barrios == Path("data/alias_barrios.csv")
    assert referencia.alias_comunas == Path("data/alias_comunas.csv")
    assert referencia.municipio_con_poligonos == "MEDELLIN - ANTIOQUIA"


def test_municipio_con_poligonos_fuera_del_area(tmp_path):
    ruta = configuracion_modificada(
        tmp_path, ('municipio_con_poligonos = "MEDELLIN - ANTIOQUIA"', 'municipio_con_poligonos = "RIONEGRO - ANTIOQUIA"')
    )
    errores, _ = errores_de(ruta)
    assert errores == ["referencia.municipio_con_poligonos: 'RIONEGRO - ANTIOQUIA' no pertenece al área metropolitana"]


def test_referencia_sin_una_ruta(tmp_path):
    ruta = configuracion_modificada(tmp_path, ('alias_comunas = "data/alias_comunas.csv"\n', ""))
    errores, _ = errores_de(ruta)
    assert errores == ["referencia.alias_comunas: falta esta clave"]


# Parámetros de la ubicación

def test_parametros_de_ubicacion_incluidos():
    ubicacion = cargar_configuracion(RUTA_INCLUIDA).ubicacion
    assert ubicacion.formato_consulta == "abreviado"
    assert ubicacion.tolerancia_metros == 250
    assert ubicacion.pausa_segundos == 1
    assert ubicacion.consulta_lugar_complemento is False
    assert "city" in ubicacion.tipos_rechazados
    assert set(ubicacion.nombres_via) == set(cargar_configuracion(RUTA_INCLUIDA).direcciones.tipos_via)


def test_ubicacion_sin_una_clave(tmp_path):
    ruta = configuracion_modificada(tmp_path, ("tolerancia_metros = 250\n", ""))
    errores, _ = errores_de(ruta)
    assert errores == ["ubicacion.tolerancia_metros: falta esta clave"]


def test_formato_de_consulta_desconocido(tmp_path):
    ruta = configuracion_modificada(tmp_path, ('formato_consulta = "abreviado"', 'formato_consulta = "completo"'))
    errores, _ = errores_de(ruta)
    assert len(errores) == 1
    assert errores[0].startswith("ubicacion.formato_consulta: 'completo'")
    assert "'abreviado'" in errores[0] and "'expandido'" in errores[0]


def test_tipo_de_via_sin_nombre(tmp_path):
    ruta = configuracion_modificada(tmp_path, ('CIR = "Circular", ', ""))
    errores, _ = errores_de(ruta)
    assert errores == ["ubicacion.nombres_via: falta el nombre del tipo de vía 'CIR'"]


@pytest.mark.parametrize("viejo, nuevo, error", [
    ("confianza_minima = 8", "confianza_minima = 11", "ubicacion.confianza_minima: debe ser un entero de 0 a 10"),
    ("confianza_minima = 8", "confianza_minima = 8.5", "ubicacion.confianza_minima: debe ser un entero"),
    ("tolerancia_metros = 250", "tolerancia_metros = -1", "ubicacion.tolerancia_metros: no puede ser negativa"),
    ("pausa_segundos = 1", 'pausa_segundos = "1"', "ubicacion.pausa_segundos: debe ser un número"),
    ("limite_consultas = 1000", "limite_consultas = 0", "ubicacion.limite_consultas: debe ser un entero positivo"),
    ("consulta_lugar_complemento = false", 'consulta_lugar_complemento = "no"',
     "ubicacion.consulta_lugar_complemento: debe ser true o false"),
    ('CL = "Calle"', 'CL = "Calle", KR = "Carrera"',
     "ubicacion.nombres_via.KR: no es un tipo de vía de direcciones.tipos_via"),
])
def test_valores_no_validos_de_ubicacion(tmp_path, viejo, nuevo, error):
    errores, _ = errores_de(configuracion_modificada(tmp_path, (viejo, nuevo)))
    assert errores == [error]


def test_pausa_decimal_valida(tmp_path):
    ruta = configuracion_modificada(tmp_path, ("pausa_segundos = 1", "pausa_segundos = 1.5"))
    assert cargar_configuracion(ruta).ubicacion.pausa_segundos == 1.5


# Puntos de los municipios

def con_puntos(tmp_path, *lineas):
    """Configuración incluida más una sección [puntos_municipios] con `lineas`."""
    ruta = configuracion_modificada(tmp_path)
    with open(ruta, "a", encoding="utf-8") as archivo:
        archivo.write("\n[puntos_municipios]\n" + "\n".join(lineas) + "\n")
    return ruta


BELLO = '"BELLO - ANTIOQUIA" = { latitud = 6.33, longitud = -75.56, fuente = "OpenCage", fecha = "2026-10-12" }'


def test_seccion_de_puntos_ausente(tmp_path):
    assert dict(cargar_configuracion(configuracion_modificada(tmp_path)).puntos_municipios) == {}


def test_puntos_de_municipios_validos(tmp_path):
    otra = '"CALDAS - ANTIOQUIA" = { latitud = 6.09, longitud = -75.63, fuente = "a mano", fecha = 2026-10-12 }'
    puntos = cargar_configuracion(con_puntos(tmp_path, BELLO, otra)).puntos_municipios
    assert puntos["BELLO - ANTIOQUIA"].latitud == 6.33
    assert puntos["BELLO - ANTIOQUIA"].fuente == "OpenCage"
    assert puntos["CALDAS - ANTIOQUIA"].fecha == "2026-10-12"


def test_punto_de_municipio_fuera_del_area(tmp_path):
    rionegro = BELLO.replace("BELLO", "RIONEGRO")
    errores, _ = errores_de(con_puntos(tmp_path, rionegro))
    assert errores == ['puntos_municipios."RIONEGRO - ANTIOQUIA": \'RIONEGRO - ANTIOQUIA\' no pertenece al área '
                       "metropolitana"]


def test_latitud_fuera_de_rango(tmp_path):
    errores, _ = errores_de(con_puntos(tmp_path, BELLO.replace("latitud = 6.33", "latitud = 95")))
    assert errores == ['puntos_municipios."BELLO - ANTIOQUIA".latitud: debe estar entre -90 y 90']


def test_punto_sin_fuente(tmp_path):
    errores, _ = errores_de(con_puntos(tmp_path, BELLO.replace(', fuente = "OpenCage"', "")))
    assert errores == ['puntos_municipios."BELLO - ANTIOQUIA".fuente: falta esta clave']


def test_estandarizar_sin_puntos(directorio_trabajo, ejecutar_main):
    # "Sección ausente": la configuración incluida no tiene [puntos_municipios].
    ejecutar_main(argv=["estandarizar"])
    assert (directorio_trabajo / "estandarizado" / "total_area_metropolitana.xlsx").exists()
