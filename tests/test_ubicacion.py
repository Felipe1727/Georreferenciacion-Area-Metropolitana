"""Escenarios de specs/ubicacion-por-niveles: la cascada con un resolvedor falso y el GeoJSON real."""
import dataclasses
from pathlib import Path
from types import MappingProxyType

import pandas as pd
import pytest

from conftest import desplazado
from georef.config import PuntoMunicipio
from georef.geocodificacion import PENDIENTE, RESULTADO, SIN_RESULTADO, Respuesta
from georef.geografia import Poligonos
from georef.ubicacion import (ACEPTADA, BARRIO, COLUMNAS_UBICACION, COMUNA, DIRECCION, FUERA_DEL_MUNICIPIO,
                              LEJOS_DEL_LUGAR_DECLARADO, MUNICIPIO, PRECISION_INSUFICIENTE, RESULTADOS, SIN_CONSULTA,
                              resumen, ubicar_registros)

GEOJSON = Path(__file__).resolve().parent.parent / "data" / "limite_barrio_vereda_cata.geojson"
MEDELLIN = "MEDELLIN - ANTIOQUIA"
ENVIGADO = "ENVIGADO - ANTIOQUIA"

# Puntos sinteticos de los municipios: solo sirven para reconocerlos en los resultados.
PUNTOS = MappingProxyType({
    MEDELLIN: PuntoMunicipio(6.0, -75.0, "prueba", "2026-10-12"),
    ENVIGADO: PuntoMunicipio(6.1, -75.1, "prueba", "2026-10-12"),
})


class ResolvedorFalso:
    """Sesion de consultas falsa: `respuestas` asocia consulta -> Respuesta; las demas no tienen resultado."""

    def __init__(self, respuestas=None):
        self.respuestas = respuestas or {}
        self.llamadas = []
        self.peticiones = 0
        self.desde_cache = 0
        self.pendientes = set()
        self.restantes = None
        self.parada = None

    def resolver(self, consulta, bounds=None, registro=""):
        self.llamadas.append((consulta, bounds, registro))
        self.peticiones += 1
        return self.respuestas.get(consulta, Respuesta(SIN_RESULTADO))

    @property
    def consultas(self):
        return [consulta for consulta, _, _ in self.llamadas]


@pytest.fixture(scope="module")
def poligonos():
    return Poligonos(GEOJSON)


@pytest.fixture
def conf(configuracion):
    return dataclasses.replace(configuracion, puntos_municipios=PUNTOS)


def codigo_de(poligonos, nombre, comuna=None):
    codigos = [c for c in poligonos.codigos if poligonos.nombre_barrio(c)[0] == nombre
               and (comuna is None or poligonos.nombre_barrio(c)[1] == comuna)]
    assert len(codigos) == 1, nombre
    return codigos[0]


def registro(direccion="CL 10 #20-30", ciudad=MEDELLIN, complemento=None, barrio=None, codigo=None, comuna=None,
             zona="URBANO"):
    return {"CODIGO": "E1", "Ciudad Residencia": ciudad, "Direccion de residencia": direccion,
            "Complemento": complemento, "Barrio": barrio, "Codigo barrio": codigo, "Comuna": comuna, "Zona": zona,
            "Programa Admision": "Programa sintetico"}


def ubicar(conf, poligonos, sesion, *registros, principal=None):
    df = pd.DataFrame(list(registros), index=range(10, 10 + len(registros)))
    if principal is None:
        principal = [True] * len(registros)
    return ubicar_registros(df, pd.Series(principal, index=df.index), conf, poligonos, sesion)


def con_barrio(poligonos, nombre, comuna=None, **otros):
    codigo = codigo_de(poligonos, nombre, comuna)
    oficial, su_comuna = poligonos.nombre_barrio(codigo)
    return registro(barrio=oficial, codigo=codigo, comuna=su_comuna, **otros)


CONSULTA = "CL 10 #20-30, MEDELLIN, ANTIOQUIA, Colombia"


def respuesta_en(latitud, longitud, tipo="building", confianza=10):
    return Respuesta(RESULTADO, latitud, longitud, confianza, tipo, "Resultado sintetico")


# Niveles de ubicacion

def test_barrio_declarado_sin_consulta_aceptada(conf, poligonos):
    fila = ubicar(conf, poligonos, ResolvedorFalso(), con_barrio(poligonos, "Laureles")).iloc[0]
    codigo = codigo_de(poligonos, "Laureles")
    assert (fila["Latitud"], fila["Longitud"]) == poligonos.punto_barrio(codigo)
    assert (fila["Nivel ubicacion"], fila["Resultado consulta"]) == (BARRIO, SIN_RESULTADO)


