"""Carga y validación del archivo de configuración (`config/georef.toml`).

La configuración se valida entera antes de devolverla: si hay errores, se lanza
`ErrorConfiguracion` con todos ellos, cada uno con la ruta de su clave. Los valores
se devuelven en dataclasses congeladas con tuplas, para que ninguna etapa pueda
modificarlos.
"""
import datetime
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

RUTA_POR_DEFECTO = Path("config") / "georef.toml"

# Identificador del universo de trabajo; da nombre a sus archivos (D5 del diseño).
AREA_METROPOLITANA = "area_metropolitana"

# El nombre de un subconjunto forma parte de nombres de archivo: solo ASCII sencillo.
PATRON_NOMBRE_SUBCONJUNTO = re.compile(r"[a-z0-9_]+")

# Formatos del texto de las consultas a OpenCage (ver georef.geocodificacion).
FORMATOS_CONSULTA = ("abreviado", "expandido")

CLAVES_UBICACION = {
    "formato_consulta", "confianza_minima", "tipos_rechazados", "tolerancia_metros", "pausa_segundos",
    "limite_consultas", "consulta_lugar_complemento", "palabras_lugar", "nombres_via",
}


class ErrorConfiguracion(Exception):
    """La configuración no se pudo leer o no es válida. `errores` contiene un texto por problema."""

    def __init__(self, ruta, errores):
        self.ruta = Path(ruta)
        self.errores = list(errores)
        super().__init__(self.mensaje())

    def mensaje(self):
        lineas = "\n".join(f"  - {error}" for error in self.errores)
        return f"Error en la configuración '{self.ruta.as_posix()}':\n{lineas}"


@dataclass(frozen=True)
class Columnas:
    """Nombres de las columnas del archivo de entrada que usa el programa."""

    ciudad: str
    direccion: str


@dataclass(frozen=True)
class VocabularioDirecciones:
    """Vocabulario de la estandarización de direcciones."""

    tipos_via: tuple[str, ...]
    palabras_clave: tuple[str, ...]
    equivalencias: tuple[tuple[str, str], ...]

    @property
    def palabras_clave_completas(self) -> tuple[str, ...]:
        """Tipos de vía más palabras clave: lo que forma parte de la dirección y no del complemento."""
        return self.tipos_via + self.palabras_clave


@dataclass(frozen=True)
class Referencia:
    """Datos de referencia geográfica: polígonos de barrios, tablas de alias y su municipio."""

    geojson: Path
    alias_barrios: Path
    alias_comunas: Path
    municipio_con_poligonos: str


@dataclass(frozen=True)
class ParametrosUbicacion:
    """Parámetros de la ubicación por niveles y de las consultas a OpenCage (sección `[ubicacion]`)."""

    formato_consulta: str
    confianza_minima: int
    tipos_rechazados: tuple[str, ...]
    tolerancia_metros: float
    pausa_segundos: float
    limite_consultas: int
    consulta_lugar_complemento: bool
    palabras_lugar: tuple[str, ...]
    nombres_via: Mapping[str, str]


@dataclass(frozen=True)
class PuntoMunicipio:
    """Punto fijo de un municipio (nivel MUNICIPIO de la ubicación), con su procedencia."""

    latitud: float
    longitud: float
    fuente: str
    fecha: str


@dataclass(frozen=True)
class Configuracion:
    """Configuración validada del proyecto."""

    area_metropolitana: tuple[str, ...]
    subconjuntos: Mapping[str, tuple[str, ...]]
    columnas: Columnas
    direcciones: VocabularioDirecciones
    referencia: Referencia
    ubicacion: ParametrosUbicacion
    # Vacío mientras no se ejecute `consultar-municipios` ni se escriban a mano.
    puntos_municipios: Mapping[str, PuntoMunicipio]
    ruta: Path


