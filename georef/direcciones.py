"""Separación por área y normalización de direcciones.

Funciones puras sobre Series y DataFrames: no leen ni escriben archivos. El
vocabulario y los nombres de columna llegan como parámetros desde la configuración.

La normalización divide el texto de cada dirección en vía y numeración, complemento,
barrio, código de barrio, comuna y zona (especificación `normalizacion-direcciones`).
Separa primero la zona y el lugar (barrio o comuna), aplica las equivalencias solo a
palabras completas del resto y conserva el separador y el formato heredados
(`dividir_complemento` y `format_dir`).
"""
import functools
import re

import pandas as pd

from georef.config import Configuracion, VocabularioDirecciones
from georef.referencia import IndiceLugares, normalizar

SEPARADOR_ZONA = "-*-"
ZONAS = ("URBANO", "RURAL")

# Columnas que la normalización escribe a continuación de la columna de dirección.
COLUMNAS_NORMALIZADAS = ["Complemento", "Barrio", "Codigo barrio", "Comuna", "Zona"]


def separar_por_area(df: pd.DataFrame, municipios, columna: str) -> list:
    """
    Separa el DataFrame en dos:
    - Registros cuya ciudad (`columna`) está en `municipios`.
    - Registros fuera de dicha área, incluidos los que no tienen ciudad.

    Args:
        df (pd.DataFrame): DataFrame original.
        municipios: Municipios del área, escritos como en la columna de ciudad.
        columna (str): Nombre de la columna de ciudad.

    Returns:
        list: [DataFrame_area, DataFrame_fuera_area]
    """
    a = df.loc[df[columna].isin(municipios)]
    return [a, df[~df[columna].isin(a[columna])]]


def reemplazar_equivalentes(s: pd.Series, equivalencias) -> pd.Series:
    """
    Pasa a mayúsculas una Serie de textos y reemplaza las palabras completas por sus abreviaturas.

    Una palabra solo se reemplaza si coincide entera con una equivalencia (`NORTE` -> `N`), nunca
    dentro de otra palabra (`URBANO` no cambia). El orden de las equivalencias no importa.

    Args:
        s (pd.Series): Serie de strings con direcciones.
        equivalencias: Pares (palabra, abreviatura).

    Returns:
        pd.Series: Serie en mayúsculas con las palabras abreviadas.
    """
    tabla = dict(equivalencias)
    return s.apply(lambda texto: " ".join(abreviar(_texto(texto).upper().split(), tabla)))


# Letras que forman una palabra: dígitos, signos y espacios la delimitan (CALLE31A, SUR-15, CLL.39).
LETRAS = "A-ZÁÉÍÓÚÜÑ"


def abreviar(palabras, tabla) -> list:
    """
    Reemplaza en cada elemento de `palabras` las palabras completas que tienen equivalencia.

    Una palabra es una secuencia de letras: `CALLE31A` -> `CL31A` y `SUR-15` -> `S-15`, pero
    `URBANO` o `SURAMERICA` no cambian. Las equivalencias más largas se aplican primero, así que el
    orden de la configuración no importa. Nunca se añaden ni se quitan espacios, de modo que se
    conserva el número de elementos.
    """
    patron = _patron_equivalencias(tuple(sorted(tabla, key=len, reverse=True)))
    return [patron.sub(lambda m: tabla[m.group(0)], palabra) for palabra in palabras] if tabla else list(palabras)


@functools.lru_cache(maxsize=8)
def _patron_equivalencias(claves):
    alternativas = "|".join(re.escape(clave) for clave in claves)
    return re.compile(f"(?<![{LETRAS}])(?:{alternativas})(?![{LETRAS}])")


def _texto(valor) -> str:
    """El valor como texto, o vacío si falta."""
    return "" if valor is None or (isinstance(valor, float) and pd.isna(valor)) else str(valor)


def identificar_vias_principales(s: pd.Series, tipos_via) -> pd.Series:
    """
    Identifica si cada dirección en la Serie comienza con uno de los tipos de vía.

    Args:
        s (pd.Series): Serie de strings con direcciones.
        tipos_via: Tipos de vía principales.

    Returns:
        pd.Series: Serie con el código de vía o None si no coincide.
    """
    s = s.copy()
    for i in s.index:
        for via in tipos_via:
            if str(s.loc[i]).startswith(via):
                s.loc[i] = via
                break
        if s.loc[i] not in tipos_via:
            s.loc[i] = None

    # Esta función retorna una serie que tiene el tipo de vía de una dirección o un valor nulo en
    # caso de que no cumpla esta condición
    return s


def dividir_complemento(s: str, palabras_clave):
    """
    Divide una dirección en parte principal y complemento basado en palabras clave.

    Args:
        s (str): Dirección completa.
        palabras_clave: Tipos de vía y palabras clave que forman parte de la dirección.

    Returns:
        list: [parte_principal, complemento]. Si no se encuentra un
            complemento, este será una cadena vacía.
    """
    delay = 0
    try:
        for i in range(len(s)):
            if delay == 0:
                if ((s[i]+s[i + 1]) in palabras_clave and not s[i + 2].isalpha()):
                    delay = 2
                elif (s[i]+s[i + 1]+s[i + 2]) in palabras_clave and not s[i + 3].isalpha():
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


