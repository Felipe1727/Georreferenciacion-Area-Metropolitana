"""Mapas HTML de las coordenadas de un área con folium.

`mapa_con_capas` construye el mapa principal de un área: una capa de puntos por nivel de
ubicación, dos capas de clusters y, si se dan los polígonos de Medellín, sus contornos y
capas coloreadas. Los registros que comparten punto y nivel se dibujan como un solo círculo
con el número de registros. `mapa_separado` construye una sola vista (`VISTAS`) para
compartirla como archivo suelto, y `generar` escribe `mapa.html` y los separados pedidos.

Solo se usan las columnas de `COLUMNAS`: ningún otro dato de los registros llega a los mapas.
"""
import copy
import html
import math
from collections import Counter
from pathlib import Path

import branca.colormap
import folium
import pandas as pd
from folium.plugins import FastMarkerCluster

from georef.ubicacion import BARRIO, COMUNA, DIRECCION, MUNICIPIO, NIVELES, RESULTADOS

# Vistas de los mapas separados; las coloreadas necesitan los polígonos de Medellín.
VISTAS = ("puntos", "clusters", "barrios_cantidad", "comunas_cantidad")
VISTAS_COLOREADAS = ("barrios_cantidad", "comunas_cantidad")
# Vistas a las que afecta `sin_municipio`.
VISTAS_DE_PUNTOS = ("puntos", "clusters")
CARPETA_SEPARADOS = "separados"

# Columna con el municipio del registro (la etapa renombra a ella la columna de ciudad).
COLUMNA_MUNICIPIO = "Municipio"
COLUMNAS = ["Latitud", "Longitud", "Nivel ubicacion", "Resultado consulta", "Barrio ubicacion",
            "Codigo barrio ubicacion", "Comuna ubicacion", COLUMNA_MUNICIPIO]

# Color del círculo y del número de cada nivel (paleta Okabe-Ito, distinguible con daltonismo).
COLORES_NIVEL = {
    DIRECCION: ("#009E73", "#ffffff"),
    BARRIO: ("#0072B2", "#ffffff"),
    COMUNA: ("#E69F00", "#000000"),
    MUNICIPIO: ("#7F7F7F", "#ffffff"),
}
# Diámetro en píxeles del círculo de un punto con 1 registro y tope para los más poblados.
DIAMETRO_MINIMO = 14
DIAMETRO_MAXIMO = 44
# Zoom máximo del encuadre, para que un solo punto no se vea a escala de edificio.
ZOOM_MAXIMO = 15

CLUSTERS = "Clusters"
CLUSTERS_SIN_MUNICIPIO = "Clusters sin MUNICIPIO"
CONTORNO_COMUNAS = "Contorno de comunas"
CONTORNO_BARRIOS = "Contorno de barrios"
BARRIOS_CANTIDAD = "Barrios por cantidad"
COMUNAS_CANTIDAD = "Comunas por cantidad"
# Relleno de los polígonos sin registros en las capas coloreadas.
COLOR_SIN_REGISTROS = "#d9d9d9"

# Capas coloreadas: tipo de polígonos, columna que se cuenta, propiedad del GeoJSON que la
# identifica, título de la escala y campos del tooltip con su etiqueta.
COLOREADAS = {
    BARRIOS_CANTIDAD: ("barrios", "Codigo barrio ubicacion", "codigo", "Registros por barrio",
                       {"nombre": "Barrio", "comuna": "Comuna", "registros": "Registros"}),
    COMUNAS_CANTIDAD: ("comunas", "Comuna ubicacion", "nombre", "Registros por comuna",
                       {"nombre": "Comuna", "registros": "Registros"}),
}


def mapa_con_capas(df: pd.DataFrame, poligonos=None) -> folium.Map:
    """
    Mapa de un área con una capa de puntos por nivel (visibles al abrir), las capas de clusters
    con y sin el nivel MUNICIPIO (ocultas), la leyenda de niveles y el encuadre en los puntos.

    Con `poligonos` (`georef.geografia.Poligonos`), añade el contorno de las comunas (visible),
    el de los barrios y los barrios y las comunas coloreados por cantidad (ocultos).
    """
    df = _con_coordenadas(df)
    mapa = _mapa_encuadrado(_limites_puntos(df))
    if poligonos is not None:
        _contornos(mapa, poligonos)
        for nombre in COLOREADAS:
            _coloreada(mapa, poligonos, df, nombre, show=False)
    _capas_puntos(mapa, df)
    _clusters(mapa, df, CLUSTERS)
    _clusters(mapa, df[df["Nivel ubicacion"] != MUNICIPIO], CLUSTERS_SIN_MUNICIPIO)
    _leyenda_niveles(mapa)
    folium.LayerControl(collapsed=False).add_to(mapa)
    return mapa


