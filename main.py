import pandas as pd, re, time, folium, os, shutil, tkinter as tk, sys, unicodedata
from opencage.geocoder import OpenCageGeocode
from folium.plugins import FastMarkerCluster
from pathlib import Path
from tkinter import filedialog



# Declaración de variables globales
tipo_vía_urbana = ['CL', 'CR', 'AV', 'CIR', 'DG', 'TV']
keywords = tipo_vía_urbana.copy() + ['BIS', 'KM']
equivalente = {
    'CALLE' : 'CL',
    'CARRERA' : 'CR',
    'CRR' : 'CR',
    'CRA' : 'CR',
    'CLL' : 'CL',
    'NÚMERO' : '#',
    'NUMERO' : '#',
    'NO' : '#',
    'DIAGONAL' : 'DG',
    'CIRCULAR' : 'CIR',
    'TRANSVERSAL' : 'TV',
    'AVENIDA' : 'AV',
    'NO.' : '#',
    'NORTE' : 'N',
    'SUR' : 'S',
    'ESTE' : 'E',
    'ORIENTE' : 'E',
    'OESTE' : 'O',
    'OCCIDENTE' : 'O'
}

área_metropolitana = [
    "MEDELLIN - ANTIOQUIA",
    "ITAGUI - ANTIOQUIA",
    "BELLO - ANTIOQUIA",
    "GIRARDOTA - ANTIOQUIA",
    "BARBOSA - ANTIOQUIA",
    "COPACABANA - ANTIOQUIA",
    "ENVIGADO - ANTIOQUIA",
    "SABANETA - ANTIOQUIA",
    "CALDAS - ANTIOQUIA",
    "LA ESTRELLA - ANTIOQUIA"
    ]

