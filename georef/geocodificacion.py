"""Consultas al proveedor de geocodificación (OpenCage) y lectura de su llave.

Contiene el texto de las consultas (formatos `abreviado` y `expandido`, lugar del complemento
y municipio) y `SesionConsultas`, que hace las peticiones con pausa, caché, registro de
diagnóstico y paradas limpias. Usa la librería `opencage` con `raw_response=True`.
"""
import csv
import datetime
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from dotenv import dotenv_values
from opencage.geocoder import (ForbiddenError, InvalidInputError, NotAuthorizedError, OpenCageGeocode,
                               RateLimitExceededError, UnknownError)


def ciudad_consulta(ciudad: str) -> str:
    """Municipio y departamento de la columna de ciudad para una consulta: 'MEDELLIN - ANTIOQUIA' -> 'MEDELLIN, ANTIOQUIA'."""
    return ", ".join(parte.strip() for parte in str(ciudad).split(" - "))


def consulta_direccion(direccion: str, ciudad: str, formato: str, nombres_via) -> str:
    """
    Texto de la consulta de un registro: su vía y numeración, el municipio, el departamento y 'Colombia'.

    Nunca incluye el complemento, el barrio ni la zona. El formato `abreviado` usa la dirección
    tal como la deja la estandarización (`CL 10 #20-30`); el `expandido` escribe el nombre del
    tipo de vía de `nombres_via` y separa `#` del número (`Calle 10 # 20-30`). La orientación
    pegada al número (`45S`) no se expande, para no confundirla con la letra de la vía.
    """
    if formato == "expandido":
        tipo, _, resto = direccion.partition(" ")
        direccion = " ".join(p for p in (nombres_via.get(tipo, tipo), resto.replace("#", "# ")) if p)
    return f"{direccion}, {ciudad_consulta(ciudad)}, Colombia"


def consulta_lugar(complemento, lugar_declarado, ciudad: str, palabras_lugar) -> str | None:
    """
    Texto de la segunda consulta, con el lugar con nombre del complemento, o None si no lo hay.

    El lugar va desde la primera palabra del complemento que está en `palabras_lugar` hasta el
    final (`APTO 301 UNIDAD LOS PINOS` -> `UNIDAD LOS PINOS`). Le siguen el barrio o la comuna
    declarados, en mayúsculas, si los hay, y la ciudad.
    """
    if not isinstance(complemento, str):
        return None
    palabras = complemento.split()
    inicio = next((i for i, palabra in enumerate(palabras) if palabra.upper() in palabras_lugar), None)
    if inicio is None:
        return None
    partes = [" ".join(palabras[inicio:])]
    if isinstance(lugar_declarado, str) and lugar_declarado.strip():
        partes.append(lugar_declarado.upper())
    return ", ".join(partes + [ciudad_consulta(ciudad), "Colombia"])


def consulta_municipio(municipio: str) -> str:
    """Texto de la consulta del punto de un municipio: '<MUNICIPIO>, <DEPARTAMENTO>, Colombia'."""
    return f"{ciudad_consulta(municipio)}, Colombia"


# Estados de la respuesta a una consulta.
RESULTADO = "RESULTADO"
SIN_RESULTADO = "SIN_RESULTADO"
PENDIENTE = "PENDIENTE"  # no se pudo consultar en esta ejecución (parada, error o sin cliente)

# Motivos por los que una sesión deja de hacer peticiones.
PARADA_CUOTA = "CUOTA_O_RITMO"
PARADA_ERRORES = "ERRORES_SEGUIDOS"
PARADA_LIMITE = "LIMITE_CONSULTAS"

# Errores seguidos tras los que se deja de consultar: protege la cuota si el servicio falla.
MAXIMO_ERRORES_SEGUIDOS = 3

COLUMNAS_CACHE = ["consulta", "fecha", "estado", "latitud", "longitud", "confianza", "tipo", "texto"]
COLUMNAS_REGISTRO = ["fecha_hora_utc", "operacion", "registro", "duracion_ms", "resultado", "restantes", "tipo",
                     "confianza"]


@dataclass(frozen=True)
class Respuesta:
    """Respuesta a una consulta: el primer resultado de OpenCage, sin resultado o pendiente."""

    estado: str
    latitud: float | None = None
    longitud: float | None = None
    confianza: int | None = None
    tipo: str | None = None
    texto: str | None = None


RESPUESTA_PENDIENTE = Respuesta(PENDIENTE)