def mapa_separado(df: pd.DataFrame, vista: str, poligonos=None, sin_municipio=False) -> folium.Map:
    """
    Mapa autónomo con una sola vista de `VISTAS`, para compartirlo como archivo suelto.

    - `puntos`: las capas de nivel con su leyenda; `clusters`: todos los registros. Las dos
      llevan el contorno de las comunas si se dan `poligonos`, y con `sin_municipio` excluyen
      el nivel MUNICIPIO.
    - `barrios_cantidad` y `comunas_cantidad`: la capa coloreada, encuadrada en Medellín.
      Necesitan `poligonos`.
    """
    if vista not in VISTAS:
        raise ValueError(f"vista desconocida: {vista!r}")
    if vista in VISTAS_COLOREADAS:
        if poligonos is None:
            raise ValueError(f"la vista '{vista}' necesita los polígonos de Medellín")
        mapa = _mapa_encuadrado(poligonos.limites_wgs84())
        nombre = BARRIOS_CANTIDAD if vista == "barrios_cantidad" else COMUNAS_CANTIDAD
        _coloreada(mapa, poligonos, _con_coordenadas(df), nombre, show=True)
        return mapa

    if sin_municipio:
        df = df[df["Nivel ubicacion"] != MUNICIPIO]
    df = _con_coordenadas(df)
    mapa = _mapa_encuadrado(_limites_puntos(df))
    if poligonos is not None:
        _contornos(mapa, poligonos, barrios=False)
    if vista == "puntos":
        _capas_puntos(mapa, df)
        _leyenda_niveles(mapa)
    else:
        _clusters(mapa, df, CLUSTERS if not sin_municipio else CLUSTERS_SIN_MUNICIPIO, show=True)
    folium.LayerControl(collapsed=False).add_to(mapa)
    return mapa


def nombre_separado(vista: str, sin_municipio: bool) -> str:
    """Nombre del archivo de un separado: `<vista>.html` o `<vista>_sin_municipio.html`."""
    sufijo = "_sin_municipio" if sin_municipio and vista in VISTAS_DE_PUNTOS else ""
    return f"{vista}{sufijo}.html"


def generar(df: pd.DataFrame, carpeta, poligonos=None, separados=(), sin_municipio=False) -> list[Path]:
    """
    Escribe `carpeta/mapa.html` y, por cada vista de `separados`, `carpeta/separados/<archivo>`
    (ver `nombre_separado`). Construye todos los mapas antes de escribir el primero, así que un
    error no deja archivos a medias. Devuelve las rutas escritas.
    """
    carpeta = Path(carpeta)
    mapas = [(carpeta / "mapa.html", mapa_con_capas(df, poligonos))]
    for vista in separados:
        mapas.append((carpeta / CARPETA_SEPARADOS / nombre_separado(vista, sin_municipio),
                      mapa_separado(df, vista, poligonos, sin_municipio)))
    for ruta, mapa in mapas:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        mapa.save(ruta)
    return [ruta for ruta, _ in mapas]


def diametro(registros: int) -> int:
    """Diámetro en píxeles del círculo de un punto con `registros` registros."""
    return min(round(DIAMETRO_MINIMO + 6 * math.sqrt(registros - 1)), DIAMETRO_MAXIMO)


def _con_coordenadas(df):
    df = df.dropna(subset=["Latitud", "Longitud"])
    if df.empty:
        raise ValueError("no hay registros con coordenadas para dibujar en el mapa")
    return df


def _limites_puntos(df):
    return [[float(df["Latitud"].min()), float(df["Longitud"].min())],
            [float(df["Latitud"].max()), float(df["Longitud"].max())]]


def _mapa_encuadrado(limites):
    """Mapa centrado en `limites` y encuadrado en ellos, sin pasar de `ZOOM_MAXIMO`."""
    (min_lat, min_lng), (max_lat, max_lng) = limites
    mapa = folium.Map(location=[(min_lat + max_lat) / 2, (min_lng + max_lng) / 2], zoom_start=12)
    mapa.fit_bounds(limites, max_zoom=ZOOM_MAXIMO)
    return mapa


def _capas_puntos(mapa, df):
    """Una capa por nivel con registros; un círculo por punto distinto dentro de cada capa."""
    for nivel in NIVELES:
        del_nivel = df[df["Nivel ubicacion"] == nivel]
        if del_nivel.empty:
            continue
        capa = folium.FeatureGroup(name=f"{nivel} ({_registros(len(del_nivel))})", show=True)
        for (latitud, longitud), grupo in del_nivel.groupby(["Latitud", "Longitud"], sort=True):
            folium.Marker(
                [latitud, longitud],
                icon=_icono(nivel, len(grupo)),
                popup=folium.Popup(_ventana(nivel, grupo), max_width=300),
            ).add_to(capa)
        capa.add_to(mapa)


