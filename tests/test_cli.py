"""Escenarios de specs/linea-de-comandos, mas los de credenciales y configuracion invalida desde la CLI."""
from pathlib import Path

import pandas as pd
import pytest

from conftest import escribir_configuracion, resultado

ESTANDARIZADO = Path("estandarizado")
PRINCIPALES = ESTANDARIZADO / "principales_area_metropolitana.xlsx"
FUERA = ESTANDARIZADO / "fuera_area_metropolitana.xlsx"
COORDENADAS = Path("coordenadas") / "coordenadas_area_metropolitana.xlsx"
MAPAS = Path("mapas") / "area_metropolitana"


@pytest.fixture
def llave_falsa(monkeypatch):
    monkeypatch.setenv("OPENCAGE_API_KEY", "llave-falsa")


@pytest.fixture
def coordenadas_previas(directorio_trabajo):
    COORDENADAS.parent.mkdir(exist_ok=True)
    pd.DataFrame(
        {
            "Ciudad Residencia": ["MEDELLIN - ANTIOQUIA", "BELLO - ANTIOQUIA"],
            "Latitud": [6.2, 6.33],
            "Longitud": [-75.5, -75.55],
            "Complemento": ["X", "Y"],
        }
    ).to_excel(COORDENADAS)
    return COORDENADAS.read_bytes()