def test_solo_comuna(conf, poligonos):
    fila = ubicar(conf, poligonos, ResolvedorFalso(), registro(comuna="EL POBLADO")).iloc[0]
    assert (fila["Latitud"], fila["Longitud"]) == poligonos.punto_comuna("EL POBLADO")
    assert fila["Nivel ubicacion"] == COMUNA


@pytest.mark.parametrize("declarado", [{}, {"barrio": "La Florida"}])  # sin nada, o barrio repetido sin codigo
def test_sin_lugar_reconocido(conf, poligonos, declarado):
    fila = ubicar(conf, poligonos, ResolvedorFalso(), registro(**declarado)).iloc[0]
    assert (fila["Latitud"], fila["Longitud"]) == (6.0, -75.0)
    assert fila["Nivel ubicacion"] == MUNICIPIO


def test_registro_especial_de_medellin(conf, poligonos):
    especial = con_barrio(poligonos, "El Plan", direccion=None, complemento="VEREDA", zona="RURAL")
    sesion = ResolvedorFalso()
    fila = ubicar(conf, poligonos, sesion, especial, principal=[False]).iloc[0]
    assert sesion.llamadas == []
    assert (fila["Nivel ubicacion"], fila["Resultado consulta"]) == (BARRIO, SIN_CONSULTA)


def test_registro_de_envigado(conf, poligonos):
    sesion = ResolvedorFalso()
    fila = ubicar(conf, poligonos, sesion, registro("CR 43A #1-50", ciudad=ENVIGADO)).iloc[0]
    assert sesion.llamadas == []
    assert (fila["Latitud"], fila["Longitud"], fila["Nivel ubicacion"]) == (6.1, -75.1, MUNICIPIO)
    assert fila["Resultado consulta"] == SIN_CONSULTA


def test_consulta_con_recuadro_y_registro(conf, poligonos):
    sesion = ResolvedorFalso()
    ubicar(conf, poligonos, sesion, registro())
    assert sesion.llamadas == [(CONSULTA, poligonos.recuadro(), 10)]


def test_formato_de_la_configuracion(conf, poligonos):
    expandido = dataclasses.replace(conf, ubicacion=dataclasses.replace(conf.ubicacion, formato_consulta="expandido"))
    sesion = ResolvedorFalso()
    ubicar(expandido, poligonos, sesion, registro())
    assert sesion.consultas == ["Calle 10 # 20-30, MEDELLIN, ANTIOQUIA, Colombia"]


# Aceptacion del punto de la API

def test_resultado_de_nivel_ciudad(conf, poligonos):
    laureles = poligonos.punto_barrio(codigo_de(poligonos, "Laureles"))
    sesion = ResolvedorFalso({CONSULTA: respuesta_en(*laureles, tipo="city")})
    fila = ubicar(conf, poligonos, sesion, con_barrio(poligonos, "Laureles")).iloc[0]
    assert (fila["Resultado consulta"], fila["Nivel ubicacion"]) == (PRECISION_INSUFICIENTE, BARRIO)


def test_confianza_insuficiente(conf, poligonos):
    laureles = poligonos.punto_barrio(codigo_de(poligonos, "Laureles"))
    sesion = ResolvedorFalso({CONSULTA: respuesta_en(*laureles, confianza=7)})
    fila = ubicar(conf, poligonos, sesion, con_barrio(poligonos, "Laureles")).iloc[0]
    assert fila["Resultado consulta"] == PRECISION_INSUFICIENTE


def test_punto_fuera_de_medellin(conf, poligonos):
    sesion = ResolvedorFalso({CONSULTA: respuesta_en(4.6, -74.08)})  # Bogota
    fila = ubicar(conf, poligonos, sesion, registro()).iloc[0]
    assert (fila["Resultado consulta"], fila["Nivel ubicacion"]) == (FUERA_DEL_MUNICIPIO, MUNICIPIO)


def test_punto_dentro_de_la_tolerancia_del_barrio(conf, poligonos):
    laureles = poligonos.geometria_barrio(codigo_de(poligonos, "Laureles"))
    punto = desplazado(poligonos, laureles, 120)
    fila = ubicar(conf, poligonos, ResolvedorFalso({CONSULTA: respuesta_en(*punto)}),
                  con_barrio(poligonos, "Laureles")).iloc[0]
    assert (fila["Latitud"], fila["Longitud"]) == punto
    assert (fila["Nivel ubicacion"], fila["Resultado consulta"]) == (DIRECCION, ACEPTADA)


