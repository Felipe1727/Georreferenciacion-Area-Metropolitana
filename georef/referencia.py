"""Índice de barrios y comunas de Medellín para reconocer el lugar declarado en una dirección.

Se construye a partir del GeoJSON oficial (solo sus propiedades, leídas con `json`) y de las
tablas `data/alias_barrios.csv` y `data/alias_comunas.csv`. Implementa la convención de
normalización y la regla de nombres repetidos de la especificación `referencia-barrios`.
"""
import csv
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

# Zona de la dirección -> valor de indicador_ur en el GeoJSON
LETRA_ZONA = {"URBANO": "U", "RURAL": "R"}

# Longitud máxima, en palabras, de un nombre que se busca al final del texto.
MAXIMO_PALABRAS = 8

# Número (con letra opcional) que puede seguir al nombre del barrio: FATIMA 4, LAURELES 2A.
NUMERO_FINAL = re.compile(r"\d+[A-Z]?")


def normalizar(texto) -> str:
    """Normaliza un nombre para compararlo: mayúsculas, sin diacríticos ni puntuación y con espacios simples."""
    if texto is None:
        return ""
    descompuesto = unicodedata.normalize("NFKD", str(texto).upper())
    sin_diacriticos = "".join(c for c in descompuesto if not unicodedata.combining(c))
    sin_puntuacion = re.sub(r"[^\w\s]|_", " ", sin_diacriticos)
    return re.sub(r"\s+", " ", sin_puntuacion).strip()


class ErrorReferencia(Exception):
    """No se pudo leer un archivo de referencia o su contenido no es coherente."""


@dataclass(frozen=True)
class Lugar:
    """
    Lugar reconocido al final de una lista de palabras.

    Las palabras `[inicio:fin]` forman el nombre reconocido; las de `[fin:]` son números finales
    que no forman parte del nombre. `barrio` es el nombre oficial (vacío si solo se reconoció una
    comuna); `codigo` y `comuna` quedan vacíos si el barrio es ambiguo.
    """

    inicio: int
    fin: int
    barrio: str
    codigo: str
    comuna: str


class IndiceLugares:
    """Nombres de barrios, alias y comunas de Medellín, cargados una vez por ejecución."""

    def __init__(self, ruta_geojson, ruta_alias_barrios, ruta_alias_comunas):
        propiedades = [f["properties"] for f in _leer_json(Path(ruta_geojson))["features"]]

        # codigo -> (nombre oficial sin espacios sobrantes, nombre_comuna, indicador_ur)
        self._poligonos = {
            p["codigo"]: (p["nombre_barrio"].strip(), p["nombre_comuna"], p["indicador_ur"]) for p in propiedades
        }
        self._codigos_por_nombre = {}
        for codigo, (nombre, _, _) in self._poligonos.items():
            self._codigos_por_nombre.setdefault(normalizar(nombre), []).append(codigo)

        self._alias_barrios = {}
        for fila in _leer_csv(Path(ruta_alias_barrios), ["alias", "codigo"]):
            if fila["codigo"] not in self._poligonos:
                raise ErrorReferencia(f"El alias '{fila['alias']}' de '{ruta_alias_barrios}' apunta al código "
                                      f"'{fila['codigo']}', que no existe en el GeoJSON.")
            self._alias_barrios[fila["alias"]] = fila["codigo"]

        comunas = {comuna for _, comuna, _ in self._poligonos.values()}
        # Comunas o corregimientos sin ningún barrio con su mismo nombre (SAN ANTONIO DE PRADO...).
        self._comunas = {normalizar(c): c for c in comunas if normalizar(c) not in self._codigos_por_nombre}
        for fila in _leer_csv(Path(ruta_alias_comunas), ["alias", "comuna"]):
            if fila["comuna"] not in comunas:
                raise ErrorReferencia(f"La variante '{fila['alias']}' de '{ruta_alias_comunas}' apunta a la comuna "
                                      f"'{fila['comuna']}', que no existe en el GeoJSON.")
            self._comunas[fila["alias"]] = fila["comuna"]

        self._nombres = set(self._codigos_por_nombre) | set(self._alias_barrios) | set(self._comunas)

    @classmethod
    def desde_configuracion(cls, referencia):
        """Construye el índice con las rutas de la sección `[referencia]` de la configuración."""
        return cls(referencia.geojson, referencia.alias_barrios, referencia.alias_comunas)

    def resolver(self, nombre: str, zona) -> str | None:
        """
        Devuelve el código del polígono para un nombre de barrio normalizado y una zona, o None.

        Un alias fija su polígono. Si el nombre corresponde a varios polígonos, se elige el de
        `indicador_ur` igual a la zona (`URBANO` -> `U`, `RURAL` -> `R`); si queda más de uno, o no
        hay zona, el barrio queda sin resolver.
        """
        if nombre in self._alias_barrios:
            return self._alias_barrios[nombre]
        candidatos = self._codigos_por_nombre.get(nombre, [])
        if len(candidatos) == 1:
            return candidatos[0]
        if not candidatos or zona not in LETRA_ZONA:
            return None
        por_zona = [c for c in candidatos if self._poligonos[c][2] == LETRA_ZONA[zona]]
        return por_zona[0] if len(por_zona) == 1 else None

    def reconocer(self, palabras, zona) -> Lugar | None:
        """
        Busca al final de `palabras` el nombre más largo que sea un barrio, un alias o una comuna.

        Si no hay ninguno, lo reintenta sin los números finales. Devuelve None si no reconoce nada.
        """
        palabras = list(palabras)
        lugar = self._sufijo_mas_largo(palabras, len(palabras), zona)
        if lugar is None:
            fin = len(palabras)
            while fin and NUMERO_FINAL.fullmatch(normalizar(palabras[fin - 1])):
                fin -= 1
            if fin < len(palabras):
                lugar = self._sufijo_mas_largo(palabras, fin, zona)
        return lugar

    def _sufijo_mas_largo(self, palabras, fin, zona):
        for inicio in range(max(0, fin - MAXIMO_PALABRAS), fin):
            nombre = normalizar(" ".join(palabras[inicio:fin]))
            if nombre in self._nombres:
                return self._lugar(nombre, zona, inicio, fin)
        return None

    def _lugar(self, nombre, zona, inicio, fin):
        if nombre in self._comunas:
            return Lugar(inicio, fin, barrio="", codigo="", comuna=self._comunas[nombre])
        codigo = self.resolver(nombre, zona)
        if codigo is None:
            # Nombre repetido sin resolver: se conserva el nombre oficial, sin código ni comuna.
            oficial = self._poligonos[self._codigos_por_nombre[nombre][0]][0]
            return Lugar(inicio, fin, barrio=oficial, codigo="", comuna="")
        oficial, comuna, _ = self._poligonos[codigo]
        return Lugar(inicio, fin, barrio=oficial, codigo=codigo, comuna=comuna)


def _leer_json(ruta: Path):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ErrorReferencia(f"No se encontró el archivo de referencia '{ruta.as_posix()}'.") from None


def _leer_csv(ruta: Path, columnas):
    try:
        with open(ruta, encoding="utf-8", newline="") as archivo:
            lector = csv.DictReader(archivo)
            filas = list(lector)
            encabezado = lector.fieldnames or []
    except FileNotFoundError:
        raise ErrorReferencia(f"No se encontró el archivo de referencia '{ruta.as_posix()}'.") from None
    faltantes = [c for c in columnas if c not in encabezado]
    if faltantes:
        raise ErrorReferencia(f"Al archivo '{ruta.as_posix()}' le faltan las columnas {faltantes}.")
    return filas
