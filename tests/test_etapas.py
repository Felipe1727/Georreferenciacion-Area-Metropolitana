"""Etapas del proceso: separación por área (specs/areas-geograficas), columnas y municipios
configurables (specs/configuracion) y lectura de coordenadas por su nombre nuevo."""
import re
import sys
from pathlib import Path

import pandas as pd
import pytest
from opencage.geocoder import RateLimitExceededError

from conftest import escribir_configuracion, resultado_api, seccion_puntos
from georef import archivos, etapas
from georef.config import cargar_configuracion
from georef.geografia import Poligonos

COORDENADAS = Path("coordenadas") / "coordenadas_area_metropolitana.xlsx"
COORDENADAS_ANTIGUO = Path("coordenadas") / "coordenadas.xlsx"
MAPAS_AM = Path("mapas") / "area_metropolitana"


@pytest.fixture
def trabajo(directorio_trabajo):
    archivos.estructura_programa()
    return directorio_trabajo


@pytest.fixture
def llave_falsa(monkeypatch):
    monkeypatch.setenv("OPENCAGE_API_KEY", "llave-falsa")


def leer(ruta):
    return pd.read_excel(ruta, index_col=0)


def test_separacion_por_municipio(trabajo, configuracion):
    etapas.estandarizar(configuracion)
    fuera = leer(archivos.RUTA_FUERA_AM)
    assert list(fuera.index) == [6, 7]
    assert set(fuera["Ciudad Residencia"]) == {"RIONEGRO - ANTIOQUIA", "MONTERIA - CORDOBA"}
    assert list(leer(archivos.RUTA_TOTAL_AM).index) == [0, 1, 2, 3, 4, 5, 8, 9]


def test_registro_sin_municipio_queda_fuera(tmp_path, monkeypatch, configuracion):
    monkeypatch.chdir(tmp_path)
    archivos.estructura_programa()
    pd.DataFrame(
        {"Ciudad Residencia": ["MEDELLIN - ANTIOQUIA", None], "Direccion de residencia": ["CL 1 2 3", "CL 4 5 6"]}
    ).to_excel(Path("original") / "base.xlsx", index=False)
    etapas.estandarizar(configuracion)
    assert list(leer(archivos.RUTA_FUERA_AM).index) == [1]


def test_nuevo_municipio_en_la_configuracion(trabajo):
    ruta = escribir_configuracion(
        trabajo / "otra.toml", ('"BARBOSA - ANTIOQUIA",', '"BARBOSA - ANTIOQUIA",\n    "RIONEGRO - ANTIOQUIA",')
    )
    etapas.estandarizar(cargar_configuracion(ruta))
    assert list(leer(archivos.RUTA_FUERA_AM).index) == [7]
    assert 6 in leer(archivos.RUTA_TOTAL_AM).index


def test_columna_ausente_no_escribe_archivos(tmp_path, monkeypatch, configuracion):
    monkeypatch.chdir(tmp_path)
    archivos.estructura_programa()
    pd.DataFrame({"Direccion de residencia": ["CL 1 2 3"]}).to_excel(Path("original") / "base.xlsx", index=False)
    with pytest.raises(SystemExit) as salida:
        etapas.estandarizar(configuracion)
    assert "'Ciudad Residencia'" in salida.value.code
    assert list(Path("estandarizado").iterdir()) == []


@pytest.mark.parametrize("etapa", ["ubicar", "generar_mapas"])
def test_nombre_antiguo_detiene_la_etapa(trabajo, configuracion, llave_falsa, cliente, etapa):
    pd.DataFrame({"Latitud": [6.2], "Longitud": [-75.5], "Complemento": ["X"]}).to_excel(COORDENADAS_ANTIGUO)
    contenido = COORDENADAS_ANTIGUO.read_bytes()
    with pytest.raises(SystemExit) as salida:
        getattr(etapas, etapa)(configuracion)
    assert "coordenadas/coordenadas.xlsx" in salida.value.code
    assert cliente.consultas == []
    assert not COORDENADAS.exists()
    assert COORDENADAS_ANTIGUO.read_bytes() == contenido
    assert not (Path("mapas") / "area_metropolitana" / "mapa.html").exists()


