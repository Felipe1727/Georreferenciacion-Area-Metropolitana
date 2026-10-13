"""Escenarios de specs/consultas-proveedor: texto de las consultas y sesión de consultas, sin red."""
import csv
import dataclasses

import pytest
from opencage.geocoder import ForbiddenError, NotAuthorizedError, RateLimitExceededError, UnknownError

from conftest import resultado_api
from georef import geocodificacion
from georef.geocodificacion import (PENDIENTE, RESULTADO, SIN_RESULTADO, SesionConsultas, consulta_direccion,
                                    consulta_lugar, consulta_municipio)

MEDELLIN = "MEDELLIN - ANTIOQUIA"
NOMBRES_VIA = {"CL": "Calle", "CR": "Carrera", "AV": "Avenida", "CIR": "Circular", "DG": "Diagonal", "TV": "Transversal"}
PALABRAS_LUGAR = ("UNIDAD", "EDIFICIO", "URBANIZACION", "URB", "CONJUNTO", "CONDOMINIO", "PARQUE")


# Texto de la consulta

def test_formato_abreviado():
    # El complemento (APTO 301) no forma parte de la consulta: solo se pasa la dirección.
    assert consulta_direccion("CL 10 #20-30", MEDELLIN, "abreviado", NOMBRES_VIA) == \
        "CL 10 #20-30, MEDELLIN, ANTIOQUIA, Colombia"


def test_formato_expandido():
    assert consulta_direccion("CL 10 #20-30", MEDELLIN, "expandido", NOMBRES_VIA) == \
        "Calle 10 # 20-30, MEDELLIN, ANTIOQUIA, Colombia"


@pytest.mark.parametrize("direccion, esperada", [
    ("CL 45S #12-15", "Calle 45S # 12-15"),
    ("TV 32B #75-20", "Transversal 32B # 75-20"),
    ("CR 50", "Carrera 50"),
])
def test_formato_expandido_conserva_numeracion(direccion, esperada):
    assert consulta_direccion(direccion, MEDELLIN, "expandido", NOMBRES_VIA) == \
        f"{esperada}, MEDELLIN, ANTIOQUIA, Colombia"


@pytest.mark.parametrize("formato", ["abreviado", "expandido"])
def test_departamento_sin_repetir(formato):
    consulta = consulta_direccion("CL 10 #20-30", MEDELLIN, formato, NOMBRES_VIA)
    assert consulta.count("ANTIOQUIA") == 1


def test_consulta_con_el_lugar_del_complemento():
    consulta = consulta_lugar("APTO 301 UNIDAD LOS PINOS", "Laureles", MEDELLIN, PALABRAS_LUGAR)
    assert consulta == "UNIDAD LOS PINOS, LAURELES, MEDELLIN, ANTIOQUIA, Colombia"
    assert "APTO 301" not in consulta


def test_lugar_sin_barrio_declarado():
    assert consulta_lugar("EDIFICIO TORRES DEL RIO", None, MEDELLIN, PALABRAS_LUGAR) == \
        "EDIFICIO TORRES DEL RIO, MEDELLIN, ANTIOQUIA, Colombia"


@pytest.mark.parametrize("complemento", ["APTO 301", "", None])
def test_complemento_sin_lugar(complemento):
    assert consulta_lugar(complemento, "Laureles", MEDELLIN, PALABRAS_LUGAR) is None


def test_consulta_de_un_municipio():
    assert consulta_municipio("LA ESTRELLA - ANTIOQUIA") == "LA ESTRELLA, ANTIOQUIA, Colombia"


# Sesión de consultas

LLAVE = "llave-de-prueba-123"
RECUADRO = "-75.71935,6.16290,-75.47190,6.37490"


@pytest.fixture
def parametros(configuracion):
    return configuracion.ubicacion


@pytest.fixture
def nueva_sesion(tmp_path, parametros, cliente):
    """Crea sesiones que comparten la caché y el registro de `tmp_path`."""

    def _nueva(llave=LLAVE, operacion="ubicar", **cambios):
        return SesionConsultas(llave, dataclasses.replace(parametros, **cambios), tmp_path / "cache.csv",
                               tmp_path / "registro.csv", operacion)

    return _nueva