def cargar_configuracion(ruta=RUTA_POR_DEFECTO) -> Configuracion:
    """Lee y valida el archivo TOML de `ruta`.

    Raises:
        ErrorConfiguracion: si el archivo no existe, no es TOML válido o no cumple la estructura esperada.
    """
    ruta = Path(ruta)
    try:
        datos = tomllib.loads(ruta.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ErrorConfiguracion(ruta, ["no existe el archivo"]) from None
    except tomllib.TOMLDecodeError as error:
        raise ErrorConfiguracion(ruta, [f"sintaxis TOML inválida: {error}"]) from None
    except UnicodeDecodeError:
        raise ErrorConfiguracion(ruta, ["el archivo no está en UTF-8"]) from None
    except OSError as error:
        raise ErrorConfiguracion(ruta, [f"no se pudo leer el archivo: {error.strerror}"]) from None

    errores = []
    configuracion = _validar(datos, ruta, errores)
    if errores:
        raise ErrorConfiguracion(ruta, errores)
    return configuracion


def _validar(datos, ruta, errores):
    """Comprueba la estructura de `datos` y devuelve la Configuracion; añade a `errores` cada problema."""
    _claves_desconocidas(datos, "", {"area_metropolitana", "subconjuntos", "columnas", "direcciones", "referencia",
                                     "ubicacion", "puntos_municipios"}, errores)

    area = _tabla(datos, "area_metropolitana", {"municipios"}, errores)
    municipios_am = _lista_textos(area, "municipios", "area_metropolitana", errores)

    subconjuntos = {}
    tabla_subconjuntos = _tabla(datos, "subconjuntos", None, errores, obligatoria=False) or {}
    for nombre in tabla_subconjuntos:
        clave = f"subconjuntos.{nombre}"
        if not PATRON_NOMBRE_SUBCONJUNTO.fullmatch(nombre) or nombre == AREA_METROPOLITANA:
            errores.append(f"{clave}: nombre no válido; usa solo minúsculas sin tildes, dígitos y guiones bajos, "
                           f"y no '{AREA_METROPOLITANA}'")
        subconjunto = _tabla(tabla_subconjuntos, nombre, {"municipios"}, errores, prefijo="subconjuntos")
        municipios = _lista_textos(subconjunto, "municipios", clave, errores)
        for municipio in municipios:
            if municipios_am and municipio not in municipios_am:
                errores.append(f"{clave}.municipios: '{municipio}' no pertenece al área metropolitana")
        subconjuntos[nombre] = municipios

    tabla_columnas = _tabla(datos, "columnas", {"ciudad", "direccion"}, errores)
    columnas = Columnas(
        ciudad=_texto(tabla_columnas, "ciudad", "columnas", errores),
        direccion=_texto(tabla_columnas, "direccion", "columnas", errores),
    )

    tabla_direcciones = _tabla(datos, "direcciones", {"tipos_via", "palabras_clave", "equivalencias"}, errores)
    tipos_via = _lista_textos(tabla_direcciones, "tipos_via", "direcciones", errores)
    palabras_clave = _lista_textos(tabla_direcciones, "palabras_clave", "direcciones", errores, admite_vacia=True)
    for palabra in sorted(set(tipos_via) & set(palabras_clave)):
        errores.append(f"direcciones: '{palabra}' está a la vez en tipos_via y en palabras_clave")
    equivalencias = _equivalencias(tabla_direcciones, errores)

    claves_referencia = {"geojson", "alias_barrios", "alias_comunas", "municipio_con_poligonos"}
    tabla_referencia = _tabla(datos, "referencia", claves_referencia, errores)
    referencia = Referencia(
        geojson=Path(_texto(tabla_referencia, "geojson", "referencia", errores)),
        alias_barrios=Path(_texto(tabla_referencia, "alias_barrios", "referencia", errores)),
        alias_comunas=Path(_texto(tabla_referencia, "alias_comunas", "referencia", errores)),
        municipio_con_poligonos=_texto(tabla_referencia, "municipio_con_poligonos", "referencia", errores),
    )
    if municipios_am and referencia.municipio_con_poligonos and \
            referencia.municipio_con_poligonos not in municipios_am:
        errores.append(f"referencia.municipio_con_poligonos: '{referencia.municipio_con_poligonos}' "
                       "no pertenece al área metropolitana")

    ubicacion = _ubicacion(_tabla(datos, "ubicacion", CLAVES_UBICACION, errores), tipos_via, errores)
    puntos = _puntos_municipios(_tabla(datos, "puntos_municipios", None, errores, obligatoria=False),
                                municipios_am, errores)

    return Configuracion(
        area_metropolitana=municipios_am,
        subconjuntos=MappingProxyType(subconjuntos),
        columnas=columnas,
        direcciones=VocabularioDirecciones(tipos_via, palabras_clave, equivalencias),
        referencia=referencia,
        ubicacion=ubicacion,
        puntos_municipios=puntos,
        ruta=ruta,
    )


def _puntos_municipios(tabla, municipios_am, errores):
    """Devuelve los puntos de `[puntos_municipios]` (municipio -> PuntoMunicipio); la sección es opcional."""
    puntos = {}
    for municipio, valor in (tabla or {}).items():
        clave = f'puntos_municipios."{municipio}"'
        if municipios_am and municipio not in municipios_am:
            errores.append(f"{clave}: '{municipio}' no pertenece al área metropolitana")
            continue
        if not isinstance(valor, dict):
            errores.append(f"{clave}: debe ser una tabla {{ latitud = ..., longitud = ..., fuente = \"...\", "
                           "fecha = \"...\" }")
            continue
        _claves_desconocidas(valor, f"{clave}.", {"latitud", "longitud", "fuente", "fecha"}, errores)
        latitud = _numero(valor, "latitud", clave, errores)
        if latitud is not None and not -90 <= latitud <= 90:
            errores.append(f"{clave}.latitud: debe estar entre -90 y 90")
            latitud = None
        longitud = _numero(valor, "longitud", clave, errores)
        if longitud is not None and not -180 <= longitud <= 180:
            errores.append(f"{clave}.longitud: debe estar entre -180 y 180")
            longitud = None
        fuente = _texto(valor, "fuente", clave, errores)
        # La fecha puede escribirse como texto ("2026-10-12") o como fecha TOML (2026-10-12).
        fecha = valor.get("fecha")
        if isinstance(fecha, (datetime.date, datetime.datetime)):
            fecha = fecha.isoformat()
        elif "fecha" in valor:
            fecha = _texto(valor, "fecha", clave, errores)
        else:
            errores.append(f"{clave}.fecha: falta esta clave")
        if None not in (latitud, longitud) and fuente and fecha:
            puntos[municipio] = PuntoMunicipio(float(latitud), float(longitud), fuente, fecha)
    return MappingProxyType(puntos)


def _ubicacion(tabla, tipos_via, errores):
    """Devuelve los ParametrosUbicacion de la sección `[ubicacion]` (o None si falta), validando cada valor."""
    if tabla is None:  # la sección ya se informó como ausente o inválida
        return None
    seccion = "ubicacion"

    formato = _texto(tabla, "formato_consulta", seccion, errores)
    if formato and formato not in FORMATOS_CONSULTA:
        errores.append(f"ubicacion.formato_consulta: '{formato}' no es válido; usa "
                       + " o ".join(f"'{f}'" for f in FORMATOS_CONSULTA))

    confianza = _numero(tabla, "confianza_minima", seccion, errores, entero=True)
    if confianza is not None and not 0 <= confianza <= 10:
        errores.append("ubicacion.confianza_minima: debe ser un entero de 0 a 10")
    tolerancia = _numero(tabla, "tolerancia_metros", seccion, errores)
    if tolerancia is not None and tolerancia < 0:
        errores.append("ubicacion.tolerancia_metros: no puede ser negativa")
    pausa = _numero(tabla, "pausa_segundos", seccion, errores)
    if pausa is not None and pausa < 0:
        errores.append("ubicacion.pausa_segundos: no puede ser negativa")
    limite = _numero(tabla, "limite_consultas", seccion, errores, entero=True)
    if limite is not None and limite <= 0:
        errores.append("ubicacion.limite_consultas: debe ser un entero positivo")

    lugar_complemento = False
    if "consulta_lugar_complemento" not in tabla:
        errores.append("ubicacion.consulta_lugar_complemento: falta esta clave")
    elif not isinstance(tabla["consulta_lugar_complemento"], bool):
        errores.append("ubicacion.consulta_lugar_complemento: debe ser true o false")
    else:
        lugar_complemento = tabla["consulta_lugar_complemento"]

    tipos_rechazados = _lista_textos(tabla, "tipos_rechazados", seccion, errores, admite_vacia=True)
    palabras_lugar = _lista_textos(tabla, "palabras_lugar", seccion, errores, admite_vacia=True)
    nombres_via = _nombres_via(tabla, tipos_via, errores)

    return ParametrosUbicacion(
        formato_consulta=formato,
        confianza_minima=confianza,
        tipos_rechazados=tipos_rechazados,
        tolerancia_metros=tolerancia,
        pausa_segundos=pausa,
        limite_consultas=limite,
        consulta_lugar_complemento=lugar_complemento,
        palabras_lugar=palabras_lugar,
        nombres_via=nombres_via,
    )


def _numero(tabla, clave, seccion, errores, entero=False):
    """Devuelve `tabla[clave]` si es un número (entero si `entero`), o None tras informar del error."""
    nombre = f"{seccion}.{clave}"
    if clave not in tabla:
        errores.append(f"{nombre}: falta esta clave")
        return None
    valor = tabla[clave]
    tipos = (int,) if entero else (int, float)
    if isinstance(valor, bool) or not isinstance(valor, tipos):
        errores.append(f"{nombre}: debe ser un {'entero' if entero else 'número'}")
        return None
    return valor


def _nombres_via(tabla, tipos_via, errores):
    """Devuelve `nombres_via` (tipo de vía -> nombre completo) y comprueba que cubre todos los tipos de vía."""
    nombre = "ubicacion.nombres_via"
    if "nombres_via" not in tabla:
        errores.append(f"{nombre}: falta esta clave")
        return MappingProxyType({})
    valor = tabla["nombres_via"]
    if not isinstance(valor, dict):
        errores.append(f"{nombre}: debe ser una tabla {{ CL = \"Calle\", ... }}")
        return MappingProxyType({})
    nombres = {}
    for tipo, texto in valor.items():
        if not isinstance(texto, str) or not texto.strip():
            errores.append(f"{nombre}.{tipo}: debe ser un texto no vacío")
        elif tipos_via and tipo not in tipos_via:  # sin tipos_via válidos, el error ya se informó
            errores.append(f"{nombre}.{tipo}: no es un tipo de vía de direcciones.tipos_via")
        else:
            nombres[tipo] = texto
    for tipo in tipos_via:
        if tipo not in valor:
            errores.append(f"{nombre}: falta el nombre del tipo de vía '{tipo}'")
    return MappingProxyType(nombres)


def _claves_desconocidas(tabla, prefijo, permitidas, errores):
    for clave in tabla:
        if clave not in permitidas:
            errores.append(f"{prefijo}{clave}: clave desconocida")


def _tabla(datos, clave, permitidas, errores, obligatoria=True, prefijo=""):
    """Devuelve la tabla `datos[clave]`, o None si falta o no es una tabla, y comprueba sus claves."""
    nombre = f"{prefijo}.{clave}" if prefijo else clave
    if clave not in datos:
        if obligatoria:
            errores.append(f"{nombre}: falta esta sección")
        return None
    tabla = datos[clave]
    if not isinstance(tabla, dict):
        errores.append(f"{nombre}: debe ser una sección ([{nombre}])")
        return None
    if permitidas is not None:
        _claves_desconocidas(tabla, f"{nombre}.", permitidas, errores)
    return tabla


def _texto(tabla, clave, seccion, errores):
    if tabla is None:  # la sección ya se informó como ausente o inválida
        return ""
    if clave not in tabla:
        errores.append(f"{seccion}.{clave}: falta esta clave")
        return ""
    valor = tabla[clave]
    if not isinstance(valor, str) or not valor.strip():
        errores.append(f"{seccion}.{clave}: debe ser un texto no vacío")
        return ""
    return valor


def _lista_textos(tabla, clave, seccion, errores, admite_vacia=False):
    """Devuelve la lista `tabla[clave]` como tupla de textos, informando de vacíos, tipos y repetidos."""
    nombre = f"{seccion}.{clave}"
    if tabla is None:  # la sección ya se informó como ausente o inválida
        return ()
    if clave not in tabla:
        errores.append(f"{nombre}: falta esta clave")
        return ()
    valor = tabla[clave]
    if not isinstance(valor, list):
        errores.append(f"{nombre}: debe ser una lista de textos")
        return ()
    if not valor and not admite_vacia:
        errores.append(f"{nombre}: la lista está vacía")
    textos = []
    for i, elemento in enumerate(valor):
        if not isinstance(elemento, str) or not elemento.strip():
            errores.append(f"{nombre}[{i}]: debe ser un texto no vacío")
        else:
            textos.append(elemento)
    for repetido in sorted({t for t in textos if textos.count(t) > 1}):
        errores.append(f"{nombre}: '{repetido}' está repetido")
    return tuple(textos)


def _equivalencias(tabla, errores):
    """Devuelve las equivalencias como tupla de pares, en el orden del archivo."""
    nombre = "direcciones.equivalencias"
    if tabla is None:  # la sección ya se informó como ausente o inválida
        return ()
    if "equivalencias" not in tabla:
        errores.append(f"{nombre}: falta esta clave")
        return ()
    valor = tabla["equivalencias"]
    if not isinstance(valor, list):
        errores.append(f"{nombre}: debe ser una lista de pares [\"PALABRA\", \"ABREVIATURA\"]")
        return ()
    pares = []
    for i, par in enumerate(valor):
        if (not isinstance(par, list) or len(par) != 2
                or not all(isinstance(t, str) for t in par) or not par[0].strip()):
            errores.append(f"{nombre}[{i}]: debe ser un par [\"PALABRA\", \"ABREVIATURA\"]")
        else:
            pares.append((par[0], par[1]))
    palabras = [palabra for palabra, _ in pares]
    for repetida in sorted({p for p in palabras if palabras.count(p) > 1}):
        errores.append(f"{nombre}: '{repetida}' tiene más de una equivalencia")
    return tuple(pares)
