"""Ubicación por niveles: el mejor punto disponible para cada registro del área metropolitana.

Para cada registro se usa el primer nivel disponible de este orden:
- **DIRECCION:** punto de OpenCage validado. Solo se consultan las vías principales del
  municipio con polígonos.
- **BARRIO:** punto representativo del barrio declarado con código.
- **COMUNA:** punto representativo de la comuna declarada.
- **MUNICIPIO:** punto del municipio en `[puntos_municipios]`.

Las funciones de este módulo no hacen peticiones por sí mismas: reciben una sesión con un
método `resolver(consulta, bounds, registro)` (`georef.geocodificacion.SesionConsultas` o un
doble de prueba).
"""
from collections import Counter

import pandas as pd

from georef.geocodificacion import PENDIENTE, RESULTADO, SIN_RESULTADO, consulta_direccion, consulta_lugar

# Niveles de ubicación, del más preciso al menos preciso.
DIRECCION = "DIRECCION"
BARRIO = "BARRIO"
COMUNA = "COMUNA"
MUNICIPIO = "MUNICIPIO"
NIVELES = (DIRECCION, BARRIO, COMUNA, MUNICIPIO)

# Valores de 'Resultado consulta' (además de SIN_RESULTADO y PENDIENTE de la sesión).
ACEPTADA = "ACEPTADA"
ACEPTADA_LUGAR = "ACEPTADA_LUGAR"
PRECISION_INSUFICIENTE = "PRECISION_INSUFICIENTE"
FUERA_DEL_MUNICIPIO = "FUERA_DEL_MUNICIPIO"
LEJOS_DEL_LUGAR_DECLARADO = "LEJOS_DEL_LUGAR_DECLARADO"
SIN_CONSULTA = "SIN_CONSULTA"
RESULTADOS = (ACEPTADA, ACEPTADA_LUGAR, SIN_RESULTADO, PRECISION_INSUFICIENTE, FUERA_DEL_MUNICIPIO,
              LEJOS_DEL_LUGAR_DECLARADO, PENDIENTE, SIN_CONSULTA)

COLUMNAS_UBICACION = ["Latitud", "Longitud", "Nivel ubicacion", "Resultado consulta", "Barrio ubicacion",
                      "Codigo barrio ubicacion", "Comuna ubicacion"]

# Columna tras la que se insertan las de ubicación (la última de la estandarización).
COLUMNA_ANTERIOR = "Zona"


def evaluar(respuesta, lugar_declarado, poligonos, parametros) -> str:
    """
    Decide si se acepta el primer resultado de una consulta (D4 del diseño).

    Devuelve ACEPTADA o el motivo del rechazo: SIN_RESULTADO, PENDIENTE, PRECISION_INSUFICIENTE
    (tipo rechazado o `confidence` insuficiente), FUERA_DEL_MUNICIPIO o LEJOS_DEL_LUGAR_DECLARADO.
    `lugar_declarado` es la geometría del barrio o la comuna declarados, o None.
    """
    if respuesta.estado != RESULTADO:
        return respuesta.estado
    if respuesta.tipo in parametros.tipos_rechazados or respuesta.confianza is None \
            or respuesta.confianza < parametros.confianza_minima:
        return PRECISION_INSUFICIENTE
    tolerancia = parametros.tolerancia_metros
    if poligonos.distancia(respuesta.latitud, respuesta.longitud, poligonos.municipio) > tolerancia:
        return FUERA_DEL_MUNICIPIO
    if lugar_declarado is not None and \
            poligonos.distancia(respuesta.latitud, respuesta.longitud, lugar_declarado) > tolerancia:
        return LEJOS_DEL_LUGAR_DECLARADO
    return ACEPTADA