def filas(ruta):
    with open(ruta, encoding="utf-8", newline="") as archivo:
        return list(csv.DictReader(archivo))


def test_parametros_de_la_peticion(nueva_sesion, cliente):
    nueva_sesion().resolver("CL 10 #20-30, MEDELLIN, ANTIOQUIA, Colombia", bounds=RECUADRO)
    consulta, parametros = cliente.llamadas[0]
    assert parametros == {"raw_response": True, "countrycode": "co", "limit": 1, "no_annotations": 1,
                          "bounds": RECUADRO}


def test_peticion_sin_recuadro(nueva_sesion, cliente):
    nueva_sesion(operacion="municipios").resolver("BELLO, ANTIOQUIA, Colombia")
    assert "bounds" not in cliente.llamadas[0][1]


def test_primer_resultado(nueva_sesion, cliente):
    cliente.respuestas["A"] = [resultado_api(6.25, -75.58, tipo="road", confianza=9, texto="Calle 10"),
                               resultado_api(1, 1)]
    respuesta = nueva_sesion().resolver("A")
    assert (respuesta.estado, respuesta.latitud, respuesta.longitud) == (RESULTADO, 6.25, -75.58)
    assert (respuesta.tipo, respuesta.confianza, respuesta.texto) == ("road", 9, "Calle 10")


def test_pausa_entre_peticiones(nueva_sesion, cliente, reloj):
    sesion = nueva_sesion()
    for consulta in ("A", "B", "C"):
        sesion.resolver(consulta)
    assert all(b - a >= 1 for a, b in zip(cliente.inicios, cliente.inicios[1:]))


def test_pausa_tras_un_error(nueva_sesion, cliente, reloj):
    cliente.respuestas["A"] = UnknownError("500 status code from API")
    sesion = nueva_sesion()
    assert sesion.resolver("A").estado == PENDIENTE
    sesion.resolver("B")
    assert cliente.inicios[1] - cliente.inicios[0] >= 1


def test_sin_espera_si_ya_paso_la_pausa(nueva_sesion, cliente, reloj):
    sesion = nueva_sesion()
    sesion.resolver("A")
    reloj.ahora += 5  # la respuesta tardó 5 s
    sesion.resolver("B")
    assert reloj.esperas == []


def test_misma_direccion_en_dos_registros(nueva_sesion, cliente):
    cliente.respuestas["A"] = [resultado_api(6.25, -75.58)]
    sesion = nueva_sesion()
    assert sesion.resolver("A", registro=1) == sesion.resolver("A", registro=2)
    assert cliente.consultas == ["A"]
    assert (sesion.peticiones, sesion.desde_cache) == (1, 1)


def test_ejecucion_interrumpida(nueva_sesion, cliente):
    primera = nueva_sesion()
    consultas = [f"CL {i} #1-1, MEDELLIN, ANTIOQUIA, Colombia" for i in range(40)]
    for consulta in consultas:
        cliente.respuestas[consulta] = [resultado_api(6.2, -75.5)]
        primera.resolver(consulta)
    # La sesión no se cierra (como si el proceso se interrumpiera): cada línea ya está en la caché.
    segunda = nueva_sesion()
    respuestas = [segunda.resolver(c) for c in consultas]
    assert len(cliente.consultas) == 40
    assert segunda.peticiones == 0 and segunda.desde_cache == 40
    assert all(r.estado == RESULTADO and r.latitud == 6.2 for r in respuestas)


def test_consulta_sin_resultado(nueva_sesion, cliente, tmp_path):
    assert nueva_sesion().resolver("NADA").estado == SIN_RESULTADO
    assert nueva_sesion().resolver("NADA").estado == SIN_RESULTADO
    assert cliente.consultas == ["NADA"]
    assert filas(tmp_path / "cache.csv")[0]["estado"] == SIN_RESULTADO


def test_errores_no_se_guardan_en_cache(nueva_sesion, cliente):
    cliente.respuestas["A"] = UnknownError("Non-JSON result from server")
    nueva_sesion().resolver("A")
    cliente.respuestas["A"] = [resultado_api(6.2, -75.5)]
    assert nueva_sesion().resolver("A").estado == RESULTADO
    assert cliente.consultas == ["A", "A"]