@pytest.fixture
def original_vacio(tmp_path, monkeypatch, sin_dialogo):
    """Directorio de trabajo con la configuracion incluida y `original/` vacio."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "original").mkdir()
    (tmp_path / "config").mkdir()
    escribir_configuracion(tmp_path / "config" / "georef.toml")
    return tmp_path


# --- Subcomandos -------------------------------------------------------------------------------

def test_subcomando_estandarizar_sin_preguntas(directorio_trabajo, ejecutar_main):
    # ejecutar_main sin opcion: cualquier input() agotaria las respuestas y fallaria.
    ejecutar_main(argv=("estandarizar",))
    assert sorted(p.name for p in ESTANDARIZADO.iterdir()) == [
        "especiales_area_metropolitana.xlsx",
        "fuera_area_metropolitana.xlsx",
        "principales_area_metropolitana.xlsx",
        "total_area_metropolitana.xlsx",
    ]


def test_subcomando_geocodificar_igual_que_opcion_2(directorio_trabajo, ejecutar_main, llave_falsa, geocodificador):
    ejecutar_main(argv=("estandarizar",))
    geocodificador.por_defecto = resultado(6.2, -75.5)
    ejecutar_main(argv=("geocodificar",))
    por_subcomando = pd.read_excel(COORDENADAS, index_col=0)
    consultas = list(geocodificador.consultas)

    COORDENADAS.unlink()
    geocodificador.consultas.clear()
    ejecutar_main(2)
    assert pd.read_excel(COORDENADAS, index_col=0).equals(por_subcomando)
    assert geocodificador.consultas == consultas


def test_subcomando_mejorar(coordenadas_previas, ejecutar_main, llave_falsa, geocodificador):
    ejecutar_main(argv=("mejorar",))
    assert pd.read_excel(COORDENADAS, index_col=0)["Latitud"].tolist() == [6.2, 6.33]


def test_subcomando_mapas(coordenadas_previas, ejecutar_main):
    ejecutar_main(argv=("mapas",))
    assert (MAPAS / "individual.html").exists()
    assert (MAPAS / "filtrados" / "clusters_filtrados.html").exists()


def test_subcomando_subconjunto(coordenadas_previas, ejecutar_main):
    ejecutar_main(argv=("subconjunto", "--area", "medellin"))
    medellin = pd.read_excel(Path("coordenadas") / "coordenadas_medellin.xlsx", index_col=0)
    assert list(medellin.index) == [0]
    assert (Path("mapas") / "medellin" / "individual.html").exists()


def test_estandarizar_sin_archivo_no_abre_dialogo(original_vacio, ejecutar_main):
    with pytest.raises(SystemExit) as salida:
        ejecutar_main(argv=("estandarizar",))
    assert "original" in salida.value.code
    assert list(ESTANDARIZADO.iterdir()) == []


def test_config_alternativa(directorio_trabajo, ejecutar_main):
    escribir_configuracion("otra.toml", ('"BARBOSA - ANTIOQUIA",', '"BARBOSA - ANTIOQUIA",\n    "RIONEGRO - ANTIOQUIA",'))
    ejecutar_main(argv=("--config", "otra.toml", "estandarizar"))
    assert list(pd.read_excel(FUERA, index_col=0).index) == [7]


# --- Menu --------------------------------------------------------------------------------------

def test_opcion_4_con_original_vacio_no_abre_dialogo(original_vacio, ejecutar_main):
    Path("coordenadas").mkdir()
    pd.DataFrame({"Latitud": [6.2], "Longitud": [-75.5]}).to_excel(COORDENADAS)
    ejecutar_main(4)
    assert (MAPAS / "individual.html").exists()


def test_opcion_1_con_original_vacio_abre_dialogo(original_vacio, ejecutar_main, monkeypatch):
    from georef import archivos

    abiertos = []

    class TkFalso:
        def withdraw(self):
            abiertos.append(True)

    monkeypatch.setattr(archivos.tk, "Tk", TkFalso)
    monkeypatch.setattr(archivos.filedialog, "askopenfilename", lambda **kwargs: "")
    with pytest.raises(SystemExit):
        ejecutar_main(1)
    assert abiertos == [True]


@pytest.mark.parametrize("eleccion", ["1", "medellin"])
def test_opcion_5_extrae_el_subconjunto_elegido(coordenadas_previas, ejecutar_main, capsys, eleccion):
    ejecutar_main(["5", eleccion])
    assert (Path("coordenadas") / "coordenadas_medellin.xlsx").exists()
    assert "1. medellin (MEDELLIN - ANTIOQUIA)" in capsys.readouterr().out


def test_opcion_invalida_se_vuelve_a_pedir(coordenadas_previas, ejecutar_main, capsys):
    ejecutar_main(["9", "4"])
    assert "Opción inválida" in capsys.readouterr().out
    assert (MAPAS / "individual.html").exists()


def test_menu_muestra_las_cinco_opciones(coordenadas_previas, ejecutar_main, capsys):
    ejecutar_main(4)
    salida = capsys.readouterr().out
    for opcion in ("1. Estandarización", "2. Conversión", "3. Mejora", "4. Generación", "5. Extracción"):
        assert opcion in salida


# --- Argumentos invalidos y ayuda ----------------------------------------------------------------

def test_subcomando_desconocido(original_vacio, ejecutar_main, capsys):
    with pytest.raises(SystemExit) as salida:
        ejecutar_main(argv=("exportar",))
    assert salida.value.code not in (None, 0)
    assert "estandarizar" in capsys.readouterr().err
    assert not ESTANDARIZADO.exists()


def test_subconjunto_sin_area(original_vacio, ejecutar_main, capsys):
    with pytest.raises(SystemExit) as salida:
        ejecutar_main(argv=("subconjunto",))
    assert salida.value.code not in (None, 0)
    assert "--area" in capsys.readouterr().err


def test_ayuda_lista_los_subcomandos(ejecutar_main, capsys):
    with pytest.raises(SystemExit) as salida:
        ejecutar_main(argv=("--help",))
    assert salida.value.code == 0
    ayuda = capsys.readouterr().out
    for subcomando in ("estandarizar", "geocodificar", "mejorar", "mapas", "subconjunto"):
        assert subcomando in ayuda
    assert "menú interactivo" in ayuda


# --- Configuracion invalida y credenciales -------------------------------------------------------

def test_configuracion_invalida_sin_efectos(coordenadas_previas, ejecutar_main, llave_falsa, geocodificador):
    escribir_configuracion("mala.toml", ("[columnas]\n", "[columnas]\ncolumna_extra = 1\n"))
    with pytest.raises(SystemExit) as salida:
        ejecutar_main(argv=("--config", "mala.toml", "geocodificar"))
    assert "columnas.columna_extra: clave desconocida" in salida.value.code
    assert geocodificador.consultas == []
    assert COORDENADAS.read_bytes() == coordenadas_previas


def test_configuracion_inexistente_no_crea_directorios(tmp_path, monkeypatch, ejecutar_main):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as salida:
        ejecutar_main(argv=("--config", "no_existe.toml", "estandarizar"))
    assert "no_existe.toml" in salida.value.code
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("subcomando", ["geocodificar", "mejorar"])
def test_subcomandos_con_proveedor_exigen_la_llave(coordenadas_previas, ejecutar_main, geocodificador, subcomando):
    with pytest.raises(SystemExit) as salida:
        ejecutar_main(argv=(subcomando,))
    assert "OPENCAGE_API_KEY" in salida.value.code
    assert geocodificador.consultas == []
    assert COORDENADAS.read_bytes() == coordenadas_previas


def test_subconjunto_no_exige_la_llave(coordenadas_previas, ejecutar_main):
    ejecutar_main(argv=("subconjunto", "--area", "medellin"))
    assert (Path("coordenadas") / "coordenadas_medellin.xlsx").exists()