def test_mapas_sin_coordenadas(trabajo, configuracion):
    with pytest.raises(SystemExit) as salida:
        etapas.generar_mapas(configuracion)
    assert salida.value.code == etapas.MENSAJE_SIN_COORDENADAS


def test_mapas_del_area_metropolitana(trabajo, configuracion):
    pd.DataFrame({"Latitud": [6.2], "Longitud": [-75.5], "Nivel ubicacion": ["BARRIO"]}).to_excel(COORDENADAS)
    etapas.generar_mapas(configuracion)
    assert (Path("mapas") / "area_metropolitana" / "mapa.html").exists()


def test_mapas_con_coordenadas_de_formato_anterior(trabajo, configuracion):
    pd.DataFrame({"Latitud": [6.2], "Longitud": [-75.5]}).to_excel(COORDENADAS)
    with pytest.raises(SystemExit) as salida:
        etapas.generar_mapas(configuracion)
    assert salida.value.code == etapas.MENSAJE_SIN_NIVEL and "ubicar" in salida.value.code
    assert not (Path("mapas") / "area_metropolitana" / "mapa.html").exists()


def test_mapas_tras_ubicar(estandarizado, llave_falsa, cliente):
    etapas.ubicar(estandarizado)
    etapas.generar_mapas(estandarizado)
    coordenadas = leer_coordenadas()
    for ruta in (COORDENADAS, Path("coordenadas") / "cache_consultas.csv", Path("coordenadas") / "registro_consultas.csv"):
        assert ruta.exists()
    mapa = (MAPAS_AM / "mapa.html").read_text()
    # Un círculo por punto distinto de cada nivel.
    assert mapa.count("L.divIcon(") == len(coordenadas.groupby(["Nivel ubicacion", "Latitud", "Longitud"]))


def test_archivo_de_referencia_inexistente(trabajo):
    ruta = escribir_configuracion(
        trabajo / "otra.toml", ('geojson = "data/limite_barrio_vereda_cata.geojson"', 'geojson = "no_existe.geojson"')
    )
    with pytest.raises(SystemExit) as salida:
        etapas.estandarizar(cargar_configuracion(ruta))
    assert salida.value.code not in (None, 0)
    assert "no_existe.geojson" in salida.value.code
    assert list(Path("estandarizado").iterdir()) == []


def test_normalizacion_de_un_registro_de_fuera(trabajo, configuracion):
    etapas.estandarizar(configuracion)
    monteria = leer(archivos.RUTA_FUERA_AM).loc[7]
    assert monteria["Direccion de residencia"] == "CR 5 #10-20"
    assert monteria["Complemento"] == "CENTRO"
    assert monteria[["Barrio", "Codigo barrio", "Comuna"]].isna().all()


def test_columnas_normalizadas_en_los_cuatro_archivos(trabajo, configuracion):
    etapas.estandarizar(configuracion)
    for ruta in (archivos.RUTA_TOTAL_AM, archivos.RUTA_PRINCIPALES_AM, archivos.RUTA_ESPECIALES_AM, archivos.RUTA_FUERA_AM):
        columnas = list(leer(ruta).columns)
        posicion = columnas.index("Direccion de residencia")
        assert columnas[posicion:posicion + 6] == [
            "Direccion de residencia", "Complemento", "Barrio", "Codigo barrio", "Comuna", "Zona"
        ]


def test_codigo_barrio_se_lee_como_texto(trabajo, configuracion):
    etapas.estandarizar(configuracion)
    # Buenos Aires (fila 1) tiene el codigo 0907: con dtype=str se conserva el cero.
    principales = pd.read_excel(archivos.RUTA_PRINCIPALES_AM, index_col=0, dtype={"Codigo barrio": str})
    assert principales.loc[1, "Codigo barrio"] == "0907"
    assert pd.read_excel(archivos.RUTA_PRINCIPALES_AM, index_col=0).loc[1, "Codigo barrio"] == 907


# Etapa ubicar

