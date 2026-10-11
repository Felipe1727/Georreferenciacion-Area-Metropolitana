"""Guardia: todos los identificadores del codigo fuente deben ser ASCII.

Python acepta identificadores Unicode (PEP 3131), asi que nada impide
reintroducirlos sin esta comprobacion. Los literales, comentarios y docstrings
pueden contener texto en espanol con tildes: son datos, no identificadores.
"""
import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIRECTORIOS_EXCLUIDOS = {".git", ".idea", "__pycache__", ".pytest_cache", ".ipynb_checkpoints",
                         "original", "estandarizado", "coordenadas", "mapas", "llave"}


def identificadores_no_ascii(fuente, nombre_archivo="<fuente>"):
    """Devuelve [(linea, identificador)] con los identificadores no ASCII de `fuente`."""
    hallados = []
    for nodo in ast.walk(ast.parse(fuente, filename=nombre_archivo)):
        nombres = []
        if isinstance(nodo, ast.Name):
            nombres = [nodo.id]
        elif isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            nombres = [nodo.name]
        elif isinstance(nodo, ast.arg):
            nombres = [nodo.arg]
        elif isinstance(nodo, ast.Attribute):
            nombres = [nodo.attr]
        elif isinstance(nodo, ast.alias):
            nombres = [nodo.name, nodo.asname or ""]
        elif isinstance(nodo, (ast.Global, ast.Nonlocal)):
            nombres = list(nodo.names)
        elif isinstance(nodo, ast.keyword):
            nombres = [nodo.arg or ""]
        hallados += [(getattr(nodo, "lineno", 0), n) for n in nombres if not n.isascii()]
    return hallados


def archivos_python():
    for ruta in RAIZ.rglob("*.py"):
        if not DIRECTORIOS_EXCLUIDOS.intersection(ruta.relative_to(RAIZ).parts):
            yield ruta


def test_identificadores_del_repositorio_son_ascii():
    problemas = []
    for ruta in archivos_python():
        relativa = ruta.relative_to(RAIZ)
        if not relativa.as_posix().isascii():
            problemas.append(f"{relativa}: nombre de modulo no ASCII")
        for linea, nombre in identificadores_no_ascii(ruta.read_text(encoding="utf-8"), str(ruta)):
            problemas.append(f"{relativa}:{linea}: {nombre}")
    assert problemas == []


def test_detecta_identificador_no_ascii():
    fuente = "def estandarización(vía):\n    área = vía\n    return área\n"
    nombres = {nombre for _, nombre in identificadores_no_ascii(fuente)}
    assert nombres == {"estandarización", "vía", "área"}


def test_ignora_literales_y_comentarios_con_tildes():
    fuente = "# Comentario con tildes: área\nmensaje = 'Opción inválida'\n"
    assert identificadores_no_ascii(fuente) == []
