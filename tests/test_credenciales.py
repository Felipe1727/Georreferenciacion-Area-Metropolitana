"""Escenarios de specs/credenciales-geocodificacion y de la estructura de trabajo."""
import os
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pytest

COORDENADAS = Path("coordenadas") / "coordenadas_area_metropolitana.xlsx"
RAIZ_REPO = Path(__file__).resolve().parent.parent


@pytest.fixture
def con_estandarizacion(con_puntos, ejecutar_main):
    """Estandarización hecha y puntos de los municipios en la configuración: solo falta la llave."""
    ejecutar_main(1)


def test_variable_definida_se_usa_sin_preguntar(con_estandarizacion, ejecutar_main, cliente, monkeypatch):
    monkeypatch.setenv("OPENCAGE_API_KEY", "llave-falsa")
    # ejecutar_main solo responde la opcion del menu: cualquier otra pregunta fallaria.
    ejecutar_main(2)
    assert cliente.llaves == ["llave-falsa"]


def test_valor_con_espacios_se_recorta(con_estandarizacion, ejecutar_main, cliente, monkeypatch):
    monkeypatch.setenv("OPENCAGE_API_KEY", "  llave-falsa \n")
    ejecutar_main(2)
    assert cliente.llaves == ["llave-falsa"]


def test_llave_solo_en_dotenv(con_estandarizacion, ejecutar_main, cliente):
    Path(".env").write_text("OPENCAGE_API_KEY=llave-de-dotenv\n")
    ejecutar_main(2)
    assert cliente.llaves == ["llave-de-dotenv"]
    # Leer .env no debe filtrar la llave al entorno del proceso.
    assert "OPENCAGE_API_KEY" not in os.environ


def test_entorno_tiene_prioridad_sobre_dotenv(con_estandarizacion, ejecutar_main, cliente, monkeypatch):
    Path(".env").write_text("OPENCAGE_API_KEY=llave-de-dotenv\n")
    monkeypatch.setenv("OPENCAGE_API_KEY", "llave-del-entorno")
    ejecutar_main(2)
    assert cliente.llaves == ["llave-del-entorno"]


def test_entorno_vacio_recurre_a_dotenv(con_estandarizacion, ejecutar_main, cliente, monkeypatch):
    Path(".env").write_text('OPENCAGE_API_KEY="  llave-de-dotenv  "\n')
    monkeypatch.setenv("OPENCAGE_API_KEY", "  ")
    ejecutar_main(2)
    assert cliente.llaves == ["llave-de-dotenv"]


def _coordenadas_previas():
    COORDENADAS.parent.mkdir(exist_ok=True)
    pd.DataFrame({"Latitud": [6.2], "Longitud": [-75.5], "Nivel ubicacion": ["BARRIO"]}).to_excel(COORDENADAS)
    return COORDENADAS.read_bytes()


def test_variable_ausente_termina_sin_modificar_salidas(con_estandarizacion, ejecutar_main, cliente):
    contenido = _coordenadas_previas()
    with pytest.raises(SystemExit) as salida:
        ejecutar_main(2)
    assert salida.value.code not in (None, 0)
    assert "OPENCAGE_API_KEY" in salida.value.code
    assert cliente.consultas == []
    assert COORDENADAS.read_bytes() == contenido


def test_variable_vacia_equivale_a_ausente(con_estandarizacion, ejecutar_main, cliente, monkeypatch):
    monkeypatch.setenv("OPENCAGE_API_KEY", "   ")
    contenido = _coordenadas_previas()
    with pytest.raises(SystemExit) as salida:
        ejecutar_main(2)
    assert "OPENCAGE_API_KEY" in salida.value.code
    assert cliente.consultas == []
    assert COORDENADAS.read_bytes() == contenido