COORDENADAS_ANTERIOR = Path("coordenadas") / "coordenadas_area_metropolitana_anterior.xlsx"
CONSULTA_LAURELES = "CL 10 #20-30, MEDELLIN, ANTIOQUIA, Colombia"
CONSULTAS_MEDELLIN = {CONSULTA_LAURELES, "CL 45S #12-15, MEDELLIN, ANTIOQUIA, Colombia",
                      "TV 32B #75-20, MEDELLIN, ANTIOQUIA, Colombia"}


@pytest.fixture
def estandarizado(trabajo, con_puntos):
    etapas.estandarizar(con_puntos)
    return con_puntos


def leer_coordenadas():
    return pd.read_excel(COORDENADAS, index_col=0, dtype={"Codigo barrio": str, "Codigo barrio ubicacion": str})


def test_primera_conversion_tras_estandarizar(estandarizado, llave_falsa, cliente):
    etapas.ubicar(estandarizado)
    coordenadas = leer_coordenadas()
    # Principales y especiales del área, en el orden del índice.
    assert list(coordenadas.index) == [0, 1, 2, 3, 4, 5, 8, 9]
    assert coordenadas[["Latitud", "Longitud", "Nivel ubicacion", "Resultado consulta"]].notna().all().all()
    assert set(cliente.consultas) == CONSULTAS_MEDELLIN


def test_registros_especiales_en_la_ubicacion(estandarizado, llave_falsa, cliente):
    etapas.ubicar(estandarizado)
    coordenadas = leer_coordenadas()
    assert set(leer(archivos.RUTA_ESPECIALES_AM).index) == {4, 5}
    assert coordenadas.loc[4, "Nivel ubicacion"] == "BARRIO"     # VEREDA EL PLAN, de Medellín
    assert coordenadas.loc[5, "Nivel ubicacion"] == "MUNICIPIO"  # FINCA, de Copacabana
    assert coordenadas.loc[[4, 5], "Resultado consulta"].tolist() == ["SIN_CONSULTA"] * 2


def test_registros_de_fuera_no_se_consultan(estandarizado, llave_falsa, cliente):
    etapas.ubicar(estandarizado)
    assert not any("RIONEGRO" in c or "MONTERIA" in c for c in cliente.consultas)


def test_conversion_reanudada(estandarizado, llave_falsa, cliente):
    cliente.respuestas = {c: RateLimitExceededError() for c in CONSULTAS_MEDELLIN - {CONSULTA_LAURELES}}
    etapas.ubicar(estandarizado)
    pendientes = leer_coordenadas()["Resultado consulta"].eq("PENDIENTE").sum()
    assert pendientes == 2
    primeras = list(cliente.consultas)
    cliente.respuestas = {}
    etapas.ubicar(estandarizado)
    nuevas = cliente.consultas[len(primeras):]
    # Solo se repiten las consultas pendientes; la de Laureles sale de la caché.
    assert sorted(nuevas) == sorted(CONSULTAS_MEDELLIN - {CONSULTA_LAURELES})
    assert not leer_coordenadas()["Resultado consulta"].eq("PENDIENTE").any()


def test_ubicacion_repetida_sin_peticiones(estandarizado, llave_falsa, cliente):
    etapas.ubicar(estandarizado)
    total = len(cliente.consultas)
    etapas.ubicar(estandarizado)
    assert len(cliente.consultas) == total


def test_ubicar_sin_estandarizar(trabajo, con_puntos, llave_falsa, cliente):
    # Solo existe el nombre anterior a fundamentos.
    pd.DataFrame({"Direccion de residencia": ["CL 1 #2-3"]}).to_excel(
        Path("estandarizado") / "principales_área_metropolitana.xlsx")
    with pytest.raises(SystemExit) as salida:
        etapas.ubicar(con_puntos)
    assert "estandarización" in salida.value.code
    assert cliente.consultas == [] and not COORDENADAS.exists()


def test_ubicar_con_el_nombre_antiguo(estandarizado, llave_falsa, cliente):
    pd.DataFrame({"Latitud": [6.2], "Longitud": [-75.5]}).to_excel(COORDENADAS_ANTIGUO)
    with pytest.raises(SystemExit) as salida:
        etapas.ubicar(estandarizado)
    assert "coordenadas/coordenadas.xlsx" in salida.value.code
    assert cliente.consultas == [] and not COORDENADAS.exists()