def format_dir(s, vocabulario: VocabularioDirecciones):
    """
    Formatea una dirección separando componentes de vía, números y complementos.

    Args:
        s (str): Dirección sin formato.
        vocabulario (VocabularioDirecciones): Tipos de vía y palabras clave.

    Returns:
        str: Dirección formateada.
    """
    tipos_via = vocabulario.tipos_via
    palabras_clave = vocabulario.palabras_clave_completas
    matches = re.findall(r'([A-ZÑ]+|\d+)', s)

    temp = ''
    part = 0
    num_already = False
    letter_already = False
    via_already = False

    for match in matches:
        if match in tipos_via:
            if not via_already:
                temp = temp + f'{match} '
                via_already = True
        elif match in palabras_clave:
            temp = temp + f'{match} ' if temp.endswith(' ') or temp == '' else temp + f' {match} '
        elif match.isnumeric():
            if num_already:
                part += 1
                match part:
                    case 1:
                        temp = temp = temp + '#' if temp.endswith(' ') else temp + ' #'
                    case 2:
                        temp = temp = temp + '-'
                num_already = False
                letter_already = False
            temp = temp + f'{match}'
            num_already = True
        else:
            temp = temp + f'{match}' if not letter_already else temp + f' {match}'
            letter_already = True

    return temp


def normalizar_direccion(texto, vocabulario: VocabularioDirecciones, indice: IndiceLugares | None = None) -> dict:
    """
    Divide el texto de una dirección en sus partes normalizadas.

    Pasos: (1) la zona sale de lo que sigue a `-*-`; (2) si hay `indice`, se reconoce al final el
    barrio o la comuna; (3) al resto se le aplican las equivalencias palabra a palabra; (4)
    `dividir_complemento` separa la vía del complemento y (5) `format_dir` da formato a la vía;
    (6) el complemento recupera sus palabras originales cuando el corte cae entre palabras.
    Ninguna palabra se pierde: los números que siguen al barrio y el texto no reconocido tras
    `-*-` van al final del complemento.

    Args:
        texto: Dirección tal como viene en el archivo de entrada.
        vocabulario (VocabularioDirecciones): Tipos de vía, palabras clave y equivalencias.
        indice (IndiceLugares | None): Índice de lugares; None para municipios sin polígonos.

    Returns:
        dict: Claves `direccion`, `principal` (si empieza por un tipo de vía) y las de
            `COLUMNAS_NORMALIZADAS`, con None en las partes vacías.
    """
    tabla = dict(vocabulario.equivalencias)
    antes, separador, despues = _texto(texto).upper().partition(SEPARADOR_ZONA)
    zona = normalizar(despues) if separador else ""
    extra = []
    if zona not in ZONAS:
        extra = despues.split()
        zona = ""

    palabras = antes.split()
    lugar = indice.reconocer(palabras, zona or None) if indice is not None and palabras else None
    resto = palabras[:lugar.inicio] if lugar else palabras
    numeros_finales = palabras[lugar.fin:] if lugar else []

    abreviadas = abreviar(resto, tabla)
    texto_abreviado = " ".join(abreviadas)
    # El espacio final evita que dividir_complemento falle (IndexError) cuando el texto acaba en
    # una palabra de dos letras, caso en el que devolvía todo como dirección.
    direccion, complemento = ([parte.strip() for parte in
                               dividir_complemento(texto_abreviado + " ", vocabulario.palabras_clave_completas)]
                              if texto_abreviado else ["", ""])
    n = len(complemento.split())
    if n and " ".join(abreviadas[len(abreviadas) - n:]) == complemento:
        palabras_complemento = resto[len(resto) - n:]
    else:
        palabras_complemento = complemento.split()

    principal = identificar_vias_principales(
        pd.Series([" ".join(abreviar(palabras, tabla))]), vocabulario.tipos_via
    ).notna().iloc[0]
    return {
        "direccion": format_dir(direccion, vocabulario) or None,
        "principal": bool(principal),
        "Complemento": " ".join(palabras_complemento + numeros_finales + extra) or None,
        "Barrio": (lugar.barrio if lugar else "") or None,
        "Codigo barrio": (lugar.codigo if lugar else "") or None,
        "Comuna": (lugar.comuna if lugar else "") or None,
        "Zona": zona or None,
    }


def normalizar_direcciones(df: pd.DataFrame, configuracion: Configuracion, indice: IndiceLugares):
    """
    Normaliza la dirección de todos los registros de `df`.

    El barrio y la comuna solo se reconocen en los registros del municipio con polígonos. Las
    columnas de `COLUMNAS_NORMALIZADAS` se colocan a continuación de la columna de dirección;
    las demás columnas y el índice se conservan.

    Returns:
        tuple: (DataFrame normalizado, Serie booleana que indica los registros de vía principal).
    """
    columna = configuracion.columnas.direccion
    con_poligonos = df[configuracion.columnas.ciudad] == configuracion.referencia.municipio_con_poligonos
    partes = [
        normalizar_direccion(texto, configuracion.direcciones, indice if usar_indice else None)
        for texto, usar_indice in zip(df[columna], con_poligonos)
    ]
    resultado = df.drop(columns=[c for c in COLUMNAS_NORMALIZADAS if c in df.columns])
    resultado[columna] = pd.Series([p["direccion"] for p in partes], index=df.index, dtype=object)
    posicion = resultado.columns.get_loc(columna) + 1
    for desplazamiento, nombre in enumerate(COLUMNAS_NORMALIZADAS):
        resultado.insert(posicion + desplazamiento, nombre,
                         pd.Series([p[nombre] for p in partes], index=df.index, dtype=object))
    principal = pd.Series([p["principal"] for p in partes], index=df.index, dtype=bool)
    return resultado, principal