def _icono(nivel, registros):
    """Círculo del color del nivel, con el número de registros dentro si hay más de uno."""
    lado = diametro(registros)
    fondo, texto = COLORES_NIVEL[nivel]
    numero = str(registros) if registros > 1 else ""
    contenido = (
        f'<div style="width:{lado}px;height:{lado}px;border-radius:50%;background:{fondo};opacity:0.85;'
        f'border:2px solid #ffffff;box-sizing:border-box;color:{texto};font:bold 12px sans-serif;'
        f'display:flex;align-items:center;justify-content:center;">{numero}</div>'
    )
    return folium.DivIcon(html=contenido, icon_size=(lado, lado), icon_anchor=(lado // 2, lado // 2))


def _ventana(nivel, grupo):
    """HTML de la ventana de un punto: solo datos de ubicación y recuentos."""
    lineas = [f"<b>Nivel:</b> {html.escape(nivel)}"]
    for etiqueta, columna in (("Municipio", COLUMNA_MUNICIPIO), ("Barrio", "Barrio ubicacion"),
                              ("Comuna", "Comuna ubicacion")):
        if columna in grupo.columns:
            valores = sorted({str(v) for v in grupo[columna].dropna()})
            if valores:
                lineas.append(f"<b>{etiqueta}:</b> {html.escape(', '.join(valores))}")
    lineas.append(f"<b>Registros:</b> {len(grupo)}")
    if "Resultado consulta" in grupo.columns:
        recuento = Counter(grupo["Resultado consulta"].dropna())
        orden = [r for r in RESULTADOS if r in recuento] + sorted(set(recuento) - set(RESULTADOS))
        lineas += [f"{html.escape(str(resultado))}: {recuento[resultado]}" for resultado in orden]
    return "<br>".join(lineas)


def _clusters(mapa, df, nombre, show=False):
    datos = df[["Latitud", "Longitud"]].astype(float).values.tolist()
    FastMarkerCluster(data=datos, name=f"{nombre} ({_registros(len(datos))})", show=show).add_to(mapa)


def _contornos(mapa, poligonos, barrios=True):
    """Contornos de comunas y barrios. El relleno transparente hace que el tooltip responda en todo el polígono."""
    folium.GeoJson(
        poligonos.geojson("comunas"), name=CONTORNO_COMUNAS, show=True,
        style_function=lambda _: {"color": "#444444", "weight": 2, "fillOpacity": 0},
        tooltip=folium.GeoJsonTooltip(fields=["nombre"], aliases=["Comuna"]),
    ).add_to(mapa)
    if not barrios:
        return
    folium.GeoJson(
        poligonos.geojson("barrios"), name=CONTORNO_BARRIOS, show=False,
        style_function=lambda _: {"color": "#777777", "weight": 1, "fillOpacity": 0},
        tooltip=folium.GeoJsonTooltip(fields=["nombre", "comuna"], aliases=["Barrio", "Comuna"]),
    ).add_to(mapa)


def cantidades(df, nombre):
    """Registros por polígono de la capa coloreada `nombre`: {codigo de barrio o comuna: registros}."""
    _, columna, _, _, _ = COLOREADAS[nombre]
    if columna not in df.columns:
        return {}
    return df[columna].dropna().astype(str).value_counts().to_dict()


def _coloreada(mapa, poligonos, df, nombre, show):
    """Polígonos coloreados por cantidad de registros, con escala; gris si no tienen ninguno."""
    tipo, _, clave, titulo, campos = COLOREADAS[nombre]
    por_poligono = cantidades(df, nombre)
    coleccion = copy.deepcopy(poligonos.geojson(tipo))
    for feature in coleccion["features"]:
        feature["properties"]["registros"] = int(por_poligono.get(feature["properties"][clave], 0))
    maximo = max((f["properties"]["registros"] for f in coleccion["features"]), default=0)
    escala = branca.colormap.linear.YlOrRd_09.scale(1, max(maximo, 2))
    escala.caption = titulo

    def estilo(feature):
        registros = feature["properties"]["registros"]
        relleno = escala(registros) if registros else COLOR_SIN_REGISTROS
        return {"fillColor": relleno, "fillOpacity": 0.7 if registros else 0.3, "color": "#555555", "weight": 1}

    folium.GeoJson(
        coleccion, name=nombre, show=show, style_function=estilo,
        tooltip=folium.GeoJsonTooltip(fields=list(campos), aliases=list(campos.values())),
    ).add_to(mapa)
    escala.add_to(mapa)


def _leyenda_niveles(mapa):
    filas = "".join(
        f'<div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;'
        f'background:{fondo};margin-right:6px;vertical-align:middle;"></span>{nivel}</div>'
        for nivel, (fondo, _) in COLORES_NIVEL.items()
    )
    leyenda = (
        '<div style="position:fixed;bottom:24px;left:12px;z-index:1000;background:#ffffff;'
        'padding:8px 10px;border:1px solid #999999;border-radius:4px;font:12px sans-serif;">'
        f'<b>Nivel de ubicación</b>{filas}'
        '<div style="margin-top:4px;">El número indica cuántos registros comparten el punto.</div></div>'
    )
    mapa.get_root().html.add_child(folium.Element(leyenda))


def _registros(n):
    return f"{n} registro" if n == 1 else f"{n} registros"
