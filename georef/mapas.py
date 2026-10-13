"""Mapas HTML de las coordenadas con folium.

La lógica es la heredada de `main.py`, salvo el filtrado, que usa el nivel de ubicación; el
cambio `mapas` sustituye el centro y el zoom fijos.
"""
from pathlib import Path

import folium
import pandas as pd
from folium.plugins import FastMarkerCluster

from georef.ubicacion import MUNICIPIO

# Vista inicial de los mapas (centro de Medellín).
CENTRO_MAPA = [6.2464186, -75.5942503]
ZOOM_INICIAL = 12


def visualizar(df : pd.DataFrame, carpeta):
    """
    Genera y guarda mapas HTML con marcadores y clusters basados en coordenadas del DataFrame.

    Escribe `individual.html` y `clusters.html` en `carpeta`, y en `carpeta/filtrados/` las
    versiones sin los registros ubicados solo a nivel de municipio. Crea las carpetas si no existen.

    Args:
        df (pd.DataFrame): DataFrame con columnas 'Latitud', 'Longitud' y 'Nivel ubicacion'.
        carpeta: Carpeta de los mapas del área (por ejemplo, `mapas/area_metropolitana`).
    """
    carpeta = Path(carpeta)
    (carpeta / "filtrados").mkdir(parents=True, exist_ok=True)
    df.dropna(subset=['Latitud', 'Longitud'], inplace=True)
    latitudes = [a['Latitud'] for a in df.to_dict('records')]
    longitudes = [a['Longitud'] for a in df.to_dict('records')]
    data = list(zip(latitudes, longitudes))

    mapa_marcadores = folium.Map(location=CENTRO_MAPA, zoom_start=ZOOM_INICIAL)
    for a in df.index:
        coordenada = (df['Latitud'][a], df['Longitud'][a])
        folium.Marker(coordenada).add_to(mapa_marcadores)

    mapa_clusters = folium.Map(location=CENTRO_MAPA, zoom_start=ZOOM_INICIAL)

    FastMarkerCluster(data=data).add_to(mapa_clusters)

    mapa_marcadores.save(carpeta / 'individual.html')
    mapa_clusters.save(carpeta / 'clusters.html')

    df_filtrado = df[df["Nivel ubicacion"] != MUNICIPIO]
    latitudes = [a['Latitud'] for a in df_filtrado.to_dict('records')]
    longitudes = [a['Longitud'] for a in df_filtrado.to_dict('records')]
    data = list(zip(latitudes, longitudes))

    mapa_marcadores = folium.Map(location=CENTRO_MAPA, zoom_start=ZOOM_INICIAL)
    for a in df_filtrado.index:
        coordenada = (df_filtrado['Latitud'][a], df_filtrado['Longitud'][a])
        folium.Marker(coordenada).add_to(mapa_marcadores)

    mapa_clusters = folium.Map(location=CENTRO_MAPA, zoom_start=ZOOM_INICIAL)

    FastMarkerCluster(data=data).add_to(mapa_clusters)

    mapa_marcadores.save(carpeta / "filtrados" / 'individual_filtrados.html')
    mapa_clusters.save(carpeta / "filtrados" / 'clusters_filtrados.html')
