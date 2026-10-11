"""Interfaz de línea de comandos: subcomandos con argparse y menú interactivo.

`python -m georef <subcomando>` ejecuta una etapa sin hacer preguntas; sin subcomando
se muestra el menú interactivo. `python main.py` llama a `main()` con los mismos
argumentos, y su modo heredado `python main.py c` equivale a `geocodificar`.
"""
import argparse
import sys
from pathlib import Path

from georef import archivos, etapas
from georef.config import RUTA_POR_DEFECTO, ErrorConfiguracion, cargar_configuracion

# Subcomando -> (función de la etapa, descripción para la ayuda)
SUBCOMANDOS = {
    "estandarizar": (etapas.estandarizar, "estandariza las direcciones del archivo de 'original/'"),
    "geocodificar": (etapas.geocodificar, "obtiene las coordenadas del área metropolitana con OpenCage"),
    "mejorar": (etapas.mejorar, "vuelve a geocodificar por barrio los puntos en el centroide de Medellín"),
    "mapas": (etapas.generar_mapas, "genera los mapas del área metropolitana"),
}

OPCIONES_MENU = {
    "1": "estandarización de direcciones",
    "2": "conversión de coordenadas",
    "3": "mejora de coordenadas (sólo si ya se realizó la conversión)",
    "4": "generación de mapas",
    "5": "extracción de un subconjunto (coordenadas y mapas, sin usar la API)",
}


def construir_parser() -> argparse.ArgumentParser:
    """Parser de `python -m georef`."""
    parser = argparse.ArgumentParser(
        prog="python -m georef",
        description="Estandarización, geocodificación y mapas de direcciones de residencia.",
        epilog="Sin subcomando se muestra el menú interactivo.",
    )
    parser.add_argument(
        "--config", type=Path, default=RUTA_POR_DEFECTO, metavar="RUTA",
        help=f"archivo de configuración (por defecto: {RUTA_POR_DEFECTO.as_posix()})",
    )
    subparsers = parser.add_subparsers(dest="subcomando", title="subcomandos", metavar="SUBCOMANDO")
    for nombre, (_, descripcion) in SUBCOMANDOS.items():
        subparsers.add_parser(nombre, help=descripcion, description=descripcion[0].upper() + descripcion[1:] + ".")
    descripcion = "extrae un subconjunto del área metropolitana (coordenadas y mapas) sin usar la API"
    subconjunto = subparsers.add_parser("subconjunto", help=descripcion,
                                        description=descripcion[0].upper() + descripcion[1:] + ".")
    subconjunto.add_argument("--area", required=True, metavar="NOMBRE",
                             help="nombre del subconjunto definido en la configuración (por ejemplo, medellin)")
    return parser


def main(argv=None):
    """
    Punto de entrada: analiza los argumentos, carga y valida la configuración, crea los
    directorios de trabajo y ejecuta el subcomando o, si no hay ninguno, el menú interactivo.
    """
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv == ["c"]:
        # Modo heredado de main.py: conversión de coordenadas sin menú.
        argv = ["geocodificar"]
    argumentos = construir_parser().parse_args(argv)

    try:
        configuracion = cargar_configuracion(argumentos.config)
    except ErrorConfiguracion as error:
        sys.exit(error.mensaje())

    archivos.estructura_programa()
    if argumentos.subcomando is None:
        menu(configuracion)
    elif argumentos.subcomando == "subconjunto":
        etapas.extraer_subconjunto(configuracion, argumentos.area)
    else:
        etapa, _ = SUBCOMANDOS[argumentos.subcomando]
        etapa(configuracion)


def menu(configuracion):
    """Muestra el menú interactivo y ejecuta la etapa elegida."""
    match seleccionar_funcionalidad():
        case "1":
            # Solo la estandarización lee 'original/': si está vacía, se ofrece el diálogo.
            archivos.verificar_y_copiar_archivo_original()
            etapas.estandarizar(configuracion)
        case "2":
            etapas.geocodificar(configuracion)
        case "3":
            etapas.mejorar(configuracion)
        case "4":
            etapas.generar_mapas(configuracion)
        case "5":
            etapas.extraer_subconjunto(configuracion, seleccionar_subconjunto(configuracion))


def seleccionar_funcionalidad():
    """
    Muestra un menú interactivo para que el usuario seleccione la funcionalidad deseada.

    Returns:
        str: Número de la opción seleccionada ('1'-'5').
    """
    print("Selecciona una funcionalidad:")
    for clave, descripcion in OPCIONES_MENU.items():
        print(f"{clave}. {descripcion.capitalize()}")

    while True:
        seleccion = input("Ingresa el número de la opción deseada (1-5): ").strip()
        if seleccion in OPCIONES_MENU:
            print(f"Has seleccionado: {OPCIONES_MENU[seleccion].capitalize()}")
            return seleccion
        else:
            print("Opción inválida. Por favor elige 1, 2, 3, 4 o 5.")


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
