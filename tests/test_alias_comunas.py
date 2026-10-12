"""Invariantes de data/alias_comunas.csv (especificacion referencia-barrios)."""
import csv
import json
from pathlib import Path

import pytest

from test_alias_barrios import RUTA_ALIAS, RUTA_GEOJSON, leer_tabla, normalizar

RAIZ = Path(__file__).resolve().parent.parent
RUTA_ALIAS_COMUNAS = RAIZ / "data" / "alias_comunas.csv"
COLUMNAS = ["alias", "comuna", "nota"]


@pytest.fixture(scope="module")
def referencia():
    """(nombres de barrio normalizados, nombres de comuna, alias de barrio), leidos con json y csv."""
    propiedades = [f["properties"] for f in json.loads(RUTA_GEOJSON.read_text(encoding="utf-8"))["features"]]
    _, alias_barrios = leer_tabla(RUTA_ALIAS)
    return (
        {normalizar(p["nombre_barrio"]) for p in propiedades},
        {p["nombre_comuna"] for p in propiedades},
        {fila["alias"] for fila in alias_barrios},
    )


def errores_tabla(ruta, referencia):
    """Devuelve la lista de invariantes incumplidos por la tabla de variantes de comuna."""
    barrios, comunas, alias_barrios = referencia
    columnas, filas = leer_tabla(ruta)
    if columnas != COLUMNAS:
        return [f"columnas {columnas}, se esperaban {COLUMNAS}"]
    nombres_comuna = {normalizar(c) for c in comunas}
    errores, vistos = [], set()
    for numero, fila in enumerate(filas, start=2):
        alias = fila["alias"]
        if alias != normalizar(alias):
            errores.append(f"línea {numero}: '{alias}' no está normalizado")
        if alias in vistos:
            errores.append(f"línea {numero}: '{alias}' está repetido")
        vistos.add(alias)
        if alias in barrios or alias in nombres_comuna:
            errores.append(f"línea {numero}: '{alias}' repite un nombre oficial de barrio o comuna")
        if alias in alias_barrios:
            errores.append(f"línea {numero}: '{alias}' ya es un alias de barrio")
        if fila["comuna"] not in comunas:
            errores.append(f"línea {numero}: la comuna '{fila['comuna']}' no existe en el GeoJSON")
        if not fila["nota"].strip():
            errores.append(f"línea {numero}: falta la nota con el motivo")
    return errores


def escribir_tabla(ruta, filas):
    with open(ruta, "w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(COLUMNAS)
        escritor.writerows(filas)
    return ruta


def test_tabla_valida(referencia):
    assert errores_tabla(RUTA_ALIAS_COMUNAS, referencia) == []


def test_variantes_incluidas():
    _, filas = leer_tabla(RUTA_ALIAS_COMUNAS)
    assert {fila["alias"]: fila["comuna"] for fila in filas} == {
        "POBLADO": "EL POBLADO",
        "RODEO": "BELEN",
        "RODEO ALTO": "BELEN",
        "RODEO SUR": "BELEN",
    }


def test_variante_que_repite_un_nombre_de_barrio(tmp_path, referencia):
    ruta = escribir_tabla(tmp_path / "alias.csv", [["EL POBLADO", "EL POBLADO", "prueba"]])
    assert any("repite un nombre oficial" in e for e in errores_tabla(ruta, referencia))


def test_comuna_inexistente(tmp_path, referencia):
    ruta = escribir_tabla(tmp_path / "alias.csv", [["NORTICO", "NORTE", "prueba"]])
    assert any("no existe en el GeoJSON" in e for e in errores_tabla(ruta, referencia))


def test_detecta_otros_incumplimientos(tmp_path, referencia):
    ruta = escribir_tabla(tmp_path / "alias.csv", [
        ["poblado", "EL POBLADO", "x"],
        ["CALAZANS", "LA AMERICA", "x"],
        ["CALAZANS", "LA AMERICA", ""],
    ])
    errores = " | ".join(errores_tabla(ruta, referencia))
    for esperado in ("no está normalizado", "ya es un alias de barrio", "está repetido", "falta la nota"):
        assert esperado in errores
