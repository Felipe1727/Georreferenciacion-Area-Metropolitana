"""Rutas de trabajo, estructura de directorios y lectura del archivo de entrada.

Todas las rutas son relativas al directorio de trabajo (la raíz del proyecto), igual
que `.env` y `config/georef.toml`. Los nombres de coordenadas y mapas se derivan del
identificador del área: `area_metropolitana` o el nombre de un subconjunto.
"""
import shutil
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import pandas as pd

from georef.config import AREA_METROPOLITANA, Columnas

CARPETA_ORIGINAL = Path("original")
CARPETA_ESTANDARIZADO = Path("estandarizado")
CARPETA_COORDENADAS = Path("coordenadas")
CARPETA_MAPAS = Path("mapas")

# Archivos generados por la estandarización (nombres solo en ASCII)
RUTA_TOTAL_AM = CARPETA_ESTANDARIZADO / f"total_{AREA_METROPOLITANA}.xlsx"
RUTA_PRINCIPALES_AM = CARPETA_ESTANDARIZADO / f"principales_{AREA_METROPOLITANA}.xlsx"
RUTA_ESPECIALES_AM = CARPETA_ESTANDARIZADO / f"especiales_{AREA_METROPOLITANA}.xlsx"
RUTA_FUERA_AM = CARPETA_ESTANDARIZADO / f"fuera_{AREA_METROPOLITANA}.xlsx"

# Copia del archivo de coordenadas de formato anterior a ubicacion-por-niveles (sin 'Nivel ubicacion').
RUTA_COORDENADAS_ANTERIOR = CARPETA_COORDENADAS / f"coordenadas_{AREA_METROPOLITANA}_anterior.xlsx"

# Caché de las respuestas de OpenCage y registro de diagnóstico de cada petición (contienen
# direcciones: están en coordenadas/, que git ignora).
RUTA_CACHE_CONSULTAS = CARPETA_COORDENADAS / "cache_consultas.csv"
RUTA_REGISTRO_CONSULTAS = CARPETA_COORDENADAS / "registro_consultas.csv"

# Nombre que tenía el archivo de coordenadas antes de modularizacion-config.
RUTA_COORDENADAS_ANTIGUA = CARPETA_COORDENADAS / "coordenadas.xlsx"

# Prefijos de los archivos que no cuentan como archivo de entrada: ocultos (incluido el
# bloqueo de LibreOffice, `.~lock.<nombre>#`) y bloqueo de Excel (`~$<nombre>`).
PREFIJOS_IGNORADOS = (".", "~$")


def ruta_coordenadas(area: str) -> Path:
    """Archivo de coordenadas de un área: `coordenadas/coordenadas_<area>.xlsx`."""
    return CARPETA_COORDENADAS / f"coordenadas_{area}.xlsx"


def carpeta_mapas(area: str) -> Path:
    """Carpeta de los mapas de un área: `mapas/<area>/`."""
    return CARPETA_MAPAS / area


def estructura_programa():
    """
    Crea la estructura de directorios requerida por el programa si no existen.
    """
    rutas = [
        CARPETA_ORIGINAL,
        CARPETA_ESTANDARIZADO,
        CARPETA_COORDENADAS,
        carpeta_mapas(AREA_METROPOLITANA) / "filtrados",
    ]
    for ruta in rutas:
        ruta.mkdir(parents=True, exist_ok=True)


def archivos_de_entrada() -> list[Path]:
    """Archivos de `original/` que cuentan como entrada: sin subdirectorios, ocultos ni bloqueos."""
    if not CARPETA_ORIGINAL.is_dir():
        return []
    return sorted(
        ruta for ruta in CARPETA_ORIGINAL.iterdir()
        if ruta.is_file() and not ruta.name.startswith(PREFIJOS_IGNORADOS)
    )


def verificar_y_copiar_archivo_original():
    """
    Si `original/` no contiene ningún archivo de entrada, permite al usuario seleccionar uno
    mediante un diálogo gráfico para copiarlo a esa carpeta. Solo lo usa el menú interactivo.
    """
    if not archivos_de_entrada():
        print("La carpeta 'original' está vacía. Selecciona un archivo para copiar allí.")

        # Oculta la ventana principal de tkinter
        root = tk.Tk()
        root.withdraw()

        # Abre el diálogo para seleccionar archivo
        archivo_origen = filedialog.askopenfilename(title="Selecciona un archivo para copiar a 'original'")

        if archivo_origen:
            # Copia el archivo a la carpeta 'original'
            archivo_destino = CARPETA_ORIGINAL / Path(archivo_origen).name
            shutil.copy(archivo_origen, archivo_destino)
            print(f"Archivo copiado a: {archivo_destino}")
        else:
            print("No se seleccionó ningún archivo.")


def leer_archivo_original() -> pd.DataFrame:
    """
    Lee el único archivo de entrada de la carpeta 'original' y lo carga en un DataFrame.

    Termina el programa con un mensaje si no hay ningún archivo de entrada o hay más de uno.

    Returns:
        pd.DataFrame: Datos cargados desde el archivo Excel.
    """
    archivos = archivos_de_entrada()
    if len(archivos) > 1:
        sys.exit("Error: Hay más de un archivo en la carpeta 'original'. Asegúrate de que solo haya uno.")
    if not archivos:
        sys.exit("Error: No hay ningún archivo en la carpeta 'original'. "
                 "Coloca allí el archivo de Excel con las direcciones.")
    return pd.read_excel(archivos[0])


def verificar_columnas(df: pd.DataFrame, columnas: Columnas):
    """Termina el programa si el archivo de entrada no tiene alguna de las columnas configuradas."""
    faltantes = [nombre for nombre in (columnas.ciudad, columnas.direccion) if nombre not in df.columns]
    if faltantes:
        nombres = ", ".join(f"'{nombre}'" for nombre in faltantes)
        sys.exit(f"Error: El archivo de entrada no tiene la columna {nombres}. "
                 "Revisa la sección [columnas] de la configuración.")


def verificar_principales_am():
    """
    Termina el programa con un mensaje si no existe el archivo de direcciones principales estandarizadas,
    necesario para la conversión de coordenadas cuando aún no hay archivo de coordenadas.
    """
    if not RUTA_PRINCIPALES_AM.exists():
        sys.exit(f"Error: No se encontró '{RUTA_PRINCIPALES_AM.as_posix()}'. "
                 "Ejecuta primero la estandarización de direcciones (opción 1).")


def verificar_nombre_antiguo_coordenadas():
    """
    Termina el programa si solo existe el archivo de coordenadas con el nombre anterior.

    Sin esta comprobación, la conversión no encontraría el archivo nuevo y volvería a
    geocodificar todo desde el principio, gastando cuota de la API.
    """
    nueva = ruta_coordenadas(AREA_METROPOLITANA)
    if RUTA_COORDENADAS_ANTIGUA.exists() and not nueva.exists():
        sys.exit(f"Error: Se encontró '{RUTA_COORDENADAS_ANTIGUA.as_posix()}', el nombre anterior del archivo "
                 f"de coordenadas. Renómbralo a '{nueva.as_posix()}' y vuelve a ejecutar "
                 "(no hace falta volver a geocodificar).")
