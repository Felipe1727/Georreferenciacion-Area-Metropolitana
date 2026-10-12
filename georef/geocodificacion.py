"""Consultas al proveedor de geocodificación (OpenCage) y lectura de su llave.

La lógica y los parámetros son los heredados de `main.py` (`n=300`, `n=400`, plantilla de
consulta y pausa de 1 s); el cambio `ubicacion-por-niveles` los rediseña.
"""
import os
import sys
import time
import unicodedata

import pandas as pd
from dotenv import dotenv_values
from opencage.geocoder import OpenCageGeocode

from georef.config import Columnas

# Punto que devuelve OpenCage cuando solo resuelve la consulta a nivel de la ciudad de Medellín.
CENTROIDE_MEDELLIN = (6.25184, -75.56359)

# Lista heredada de barrios de Medellín que usa la mejora de coordenadas. Es incompleta y no
# coincide con los nombres oficiales; la sustituye el GeoJSON en ubicacion-por-niveles.
BARRIOS_MEDELLIN = [
    "ALDEA PABLO VI",
    "ALEJANDRIA",
    "ALEJANDRO ECHEVARRIA",
    "ALFONSO LOPEZ",
    "ALTAMIRA",
    "ALTAVISTA",
    "POBLADO",
    "ANDALUCIA",
    "ANTONIO NARINO",
    "ARANJUEZ",
    "ASOMADERA N1",
    "ASOMADERA N2",
    "ASOMADERA N3",
    "ASTORGA",
    "AURES N1",
    "AURES N2",
    "BARRIO CAICEDO",
    "BARRIO COLOMBIA",
    "BARRIO CRISTOBAL",
    "BARRIOS DE JESUS",
    "BELEN",
    "BELLO HORIZONTE",
    "BICENTENARIO",
    "BOSTON",
    "BOSQUES DE SAN PABLO",
    "BOMBONA N1",
    "BOMBONA N2",
    "BRASILIA",
    "BOSQUE",
    "BOLIVARIANA",
    "CALASANZ",
    "CALLE NUEVA",
    "CAMPO ALEGRE",
    "CAMPO AMOR",
    "CAMPO VALDES",
    "CANTV",
    "CANTAR",
    "CASTILLA",
    "CASTROPOL",
    "CATALUÑA",
    "CASTILLA",
    "CAICEDO",
    "CATEDRAL",
    "CARIBE",
    "CARLOS E. RESTREPO",
    "CARLOS E RESTREPO",
    "CENTRAL GARC",
    "CERRO EL VOLADOR",
    "CERRO NUTIBARA",
    "CHARCO MORALES",
    "CIELO",
    "COLON",
    "COLONIA LIBRE",
    "COLONIAL",
    "COMUNA 1",
    "COMUNA 13",
    "COMUNA 4",
    "COMUNA 7",
    "CONDINA",
    "CONQUISTADORES",
    "CORAZON DE JESUS",
    "CORAZON DE JESUS – BARRIO TRISTE",
    "CÓRDOBA",
    "CORTEXTO",
    "CRISTO REY",
    "DARE",
    "DIEGO ECHEVARRIA",
    "DOS QUETAZALES",
    "EDUCACION",
    "ESPINAL",
    "ESTACION VILLA",
    "ESTANCIA DEL MAR",
    "ESTADIO",
    "EUFEMIA CRUZ",
    "EXPOSICION",
    "FONTIBON",
    "FERRINI",
    "FLORENCIA",
    "FLORIDA",
    "FLORIDA NUEVA",
    "FLORIDA VILLA",
    "FUSIBLES",
    "GENERAL MOTOBIEN",
    "GENERAL PERON",
    "GIRARDOT",
    "GRANADA",
    "GRANIZAL",
    "GRANIZAL",
    "GUAYABAL",
    "HABSAÑA",
    "HATILLO",
    "HORIZONTES",
    "HUNTER",
    "HUMBERTO",
    "JARDINES",
    "JUAN PABLO II",
    "JOSE JIMENEZ",
    "LA AVANZADA",
    "LA BARCALERA",
    "LA BATERIA",
    "LA CABAÑA",
    "LA CASCADA",
    "LA COLINA",
    "LA COMUNA 1",
    "LA COMUNA 2",
    "LA ESPERANZA",
    "LA FLORIDA",
    "LA FRONTERA",
    "LA GLORIA",
    "LA HONDONADA",
    "LA ISLA",
    "LOMA DE LOS BERNAL",
    "LA LOMA DE LOS ORIENTALES",
    "LA MERCED",
    "LA MOTA",
    "LA PALMA",
    "LA PARRANDA",
    "LA PILARICA",
    "LA PLAYA"
]


def obtener_llave():
    """
    Obtiene la llave API de OpenCage de la variable 'OPENCAGE_API_KEY'.

    La busca primero en el entorno del proceso y, si ahí no está o está vacía, en el archivo '.env' del
    directorio de trabajo, sin modificar el entorno. La llave nunca se guarda en archivos ni se solicita
    por consola. Si no se encuentra, el programa termina con un mensaje que explica cómo definirla.

    Returns:
        str: La llave API sin espacios al inicio ni al final.
    """
    llave = os.environ.get("OPENCAGE_API_KEY", "").strip()
    if not llave:
        llave = (dotenv_values(".env").get("OPENCAGE_API_KEY") or "").strip()
    if not llave:
        sys.exit(
            "Error: No se encontró la llave de OpenCage en la variable 'OPENCAGE_API_KEY'.\n"
            "Defínela en un archivo '.env' en la carpeta del proyecto:\n"
            "  cp .env.example .env    (luego escribe la llave en .env y ejecuta: chmod 600 .env)\n"
            "o como variable de entorno, por ejemplo:\n"
            "  export OPENCAGE_API_KEY=<tu-llave>"
        )
    return llave