class SesionConsultas:
    """
    Consultas a OpenCage de una ejecución, con pausa, caché, registro de diagnóstico y paradas.

    - Antes de cada petición espera hasta que hayan pasado `pausa_segundos` desde el inicio de
      la anterior, también si la anterior terminó en error.
    - Cada respuesta correcta (con o sin resultados) se añade a la caché en cuanto llega, y una
      consulta que ya está en la caché nunca se repite.
    - Deja de hacer peticiones, sin perder lo obtenido, si OpenCage indica cuota o ritmo excedidos,
      tras `MAXIMO_ERRORES_SEGUIDOS` errores seguidos o al llegar a `limite_consultas`. Desde ese
      momento, lo que no está en la caché queda PENDIENTE.
    - Sin llave (`llave=None`) no hace peticiones: solo usa la caché.
    - Sin `ruta_cache` (None), las respuestas solo se recuerdan durante la sesión.
    - Si OpenCage rechaza la llave, termina el programa sin mostrarla.
    """

    def __init__(self, llave, parametros, ruta_cache, ruta_registro, operacion):
        self._cliente = OpenCageGeocode(llave) if llave else None
        self._pausa = parametros.pausa_segundos
        self._limite = parametros.limite_consultas
        self._ruta_cache = Path(ruta_cache) if ruta_cache is not None else None
        self._ruta_registro = Path(ruta_registro)
        self._operacion = operacion
        self._cache = _leer_cache(self._ruta_cache) if self._ruta_cache is not None else {}
        self._inicio_anterior = None
        self._errores_seguidos = 0
        self.peticiones = 0
        self.desde_cache = 0
        self.pendientes = set()  # consultas distintas que quedaron sin respuesta
        self.parada = None
        self.restantes = None  # últimas peticiones restantes que informó OpenCage

    def resolver(self, consulta, bounds=None, registro="") -> Respuesta:
        """Devuelve la respuesta a `consulta`, de la caché o con una petición. `registro` va al registro."""
        if consulta in self._cache:
            self.desde_cache += 1
            return self._cache[consulta]
        if self._cliente is None or self.parada:
            self.pendientes.add(consulta)
            return RESPUESTA_PENDIENTE
        if self.peticiones >= self._limite:
            self.parada = PARADA_LIMITE
            self.pendientes.add(consulta)
            return RESPUESTA_PENDIENTE

        parametros = {"countrycode": "co", "limit": 1, "no_annotations": 1}
        if bounds:
            parametros["bounds"] = bounds
        self._esperar()
        self._inicio_anterior = time.monotonic()
        self.peticiones += 1
        try:
            datos = self._cliente.geocode(consulta, raw_response=True, **parametros)
        except RateLimitExceededError:
            self._registrar(registro, "RateLimitExceededError")
            self.parada = PARADA_CUOTA
            self.pendientes.add(consulta)
            return RESPUESTA_PENDIENTE
        except (NotAuthorizedError, ForbiddenError) as error:
            self._registrar(registro, type(error).__name__)
            sys.exit("Error: OpenCage rechazó la llave de 'OPENCAGE_API_KEY' (no autorizada o bloqueada). "
                     "Revisa la llave en tu archivo '.env' o en el entorno. No se escribió el archivo de coordenadas.")
        except (UnknownError, InvalidInputError, requests.RequestException) as error:
            self._registrar(registro, type(error).__name__)
            self._errores_seguidos += 1
            if self._errores_seguidos >= MAXIMO_ERRORES_SEGUIDOS:
                self.parada = PARADA_ERRORES
            self.pendientes.add(consulta)
            return RESPUESTA_PENDIENTE

        self._errores_seguidos = 0
        self.restantes = (datos.get("rate") or {}).get("remaining", self.restantes)
        respuesta = _primera_respuesta(datos.get("results") or [])
        self._registrar(registro, respuesta.estado, respuesta, (datos.get("rate") or {}).get("remaining"))
        self._guardar_en_cache(consulta, respuesta)
        return respuesta

    def _esperar(self):
        if self._inicio_anterior is not None:
            espera = self._pausa - (time.monotonic() - self._inicio_anterior)
            if espera > 0:
                time.sleep(espera)

    def _guardar_en_cache(self, consulta, respuesta):
        self._cache[consulta] = respuesta
        if self._ruta_cache is None:
            return
        fila = {"consulta": consulta, "fecha": datetime.date.today().isoformat(), "estado": respuesta.estado,
                "latitud": respuesta.latitud, "longitud": respuesta.longitud, "confianza": respuesta.confianza,
                "tipo": respuesta.tipo, "texto": respuesta.texto}
        _anadir_fila(self._ruta_cache, COLUMNAS_CACHE, fila)

    def _registrar(self, registro, resultado, respuesta=None, restantes=None):
        duracion = round((time.monotonic() - self._inicio_anterior) * 1000)
        fila = {"fecha_hora_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                "operacion": self._operacion, "registro": registro, "duracion_ms": duracion,
                "resultado": resultado, "restantes": restantes,
                "tipo": respuesta.tipo if respuesta else None,
                "confianza": respuesta.confianza if respuesta else None}
        _anadir_fila(self._ruta_registro, COLUMNAS_REGISTRO, fila)


def _primera_respuesta(resultados) -> Respuesta:
    if not resultados:
        return Respuesta(SIN_RESULTADO)
    primero = resultados[0]
    return Respuesta(
        RESULTADO,
        latitud=float(primero["geometry"]["lat"]),
        longitud=float(primero["geometry"]["lng"]),
        confianza=primero.get("confidence"),
        tipo=(primero.get("components") or {}).get("_type"),
        texto=primero.get("formatted"),
    )


def _leer_cache(ruta: Path) -> dict:
    """Carga la caché CSV en un diccionario consulta -> Respuesta (vacío si el archivo no existe)."""
    if not ruta.exists():
        return {}
    cache = {}
    with open(ruta, encoding="utf-8", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            def valor(columna, tipo):
                texto = fila.get(columna) or ""
                return tipo(texto) if texto else None
            cache[fila["consulta"]] = Respuesta(
                fila["estado"], valor("latitud", float), valor("longitud", float),
                valor("confianza", lambda t: int(float(t))), fila.get("tipo") or None, fila.get("texto") or None,
            )
    return cache


def _anadir_fila(ruta: Path, columnas, fila):
    """Añade `fila` al CSV de `ruta` (con encabezado si es nuevo) y lo cierra, para no perderla si el proceso cae."""
    nuevo = not ruta.exists() or ruta.stat().st_size == 0
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "a", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas)
        if nuevo:
            escritor.writeheader()
        escritor.writerow({c: "" if fila.get(c) is None else fila[c] for c in columnas})


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
