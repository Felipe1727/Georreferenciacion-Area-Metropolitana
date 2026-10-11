"""Carga y validación del archivo de configuración (`config/georef.toml`).

La configuración se valida entera antes de devolverla: si hay errores, se lanza
`ErrorConfiguracion` con todos ellos, cada uno con la ruta de su clave. Los valores
se devuelven en dataclasses congeladas con tuplas, para que ninguna etapa pueda
modificarlos.
"""
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
class Configuracion:
    """Configuración validada del proyecto."""

    area_metropolitana: tuple[str, ...]
    subconjuntos: Mapping[str, tuple[str, ...]]
    columnas: Columnas
    direcciones: VocabularioDirecciones
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
    _claves_desconocidas(datos, "", {"area_metropolitana", "subconjuntos", "columnas", "direcciones"}, errores)

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

    return Configuracion(
        area_metropolitana=municipios_am,
        subconjuntos=MappingProxyType(subconjuntos),
        columnas=columnas,
        direcciones=VocabularioDirecciones(tipos_via, palabras_clave, equivalencias),
        ruta=ruta,
    )


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