def test_cuota_agotada(nueva_sesion, cliente):
    cliente.respuestas["B"] = RateLimitExceededError()
    sesion = nueva_sesion()
    estados = [sesion.resolver(c).estado for c in ("A", "B", "C", "D")]
    assert estados == [SIN_RESULTADO, PENDIENTE, PENDIENTE, PENDIENTE]
    assert cliente.consultas == ["A", "B"]
    assert sesion.parada == geocodificacion.PARADA_CUOTA
    assert sesion.pendientes == {"B", "C", "D"}


def test_cache_despues_de_una_parada(nueva_sesion, cliente):
    cliente.respuestas["A"] = [resultado_api(6.2, -75.5)]
    nueva_sesion().resolver("A")
    cliente.respuestas["B"] = RateLimitExceededError()
    sesion = nueva_sesion()
    sesion.resolver("B")
    assert sesion.resolver("A").estado == RESULTADO


def test_errores_seguidos(nueva_sesion, cliente):
    for consulta in ("A", "B", "C"):
        cliente.respuestas[consulta] = UnknownError("500 status code from API")
    sesion = nueva_sesion()
    for consulta in ("A", "B", "C", "D"):
        sesion.resolver(consulta)
    assert cliente.consultas == ["A", "B", "C"]
    assert sesion.parada == geocodificacion.PARADA_ERRORES


def test_error_aislado(nueva_sesion, cliente):
    cliente.respuestas["A"] = UnknownError("500 status code from API")
    sesion = nueva_sesion()
    estados = [sesion.resolver(c).estado for c in ("A", "B", "C")]
    assert estados == [PENDIENTE, SIN_RESULTADO, SIN_RESULTADO]
    assert sesion.parada is None and sesion.pendientes == {"A"}


def test_limite_por_ejecucion(nueva_sesion, cliente):
    sesion = nueva_sesion(limite_consultas=100)
    estados = [sesion.resolver(f"C{i}").estado for i in range(300)]
    assert len(cliente.consultas) == 100
    assert estados.count(PENDIENTE) == 200
    assert sesion.parada == geocodificacion.PARADA_LIMITE


@pytest.mark.parametrize("error", [NotAuthorizedError(), ForbiddenError()])
def test_llave_rechazada(nueva_sesion, cliente, capsys, error):
    cliente.respuestas["A"] = error
    with pytest.raises(SystemExit) as salida:
        nueva_sesion().resolver("A")
    assert "OPENCAGE_API_KEY" in str(salida.value.code)
    assert LLAVE not in str(salida.value.code) + capsys.readouterr().out


def test_sin_cliente(nueva_sesion, cliente):
    cliente.respuestas["A"] = [resultado_api(6.2, -75.5)]
    nueva_sesion().resolver("A")
    sesion = nueva_sesion(llave=None)
    assert sesion.resolver("A").estado == RESULTADO
    assert sesion.resolver("B").estado == PENDIENTE
    assert cliente.consultas == ["A"] and cliente.llaves == [LLAVE]


def test_registro_de_una_peticion_correcta(nueva_sesion, cliente, reloj, tmp_path):
    consulta = "CL 10 #20-30, MEDELLIN, ANTIOQUIA, Colombia"
    cliente.respuestas[consulta] = [resultado_api(6.25, -75.58, tipo="road", confianza=9)]
    nueva_sesion().resolver(consulta, registro=17)
    [fila] = filas(tmp_path / "registro.csv")
    assert (fila["operacion"], fila["registro"], fila["resultado"]) == ("ubicar", "17", RESULTADO)
    assert (fila["tipo"], fila["confianza"], fila["restantes"]) == ("road", "9", "2399")
    assert fila["duracion_ms"] == "0" and fila["fecha_hora_utc"].endswith("+00:00")
    contenido = (tmp_path / "registro.csv").read_text(encoding="utf-8")
    assert "CL 10" not in contenido and LLAVE not in contenido


def test_registro_de_una_peticion_con_error(nueva_sesion, cliente, tmp_path):
    cliente.respuestas["A"] = UnknownError("500 status code from API")
    nueva_sesion().resolver("A", registro=3)
    [fila] = filas(tmp_path / "registro.csv")
    assert fila["resultado"] == "UnknownError" and fila["restantes"] == ""