def test_se_conserva_el_archivo_de_formato_anterior(estandarizado, llave_falsa, cliente):
    pd.DataFrame({"Latitud": [6.2], "Longitud": [-75.5]}).to_excel(COORDENADAS)
    contenido = COORDENADAS.read_bytes()
    etapas.ubicar(estandarizado)
    assert COORDENADAS_ANTERIOR.read_bytes() == contenido
    assert "Nivel ubicacion" in leer_coordenadas().columns


def test_archivo_de_formato_nuevo_no_se_conserva(estandarizado, llave_falsa, cliente):
    etapas.ubicar(estandarizado)
    etapas.ubicar(estandarizado)
    assert not COORDENADAS_ANTERIOR.exists()


def test_copia_anterior_ya_existente(estandarizado, llave_falsa, cliente):
    pd.DataFrame({"Latitud": [6.2], "Longitud": [-75.5]}).to_excel(COORDENADAS)
    pd.DataFrame({"Latitud": [6.3], "Longitud": [-75.6]}).to_excel(COORDENADAS_ANTERIOR)
    with pytest.raises(SystemExit) as salida:
        etapas.ubicar(estandarizado)
    assert salida.value.code not in (None, 0)
    assert COORDENADAS.as_posix() in salida.value.code and COORDENADAS_ANTERIOR.as_posix() in salida.value.code
    assert cliente.consultas == []


def test_municipio_sin_punto(trabajo, configuracion, llave_falsa, cliente):
    etapas.estandarizar(configuracion)
    ruta = trabajo / "config" / "georef.toml"
    municipios = [m for m in configuracion.area_metropolitana if m != "CALDAS - ANTIOQUIA"]
    with open(ruta, "a", encoding="utf-8") as archivo:
        archivo.write(seccion_puntos(municipios))
    with pytest.raises(SystemExit) as salida:
        etapas.ubicar(cargar_configuracion(ruta))
    assert salida.value.code not in (None, 0)
    assert "CALDAS - ANTIOQUIA" in salida.value.code and "consultar-municipios" in salida.value.code
    assert cliente.consultas == [] and not COORDENADAS.exists()


def test_punto_corregido_a_mano(estandarizado, llave_falsa, cliente):
    etapas.ubicar(estandarizado)
    ruta = estandarizado.ruta
    texto = ruta.read_text(encoding="utf-8")
    linea = next(l for l in texto.splitlines() if l.startswith('"BELLO - ANTIOQUIA"'))
    ruta.write_text(texto.replace(linea, linea.split(" = ")[0] + ' = { latitud = 6.5, longitud = -75.5, '
                                  'fuente = "a mano", fecha = "2026-10-12" }'), encoding="utf-8")
    peticiones = len(cliente.consultas)
    etapas.ubicar(cargar_configuracion(ruta))
    assert leer_coordenadas().loc[3, "Latitud"] == 6.5  # registro de Bello
    assert len(cliente.consultas) == peticiones


def test_resumen_de_la_ubicacion(estandarizado, llave_falsa, cliente, capsys):
    cliente.respuestas[CONSULTA_LAURELES] = [resultado_api(6.2, -75.5, tipo="city")]
    etapas.ubicar(estandarizado)
    salida = capsys.readouterr().out
    assert "Por nivel:" in salida and "MUNICIPIO:" in salida and "PRECISION_INSUFICIENTE: 1" in salida
    assert "Peticiones a OpenCage: 3" in salida
    assert not any(direccion in salida for direccion in ("CL 10", "LAURELES", "CALASANZ", "BUENOS AIRES"))


def test_avance_de_la_ubicacion(estandarizado, llave_falsa, cliente, capsys):
    etapas.ubicar(estandarizado)
    avance = capsys.readouterr().err
    # Fuera de una terminal: una línea cada 100 registros y la del último.
    assert avance.splitlines() == [l for l in avance.splitlines() if l.startswith("Registro ")]
    assert "Registro 8 de 8 · peticiones a OpenCage: " in avance
    assert not any(direccion in avance for direccion in ("CL 10", "LAURELES", "CALASANZ", "MEDELLIN"))