def ubicar_registros(df: pd.DataFrame, principal: pd.Series, configuracion, poligonos, sesion,
                     avance=None) -> pd.DataFrame:
    """
    Devuelve una copia de `df` con las columnas de ubicación tras `Zona`.

    `principal` indica, por índice, qué registros son de vía principal. Todos los municipios de
    `df` deben tener punto en `configuracion.puntos_municipios`. Si se da `avance`, se llama con
    (número del registro, total de registros) antes de procesar cada uno.
    """
    columnas = configuracion.columnas
    parametros = configuracion.ubicacion
    municipio_poligonos = configuracion.referencia.municipio_con_poligonos
    bounds = poligonos.recuadro()

    filas = []
    for numero, (indice, registro) in enumerate(df.iterrows(), start=1):
        if avance:
            avance(numero, len(df))
        ciudad = registro[columnas.ciudad]
        if ciudad != municipio_poligonos:
            filas.append(_en_municipio(configuracion, ciudad, SIN_CONSULTA))
            continue

        codigo, comuna = _lugar_declarado(registro, poligonos)
        lugar = poligonos.geometria_barrio(codigo) if codigo else (
            poligonos.geometria_comuna(comuna) if comuna else None)

        resultado = SIN_CONSULTA
        direccion = registro[columnas.direccion]
        if principal[indice] and isinstance(direccion, str) and direccion.strip():
            consulta = consulta_direccion(direccion, ciudad, parametros.formato_consulta, parametros.nombres_via)
            respuesta = sesion.resolver(consulta, bounds=bounds, registro=indice)
            resultado = evaluar(respuesta, lugar, poligonos, parametros)
            if resultado == ACEPTADA:
                filas.append(_en_direccion(respuesta, resultado, poligonos))
                continue
            if resultado != PENDIENTE and parametros.consulta_lugar_complemento:
                declarado = poligonos.nombre_barrio(codigo)[0] if codigo else comuna
                texto = consulta_lugar(registro.get("Complemento"), declarado, ciudad, parametros.palabras_lugar)
                if texto:
                    respuesta = sesion.resolver(texto, bounds=bounds, registro=indice)
                    if evaluar(respuesta, lugar, poligonos, parametros) == ACEPTADA:
                        filas.append(_en_direccion(respuesta, ACEPTADA_LUGAR, poligonos))
                        continue

        if codigo:
            nombre, comuna_barrio = poligonos.nombre_barrio(codigo)
            filas.append(_fila(*poligonos.punto_barrio(codigo), BARRIO, resultado, nombre, codigo, comuna_barrio))
        elif comuna:
            filas.append(_fila(*poligonos.punto_comuna(comuna), COMUNA, resultado, None, None, comuna))
        else:
            filas.append(_en_municipio(configuracion, ciudad, resultado))

    ubicacion = pd.DataFrame(filas, index=df.index, columns=COLUMNAS_UBICACION)
    ubicacion = ubicacion.astype({"Latitud": float, "Longitud": float, "Nivel ubicacion": object,
                                  "Resultado consulta": object, "Barrio ubicacion": object,
                                  "Codigo barrio ubicacion": object, "Comuna ubicacion": object})
    posicion = df.columns.get_loc(COLUMNA_ANTERIOR) + 1 if COLUMNA_ANTERIOR in df.columns else len(df.columns)
    return pd.concat([df.iloc[:, :posicion], ubicacion, df.iloc[:, posicion:]], axis=1)


def resumen(df: pd.DataFrame, sesion) -> str:
    """Resumen de una ubicación con cifras agregadas (sin direcciones ni otros datos de un registro)."""
    lineas = [f"Registros ubicados: {len(df)}", "Por nivel:"]
    niveles = Counter(df["Nivel ubicacion"])
    lineas += [f"  {nivel}: {niveles.get(nivel, 0)}" for nivel in NIVELES]
    lineas.append("Por resultado de la consulta:")
    resultados = Counter(df["Resultado consulta"])
    lineas += [f"  {resultado}: {resultados[resultado]}" for resultado in RESULTADOS if resultados.get(resultado)]
    lineas.append(f"Peticiones a OpenCage: {sesion.peticiones}; consultas resueltas desde la caché: "
                  f"{sesion.desde_cache}; consultas pendientes: {len(sesion.pendientes)}")
    if sesion.restantes is not None:
        lineas.append(f"Peticiones restantes hoy según OpenCage: {sesion.restantes}")
    if sesion.parada:
        lineas.append(f"Se dejó de consultar por: {MOTIVOS_PARADA.get(sesion.parada, sesion.parada)}. "
                      "Los registros pendientes tienen su ubicación de respaldo; vuelve a ejecutar 'ubicar' "
                      "para continuar desde ese punto (la cuota del free trial se renueva a las 19:00 de Colombia).")
    elif sesion.pendientes:
        lineas.append("Hay consultas pendientes: vuelve a ejecutar 'ubicar' para completarlas.")
    return "\n".join(lineas)