def test_prevalece_el_lugar_declarado(conf, poligonos):
    codigo = codigo_de(poligonos, "Laureles")
    punto = desplazado(poligonos, poligonos.geometria_barrio(codigo), 2000)
    fila = ubicar(conf, poligonos, ResolvedorFalso({CONSULTA: respuesta_en(*punto)}),
                  con_barrio(poligonos, "Laureles")).iloc[0]
    assert fila["Resultado consulta"] == LEJOS_DEL_LUGAR_DECLARADO
    assert (fila["Latitud"], fila["Longitud"], fila["Nivel ubicacion"]) == (*poligonos.punto_barrio(codigo), BARRIO)


def test_comuna_declarada_valida_el_punto(conf, poligonos):
    punto = desplazado(poligonos, poligonos.geometria_comuna("EL POBLADO"), 2000)
    fila = ubicar(conf, poligonos, ResolvedorFalso({CONSULTA: respuesta_en(*punto)}),
                  registro(comuna="EL POBLADO")).iloc[0]
    assert (fila["Resultado consulta"], fila["Nivel ubicacion"]) == (LEJOS_DEL_LUGAR_DECLARADO, COMUNA)


def test_sin_lugar_declarado(conf, poligonos):
    punto = poligonos.punto_barrio(codigo_de(poligonos, "Laureles"))
    fila = ubicar(conf, poligonos, ResolvedorFalso({CONSULTA: respuesta_en(*punto)}), registro()).iloc[0]
    assert (fila["Nivel ubicacion"], fila["Resultado consulta"]) == (DIRECCION, ACEPTADA)


def test_consulta_pendiente(conf, poligonos):
    sesion = ResolvedorFalso({CONSULTA: Respuesta(PENDIENTE)})
    fila = ubicar(conf, poligonos, sesion, con_barrio(poligonos, "Laureles")).iloc[0]
    assert (fila["Resultado consulta"], fila["Nivel ubicacion"]) == (PENDIENTE, BARRIO)


# Columnas del archivo de coordenadas

def test_columnas_e_indice(conf, poligonos):
    resultado = ubicar(conf, poligonos, ResolvedorFalso(), registro(), registro(ciudad=ENVIGADO))
    assert list(resultado.columns) == [
        "CODIGO", "Ciudad Residencia", "Direccion de residencia", "Complemento", "Barrio", "Codigo barrio", "Comuna",
        "Zona", *COLUMNAS_UBICACION, "Programa Admision",
    ]
    assert list(resultado.index) == [10, 11]
    assert resultado["Programa Admision"].tolist() == ["Programa sintetico"] * 2


def test_registro_a_nivel_de_direccion(conf, poligonos):
    codigo = codigo_de(poligonos, "Laureles")
    punto = poligonos.punto_barrio(codigo)
    fila = ubicar(conf, poligonos, ResolvedorFalso({CONSULTA: respuesta_en(*punto)}), registro()).iloc[0]
    assert (fila["Barrio ubicacion"], fila["Codigo barrio ubicacion"]) == ("Laureles", codigo)
    assert fila["Comuna ubicacion"] == poligonos.nombre_barrio(codigo)[1]


def test_codigo_ubicacion_como_texto(conf, poligonos):
    fila = ubicar(conf, poligonos, ResolvedorFalso(), con_barrio(poligonos, "Barrio de Jesús")).iloc[0]
    assert fila["Codigo barrio ubicacion"] == "0902"


def test_registro_a_nivel_de_comuna(conf, poligonos):
    fila = ubicar(conf, poligonos, ResolvedorFalso(), registro(comuna="EL POBLADO")).iloc[0]
    assert fila["Comuna ubicacion"] == "EL POBLADO"
    assert pd.isna(fila["Barrio ubicacion"]) and pd.isna(fila["Codigo barrio ubicacion"])


def test_registro_a_nivel_de_municipio(conf, poligonos):
    fila = ubicar(conf, poligonos, ResolvedorFalso(), registro(ciudad=ENVIGADO)).iloc[0]
    assert all(pd.isna(fila[c]) for c in ("Barrio ubicacion", "Codigo barrio ubicacion", "Comuna ubicacion"))


def test_metadatos_de_la_api_fuera_del_excel(conf, poligonos):
    punto = poligonos.punto_barrio(codigo_de(poligonos, "Laureles"))
    resultado = ubicar(conf, poligonos, ResolvedorFalso({CONSULTA: respuesta_en(*punto)}), registro())
    texto = " ".join(map(str, resultado.columns)).lower() + " " + resultado.astype(str).to_string()
    assert "confidence" not in texto and "confianza" not in texto and "Resultado sintetico" not in texto


