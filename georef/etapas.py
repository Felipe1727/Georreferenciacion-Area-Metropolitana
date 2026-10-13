"""Una función por etapa del proceso.

Cada etapa lee sus entradas, llama a los módulos de dominio y escribe sus salidas con
las rutas de `georef.archivos`. Las usan por igual los subcomandos y el menú interactivo.
"""
import datetime
import random
import sys
import tomllib

import pandas as pd

from georef import archivos, direcciones, geocodificacion, mapas, ubicacion
from georef.config import (AREA_METROPOLITANA, FORMATOS_CONSULTA, Configuracion, ErrorConfiguracion,
                           cargar_configuracion)
from georef.geografia import Poligonos
from georef.referencia import ErrorReferencia, IndiceLugares

MENSAJE_SIN_COORDENADAS = "Error: Necesitas primero procesar las coordenadas."
MENSAJE_SIN_NIVEL = ("Error: El archivo de coordenadas no tiene la columna 'Nivel ubicacion' (es de una versión "
                     "anterior). Ejecuta primero la ubicación: python -m georef ubicar")


class Avance:
    """
    Línea de avance de las consultas, en la salida de errores, solo con cifras agregadas.

    En una terminal se reescribe en el mismo sitio en cada paso. Si la salida va a un archivo o a
    otro programa, se escribe una línea cada `cada` pasos y en el último.
    """

    def __init__(self, sesion, unidad: str, cada: int = 100):
        self._sesion = sesion
        self._unidad = unidad
        self._cada = cada
        self._en_terminal = sys.stderr.isatty()
        self._escrita = False

    def __call__(self, actual: int, total: int):
        sesion = self._sesion
        texto = (f"{self._unidad} {actual} de {total} · peticiones a OpenCage: {sesion.peticiones} · "
                 f"desde la caché: {sesion.desde_cache} · pendientes: {len(sesion.pendientes)}")
        if self._en_terminal:
            print(f"\r{texto}", end="", file=sys.stderr, flush=True)
            self._escrita = True
        elif actual % self._cada == 0 or actual == total:
            print(texto, file=sys.stderr, flush=True)

    def terminar(self):
        """Pasa a la línea siguiente para que lo que se imprima después no se mezcle con el avance."""
        if self._escrita:
            print(file=sys.stderr, flush=True)
            self._escrita = False


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


def ubicar(configuracion: Configuracion, sin_consultas: bool = False):
    """
    Ubica a cada registro del área metropolitana por niveles (opción 2 del menú).

    Lee los principales y los especiales de `estandarizado/` y escribe de nuevo, por completo,
    `coordenadas/coordenadas_area_metropolitana.xlsx`. Lo ya consultado sale de la caché. Todas
    las comprobaciones se hacen antes de la primera petición. Con `sin_consultas` no se hace
    ninguna petición ni se pide la llave: lo que no está en la caché queda pendiente.
    """
    archivos.verificar_nombre_antiguo_coordenadas()
    for ruta in (archivos.RUTA_PRINCIPALES_AM, archivos.RUTA_ESPECIALES_AM):
        if not ruta.exists():
            sys.exit(f"Error: No se encontró '{ruta.as_posix()}'. "
                     "Ejecuta primero la estandarización de direcciones (opción 1).")
    ruta_coordenadas = archivos.ruta_coordenadas(AREA_METROPOLITANA)
    conservar_anterior = _formato_anterior(ruta_coordenadas)
    faltan = [m for m in configuracion.area_metropolitana if m not in configuracion.puntos_municipios]
    if faltan:
        sys.exit("Error: Faltan los puntos de estos municipios en la sección [puntos_municipios] de la "
                 f"configuración: {', '.join(faltan)}.\n"
                 "Ejecuta 'python -m georef consultar-municipios' o escríbelos a mano.")
    llave = None if sin_consultas else geocodificacion.obtener_llave()
    try:
        poligonos = Poligonos.cargar(configuracion.referencia.geojson)
    except ErrorReferencia as error:
        sys.exit(f"Error: {error}")

    tipos = {"Codigo barrio": str}
    principales = pd.read_excel(archivos.RUTA_PRINCIPALES_AM, index_col=0, dtype=tipos)
    especiales = pd.read_excel(archivos.RUTA_ESPECIALES_AM, index_col=0, dtype=tipos)
    df = pd.concat([principales, especiales]).sort_index()
    principal = pd.Series(df.index.isin(principales.index), index=df.index)

    sesion = geocodificacion.SesionConsultas(llave, configuracion.ubicacion, archivos.RUTA_CACHE_CONSULTAS,
                                             archivos.RUTA_REGISTRO_CONSULTAS, "ubicar")
    avance = Avance(sesion, "Registro")
    try:
        resultado = ubicacion.ubicar_registros(df, principal, configuracion, poligonos, sesion, avance)
    finally:
        avance.terminar()

    if conservar_anterior:
        ruta_coordenadas.rename(archivos.RUTA_COORDENADAS_ANTERIOR)
        print(f"El archivo de coordenadas anterior se conservó como "
              f"'{archivos.RUTA_COORDENADAS_ANTERIOR.as_posix()}'.")
    resultado.to_excel(ruta_coordenadas)
    print(ubicacion.resumen(resultado, sesion))
    print(f"Coordenadas escritas en '{ruta_coordenadas.as_posix()}'.")