def cifras_comparacion(respuestas, poligonos, parametros) -> str:
    """
    Cifras agregadas de un formato de consulta en el diagnóstico `comparar-consultas`.

    `respuestas` es una lista de pares (Respuesta, código del barrio declarado). Las distancias
    se miden al polígono del barrio declarado. No incluye ninguna dirección.
    """
    total = len(respuestas)
    respondidas = [(r, codigo) for r, codigo in respuestas if r.estado != PENDIENTE]
    con_resultado = [(r, codigo) for r, codigo in respondidas if r.estado == RESULTADO]
    distancias = [poligonos.distancia(r.latitud, r.longitud, poligonos.geometria_barrio(codigo))
                  for r, codigo in con_resultado]
    aceptadas = sum(evaluar(r, poligonos.geometria_barrio(codigo), poligonos, parametros) == ACEPTADA
                    for r, codigo in con_resultado)
    confianzas = [r.confianza for r, _ in con_resultado if r.confianza is not None]
    tipos = Counter(r.tipo or "(sin tipo)" for r, _ in con_resultado)

    def porcentaje(parte, todo):
        return f"{parte} ({100 * parte / todo:.1f} %)" if todo else "0"

    lineas = [
        f"  Consultas de la muestra: {total}; respondidas: {len(respondidas)}; pendientes: {total - len(respondidas)}",
        f"  Con resultado: {porcentaje(len(con_resultado), len(respondidas))}",
        "  Tipos de resultado: " + (", ".join(f"{tipo} {n}" for tipo, n in tipos.most_common()) or "ninguno"),
        f"  Confidence mediana: {pd.Series(confianzas).median() if confianzas else '-'}",
        f"  Dentro del barrio declarado: {porcentaje(sum(d == 0 for d in distancias), len(con_resultado))}",
        f"  A {parametros.tolerancia_metros} m o menos del barrio declarado: "
        f"{porcentaje(sum(d <= parametros.tolerancia_metros for d in distancias), len(con_resultado))}",
        f"  Distancia mediana al barrio declarado: "
        f"{f'{pd.Series(distancias).median():.0f} m' if distancias else '-'}",
        f"  Aceptadas con la configuración actual: {porcentaje(aceptadas, len(con_resultado))}",
    ]
    return "\n".join(lineas)


MOTIVOS_PARADA = {
    "CUOTA_O_RITMO": "OpenCage indicó cuota o ritmo excedidos",
    "ERRORES_SEGUIDOS": "varios errores seguidos de OpenCage",
    "LIMITE_CONSULTAS": "se alcanzó limite_consultas de la configuración",
}


def _lugar_declarado(registro, poligonos):
    """(código de barrio, comuna) declarados que existen en los polígonos; vacíos si no los hay."""
    codigo = registro.get("Codigo barrio")
    codigo = codigo if isinstance(codigo, str) and codigo in poligonos.codigos else None
    comuna = registro.get("Comuna")
    comuna = comuna if isinstance(comuna, str) and comuna in poligonos.comunas else None
    return codigo, comuna


def _en_direccion(respuesta, resultado, poligonos):
    codigo = poligonos.barrio_en(respuesta.latitud, respuesta.longitud)
    nombre, comuna = poligonos.nombre_barrio(codigo) if codigo else (None, None)
    return _fila(respuesta.latitud, respuesta.longitud, DIRECCION, resultado, nombre, codigo, comuna)


def _en_municipio(configuracion, ciudad, resultado):
    punto = configuracion.puntos_municipios[ciudad]
    return _fila(punto.latitud, punto.longitud, MUNICIPIO, resultado, None, None, None)


def _fila(latitud, longitud, nivel, resultado, barrio, codigo, comuna):
    return [latitud, longitud, nivel, resultado, barrio, codigo, comuna]
