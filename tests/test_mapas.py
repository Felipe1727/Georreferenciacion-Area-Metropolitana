"""Caracterizacion de la generacion de mapas."""
import pandas as pd

from georef.mapas import visualizar
from conftest import CENTROIDE_MEDELLIN


def rutas_mapas(carpeta):
    return {
        "individual": carpeta / "individual.html",
        "clusters": carpeta / "clusters.html",
        "individual_filtrados": carpeta / "filtrados" / "individual_filtrados.html",
        "clusters_filtrados": carpeta / "filtrados" / "clusters_filtrados.html",
    }


def test_visualizar_genera_cuatro_mapas_y_filtra_centroide(tmp_path):
    carpeta = tmp_path / "mapas" / "area_metropolitana"
    df = pd.DataFrame(
        {
            "Latitud": [6.2, CENTROIDE_MEDELLIN[0], 6.3, None],
            "Longitud": [-75.5, CENTROIDE_MEDELLIN[1], -75.6, None],
        }
    )

    visualizar(df, carpeta)

    mapas = rutas_mapas(carpeta)
    assert all(ruta.exists() for ruta in mapas.values())
    # Un L.marker( por fila con coordenadas; la fila sin coordenadas se descarta.
    assert mapas["individual"].read_text().count("L.marker(") == 3
    # El mapa filtrado excluye ademas el centroide de Medellin.
    assert mapas["individual_filtrados"].read_text().count("L.marker(") == 2


def test_visualizar_crea_la_carpeta_del_area(tmp_path):
    carpeta = tmp_path / "mapas" / "medellin"
    visualizar(pd.DataFrame({"Latitud": [6.2], "Longitud": [-75.5]}), carpeta)
    assert all(ruta.exists() for ruta in rutas_mapas(carpeta).values())