def test_avance_en_una_terminal(estandarizado, llave_falsa, cliente, capsys, monkeypatch):
    monkeypatch.setattr(sys.stderr, "isatty", lambda: True)
    etapas.ubicar(estandarizado)
    avance = capsys.readouterr().err
    assert [f"Registro {n} de 8" in avance for n in range(1, 9)] == [True] * 8
    assert avance.count("\r") == 8 and avance.endswith("pendientes: 0\n")


def test_ubicacion_sin_consultas(estandarizado, cliente):
    # Sin llave definida (el fixture autouse la elimina del entorno).
    etapas.ubicar(estandarizado, sin_consultas=True)
    coordenadas = leer_coordenadas()
    assert cliente.consultas == [] and cliente.llaves == []
    assert set(coordenadas["Resultado consulta"]) <= {"PENDIENTE", "SIN_CONSULTA"}
    assert coordenadas["Latitud"].notna().all()


# Mapas (specs/mapas y specs/archivos-de-salida)

def coordenadas_sinteticas(codigo=None):
    pd.DataFrame({"Ciudad Residencia": ["MEDELLIN - ANTIOQUIA", "BELLO - ANTIOQUIA"],
                  "Direccion de residencia": ["CL 1 #2-3", "CR 4 #5-6"],
                  "Latitud": [6.25, 6.33], "Longitud": [-75.58, -75.55], "Nivel ubicacion": ["BARRIO", "MUNICIPIO"],
                  "Codigo barrio ubicacion": [codigo, None]}).to_excel(COORDENADAS)


def test_mapas_anteriores_presentes(trabajo, configuracion, capsys):
    coordenadas_sinteticas()
    (MAPAS_AM / "individual.html").write_text("anterior", encoding="utf-8")
    (MAPAS_AM / "filtrados").mkdir()
    etapas.generar_mapas(configuracion)
    salida = capsys.readouterr().out
    assert "ya no se actualizan" in salida and "individual.html" in salida and "filtrados" in salida
    assert (MAPAS_AM / "individual.html").read_text(encoding="utf-8") == "anterior"
    assert (MAPAS_AM / "filtrados").is_dir()


def test_sin_aviso_sin_mapas_anteriores(trabajo, configuracion, capsys):
    coordenadas_sinteticas()
    etapas.generar_mapas(configuracion)
    salida = capsys.readouterr().out
    assert "ya no se actualizan" not in salida and "mapas/area_metropolitana/mapa.html" in salida


def test_opcion_sin_municipio_sin_separados(trabajo, configuracion):
    coordenadas_sinteticas()
    with pytest.raises(SystemExit) as salida:
        etapas.generar_mapas(configuracion, sin_municipio=True)
    assert "--separado" in salida.value.code
    assert not (MAPAS_AM / "mapa.html").exists()


def test_todos_los_separados_sin_municipio(trabajo, configuracion):
    coordenadas_sinteticas()
    etapas.generar_mapas(configuracion, ["todos"], sin_municipio=True)
    assert sorted(p.name for p in (MAPAS_AM / "separados").iterdir()) == [
        "barrios_cantidad.html", "clusters_sin_municipio.html", "comunas_cantidad.html", "puntos_sin_municipio.html"]


def test_codigo_de_barrio_con_cero_inicial_en_la_capa_coloreada(trabajo, configuracion):
    poligonos = Poligonos.cargar(configuracion.referencia.geojson)
    codigo = next(c for c in poligonos.codigos if c.startswith("0"))
    coordenadas_sinteticas(codigo)
    etapas.generar_mapas(configuracion, ["barrios_cantidad"])
    mapa = (MAPAS_AM / "separados" / "barrios_cantidad.html").read_text(encoding="utf-8")
    assert re.search(rf'"codigo": "{codigo}", [^}}]*"registros": 1\b', mapa)


def test_los_mapas_no_contienen_otras_columnas(trabajo, configuracion):
    coordenadas_sinteticas()
    etapas.generar_mapas(configuracion, ["todos"])
    for ruta in MAPAS_AM.rglob("*.html"):
        contenido = ruta.read_text(encoding="utf-8")
        assert "CL 1 #2-3" not in contenido and "CR 4 #5-6" not in contenido