barrios_medellin = [
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




def main():
    """
    Función principal que maneja la interfaz de línea de comandos y coordina las funcionalidades disponibles:
    1. Lectura y estandarización de direcciones.
    2. Conversión de coordenadas usando reverse geocoding.
    3. Mejora de coordenadas basadas en barrios.
    4. Generación de mapas interactivos.
    """
    if len(sys.argv) == 2:
        if sys.argv[1] == "c":
            ruta_archivo = Path("llave") / "llave.txt"

            llave = ""

            with open(ruta_archivo, "r", encoding="utf-8") as archivo:
                primera_linea = archivo.readline().strip()  # strip() elimina espacios al principio y al final

            llave = primera_linea

            ruta_archivo = Path("coordenadas") / "coordenadas.xlsx"

            if os.path.exists(ruta_archivo):
                df = pd.read_excel(ruta_archivo)
            else:
                df = pd.read_excel(Path("estandarizado") / "principales_área_metropolitana.xlsx")
            am_vías_principales_coordenadas = reverse_geocoding(df.copy(), api_key=llave)
            am_vías_principales_coordenadas.to_excel(Path("coordenadas") / "coordenadas.xlsx")

            sys.exit()

    estructura_programa()
    verificar_y_copiar_archivo_original()
    # Lectura de la base de datos
    df = leer_archivo_original()
    seleccion = int(seleccionar_funcionalidad())
    match seleccion:
        case 1:
            # am -> área metropolitana
            # nam -> no área metropolitana
            a, b = filtrar_área_metropolitana(df)
            am = pd.DataFrame(a)
            nam = pd.DataFrame(b)
            # Acondicionamiento básico de ambos DF
            am.loc[:, "Direccion de residencia"] = reemplazar_equivalentes(am.loc[:, "Direccion de residencia"])
            nam.loc[:, "Direccion de residencia"] = reemplazar_equivalentes(nam.loc[:, "Direccion de residencia"])

            # Filtro de los tipos de vía principales en el DF am
            am_vías_principales, am_vías_especiales = filtrar_vías_principales(am.copy())

            # Estandarización direcciones
            am_vías_principales = estandarización(am_vías_principales)
    
            am.to_excel(Path("estandarizado") / "total_área_metropolitana.xlsx")
            am_vías_principales.to_excel(Path("estandarizado") / "principales_área_metropolitana.xlsx")
            am_vías_especiales.to_excel(Path("estandarizado") / "especiales_área_metropolitana.xlsx")
            nam.to_excel(Path("estandarizado") / "fuera_área_metropolitana.xlsx")

        case 2:
            ruta_archivo = Path("coordenadas") / "coordenadas.xlsx"
            llave = obtener_llave()

            if os.path.exists(ruta_archivo):
                df = pd.read_excel(ruta_archivo, index_col=0)
            else:
                df = pd.read_excel(Path("estandarizado") / "principales_área_metropolitana.xlsx", index_col=0)
            am_vías_principales_coordenadas = reverse_geocoding(df.copy(), api_key=llave)
            am_vías_principales_coordenadas.to_excel(Path("coordenadas") / "coordenadas.xlsx")

        case 3:
            llave = obtener_llave()
            ruta_archivo = Path("coordenadas") / "coordenadas.xlsx"
            if os.path.exists(ruta_archivo):
                df = pd.read_excel(ruta_archivo, index_col=0)
            else:
                sys.exit('Error: Necesitas primero procesar las coordenadas.')

            coordenadas = rellenar_por_barrio(api_key=llave,df=df.copy())
            coordenadas.to_excel(Path("coordenadas") / "coordenadas.xlsx")

        case 4:
            visualizar(pd.read_excel(Path('coordenadas') / 'coordenadas.xlsx'))


def seleccionar_funcionalidad():
    """
    Muestra un menú interactivo para que el usuario seleccione la funcionalidad deseada.

    Returns:
        str: Número de la opción seleccionada ('1'-'4').
    """
    opciones = {
        "1": "estandarización de direcciones",
        "2": "conversión de coordenadas",
        "3": "mejora de coordenadas (sólo si ya se realizó la conversión)",
        "4": "generación de mapas"
    }

    print("Selecciona una funcionalidad:")
    for clave, descripcion in opciones.items():
        print(f"{clave}. {descripcion.capitalize()}")

    while True:
        seleccion = input("Ingresa el número de la opción deseada (1-4): ").strip()
        if seleccion in opciones:
            print(f"Has seleccionado: {opciones[seleccion].capitalize()}")
            return seleccion
        else:
            print("Opción inválida. Por favor elige 1, 2, 3 o 4.")


def verificar_y_copiar_archivo_original():
    """
    Verifica si la carpeta 'original' está vacía y, de ser así, permite al usuario seleccionar un archivo via diálogo
    gráfico para copiarlo a dicha carpeta.
    """
    carpeta_original = Path("original")

    # Verifica si está vacía
    if not any(carpeta_original.iterdir()):
        print("La carpeta 'original' está vacía. Selecciona un archivo para copiar allí.")

        # Oculta la ventana principal de tkinter
        root = tk.Tk()
        root.withdraw()

        # Abre el diálogo para seleccionar archivo
        archivo_origen = filedialog.askopenfilename(title="Selecciona un archivo para copiar a 'original'")

        if archivo_origen:
            # Copia el archivo a la carpeta 'original'
            archivo_destino = carpeta_original / Path(archivo_origen).name
            shutil.copy(archivo_origen, archivo_destino)
            print(f"Archivo copiado a: {archivo_destino}")
        else:
            print("No se seleccionó ningún archivo.")

def estructura_programa():
    """
    Crea la estructura de directorios requerida por el programa si no existen.
    """
    rutas = [
        Path("original"),
        Path("estandarizado"),
        Path("coordenadas"),
        Path("mapas") / "filtrados",
        Path("llave") / "llave.txt"
    ]

    for ruta in rutas:
        # Si es un archivo (tiene sufijo como .txt), crea su carpeta padre
        if ruta.suffix:
            ruta.parent.mkdir(parents=True, exist_ok=True)
        else:
            ruta.mkdir(parents=True, exist_ok=True)

def leer_archivo_original() -> pd.DataFrame:
    """
    Lee el único archivo presente en la carpeta 'original' y lo carga en un DataFrame.

    Returns:
        pd.DataFrame: Datos cargados desde el archivo Excel.
    """
    carpeta = Path("original")
    archivos = list(carpeta.glob("*"))

    # Filtrar solo archivos (ignora subdirectorios)
    archivos = [f for f in archivos if f.is_file()]

    if len(archivos) > 1:
        print("Error: Hay más de un archivo en la carpeta 'original'. Asegúrate de que solo haya uno.")
        sys.exit(1)

    archivo = archivos[0]

    # Leer el archivo Excel y devolver el DataFrame
    df = pd.read_excel(archivo)
    return df

def obtener_llave():
    """
    Obtiene la llave API almacenada en 'llave/llave.txt', permite al usuario decidir usarla o ingresar una nueva,
    y opcionalmente guarda la nueva llave para futuras ejecuciones.

    Returns:
        str: La llave API seleccionada o ingresada.
    """

    # Ruta del archivo
    ruta_archivo = Path("llave") / "llave.txt"

    # Asegura que el directorio existe
    os.makedirs(os.path.dirname(ruta_archivo), exist_ok=True)

    llave = ""


    # Paso 1: Verificar si el archivo existe y leer la primera línea
    if os.path.exists(ruta_archivo):
        with open(ruta_archivo, "r", encoding="utf-8") as archivo:
            primera_linea = archivo.readline().strip()  # strip() elimina espacios al principio y al final

        if primera_linea:
            previa = input("Se encontró una llave en el sistema de una ejecución previa, ¿Desea usarla? (s/n): ").strip().lower()
            if previa == "s":
                llave = primera_linea
            else:
                llave = input("Ingresa una llave: ").strip()
                guardar = input("¿Deseas guardar esta llave para la próxima ejecución? (s/n): ").strip().lower()
                if guardar == "s":
                    with open(ruta_archivo, "w", encoding="utf-8") as archivo:
                        archivo.write(llave + "\n")
        else:
            # No hay contenido válido en la primera línea
            llave = input("No se encontró una llave válida. Ingresa una llave: ").strip()
            guardar = input("¿Deseas guardar esta llave para la próxima ejecución? (s/n): ").strip().lower()
            if guardar == "s":
                with open(ruta_archivo, "w", encoding="utf-8") as archivo:
                    archivo.write(llave + "\n")
    else:
        # El archivo no existe
        llave = input("No se encontró el archivo de llave. Ingresa una llave: ").strip()
        guardar = input("¿Deseas guardar esta llave para la próxima ejecución? (s/n): ").strip().lower()
        if guardar == "s":
            with open(ruta_archivo, "w", encoding="utf-8") as archivo:
                archivo.write(llave + "\n")

    # Mostrar la llave obtenida
    return llave


def filtrar_área_metropolitana(df : pd.DataFrame) -> pd.DataFrame:
    """
    Separa el DataFrame en dos listas:
    - Registros cuya 'Ciudad Residencia' pertenece al área metropolitana.
    - Registros fuera de dicha área.

    Args:
        df (pd.DataFrame): DataFrame original con columna 'Ciudad Residencia'.

    Returns:
        list: [DataFrame_area_metropolitana, DataFrame_fuera_area]
    """
    a = df.loc[df["Ciudad Residencia"].isin(área_metropolitana)]
    return [a, df[~df["Ciudad Residencia"].isin(a["Ciudad Residencia"])]]
    

def reemplazar_equivalentes(s : pd.Series) -> pd.Series:
    """
    Reemplaza en una Serie de direcciones las palabras clave por sus equivalentes abreviados.

    Args:
        s (pd.Series): Serie de strings con direcciones.

    Returns:
        pd.Series: Serie con direcciones normalizadas en mayúsculas y abreviadas.
    """
    s = s.apply(str.upper)
    for i in equivalente:
        s = s.str.replace(i, equivalente[i])
    return s 


def filtrar_vías_principales(df : pd.DataFrame):
    """
    Filtra el DataFrame para separar las direcciones que comienzan con un tipo de vía principal.

    Args:
        df (pd.DataFrame): DataFrame con columna 'Direccion de residencia'.

    Returns:
        list: [DataFrame_principales, DataFrame_especiales]
    """
    s = identificar_vías_principales(pd.Series(df.loc[:, "Direccion de residencia"].copy()))
    s.dropna(inplace=True)

    index_drop = list((set(df.index.copy()) - set(s.index.copy())))
    new_df = df.drop(index_drop, inplace=False)

    return [new_df, df[~df["Direccion de residencia"].isin(new_df["Direccion de residencia"])]]


def identificar_vías_principales(s : pd.Series) -> pd.Series:
    """
    Identifica si cada dirección en la Serie comienza con un tipo de vía definido en 'tipo_vía_urbana'.

    Args:
        s (pd.Series): Serie de strings con direcciones.

    Returns:
        pd.Series: Serie con el código de vía o None si no coincide.
    """
    s = s.copy()
    for i in s.index:
        for vía in tipo_vía_urbana:
            if str(s.loc[i]).startswith(vía):
                s.loc[i] = vía
                break
        if s.loc[i] not in tipo_vía_urbana:
            s.loc[i] = None

    #Esta función retorna una serie que tiene el tipo de vía de una dirección o un valor nulo en 
    # caso de que no cumpla esta condición 
    return s

def estandarización(df : pd.DataFrame):
    """
    Aplica procesamiento de estandarización de direcciones y añade la columna 'Complemento'.

    Args:
        df (pd.DataFrame): DataFrame con columna 'Direccion de residencia'.

    Returns:
        pd.DataFrame: DataFrame estandarizado con nueva columna 'Complemento'.
    """
    añadir_columna_complemento(df)
    df.loc[:, "Direccion de residencia"] = df.loc[:, "Direccion de residencia"].apply(format_dir)
    
    # Reordenar columnas: mover "Complemento" al lado de "Direccion de residencia"
    columnas = df.columns.tolist()
    if "Complemento" in columnas and "Direccion de residencia" in columnas:
        columnas.remove("Complemento")
        idx = columnas.index("Direccion de residencia") + 1
        columnas.insert(idx, "Complemento")
        df = df[columnas]
    return df

def añadir_columna_complemento(df : pd.DataFrame):
    """
    Separa la dirección en base al complemento y añade la columna 'Complemento' al DataFrame.

    Args:
        df (pd.DataFrame): DataFrame con columna 'Direccion de residencia'.
    """
    partes = df["Direccion de residencia"].astype("string").map(dividir_complemento, na_action="ignore")
    df["Direccion de residencia"] = partes.str[0].astype("string")
    df["Complemento"] = partes.str[1].astype("string")


def dividir_complemento(s : str):
    """
    Divide una dirección en parte principal y complemento basado en palabras clave.

    Args:
        s (str): Dirección completa.

    Returns:
        list: [parte_principal, complemento]. Si no se encuentra un
            complemento, este será una cadena vacía.
    """
    delay = 0
    try:
        for i in range(len(s)):
            if delay == 0:
                if ((s[i]+s[i + 1]) in keywords and not s[i + 2].isalpha()):
                    delay = 2
                elif (s[i]+s[i + 1]+s[i + 2]) in keywords and not s[i + 3].isalpha():
                    delay = 3
                else:
                    if s[i].isalpha() and s[i + 1].isalpha():
                        if s[i] != s[i + 1]:
                            new_str = s.split(s[i] + s[i + 1], 1)
                            new_str[1] = (s[i] + s[i + 1] + new_str[1]).strip()
                            new_str[0] = new_str[0].strip()
                            return new_str
            else:
                delay -= 1
    except IndexError:
        return [s, '']

    return [s, '']
    
def format_dir(s):
    """
    Formatea una dirección separando componentes de vía, números y complementos.

    Args:
        s (str): Dirección sin formato.

    Returns:
        str: Dirección formateada.
    """
    matches = re.findall(r'([A-ZÑ]+|\d+)', s)

    temp = ''
    part = 0
    num_aldready = False
    letter_aldready = False
    via_aldready = False

    for match in matches:
        if match in tipo_vía_urbana:
            if not via_aldready:
                temp = temp + f'{match} '
                via_aldready = True
        elif match in keywords:
            temp = temp + f'{match} ' if temp.endswith(' ') or temp == '' else temp + f' {match} '
        elif match.isnumeric():
            if num_aldready:
                part += 1
                match part:
                    case 1:
                        temp = temp = temp + '#' if temp.endswith(' ') else temp + ' #'
                    case 2:
                        temp = temp = temp + '-'
                num_aldready = False
                letter_aldready = False
            temp = temp + f'{match}'
            num_aldready = True
        else:
            temp = temp + f'{match}' if not letter_aldready else temp + f' {match}'
            letter_aldready = True
    
    return temp



def reverse_geocoding(df: pd.DataFrame, api_key: str, n = 300) -> pd.DataFrame:
    """
    Realiza reverse geocoding sobre un número exacto de registros (n), partiendo desde:
    - El primer registro si no existen columnas 'Latitud' y 'Longitud'.
    - El primer registro donde 'Latitud' o 'Longitud' están vacíos, si ya existen.

    Se realiza una consulta por segundo (como exige la API de OpenCage).
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

        direccion = f"{df.at[idx,'Direccion de residencia']}, {df.at[idx,'Ciudad Residencia'].replace(' -',',')}, Antioquia, Colombia"

        try:
            resultados = geocoder.geocode(direccion, no_annotations=1, countrycode='co')
        except Exception as e:
            print(f"‼ Error al consultar idx={idx}: {e}")
            continue

        if resultados and len(resultados):
            df.at[idx, 'Longitud'] = resultados[0]['geometry']['lng']
            df.at[idx, 'Latitud']  = resultados[0]['geometry']['lat']
        else:
            df.at[idx, 'Longitud'] = geocoder.geocode(df.at[idx,'Ciudad Residencia'].replace(' -',',')
                                                      , no_annotations=1, countrycode='co')[0]['geometry']['lng']
            df.at[idx, 'Latitud']  = geocoder.geocode(df.at[idx,'Ciudad Residencia'].replace(' -',',')
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


def visualizar(df : pd.DataFrame):
    """
    Genera y guarda mapas HTML con marcadores y clusters basados en coordenadas del DataFrame.

    Args:
        df (pd.DataFrame): DataFrame con columnas 'Latitud' y 'Longitud'.
    """
    df.dropna(subset=['Latitud', 'Longitud'], inplace=True)
    latitudes = [a['Latitud'] for a in df.to_dict('records')]
    longitudes = [a['Longitud'] for a in df.to_dict('records')]
    data = list(zip(latitudes, longitudes))

    map = folium.Map(location=[6.2464186, -75.5942503], zoom_start=12)
    for a in df.index:
        coordenada = (df['Latitud'][a], df['Longitud'][a])
        folium.Marker(coordenada).add_to(map)

    map2 = folium.Map(location=[6.2464186, -75.5942503], zoom_start=12)

    FastMarkerCluster(data=data).add_to(map2)

    map.save(Path('mapas') / 'individual.html')
    map2.save(Path('mapas') / 'clusters.html')

    df_filtrado = df[
        ~((df["Latitud"] == 6.25184) & (df["Longitud"] == -75.56359))
    ]
    latitudes = [a['Latitud'] for a in df_filtrado.to_dict('records')]
    longitudes = [a['Longitud'] for a in df_filtrado.to_dict('records')]
    data = list(zip(latitudes, longitudes))

    map = folium.Map(location=[6.2464186, -75.5942503], zoom_start=12)
    for a in df_filtrado.index:
        coordenada = (df_filtrado['Latitud'][a], df_filtrado['Longitud'][a])
        folium.Marker(coordenada).add_to(map)

    map2 = folium.Map(location=[6.2464186, -75.5942503], zoom_start=12)

    FastMarkerCluster(data=data).add_to(map2)

    map.save(Path('mapas') / "filtrados" / 'individual_filtrados.html')
    map2.save(Path('mapas') / "filtrados" / 'clusters_filtrados.html')


def rellenar_por_barrio(df: pd.DataFrame,
                        api_key: str,
                        n = 400) -> pd.DataFrame:
    """
    Para registros con lat=6.25184 y lon=-75.56359 y Complemento conteniendo
    un barrio de barrios_medellin, re-geocodifica usando Ciudad + Barrio.
    No hace más de n llamadas al API.
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
        if lat == 6.25184 and lon == -75.56359:
            comp_norm = normaliza(str(complemento))
            # ¿Algún barrio está contenido en el texto normalizado?
            barrio_encontrado = next((b for b in barrios_medellin if b in comp_norm), None)
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
    

if __name__ == "__main__":
    main()