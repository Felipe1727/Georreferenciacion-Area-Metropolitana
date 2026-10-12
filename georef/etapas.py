"""Una función por etapa del proceso.

Cada etapa lee sus entradas, llama a los módulos de dominio y escribe sus salidas con
las rutas de `georef.archivos`. Las usan por igual los subcomandos y el menú interactivo.
"""
import sys

import pandas as pd

from georef import archivos, direcciones, geocodificacion, mapas
from georef.config import AREA_METROPOLITANA, Configuracion
from georef.referencia import ErrorReferencia, IndiceLugares

MENSAJE_SIN_COORDENADAS = "Error: Necesitas primero procesar las coordenadas."


def estandarizar(configuracion: Configuracion):
    """
    Lee el archivo de `original/`, normaliza todas sus direcciones, las separa por área y escribe
    los cuatro archivos de `estandarizado/`. El barrio y la comuna solo se reconocen en el
    municipio con polígonos.
    """
    try:
        indice = IndiceLugares.desde_configuracion(configuracion.referencia)
    except ErrorReferencia as error:
        sys.exit(f"Error: {error}")
    df = archivos.leer_archivo_original()
    archivos.verificar_columnas(df, configuracion.columnas)

    normalizado, principal = direcciones.normalizar_direcciones(df, configuracion, indice)
    # am -> área metropolitana
    # nam -> no área metropolitana
    am, nam = direcciones.separar_por_area(normalizado, configuracion.area_metropolitana,
                                           configuracion.columnas.ciudad)
    es_principal = principal[am.index]
    am_vias_principales = am[es_principal]
    am_vias_especiales = am[~es_principal]

    am.to_excel(archivos.RUTA_TOTAL_AM)
    am_vias_principales.to_excel(archivos.RUTA_PRINCIPALES_AM)
    am_vias_especiales.to_excel(archivos.RUTA_ESPECIALES_AM)
    nam.to_excel(archivos.RUTA_FUERA_AM)


def geocodificar(configuracion: Configuracion):
    """Geocodifica los registros pendientes del área metropolitana (opción 2 del menú)."""
    archivos.verificar_nombre_antiguo_coordenadas()
    ruta_archivo = archivos.ruta_coordenadas(AREA_METROPOLITANA)
    llave = geocodificacion.obtener_llave()

    if ruta_archivo.exists():
        df = pd.read_excel(ruta_archivo, index_col=0)
    else:
        archivos.verificar_principales_am()
        df = pd.read_excel(archivos.RUTA_PRINCIPALES_AM, index_col=0)
    coordenadas = geocodificacion.geocodificar_direcciones(df.copy(), api_key=llave, columnas=configuracion.columnas)
    coordenadas.to_excel(ruta_archivo)


def mejorar(configuracion: Configuracion):
    """Vuelve a geocodificar por barrio los puntos en el centroide de Medellín (opción 3 del menú)."""
    archivos.verificar_nombre_antiguo_coordenadas()
    llave = geocodificacion.obtener_llave()
    ruta_archivo = archivos.ruta_coordenadas(AREA_METROPOLITANA)
    if ruta_archivo.exists():
        df = pd.read_excel(ruta_archivo, index_col=0)
    else:
        sys.exit(MENSAJE_SIN_COORDENADAS)

    coordenadas = geocodificacion.rellenar_por_barrio(api_key=llave, df=df.copy())
    coordenadas.to_excel(ruta_archivo)


def generar_mapas(configuracion: Configuracion):
    """Genera los mapas del área metropolitana en `mapas/area_metropolitana/` (opción 4 del menú)."""
    archivos.verificar_nombre_antiguo_coordenadas()
    ruta_archivo = archivos.ruta_coordenadas(AREA_METROPOLITANA)
    if not ruta_archivo.exists():
        sys.exit(MENSAJE_SIN_COORDENADAS)
    mapas.visualizar(pd.read_excel(ruta_archivo), archivos.carpeta_mapas(AREA_METROPOLITANA))


def extraer_subconjunto(configuracion: Configuracion, nombre: str):
    """
    Extrae un subconjunto del área metropolitana de las coordenadas ya obtenidas, sin consultar la API.

    Escribe `coordenadas/coordenadas_<nombre>.xlsx` (mismas columnas e índice que el archivo del área
    metropolitana) y sus mapas en `mapas/<nombre>/`.
    """
    if nombre not in configuracion.subconjuntos:
        disponibles = ", ".join(sorted(configuracion.subconjuntos)) or "ninguno"
        sys.exit(f"Error: El subconjunto '{nombre}' no está definido en la configuración. "
                 f"Subconjuntos disponibles: {disponibles}.")
    archivos.verificar_nombre_antiguo_coordenadas()
    ruta_area = archivos.ruta_coordenadas(AREA_METROPOLITANA)
    if not ruta_area.exists():
        sys.exit(MENSAJE_SIN_COORDENADAS)

    df = pd.read_excel(ruta_area, index_col=0)
    ciudad = configuracion.columnas.ciudad
    if ciudad not in df.columns:
        sys.exit(f"Error: '{ruta_area.as_posix()}' no tiene la columna '{ciudad}'. "
                 "Revisa la sección [columnas] de la configuración.")
    municipios = configuracion.subconjuntos[nombre]
    subconjunto = df[df[ciudad].isin(municipios)]
    if subconjunto.empty:
        sys.exit(f"Error: Ningún registro de '{ruta_area.as_posix()}' pertenece al subconjunto '{nombre}' "
                 f"({', '.join(municipios)}).")

    ruta_subconjunto = archivos.ruta_coordenadas(nombre)
    subconjunto.to_excel(ruta_subconjunto)
    mapas.visualizar(subconjunto.copy(), archivos.carpeta_mapas(nombre))
    print(f"Subconjunto '{nombre}': {len(subconjunto)} registros en '{ruta_subconjunto.as_posix()}' "
          f"y mapas en '{archivos.carpeta_mapas(nombre).as_posix()}/'.")
