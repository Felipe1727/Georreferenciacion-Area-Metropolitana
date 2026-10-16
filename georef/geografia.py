"""Polígonos de barrios, comunas y municipio de Medellín para la ubicación por niveles.

Lee las geometrías de `data/limite_barrio_vereda_cata.geojson` con `json` y `shapely`, sin
geopandas ni GDAL (que, sin activar el entorno conda, no encuentran la base de datos de PROJ).
Las operaciones métricas (puntos representativos y distancias) se hacen en el sistema de
coordenadas del archivo, EPSG:9377, que mide en metros; los puntos se entregan en WGS84
(latitud y longitud). Para los mapas, los polígonos se entregan en WGS84 y simplificados.
"""
import functools
import json
from pathlib import Path

import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import mapping, shape

from georef.referencia import ErrorReferencia

WGS84 = "EPSG:4326"
# Simplificación de los polígonos para dibujarlos en los mapas: tolerancia en metros (CRS del
# archivo) y rejilla de las coordenadas WGS84 en grados (1e-5 grados, aproximadamente 1 m).
TOLERANCIA_DIBUJO_METROS = 5
PRECISION_DIBUJO_GRADOS = 1e-5


class Poligonos:
    """Polígonos de barrios (por `codigo`), de comunas (unión de sus barrios) y del municipio."""

    def __init__(self, ruta_geojson):
        ruta = Path(ruta_geojson)
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise ErrorReferencia(f"No se encontró el archivo de referencia '{ruta.as_posix()}'.") from None
        crs = (datos.get("crs") or {}).get("properties", {}).get("name")
        if not crs:
            raise ErrorReferencia(f"El GeoJSON '{ruta.as_posix()}' no declara su sistema de coordenadas.")

        # codigo -> geometría en el CRS del archivo; codigo -> (nombre oficial, nombre_comuna)
        self._barrios = {}
        self._nombres = {}
        for feature in datos["features"]:
            propiedades = feature["properties"]
            codigo = propiedades["codigo"]
            self._barrios[codigo] = shape(feature["geometry"])
            self._nombres[codigo] = (propiedades["nombre_barrio"].strip(), propiedades["nombre_comuna"])

        por_comuna = {}
        for codigo, (_, comuna) in self._nombres.items():
            por_comuna.setdefault(comuna, []).append(self._barrios[codigo])
        self._comunas = {comuna: shapely.union_all(geometrias) for comuna, geometrias in por_comuna.items()}
        self.municipio = shapely.union_all(list(self._barrios.values()))

        self._a_wgs84 = Transformer.from_crs(crs, WGS84, always_xy=True)
        self._desde_wgs84 = Transformer.from_crs(WGS84, crs, always_xy=True)

        self._codigos = list(self._barrios)
        self._arbol = shapely.STRtree([self._barrios[codigo] for codigo in self._codigos])
        self._puntos = {}
        self._geojson = {}

    @classmethod
    def cargar(cls, ruta_geojson):
        """
        Devuelve los polígonos de `ruta_geojson`, construidos una sola vez por proceso.

        Construirlos tarda unos segundos (unión de comunas y municipio); la caché se invalida si
        el archivo cambia.
        """
        ruta = Path(ruta_geojson).resolve()
        if not ruta.exists():
            return cls(ruta_geojson)  # lanza ErrorReferencia con la ruta indicada
        return _cargar(ruta, ruta.stat().st_mtime_ns)

    @property
    def codigos(self):
        """Códigos de los barrios, como texto (con sus ceros a la izquierda)."""
        return tuple(self._codigos)

    @property
    def comunas(self):
        """Nombres de las comunas y corregimientos."""
        return tuple(self._comunas)

    def geometria_barrio(self, codigo):
        """Polígono del barrio `codigo`, en el CRS del archivo."""
        return self._barrios[codigo]

    def geometria_comuna(self, comuna):
        """Unión de los polígonos de los barrios de `comuna`, en el CRS del archivo."""
        return self._comunas[comuna]

    def nombre_barrio(self, codigo):
        """(nombre oficial, comuna) del barrio `codigo`."""
        return self._nombres[codigo]

    def punto_barrio(self, codigo):
        """Punto representativo del barrio, como (latitud, longitud)."""
        return self._punto(("barrio", codigo), self._barrios[codigo])

    def punto_comuna(self, comuna):
        """Punto representativo de la unión de los barrios de la comuna, como (latitud, longitud)."""
        return self._punto(("comuna", comuna), self._comunas[comuna])

    def a_metros(self, latitud, longitud):
        """Punto WGS84 convertido al CRS del archivo (en metros)."""
        x, y = self._desde_wgs84.transform(longitud, latitud)
        return shapely.Point(x, y)

    def a_wgs84(self, punto):
        """Punto del CRS del archivo convertido a (latitud, longitud)."""
        longitud, latitud = self._a_wgs84.transform(punto.x, punto.y)
        return latitud, longitud

    def distancia(self, latitud, longitud, geometria):
        """Distancia en metros del punto WGS84 a `geometria` (0 si está dentro)."""
        return geometria.distance(self.a_metros(latitud, longitud))

    def barrio_en(self, latitud, longitud):
        """Código del barrio que contiene el punto WGS84, o None si cae fuera de todos."""
        punto = self.a_metros(latitud, longitud)
        indices = self._arbol.query(punto, predicate="within")
        # predicate="within" devuelve las geometrías del árbol para las que el punto está dentro.
        return self._codigos[indices[0]] if len(indices) else None

    def recuadro(self):
        """Recuadro WGS84 del municipio para el parámetro `bounds` de OpenCage: 'min_lng,min_lat,max_lng,max_lat'."""
        min_lng, min_lat, max_lng, max_lat = self._en_wgs84(self.municipio).bounds
        # Redondeo hacia fuera para que el recuadro contenga todo el municipio.
        return ",".join(f"{v:.5f}" for v in (np.floor(min_lng * 1e5) / 1e5, np.floor(min_lat * 1e5) / 1e5,
                                             np.ceil(max_lng * 1e5) / 1e5, np.ceil(max_lat * 1e5) / 1e5))

    def limites_wgs84(self):
        """Límites WGS84 del municipio para encuadrar un mapa: [[min_lat, min_lng], [max_lat, max_lng]]."""
        min_lng, min_lat, max_lng, max_lat = self._en_wgs84(self.municipio).bounds
        return [[min_lat, min_lng], [max_lat, max_lng]]

    def geojson(self, tipo):
        """
        FeatureCollection en WGS84 de los barrios (`tipo="barrios"`) o de las comunas (`"comunas"`)
        para dibujar en un mapa.

        Cada geometría se simplifica con una tolerancia de `TOLERANCIA_DIBUJO_METROS` en el CRS del
        archivo y se redondea a la rejilla `PRECISION_DIBUJO_GRADOS`. Propiedades: `codigo`, `nombre`
        y `comuna` en los barrios, y `nombre` en las comunas. Se calcula una vez por instancia: quien
        quiera modificarlo debe trabajar sobre una copia.
        """
        if tipo not in ("barrios", "comunas"):
            raise ValueError(f"tipo de polígonos desconocido: {tipo!r}")
        if tipo not in self._geojson:
            if tipo == "barrios":
                elementos = [(self._barrios[codigo], {"codigo": codigo, "nombre": self._nombres[codigo][0],
                                                      "comuna": self._nombres[codigo][1]})
                             for codigo in self._codigos]
            else:
                elementos = [(geometria, {"nombre": comuna}) for comuna, geometria in self._comunas.items()]
            self._geojson[tipo] = {"type": "FeatureCollection", "features": [
                {"type": "Feature", "properties": propiedades, "geometry": mapping(self._para_dibujar(geometria))}
                for geometria, propiedades in elementos
            ]}
        return self._geojson[tipo]

    def _para_dibujar(self, geometria):
        simplificada = geometria.simplify(TOLERANCIA_DIBUJO_METROS)
        return shapely.set_precision(self._en_wgs84(simplificada), PRECISION_DIBUJO_GRADOS)

    def _en_wgs84(self, geometria):
        return shapely.transform(
            geometria, lambda xy: np.column_stack(self._a_wgs84.transform(xy[:, 0], xy[:, 1]))
        )

    def _punto(self, clave, geometria):
        if clave not in self._puntos:
            self._puntos[clave] = self.a_wgs84(geometria.representative_point())
        return self._puntos[clave]


@functools.lru_cache(maxsize=4)
def _cargar(ruta, modificado):
    # `modificado` solo forma parte de la clave de la caché.
    return Poligonos(ruta)