def _formato_anterior(ruta_coordenadas) -> bool:
    """
    Indica si el archivo de coordenadas existente tiene el formato anterior (sin 'Nivel ubicacion')
    y hay que conservarlo. Termina el programa si el nombre donde se conservaría ya está ocupado.
    """
    if not ruta_coordenadas.exists():
        return False
    columnas = pd.read_excel(ruta_coordenadas, index_col=0, nrows=0).columns
    if "Nivel ubicacion" in columnas:
        return False
    anterior = archivos.RUTA_COORDENADAS_ANTERIOR
    if anterior.exists():
        sys.exit(f"Error: '{ruta_coordenadas.as_posix()}' tiene el formato anterior (sin 'Nivel ubicacion') y no "
                 f"se puede conservar porque ya existe '{anterior.as_posix()}'. Mueve o renombra uno de los dos "
                 "y vuelve a ejecutar.")
    return True


def consultar_municipios(configuracion: Configuracion):
    """
    Consulta una vez a OpenCage el punto de los municipios del área sin punto en la configuración.

    Muestra cada resultado para revisarlo. Si la configuración no tiene `[puntos_municipios]`, la
    añade al final del archivo, sin tocar el resto. Si ya la tiene, no modifica el archivo y
    muestra las líneas que hay que copiar.
    """
    faltan = [m for m in configuracion.area_metropolitana if m not in configuracion.puntos_municipios]
    if not faltan:
        print("Todos los municipios del área metropolitana ya tienen punto en [puntos_municipios]. "
              "No se hizo ninguna petición.")
        return
    ruta = configuracion.ruta
    texto_original = ruta.read_text(encoding="utf-8")
    seccion_existente = "puntos_municipios" in tomllib.loads(texto_original)
    llave = geocodificacion.obtener_llave()
    sesion = geocodificacion.SesionConsultas(llave, configuracion.ubicacion, None,
                                             archivos.RUTA_REGISTRO_CONSULTAS, "municipios")
    fecha = datetime.date.today().isoformat()

    lineas, sin_punto = [], []
    for municipio in faltan:
        respuesta = sesion.resolver(geocodificacion.consulta_municipio(municipio), registro=municipio)
        if respuesta.estado != geocodificacion.RESULTADO:
            sin_punto.append(municipio)
            motivo = "sin resultado" if respuesta.estado == geocodificacion.SIN_RESULTADO else "no se pudo consultar"
            print(f"- {municipio}: {motivo}.")
            continue
        print(f"- {municipio}: latitud {respuesta.latitud}, longitud {respuesta.longitud} "
              f"(tipo {respuesta.tipo}, confidence {respuesta.confianza}): {respuesta.texto}")
        lineas.append(f'"{municipio}" = {{ latitud = {respuesta.latitud!r}, longitud = {respuesta.longitud!r}, '
                      f'fuente = "OpenCage", fecha = "{fecha}" }}')
    print(f"Peticiones a OpenCage: {sesion.peticiones}.")
    if sin_punto:
        print("Añade a mano en [puntos_municipios] el punto de: " + ", ".join(sin_punto) + ".")
    if not lineas:
        return

    if seccion_existente:
        print("La configuración ya tiene la sección [puntos_municipios], así que no se modificó. "
              "Copia en ella estas líneas:\n" + "\n".join(lineas))
        return
    bloque = ("\n# Puntos del nivel MUNICIPIO de la ubicación. Generados con 'python -m georef consultar-municipios'\n"
              f"# el {fecha} (fuente: OpenCage; consulta \"<MUNICIPIO>, <DEPARTAMENTO>, Colombia\").\n"
              "# Revísalos y corrígelos a mano si alguno no es el municipio correcto.\n"
              "[puntos_municipios]\n" + "\n".join(lineas) + "\n")
    separador = "" if texto_original.endswith("\n") else "\n"
    ruta.write_text(texto_original + separador + bloque, encoding="utf-8")
    try:
        cargar_configuracion(ruta)
    except ErrorConfiguracion as error:
        ruta.write_text(texto_original, encoding="utf-8")
        sys.exit("Error: Los puntos obtenidos no son válidos y no se guardaron (el archivo de configuración "
                 f"quedó como estaba).\n{error.mensaje()}")
    print(f"Puntos añadidos al final de '{ruta.as_posix()}'. Revísalos antes de ejecutar 'ubicar'.")


