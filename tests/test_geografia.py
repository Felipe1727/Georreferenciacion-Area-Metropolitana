"""Geometrías del GeoJSON real para la ubicación por niveles (georef.geografia)."""
import json
import os
from pathlib import Path

import pytest

from conftest import desplazado
from georef.geografia import Poligonos
from georef.referencia import ErrorReferencia

GEOJSON = Path(__file__).resolve().parent.parent / "data" / "limite_barrio_vereda_cata.geojson"


@pytest.fixture(scope="module")
def poligonos():
    return Poligonos(GEOJSON)


def codigo_de(poligonos, nombre):
    """Código del único barrio con ese nombre oficial."""
    codigos = [c for c in poligonos.codigos if poligonos.nombre_barrio(c)[0] == nombre]
    assert len(codigos) == 1, nombre
    return codigos[0]


def test_barrio_de_forma_concava(poligonos):
    # Hay barrios cuyo centroide cae fuera del propio polígono; su punto representativo, no.
    concavos = [c for c in poligonos.codigos
                if not poligonos.geometria_barrio(c).contains(poligonos.geometria_barrio(c).centroid)]
    assert concavos
    for codigo in concavos:
        latitud, longitud = poligonos.punto_barrio(codigo)
        assert poligonos.geometria_barrio(codigo).contains(poligonos.a_metros(latitud, longitud))


def test_puntos_representativos_dentro(poligonos):
    for codigo in poligonos.codigos:
        assert poligonos.distancia(*poligonos.punto_barrio(codigo), poligonos.geometria_barrio(codigo)) == 0
    for comuna in poligonos.comunas:
        assert poligonos.distancia(*poligonos.punto_comuna(comuna), poligonos.geometria_comuna(comuna)) == 0


def test_puntos_en_wgs84_dentro_de_medellin(poligonos):
    latitud, longitud = poligonos.punto_barrio(codigo_de(poligonos, "Laureles"))
    assert 6.1 < latitud < 6.4 and -75.8 < longitud < -75.4


def test_distancia_en_metros(poligonos):
    laureles = poligonos.geometria_barrio(codigo_de(poligonos, "Laureles"))
    assert poligonos.distancia(*poligonos.punto_barrio(codigo_de(poligonos, "Laureles")), laureles) == 0
    assert poligonos.distancia(*desplazado(poligonos, laureles, 120), laureles) == pytest.approx(120, abs=1)
    assert poligonos.distancia(*desplazado(poligonos, laureles, 2000), laureles) == pytest.approx(2000, abs=1)


def test_barrio_que_contiene_un_punto(poligonos):
    codigo = codigo_de(poligonos, "Laureles")
    assert poligonos.barrio_en(*poligonos.punto_barrio(codigo)) == codigo
    assert poligonos.barrio_en(4.6, -74.08) is None  # Bogotá


def test_comunas_unidas(poligonos):
    assert len(poligonos.comunas) == 21
    el_poblado = poligonos.geometria_comuna("EL POBLADO")
    assert el_poblado.contains(poligonos.geometria_barrio(codigo_de(poligonos, "Manila")).representative_point())


def test_codigo_como_texto(poligonos):
    assert "0902" in poligonos.codigos
    assert all(isinstance(c, str) and len(c) == 4 for c in poligonos.codigos)


def test_recuadro_en_orden_de_opencage(poligonos):
    min_lng, min_lat, max_lng, max_lat = (float(v) for v in poligonos.recuadro().split(","))
    assert min_lng < max_lng < 0 < min_lat < max_lat
    for codigo in poligonos.codigos:
        latitud, longitud = poligonos.punto_barrio(codigo)
        assert min_lat <= latitud <= max_lat and min_lng <= longitud <= max_lng


def coordenadas_de(geometria):
    """Todos los pares (lng, lat) de un Polygon o MultiPolygon en formato GeoJSON."""
    poligonos = [geometria["coordinates"]] if geometria["type"] == "Polygon" else geometria["coordinates"]
    return [punto for poligono in poligonos for anillo in poligono for punto in anillo]


def test_geojson_para_dibujar(poligonos):
    barrios, comunas = poligonos.geojson("barrios"), poligonos.geojson("comunas")
    assert len(barrios["features"]) == 349 and len(comunas["features"]) == 21
    for coleccion in (barrios, comunas):
        for feature in coleccion["features"]:
            for lng, lat in coordenadas_de(feature["geometry"]):
                assert 6.0 < lat < 6.5 and -75.8 < lng < -75.4
    propiedades = {f["properties"]["codigo"]: f["properties"] for f in barrios["features"]}
    assert set(propiedades) == set(poligonos.codigos)
    codigo = next(c for c in poligonos.codigos if c.startswith("0"))
    assert isinstance(propiedades[codigo]["codigo"], str)  # con su cero inicial
    assert (propiedades[codigo]["nombre"], propiedades[codigo]["comuna"]) == poligonos.nombre_barrio(codigo)
    assert {f["properties"]["nombre"] for f in comunas["features"]} == set(poligonos.comunas)


def test_geojson_simplificado(poligonos):
    assert len(json.dumps(poligonos.geojson("barrios"))) < 1_000_000
    assert len(json.dumps(poligonos.geojson("comunas"))) < 300_000
    assert poligonos.geojson("barrios") is poligonos.geojson("barrios")  # calculado una sola vez
    with pytest.raises(ValueError):
        poligonos.geojson("veredas")


def test_limites_contienen_el_recuadro(poligonos):
    (min_lat, min_lng), (max_lat, max_lng) = poligonos.limites_wgs84()
    r_min_lng, r_min_lat, r_max_lng, r_max_lat = map(float, poligonos.recuadro().split(","))
    # El recuadro redondea hacia fuera a 5 decimales; los límites son los exactos.
    assert r_min_lat <= min_lat < max_lat <= r_max_lat and r_min_lng <= min_lng < max_lng <= r_max_lng
    assert all(abs(a - b) < 1e-5 for a, b in ((min_lat, r_min_lat), (max_lat, r_max_lat),
                                              (min_lng, r_min_lng), (max_lng, r_max_lng)))


def test_archivo_inexistente(tmp_path):
    with pytest.raises(ErrorReferencia, match="no_existe.geojson"):
        Poligonos(tmp_path / "no_existe.geojson")


def test_carga_unica_por_proceso(tmp_path):
    assert Poligonos.cargar(GEOJSON) is Poligonos.cargar(GEOJSON)
    copia = tmp_path / "copia.geojson"
    copia.write_bytes(GEOJSON.read_bytes())
    primera = Poligonos.cargar(copia)
    # El archivo cambia (nueva fecha de modificación): se vuelve a construir.
    os.utime(copia, ns=(0, copia.stat().st_mtime_ns + 1))
    assert Poligonos.cargar(copia) is not primera


def test_carga_de_un_archivo_inexistente(tmp_path):
    with pytest.raises(ErrorReferencia, match="no_existe.geojson"):
        Poligonos.cargar(tmp_path / "no_existe.geojson")
