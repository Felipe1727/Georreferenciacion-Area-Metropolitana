"""Invariantes de data/alias_barrios.csv frente al GeoJSON oficial (especificación referencia-barrios)."""
import csv
import json
from pathlib import Path

import pytest

from georef.referencia import normalizar

RAIZ = Path(__file__).resolve().parent.parent
RUTA_GEOJSON = RAIZ / "data" / "limite_barrio_vereda_cata.geojson"
RUTA_ALIAS = RAIZ / "data" / "alias_barrios.csv"
COLUMNAS = ["alias", "codigo", "nombre_oficial", "nota"]


@pytest.fixture(scope="module")
def poligonos():
    """codigo -> nombre_barrio, leído con json (no necesita geopandas ni PROJ)."""
    datos = json.loads(RUTA_GEOJSON.read_text(encoding="utf-8"))
    return {f["properties"]["codigo"]: f["properties"]["nombre_barrio"] for f in datos["features"]}


def leer_tabla(ruta):
    with open(ruta, encoding="utf-8", newline="") as archivo:
        lector = csv.DictReader(archivo)
        return lector.fieldnames, list(lector)


def errores_tabla(ruta, poligonos):
    """Devuelve la lista de invariantes incumplidos por la tabla de alias (vacía si es válida)."""
    columnas, filas = leer_tabla(ruta)
    if columnas != COLUMNAS:
        return [f"columnas {columnas}, se esperaban {COLUMNAS}"]
    oficiales = {normalizar(nombre) for nombre in poligonos.values()}
    errores, vistos = [], set()
    for numero, fila in enumerate(filas, start=2):
        alias, codigo = fila["alias"], fila["codigo"]
        if alias != normalizar(alias):
            errores.append(f"línea {numero}: '{alias}' no está normalizado")
        if alias in vistos:
            errores.append(f"línea {numero}: '{alias}' está repetido")
        vistos.add(alias)
        if alias in oficiales:
            errores.append(f"línea {numero}: '{alias}' redefiniría un nombre oficial")
        if codigo not in poligonos:
            errores.append(f"línea {numero}: el codigo '{codigo}' no existe en el GeoJSON")
        elif fila["nombre_oficial"] != poligonos[codigo]:
            errores.append(f"línea {numero}: nombre_oficial '{fila['nombre_oficial']}' no es '{poligonos[codigo]}'")
        if not fila["nota"].strip():
            errores.append(f"línea {numero}: falta la nota con el motivo del alias")
    return errores


def escribir_tabla(ruta, filas):
    with open(ruta, "w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(COLUMNAS)
        escritor.writerows(filas)
    return ruta


def test_normalizacion():
    assert normalizar("Área de Expansión Pajarito") == "AREA DE EXPANSION PAJARITO"
    assert normalizar("La Cabaña") == "LA CABANA"
    assert normalizar("  carlos e.  restrepo ") == "CARLOS E RESTREPO"


def test_codigo_unico_y_como_texto(poligonos):
    datos = json.loads(RUTA_GEOJSON.read_text(encoding="utf-8"))
    codigos = [f["properties"]["codigo"] for f in datos["features"]]
    assert len(codigos) == 349 and len(set(codigos)) == 349
    assert all(isinstance(c, str) for c in codigos) and "0806" in poligonos


def test_tabla_valida(poligonos):
    assert RUTA_ALIAS.exists(), "Falta data/alias_barrios.csv"
    assert errores_tabla(RUTA_ALIAS, poligonos) == []


def test_codigo_conserva_ceros(poligonos):
    _, filas = leer_tabla(RUTA_ALIAS)
    assert all(len(fila["codigo"]) == 4 for fila in filas)


def test_alias_que_repite_un_nombre_oficial(tmp_path, poligonos):
    codigo = next(c for c, n in poligonos.items() if n == "Laureles")
    ruta = escribir_tabla(tmp_path / "alias.csv", [["LAURELES", codigo, "Laureles", "prueba"]])
    assert any("redefiniría un nombre oficial" in e for e in errores_tabla(ruta, poligonos))


def test_codigo_inexistente(tmp_path, poligonos):
    ruta = escribir_tabla(tmp_path / "alias.csv", [["LAURELEZ", "9999", "Laureles", "variante ortográfica"]])
    assert any("no existe en el GeoJSON" in e for e in errores_tabla(ruta, poligonos))


def test_detecta_otros_incumplimientos(tmp_path, poligonos):
    codigo = next(c for c, n in poligonos.items() if n == "Calasanz")
    ruta = escribir_tabla(tmp_path / "alias.csv", [
        ["calazans", codigo, "Calasanz", "variante ortográfica"],
        ["CALAZANS", codigo, "Calasanz", "variante ortográfica"],
        ["CALAZANS", codigo, "Otro nombre", ""],
    ])
    errores = " | ".join(errores_tabla(ruta, poligonos))
    for esperado in ("no está normalizado", "está repetido", "no es 'Calasanz'", "falta la nota"):
        assert esperado in errores
