"""Interfaz de línea de comandos: subcomandos con argparse y menú interactivo.

`python -m georef <subcomando>` ejecuta una etapa sin hacer preguntas; sin subcomando
se muestra el menú interactivo. `python main.py` llama a `main()` con los mismos
argumentos, y su modo heredado `python main.py c` equivale a `ubicar`. Los diagnósticos
(`consultar-municipios` y `comparar-consultas`) solo existen como subcomandos.
"""
import argparse
import sys
from pathlib import Path

from georef import archivos, etapas
from georef.config import RUTA_POR_DEFECTO, ErrorConfiguracion, cargar_configuracion

# Subcomando -> descripción para la ayuda (en el orden en que se listan)
SUBCOMANDOS = {
    "estandarizar": "estandariza las direcciones del archivo de 'original/'",
    "ubicar": "ubica por niveles (dirección, barrio, comuna o municipio) a los registros del área metropolitana",
    "mapas": "genera los mapas del área metropolitana",
    "subconjunto": "extrae un subconjunto del área metropolitana (coordenadas y mapas) sin usar la API",
    "consultar-municipios": "consulta una vez a OpenCage el punto de los municipios que no lo tienen en la "
                            "configuración",
    "comparar-consultas": "compara en una muestra los dos formatos de consulta a OpenCage (solo cifras agregadas)",
}

OPCIONES_MENU = {
    "1": "estandarización de direcciones",
    "2": "ubicación por niveles (coordenadas)",
    "3": "generación de mapas",
    "4": "extracción de un subconjunto (coordenadas y mapas, sin usar la API)",
}


def construir_parser() -> argparse.ArgumentParser:
    """Parser de `python -m georef`."""
    parser = argparse.ArgumentParser(
        prog="python -m georef",
        description="Estandarización, ubicación por niveles y mapas de direcciones de residencia.",
        epilog="Sin subcomando se muestra el menú interactivo.",
    )
    parser.add_argument(
        "--config", type=Path, default=RUTA_POR_DEFECTO, metavar="RUTA",
        help=f"archivo de configuración (por defecto: {RUTA_POR_DEFECTO.as_posix()})",
    )
    subparsers = parser.add_subparsers(dest="subcomando", title="subcomandos", metavar="SUBCOMANDO")
    subparsers_por_nombre = {
        nombre: subparsers.add_parser(nombre, help=descripcion,
                                      description=descripcion[0].upper() + descripcion[1:] + ".")
        for nombre, descripcion in SUBCOMANDOS.items()
    }
    subparsers_por_nombre["ubicar"].add_argument(
        "--sin-consultas", action="store_true",
        help="no hace peticiones ni pide la llave: usa solo la caché y deja pendiente lo demás")
    subparsers_por_nombre["subconjunto"].add_argument(
        "--area", required=True, metavar="NOMBRE",
        help="nombre del subconjunto definido en la configuración (por ejemplo, medellin)")
    subparsers_por_nombre["comparar-consultas"].add_argument(
        "--muestra", required=True, type=entero_positivo, metavar="N",
        help="número máximo de direcciones distintas de la muestra (cada una se consulta en los dos formatos)")
    return parser


def entero_positivo(texto):
    """Tipo de argparse para `--muestra`: un entero mayor que cero."""
    try:
        valor = int(texto)
    except ValueError:
        valor = 0
    if valor <= 0:
        raise argparse.ArgumentTypeError(f"la muestra debe ser un entero positivo, no '{texto}'")
    return valor


def main(argv=None):
    """
    Punto de entrada: analiza los argumentos, carga y valida la configuración, crea los
    directorios de trabajo y ejecuta el subcomando o, si no hay ninguno, el menú interactivo.
    """
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv == ["c"]:
        # Modo heredado de main.py: conversión de coordenadas (ahora, la ubicación) sin menú.
        argv = ["ubicar"]
    argumentos = construir_parser().parse_args(argv)

    try:
        configuracion = cargar_configuracion(argumentos.config)
    except ErrorConfiguracion as error:
        sys.exit(error.mensaje())

    archivos.estructura_programa()
    match argumentos.subcomando:
        case None:
            menu(configuracion)
        case "estandarizar":
            etapas.estandarizar(configuracion)
        case "ubicar":
            etapas.ubicar(configuracion, sin_consultas=argumentos.sin_consultas)
        case "mapas":
            etapas.generar_mapas(configuracion)
        case "subconjunto":
            etapas.extraer_subconjunto(configuracion, argumentos.area)
        case "consultar-municipios":
            etapas.consultar_municipios(configuracion)
        case "comparar-consultas":
            etapas.comparar_consultas(configuracion, argumentos.muestra)


def menu(configuracion):
    """Muestra el menú interactivo y ejecuta la etapa elegida."""
    match seleccionar_funcionalidad():
        case "1":
            # Solo la estandarización lee 'original/': si está vacía, se ofrece el diálogo.
            archivos.verificar_y_copiar_archivo_original()
            etapas.estandarizar(configuracion)
        case "2":
            etapas.ubicar(configuracion)
        case "3":
            etapas.generar_mapas(configuracion)
        case "4":
            etapas.extraer_subconjunto(configuracion, seleccionar_subconjunto(configuracion))


def seleccionar_funcionalidad():
    """
    Muestra un menú interactivo para que el usuario seleccione la funcionalidad deseada.

    Returns:
        str: Número de la opción seleccionada ('1'-'4').
    """
    print("Selecciona una funcionalidad:")
    for clave, descripcion in OPCIONES_MENU.items():
        print(f"{clave}. {descripcion.capitalize()}")

    while True:
        seleccion = input("Ingresa el número de la opción deseada (1-4): ").strip()
        if seleccion in OPCIONES_MENU:
            print(f"Has seleccionado: {OPCIONES_MENU[seleccion].capitalize()}")
            return seleccion
        else:
            print("Opción inválida. Por favor elige 1, 2, 3 o 4.")


def seleccionar_subconjunto(configuracion):
    """Lista los subconjuntos configurados y devuelve el nombre del elegido (por número o por nombre)."""
    nombres = sorted(configuracion.subconjuntos)
    if not nombres:
        sys.exit("Error: La configuración no define ningún subconjunto. "
                 "Añade uno en la sección [subconjuntos] del archivo de configuración.")

    print("Subconjuntos disponibles:")
    for numero, nombre in enumerate(nombres, start=1):
        print(f"{numero}. {nombre} ({', '.join(configuracion.subconjuntos[nombre])})")

    while True:
        seleccion = input(f"Ingresa el número o el nombre del subconjunto (1-{len(nombres)}): ").strip()
        if seleccion in nombres:
            return seleccion
        if seleccion.isdigit() and 1 <= int(seleccion) <= len(nombres):
            return nombres[int(seleccion) - 1]
        print("Subconjunto inválido.")
