"""Mapas de un área (specs/mapas): capas, puntos agrupados, ventana, clusters, polígonos y encuadre."""
import json
from pathlib import Path

import folium
import pandas as pd
import pytest
from folium.plugins import FastMarkerCluster

from georef.geografia import Poligonos
from georef.mapas import VISTAS, ZOOM_MAXIMO, diametro, generar, mapa_con_capas, mapa_separado

GEOJSON = Path(__file__).resolve().parent.parent / "data" / "limite_barrio_vereda_cata.geojson"

LAURELES = (6.2440, -75.5960)
BARBOSA = [(6.4370, -75.3314), (6.4420, -75.3250)]


@pytest.fixture(scope="module")
def poligonos():
    return Poligonos.cargar(GEOJSON)


def registros(*filas):
    """
    DataFrame de coordenadas con filas
    (latitud, longitud, nivel[, resultado, barrio, comuna, municipio, codigo de barrio]).
    """
    columnas = ["Latitud", "Longitud", "Nivel ubicacion", "Resultado consulta", "Barrio ubicacion",
                "Comuna ubicacion", "Municipio", "Codigo barrio ubicacion"]
    completas = [tuple(fila) + (None,) * (len(columnas) - len(fila)) for fila in filas]
    return pd.DataFrame(completas, columns=columnas)


def capas(mapa):
    """Capas del control de capas por su nombre (puntos, clusters y polígonos)."""
    tipos = (folium.FeatureGroup, FastMarkerCluster, folium.GeoJson)
    return {hijo.layer_name: hijo for hijo in mapa._children.values() if isinstance(hijo, tipos)}


def capa(mapa, prefijo):
    encontradas = [c for nombre, c in capas(mapa).items() if nombre == prefijo or nombre.startswith(prefijo + " (")]
    assert len(encontradas) == 1, (prefijo, list(capas(mapa)))
    return encontradas[0]


def marcadores(capa_):
    return [hijo for hijo in capa_._children.values() if isinstance(hijo, folium.Marker)]


def icono(marcador):
    return next(h for h in marcador._children.values() if isinstance(h, folium.DivIcon)).options["html"]


def ventana(marcador):
    popup = next(h for h in marcador._children.values() if isinstance(h, folium.Popup))
    return next(iter(popup.html._children.values())).data


def encuadre(mapa):
    ajuste = next(h for h in mapa._children.values() if type(h).__name__ == "FitBounds")
    return ajuste.bounds, ajuste.options


def test_mapa_del_area_metropolitana():
    mapa = mapa_con_capas(registros((6.20, -75.50, "DIRECCION"), (6.21, -75.51, "BARRIO"),
                                    (6.22, -75.52, "COMUNA"), (6.30, -75.40, "MUNICIPIO")))
    for nivel in ("DIRECCION", "BARRIO", "COMUNA", "MUNICIPIO"):
        assert capa(mapa, nivel).show is True
    assert capa(mapa, "Clusters").show is False
    assert capa(mapa, "Clusters sin MUNICIPIO").show is False
    assert any(isinstance(h, folium.LayerControl) for h in mapa._children.values())


def test_clusters_con_y_sin_municipio():
    df = registros(*[(6.20 + i / 100, -75.50, "BARRIO") for i in range(3)],
                   *[(6.30 + i / 100, -75.40, "MUNICIPIO") for i in range(2)])
    mapa = mapa_con_capas(df)
    assert len(capa(mapa, "Clusters").data) == 5
    assert len(capa(mapa, "Clusters sin MUNICIPIO").data) == 3


def test_nivel_sin_registros():
    mapa = mapa_con_capas(registros((6.20, -75.50, "BARRIO"), (6.30, -75.40, "MUNICIPIO")))
    assert not any(nombre.startswith("COMUNA") for nombre in capas(mapa))
    assert not any(nombre.startswith("DIRECCION") for nombre in capas(mapa))
    capa(mapa, "BARRIO"), capa(mapa, "MUNICIPIO")


def test_varios_registros_en_el_punto_de_un_barrio():
    mapa = mapa_con_capas(registros(*[(*LAURELES, "BARRIO")] * 9, (6.25, -75.57, "BARRIO")))
    puntos = marcadores(capa(mapa, "BARRIO"))
    assert len(puntos) == 2
    nueve = next(m for m in puntos if tuple(m.location) == LAURELES)
    assert ">9</div>" in icono(nueve)
    assert f"width:{diametro(9)}px" in icono(nueve) and diametro(9) > diametro(1)


def test_un_solo_registro():
    mapa = mapa_con_capas(registros((*LAURELES, "DIRECCION")))
    (punto,) = marcadores(capa(mapa, "DIRECCION"))
    assert icono(punto).endswith("></div>")  # sin número
    assert "#009E73" in icono(punto)