# Valores de Resultado consulta

def test_valores_posibles(conf, poligonos):
    punto = poligonos.punto_barrio(codigo_de(poligonos, "Laureles"))
    sesion = ResolvedorFalso({CONSULTA: respuesta_en(*punto), "CL 1 #1-1, MEDELLIN, ANTIOQUIA, Colombia":
                              Respuesta(PENDIENTE)})
    resultado = ubicar(conf, poligonos, sesion, registro(), registro("CL 1 #1-1"), registro("CL 2 #2-2"),
                       registro(ciudad=ENVIGADO), registro(direccion=None), principal=[True, True, True, True, False])
    assert set(resultado["Resultado consulta"]) <= set(RESULTADOS)
    assert resultado["Resultado consulta"].tolist() == [ACEPTADA, PENDIENTE, SIN_RESULTADO, SIN_CONSULTA, SIN_CONSULTA]


# Resumen de la ubicacion

def test_resumen_sin_direcciones(conf, poligonos):
    sesion = ResolvedorFalso()
    resultado = ubicar(conf, poligonos, sesion, con_barrio(poligonos, "Laureles"), registro(ciudad=ENVIGADO))
    texto = resumen(resultado, sesion)
    assert "BARRIO: 1" in texto and "MUNICIPIO: 1" in texto
    assert "SIN_RESULTADO: 1" in texto and "SIN_CONSULTA: 1" in texto
    assert "CL 10" not in texto and "Laureles" not in texto


# Consulta con el lugar del complemento

def con_lugar_complemento(conf, activada):
    return dataclasses.replace(conf, ubicacion=dataclasses.replace(conf.ubicacion,
                                                                   consulta_lugar_complemento=activada))


def test_opcion_desactivada(conf, poligonos):
    assert conf.ubicacion.consulta_lugar_complemento is False  # configuracion incluida
    sesion = ResolvedorFalso()
    ubicar(conf, poligonos, sesion, con_barrio(poligonos, "Laureles", complemento="APTO 301 UNIDAD LOS PINOS"))
    assert sesion.consultas == [CONSULTA]


def test_opcion_activada(conf, poligonos):
    sesion = ResolvedorFalso()
    ubicar(con_lugar_complemento(conf, True), poligonos, sesion,
           con_barrio(poligonos, "Laureles", complemento="APTO 301 UNIDAD LOS PINOS"))
    assert len(sesion.consultas) == 2
    segunda = sesion.consultas[1]
    assert segunda.startswith("UNIDAD LOS PINOS, LAURELES") and "APTO 301" not in segunda
    assert sesion.llamadas[1][1] == poligonos.recuadro()


def test_lugar_aceptado(conf, poligonos):
    codigo = codigo_de(poligonos, "Laureles")
    punto = poligonos.punto_barrio(codigo)
    sesion = ResolvedorFalso({"UNIDAD LOS PINOS, LAURELES, MEDELLIN, ANTIOQUIA, Colombia": respuesta_en(*punto)})
    fila = ubicar(con_lugar_complemento(conf, True), poligonos, sesion,
                  con_barrio(poligonos, "Laureles", complemento="APTO 301 UNIDAD LOS PINOS")).iloc[0]
    assert (fila["Nivel ubicacion"], fila["Resultado consulta"]) == (DIRECCION, "ACEPTADA_LUGAR")


def test_lugar_tambien_rechazado(conf, poligonos):
    sesion = ResolvedorFalso()
    fila = ubicar(con_lugar_complemento(conf, True), poligonos, sesion,
                  con_barrio(poligonos, "Laureles", complemento="UNIDAD LOS PINOS")).iloc[0]
    # Se conserva el motivo de la primera consulta y se usa el respaldo.
    assert (fila["Nivel ubicacion"], fila["Resultado consulta"]) == (BARRIO, SIN_RESULTADO)


def test_sin_segunda_consulta_si_esta_pendiente(conf, poligonos):
    sesion = ResolvedorFalso({CONSULTA: Respuesta(PENDIENTE)})
    ubicar(con_lugar_complemento(conf, True), poligonos, sesion,
           con_barrio(poligonos, "Laureles", complemento="UNIDAD LOS PINOS"))
    assert sesion.consultas == [CONSULTA]


def test_sin_lugar_con_nombre(conf, poligonos):
    sesion = ResolvedorFalso()
    ubicar(con_lugar_complemento(conf, True), poligonos, sesion,
           con_barrio(poligonos, "Laureles", complemento="APTO 301"))
    assert sesion.consultas == [CONSULTA]
