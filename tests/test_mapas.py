"""Generacion de mapas y su filtrado por nivel de ubicacion (specs/ubicacion-por-niveles)."""
import pandas as pd

from georef.mapas import visualizar


def rutas_mapas(carpeta):
    return {
        "individual": carpeta / "individual.html",
        "clusters": carpeta / "clusters.html",
        "individual_filtrados": carpeta / "filtrados" / "individual_filtrados.html",
        "clusters_filtrados": carpeta / "filtrados" / "clusters_filtrados.html",
    }


def test_mapas_filtrados_por_nivel(tmp_path):
    carpeta = tmp_path / "mapas" / "area_metropolitana"
    df = pd.DataFrame(
        {
            "Latitud": [6.20, 6.21, 6.22, 6.30, 6.31, None],
            "Longitud": [-75.50, -75.51, -75.52, -75.40, -75.41, None],
            "Nivel ubicacion": ["BARRIO", "BARRIO", "BARRIO", "MUNICIPIO", "MUNICIPIO", "BARRIO"],
        }
    )

    visualizar(df, carpeta)

    mapas = rutas_mapas(carpeta)
    assert all(ruta.exists() for ruta in mapas.values())
    # Un L.marker( por fila con coordenadas; la fila sin coordenadas se descarta.
    assert mapas["individual"].read_text().count("L.marker(") == 5
    # El mapa filtrado excluye los registros ubicados solo a nivel de municipio.
    assert mapas["individual_filtrados"].read_text().count("L.marker(") == 3


def test_mismo_punto_en_otro_nivel_no_se_filtra(tmp_path):
    # El filtrado depende del nivel, no de una coordenada fija.
    carpeta = tmp_path / "mapas" / "area_metropolitana"
    df = pd.DataFrame({"Latitud": [6.25, 6.25], "Longitud": [-75.56, -75.56],
                       "Nivel ubicacion": ["DIRECCION", "MUNICIPIO"]})
    visualizar(df, carpeta)
    assert rutas_mapas(carpeta)["individual_filtrados"].read_text().count("L.marker(") == 1


def test_visualizar_crea_la_carpeta_del_area(tmp_path):
    carpeta = tmp_path / "mapas" / "medellin"
    visualizar(pd.DataFrame({"Latitud": [6.2], "Longitud": [-75.5], "Nivel ubicacion": ["BARRIO"]}), carpeta)
    assert all(ruta.exists() for ruta in rutas_mapas(carpeta).values())