def test_mismo_punto_en_distinto_nivel():
    mapa = mapa_con_capas(registros((*LAURELES, "DIRECCION"), (*LAURELES, "MUNICIPIO")))
    assert len(marcadores(capa(mapa, "DIRECCION"))) == 1
    assert len(marcadores(capa(mapa, "MUNICIPIO"))) == 1


def test_tamano_maximo_del_circulo():
    assert diametro(1) == 14 and diametro(1000) == 44


def test_ventana_de_un_punto_de_barrio():
    fila = (*LAURELES, "BARRIO")
    lugar = ("Laureles", "LAURELES ESTADIO", "MEDELLIN - ANTIOQUIA")
    df = registros(*[(*fila, "PRECISION_INSUFICIENTE", *lugar)] * 3, *[(*fila, "SIN_CONSULTA", *lugar)] * 2)
    (punto,) = marcadores(capa(mapa_con_capas(df), "BARRIO"))
    contenido = ventana(punto)
    for texto in ("<b>Nivel:</b> BARRIO", "<b>Municipio:</b> MEDELLIN - ANTIOQUIA", "<b>Barrio:</b> Laureles",
                  "<b>Comuna:</b> LAURELES ESTADIO", "<b>Registros:</b> 5", "PRECISION_INSUFICIENTE: 3",
                  "SIN_CONSULTA: 2"):
        assert texto in contenido


def test_encuadre_en_los_puntos_de_un_municipio():
    mapa = mapa_con_capas(registros(*[(*punto, "MUNICIPIO") for punto in BARBOSA]))
    limites, opciones = encuadre(mapa)
    assert limites == [[6.4370, -75.3314], [6.4420, -75.3250]]
    assert opciones == {"maxZoom": ZOOM_MAXIMO}


def test_un_unico_punto():
    mapa = mapa_con_capas(registros((*LAURELES, "BARRIO")))
    limites, opciones = encuadre(mapa)
    assert limites == [list(LAURELES), list(LAURELES)] and opciones["maxZoom"] == 15
    assert '"maxZoom": 15' in mapa.get_root().render()


def test_filas_sin_coordenadas_se_descartan():
    mapa = mapa_con_capas(registros((*LAURELES, "BARRIO"), (None, None, "BARRIO")))
    assert len(capa(mapa, "Clusters").data) == 1


POLIGONOS = ("Contorno de comunas", "Contorno de barrios", "Barrios por cantidad", "Comunas por cantidad")


def test_capas_de_comunas_y_barrios(poligonos):
    mapa = mapa_con_capas(registros((*LAURELES, "BARRIO")), poligonos)
    assert {nombre: capa(mapa, nombre).show for nombre in POLIGONOS} == {
        "Contorno de comunas": True, "Contorno de barrios": False,
        "Barrios por cantidad": False, "Comunas por cantidad": False}
    assert len(capa(mapa, "Contorno de barrios").data["features"]) == 349
    assert len(capa(mapa, "Comunas por cantidad").data["features"]) == 21


def test_sin_poligonos_no_hay_capas_de_poligonos():
    mapa = mapa_con_capas(registros((*BARBOSA[0], "MUNICIPIO")))
    assert not set(POLIGONOS) & set(capas(mapa))


def cantidades_en(mapa, nombre, clave):
    return {f["properties"][clave]: f["properties"]["registros"] for f in capa(mapa, nombre).data["features"]}


def test_cantidad_por_barrio_y_por_comuna(poligonos):
    codigo = next(c for c in poligonos.codigos if poligonos.nombre_barrio(c)[0] == "Laureles")
    nombre, comuna = poligonos.nombre_barrio(codigo)
    en_barrio = (nombre, comuna, "MEDELLIN - ANTIOQUIA", codigo)
    df = registros(*[(*LAURELES, "BARRIO", "SIN_CONSULTA", *en_barrio)] * 3,
                   (6.2450, -75.5950, "DIRECCION", "ACEPTADA", *en_barrio),
                   (6.2400, -75.5900, "COMUNA", "SIN_CONSULTA", None, comuna, "MEDELLIN - ANTIOQUIA"),
                   (6.2500, -75.5700, "MUNICIPIO", "SIN_CONSULTA", None, None, "MEDELLIN - ANTIOQUIA"))
    mapa = mapa_con_capas(df, poligonos)
    por_barrio = cantidades_en(mapa, "Barrios por cantidad", "codigo")
    por_comuna = cantidades_en(mapa, "Comunas por cantidad", "nombre")
    assert por_barrio[codigo] == 4 and por_comuna[comuna] == 5
    # El registro de nivel MUNICIPIO no cuenta en ningún barrio ni comuna.
    assert sum(por_barrio.values()) == 4 and sum(por_comuna.values()) == 5


def test_poligonos_sin_registros_en_gris(poligonos):
    mapa = mapa_con_capas(registros((*LAURELES, "BARRIO")), poligonos)
    html = mapa.get_root().render()
    assert "#d9d9d9" in html  # relleno de los polígonos sin registros
    assert "Registros por barrio" in html and "Registros por comuna" in html  # escalas