def geocodificar_direcciones(df: pd.DataFrame, api_key: str, columnas: Columnas, n = 300) -> pd.DataFrame:
    """
    Realiza geocodificación directa (dirección -> coordenadas) sobre un número exacto de registros (n), partiendo desde:
    - El primer registro si no existen columnas 'Latitud' y 'Longitud'.
    - El primer registro donde 'Latitud' o 'Longitud' están vacíos, si ya existen.

    Se realiza una consulta por segundo (como exige la API de OpenCage).
    `columnas` indica los nombres de las columnas de dirección y ciudad.
    """
    geocoder = OpenCageGeocode(api_key)

    # Crear columnas si no existen
    if 'Latitud' not in df.columns:
        df['Latitud'] = None
    if 'Longitud' not in df.columns:
        df['Longitud'] = None

    # Encontrar primer índice donde falta alguna coordenada
    start_idx = None
    for idx in df.index:
        if pd.isna(df.at[idx, 'Latitud']) or pd.isna(df.at[idx, 'Longitud']):
            start_idx = idx
            break

    if start_idx is None:
        print("Todas las coordenadas ya están completas. No se necesita geocodificación.")
        return df

    # Geocodificar exactamente n registros desde start_idx
    processed = 0
    for idx in df.loc[start_idx:].index:
        if processed >= n:
            break

        direccion = f"{df.at[idx, columnas.direccion]}, {df.at[idx, columnas.ciudad].replace(' -',',')}, Antioquia, Colombia"

        try:
            resultados = geocoder.geocode(direccion, no_annotations=1, countrycode='co')
        except Exception as e:
            print(f"‼ Error al consultar idx={idx}: {e}")
            continue

        if resultados and len(resultados):
            df.at[idx, 'Longitud'] = resultados[0]['geometry']['lng']
            df.at[idx, 'Latitud']  = resultados[0]['geometry']['lat']
        else:
            df.at[idx, 'Longitud'] = geocoder.geocode(df.at[idx, columnas.ciudad].replace(' -',',')
                                                      , no_annotations=1, countrycode='co')[0]['geometry']['lng']
            df.at[idx, 'Latitud']  = geocoder.geocode(df.at[idx, columnas.ciudad].replace(' -',',')
                                                      , no_annotations=1, countrycode='co')[0]['geometry']['lat']

        processed += 1
        print(f"✓ Coordenadas asignadas en fila {idx}\nRegistros procesados: {processed}")
        time.sleep(1)

    # Reordenar columnas si existe 'Complemento'
    cols = df.columns.tolist()
    if 'Complemento' in cols:
        idx_comp = cols.index('Complemento')
        geo_cols = ['Latitud', 'Longitud']
        for col in geo_cols:
            if col in cols:
                cols.remove(col)
        cols = cols[:idx_comp+1] + geo_cols + cols[idx_comp+1:]
        df = df[cols]

    return df


def rellenar_por_barrio(df: pd.DataFrame,
                        api_key: str,
                        n = 400) -> pd.DataFrame:
    """
    Para registros con lat=6.25184 y lon=-75.56359 y Complemento conteniendo
    un barrio de BARRIOS_MEDELLIN, re-geocodifica usando Ciudad + Barrio.
    No hace más de n llamadas al API.

    Desde normalizacion-direcciones el barrio reconocido está en la columna 'Barrio' y no
    dentro de 'Complemento', así que se busca en ambas.
    """
    geocoder = OpenCageGeocode(api_key)
    llamadas = 0

    latitud = df['Latitud'].copy()
    longitud = df["Longitud"].copy()

    # Preprocesar lista de barrios: sin tildes y en mayúsculas
    def normaliza(texto: str) -> str:
        # Quita tildes
        s = unicodedata.normalize('NFD', texto)
        s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
        return s.upper()


    for idx, row in df.iterrows():
        if llamadas >= n:
            break

        lat = row.get('Latitud', None)
        lon = row.get('Longitud', None)
        complemento = row.get('Complemento', '')
        barrio = row.get('Barrio', None)
        if lat == CENTROIDE_MEDELLIN[0] and lon == CENTROIDE_MEDELLIN[1]:
            texto = str(complemento) if pd.isna(barrio) else f"{complemento} {barrio}"
            comp_norm = normaliza(texto)
            # ¿Algún barrio está contenido en el texto normalizado?
            barrio_encontrado = next((b for b in BARRIOS_MEDELLIN if b in comp_norm), None)
            if barrio_encontrado:
                # Construir dirección: ciudad + barrio
                direccion = f"{barrio_encontrado}, MEDELLIN"

                try:
                    resultados = geocoder.geocode(direccion, no_annotations=1, countrycode='co')
                except Exception as e:
                    print(f"‼ Error al geocodificar idx={idx}: {e}")
                    continue

                if resultados and len(resultados):
                    longitud.loc[idx] = resultados[0]['geometry']['lng']
                    latitud.loc[idx]  = resultados[0]['geometry']['lat']
                    print(f"✓ Re-geocodificado idx={idx} → {barrio_encontrado}")
                else:
                    print(f"– Sin resultados para idx={idx}, barrio={barrio_encontrado}")

                llamadas += 1
                time.sleep(1)  # pausa mínima entre llamadas

    df["Latitud"] = latitud
    df["Longitud"] = longitud
    if llamadas == 0:
        print("Los registros han sido optimizados")
    else:
        print(f"🗸 Total de llamadas realizadas: {llamadas}")
    return df