def comparar_consultas(configuracion: Configuracion, muestra: int):
    """
    Compara los dos formatos de consulta a OpenCage sobre una muestra de direcciones de Medellín.

    La muestra (hasta `muestra` direcciones distintas de vía principal con barrio declarado con
    código) es siempre la misma para el mismo archivo. Cada dirección se consulta en los dos
    formatos, alternándolos, con la misma pausa, caché, límite y paradas que la ubicación. Solo
    muestra cifras agregadas y no escribe el archivo de coordenadas.
    """
    archivos.verificar_principales_am()
    llave = geocodificacion.obtener_llave()
    try:
        poligonos = Poligonos.cargar(configuracion.referencia.geojson)
    except ErrorReferencia as error:
        sys.exit(f"Error: {error}")

    columnas = configuracion.columnas
    principales = pd.read_excel(archivos.RUTA_PRINCIPALES_AM, index_col=0, dtype={"Codigo barrio": str})
    candidatos = principales[
        (principales[columnas.ciudad] == configuracion.referencia.municipio_con_poligonos)
        & principales["Codigo barrio"].isin(poligonos.codigos)
        & principales[columnas.direccion].notna()
    ].drop_duplicates(columnas.direccion).sort_values(columnas.direccion)
    elegidos = candidatos.iloc[sorted(random.Random(0).sample(range(len(candidatos)),
                                                              min(muestra, len(candidatos))))]
    if elegidos.empty:
        sys.exit("Error: No hay direcciones de vía principal con barrio declarado para comparar.")

    parametros = configuracion.ubicacion
    sesion = geocodificacion.SesionConsultas(llave, parametros, archivos.RUTA_CACHE_CONSULTAS,
                                             archivos.RUTA_REGISTRO_CONSULTAS, "comparar")
    bounds = poligonos.recuadro()
    respuestas = {formato: [] for formato in FORMATOS_CONSULTA}
    avance = Avance(sesion, "Dirección", cada=10)
    try:
        for numero, (indice, registro) in enumerate(elegidos.iterrows(), start=1):
            avance(numero, len(elegidos))
            for formato in FORMATOS_CONSULTA:
                consulta = geocodificacion.consulta_direccion(registro[columnas.direccion],
                                                              registro[columnas.ciudad], formato,
                                                              parametros.nombres_via)
                respuesta = sesion.resolver(consulta, bounds=bounds, registro=indice)
                respuestas[formato].append((respuesta, registro["Codigo barrio"]))
    finally:
        avance.terminar()

    print(f"Muestra: {len(elegidos)} direcciones distintas de Medellín con barrio declarado "
          f"(de {len(candidatos)} disponibles).")
    for formato in FORMATOS_CONSULTA:
        print(f"Formato '{formato}':")
        print(ubicacion.cifras_comparacion(respuestas[formato], poligonos, parametros))
    print(f"Peticiones a OpenCage: {sesion.peticiones}; consultas resueltas desde la caché: {sesion.desde_cache}.")
    if sesion.restantes is not None:
        print(f"Peticiones restantes hoy según OpenCage: {sesion.restantes}")
    if sesion.parada:
        print(f"Se dejó de consultar por: {ubicacion.MOTIVOS_PARADA.get(sesion.parada, sesion.parada)}. "
              "Vuelve a ejecutar el comando para completar la muestra.")
    print(f"Formato configurado ahora: '{parametros.formato_consulta}' (sección [ubicacion]).")


def generar_mapas(configuracion: Configuracion):
    """Genera los mapas del área metropolitana en `mapas/area_metropolitana/` (opción 3 del menú)."""
    archivos.verificar_nombre_antiguo_coordenadas()
    ruta_archivo = archivos.ruta_coordenadas(AREA_METROPOLITANA)
    if not ruta_archivo.exists():
        sys.exit(MENSAJE_SIN_COORDENADAS)
    df = pd.read_excel(ruta_archivo, index_col=0)
    if "Nivel ubicacion" not in df.columns:
        sys.exit(MENSAJE_SIN_NIVEL)
    mapas.visualizar(df, archivos.carpeta_mapas(AREA_METROPOLITANA))


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
    if "Nivel ubicacion" not in df.columns:
        sys.exit(MENSAJE_SIN_NIVEL)
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