def test_dotenv_con_variable_vacia_equivale_a_ausente(con_estandarizacion, ejecutar_main, cliente):
    Path(".env").write_text("OPENCAGE_API_KEY=\n")
    contenido = _coordenadas_previas()
    with pytest.raises(SystemExit) as salida:
        ejecutar_main(2)
    assert "OPENCAGE_API_KEY" in salida.value.code
    assert ".env" in salida.value.code
    assert cliente.consultas == []
    assert COORDENADAS.read_bytes() == contenido


def test_modo_c_sin_variable_termina(con_estandarizacion, ejecutar_main, cliente):
    with pytest.raises(SystemExit) as salida:
        ejecutar_main(argv=("c",))
    assert "OPENCAGE_API_KEY" in salida.value.code
    assert not COORDENADAS.exists()


def test_llave_no_se_persiste_ni_se_muestra(con_estandarizacion, ejecutar_main, cliente, monkeypatch, capsys):
    monkeypatch.setenv("OPENCAGE_API_KEY", "secreto-123")
    ejecutar_main(2)
    assert not Path("llave").exists()
    assert "secreto-123" not in capsys.readouterr().out
    assert not any("secreto-123" in p.read_bytes().decode("latin-1") for p in Path(".").rglob("*") if p.is_file())


def test_ubicacion_sin_consultas_no_exige_credencial(con_estandarizacion, ejecutar_main, cliente):
    ejecutar_main(argv=("ubicar", "--sin-consultas"))
    assert COORDENADAS.exists()
    assert cliente.llaves == [] and cliente.consultas == []


def test_estandarizacion_no_exige_credencial(directorio_trabajo, ejecutar_main):
    ejecutar_main(1)
    assert (Path("estandarizado") / "principales_area_metropolitana.xlsx").exists()


def test_primera_ejecucion_crea_directorios_sin_llave(directorio_trabajo, ejecutar_main):
    ejecutar_main(1)
    for directorio in ("original", "estandarizado", "coordenadas", Path("mapas") / "area_metropolitana"):
        assert Path(directorio).is_dir()
    assert not Path("llave").exists()
    assert not (Path("mapas") / "area_metropolitana" / "filtrados").exists()


def test_plantilla_dotenv_sin_llave():
    plantilla = (RAIZ_REPO / ".env.example").read_text()
    lineas = [l for l in plantilla.splitlines() if l.startswith("OPENCAGE_API_KEY")]
    assert lineas == ["OPENCAGE_API_KEY="]


@pytest.mark.skipif(shutil.which("git") is None, reason="git no disponible")
def test_dotenv_ignorado_y_plantilla_versionable():
    def ignorado(ruta):
        return subprocess.run(["git", "check-ignore", "-q", ruta], cwd=RAIZ_REPO).returncode == 0

    assert ignorado(".env")
    assert not ignorado(".env.example")


@pytest.mark.skipif(shutil.which("git") is None, reason="git no disponible")
def test_artefactos_de_openspec_con_el_nombre_de_un_directorio_de_datos():
    def ignorado(ruta):
        return subprocess.run(["git", "check-ignore", "-q", "--no-index", ruta], cwd=RAIZ_REPO).returncode == 0

    assert not ignorado("openspec/changes/mapas/proposal.md")
    assert not ignorado("openspec/specs/mapas/spec.md")
    assert ignorado("mapas/area_metropolitana/mapa.html")
    assert ignorado("notebooks/mapas/mapa.html")
    assert all(ignorado(f"{carpeta}/archivo.xlsx") for carpeta in ("original", "estandarizado", "coordenadas", "llave"))
    assert not ignorado("data/limite_barrio_vereda_cata.geojson")


def test_variable_vacia_en_comparar_consultas(con_estandarizacion, ejecutar_main, cliente, monkeypatch):
    monkeypatch.setenv("OPENCAGE_API_KEY", "   ")
    with pytest.raises(SystemExit) as salida:
        ejecutar_main(argv=("comparar-consultas", "--muestra", "5"))
    assert "OPENCAGE_API_KEY" in salida.value.code
    assert cliente.consultas == []