def test_las_capas_coloreadas_no_modifican_los_poligonos(poligonos):
    mapa_con_capas(registros((*LAURELES, "BARRIO")), poligonos)
    assert "registros" not in poligonos.geojson("barrios")["features"][0]["properties"]


def tres_barrio_dos_municipio():
    return registros(*[(6.24 + i / 100, -75.59, "BARRIO", "SIN_CONSULTA") for i in range(3)],
                     *[(6.34 + i / 100, -75.55, "MUNICIPIO", "SIN_CONSULTA") for i in range(2)])


def archivos_en(carpeta):
    return sorted(r.relative_to(carpeta).as_posix() for r in carpeta.rglob("*") if r.is_file())


def test_dos_separados(tmp_path, poligonos):
    carpeta = tmp_path / "mapas" / "area_metropolitana"
    rutas = generar(tres_barrio_dos_municipio(), carpeta, poligonos, separados=["puntos", "comunas_cantidad"])
    assert archivos_en(carpeta) == ["mapa.html", "separados/comunas_cantidad.html", "separados/puntos.html"]
    assert sorted(rutas) == sorted(carpeta / a for a in archivos_en(carpeta))


def test_sin_separados(tmp_path):
    carpeta = tmp_path / "mapas" / "medellin"
    generar(tres_barrio_dos_municipio(), carpeta)
    assert archivos_en(carpeta) == ["mapa.html"] and not (carpeta / "separados").exists()


def test_puntos_sin_municipio(tmp_path):
    df = tres_barrio_dos_municipio()
    mapa = mapa_separado(df, "puntos", sin_municipio=True)
    assert not any(nombre.startswith("MUNICIPIO") for nombre in capas(mapa))
    assert len(marcadores(capa(mapa, "BARRIO"))) == 3
    carpeta = tmp_path / "mapas" / "area_metropolitana"
    generar(df, carpeta, separados=["puntos"], sin_municipio=True)
    assert archivos_en(carpeta) == ["mapa.html", "separados/puntos_sin_municipio.html"]


def test_clusters_sin_municipio():
    mapa = mapa_separado(tres_barrio_dos_municipio(), "clusters", sin_municipio=True)
    clusters = capa(mapa, "Clusters sin MUNICIPIO")
    assert len(clusters.data) == 3 and clusters.show is True
    assert len(capa(mapa_separado(tres_barrio_dos_municipio(), "clusters"), "Clusters").data) == 5


def test_separados_coloreados(poligonos):
    df = tres_barrio_dos_municipio()
    mapa = mapa_separado(df, "barrios_cantidad", poligonos, sin_municipio=True)
    assert capa(mapa, "Barrios por cantidad").show is True
    assert not any(isinstance(c, folium.FeatureGroup) for c in capas(mapa).values())  # sin puntos
    assert encuadre(mapa)[0] == poligonos.limites_wgs84()


def test_separado_coloreado_sin_poligonos():
    with pytest.raises(ValueError, match="polígonos"):
        mapa_separado(tres_barrio_dos_municipio(), "comunas_cantidad")


def test_vista_desconocida(tmp_path):
    with pytest.raises(ValueError, match="calor"):
        generar(tres_barrio_dos_municipio(), tmp_path / "mapas", separados=["calor"])
    assert not (tmp_path / "mapas").exists()  # nada a medias


def test_sin_datos_del_estudiante(tmp_path, poligonos):
    df = tres_barrio_dos_municipio()
    personales = {
        "Nombre": ["ANA PRUEBA UNO", "LUIS PRUEBA DOS", "EVA PRUEBA TRES", "IVAN PRUEBA CUATRO", "OLGA PRUEBA CINCO"],
        "Direccion de residencia": [f"CL 99X #88-{i}7 MUÑOZ SINTÉTICA" for i in range(5)],
        "Complemento": [f"APTO 9{i}9 TORRE SINTETICA" for i in range(5)],
        "Documento": [f"99887766{i}" for i in range(5)],
    }
    df = df.assign(**personales)
    carpeta = tmp_path / "mapas" / "area_metropolitana"
    rutas = generar(df, carpeta, poligonos, separados=VISTAS)
    assert len(rutas) == 1 + len(VISTAS)
    contenido = "".join(ruta.read_text(encoding="utf-8") for ruta in rutas)
    # folium escapa el texto dentro del JavaScript (por ejemplo, Ñ como \u00d1): se buscan las dos formas.
    formas = [forma for valores in personales.values() for v in valores for forma in (v, json.dumps(v)[1:-1])]
    assert not [forma for forma in formas if forma in contenido]


def test_tamano_del_mapa_con_poligonos(tmp_path, poligonos):
    (ruta,) = generar(tres_barrio_dos_municipio(), tmp_path, poligonos)
    assert ruta.stat().st_size < 3_000_000
