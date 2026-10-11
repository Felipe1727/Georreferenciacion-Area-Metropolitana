"""Separación por área y estandarización de direcciones.

Funciones puras sobre Series y DataFrames: no leen ni escriben archivos. El
vocabulario y los nombres de columna llegan como parámetros desde la configuración.

La lógica es la heredada de `main.py`, incluidos sus defectos conocidos (el reemplazo
de equivalencias por subcadena convierte `URBANO` en `URBA#`); los corrige el cambio
`ubicacion-por-niveles`.
"""
import re

import pandas as pd

from georef.config import VocabularioDirecciones


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
    Reemplaza en una Serie de direcciones las palabras clave por sus equivalentes abreviados.

    Las equivalencias se aplican en orden y por subcadena (comportamiento heredado).

    Args:
        s (pd.Series): Serie de strings con direcciones.
        equivalencias: Pares (palabra, abreviatura), en el orden en que se aplican.

    Returns:
        pd.Series: Serie con direcciones normalizadas en mayúsculas y abreviadas.
    """
    s = s.apply(str.upper)
    for palabra, abreviatura in equivalencias:
        s = s.str.replace(palabra, abreviatura)
    return s


def filtrar_vias_principales(df: pd.DataFrame, columna: str, tipos_via) -> list:
    """
    Filtra el DataFrame para separar las direcciones que comienzan con un tipo de vía principal.

    Args:
        df (pd.DataFrame): DataFrame con la columna de dirección.
        columna (str): Nombre de la columna de dirección.
        tipos_via: Tipos de vía principales.

    Returns:
        list: [DataFrame_principales, DataFrame_especiales]
    """
    s = identificar_vias_principales(pd.Series(df.loc[:, columna].copy()), tipos_via)
    s.dropna(inplace=True)

    index_drop = list((set(df.index.copy()) - set(s.index.copy())))
    new_df = df.drop(index_drop, inplace=False)

    return [new_df, df[~df[columna].isin(new_df[columna])]]


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


def estandarizar(df: pd.DataFrame, vocabulario: VocabularioDirecciones, columna: str) -> pd.DataFrame:
    """
    Aplica procesamiento de estandarización de direcciones y añade la columna 'Complemento'.

    Args:
        df (pd.DataFrame): DataFrame con la columna de dirección.
        vocabulario (VocabularioDirecciones): Tipos de vía y palabras clave.
        columna (str): Nombre de la columna de dirección.

    Returns:
        pd.DataFrame: DataFrame estandarizado con nueva columna 'Complemento'.
    """
    agregar_columna_complemento(df, vocabulario.palabras_clave_completas, columna)
    df.loc[:, columna] = df.loc[:, columna].apply(format_dir, vocabulario=vocabulario)

    # Reordenar columnas: mover "Complemento" al lado de la columna de dirección
    columnas = df.columns.tolist()
    if "Complemento" in columnas and columna in columnas:
        columnas.remove("Complemento")
        idx = columnas.index(columna) + 1
        columnas.insert(idx, "Complemento")
        df = df[columnas]
    return df


def agregar_columna_complemento(df: pd.DataFrame, palabras_clave, columna: str):
    """
    Separa la dirección en base al complemento y añade la columna 'Complemento' al DataFrame.

    Args:
        df (pd.DataFrame): DataFrame con la columna de dirección.
        palabras_clave: Tipos de vía y palabras clave que forman parte de la dirección.
        columna (str): Nombre de la columna de dirección.
    """
    partes = df[columna].astype("string").map(
        lambda s: dividir_complemento(s, palabras_clave), na_action="ignore"
    )
    df[columna] = partes.str[0].astype("string")
    df["Complemento"] = partes.str[1].astype("string")


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
