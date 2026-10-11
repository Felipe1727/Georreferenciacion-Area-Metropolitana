"""Caracterizacion de la generacion de mapas."""
from pathlib import Path

import pandas as pd

import main
from conftest import CENTROIDE_MEDELLIN

MAPAS = {
    "individual": Path("mapas") / "individual.html",
    "clusters": Path("mapas") / "clusters.html",
    "individual_filtrados": Path("mapas") / "filtrados" / "individual_filtrados.html",
    "clusters_filtrados": Path("mapas") / "filtrados" / "clusters_filtrados.html",
}


def test_visualizar_genera_cuatro_mapas_y_filtra_centroide(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "mapas" / "filtrados").mkdir(parents=True)
    df = pd.DataFrame(
        {
            "Latitud": [6.2, CENTROIDE_MEDELLIN[0], 6.3, None],
            "Longitud": [-75.5, CENTROIDE_MEDELLIN[1], -75.6, None],
        }
    )

    main.visualizar(df)

    assert all(ruta.exists() for ruta in MAPAS.values())
    # Un L.marker( por fila con coordenadas; la fila sin coordenadas se descarta.
    assert MAPAS["individual"].read_text().count("L.marker(") == 3
    # El mapa filtrado excluye ademas el centroide de Medellin.
    assert MAPAS["individual_filtrados"].read_text().count("L.marker(") == 2
