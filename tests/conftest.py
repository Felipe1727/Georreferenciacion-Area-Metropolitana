"""Datos sinteticos y dobles de prueba compartidos.

Ningun valor procede de `original/`: las direcciones son inventadas e imitan
las formas reales (via + numeros + complemento + `BARRIO -*- ZONA`).
"""
import dataclasses
import re
from pathlib import Path

import pandas as pd
import pytest
import shapely

from georef import archivos, cli, geocodificacion
from georef.config import cargar_configuracion

RAIZ_REPO = Path(__file__).resolve().parent.parent
RUTA_CONFIGURACION = RAIZ_REPO / "config" / "georef.toml"

# Direccion de residencia -> Ciudad Residencia
DIRECCIONES = {
    "CL 10 20 30 LAURELES -*- URBANO": "MEDELLIN - ANTIOQUIA",
    "CALLE 45 SUR 12 15 APARTAMENTO 301 BUENOS AIRES -*- URBANO": "MEDELLIN - ANTIOQUIA",
    "CARRERA 43 A 1 50 UNIDAD LOS PINOS -*- URBANO": "ENVIGADO - ANTIOQUIA",
    "CR 50 NORTE 30 20 -*- URBANO": "BELLO - ANTIOQUIA",
    "VEREDA EL PLAN -*- RURAL": "MEDELLIN - ANTIOQUIA",
    "FINCA LA ESPERANZA -*- RURAL": "COPACABANA - ANTIOQUIA",
    "CL 50 40 30": "RIONEGRO - ANTIOQUIA",
    "CR 5 10 20 CENTRO": "MONTERIA - CORDOBA",
    "TV 32 B 75 20 CASA 2 CALASANZ -*- URBANO": "MEDELLIN - ANTIOQUIA",
    "DG 50 A 35 12 SURAMERICA -*- URBANO": "ITAGUI - ANTIOQUIA",
}

def resultado_api(lat, lng, tipo="building", confianza=10, texto="Resultado sintetico"):
    """Un resultado de OpenCage con los campos que usa la ubicacion."""
    return {"geometry": {"lat": lat, "lng": lng}, "confidence": confianza, "components": {"_type": tipo},
            "formatted": texto}


class ClienteFalso:
    """Sustituto de OpenCageGeocode para la sesion de consultas (respuestas `raw_response`).

    `respuestas` asocia consulta -> lista de resultados, respuesta completa (dict con
    "results") o excepcion a lanzar. Las consultas no previstas no tienen resultados.
    Registra cada consulta con sus parametros y el instante (reloj del proceso) en que empieza.
    """

    def __init__(self, respuestas=None, restantes=2400):
        self.respuestas = respuestas or {}
        self.restantes = restantes
        self.llamadas = []  # (consulta, parametros)
        self.inicios = []
        self.llaves = []

    def __call__(self, key):
        self.llaves.append(key)
        return self

    @property
    def consultas(self):
        return [consulta for consulta, _ in self.llamadas]

    def geocode(self, consulta, **parametros):
        self.inicios.append(geocodificacion.time.monotonic())
        self.llamadas.append((consulta, parametros))
        valor = self.respuestas.get(consulta, [])
        if isinstance(valor, Exception):
            raise valor
        if isinstance(valor, dict):
            return valor
        self.restantes -= 1
        return {"results": valor, "rate": {"limit": 2500, "remaining": self.restantes}}


class RelojFalso:
    """Reloj para `time.monotonic` y `time.sleep`: dormir avanza el reloj sin esperar de verdad."""

    def __init__(self):
        self.ahora = 1000.0
        self.esperas = []

    def monotonic(self):
        return self.ahora

    def sleep(self, segundos):
        self.esperas.append(segundos)
        self.ahora += segundos


@pytest.fixture
def reloj(monkeypatch):
    falso = RelojFalso()
    monkeypatch.setattr(geocodificacion.time, "monotonic", falso.monotonic)
    monkeypatch.setattr(geocodificacion.time, "sleep", falso.sleep)
    return falso


@pytest.fixture
def cliente(monkeypatch, reloj):
    """Instala un ClienteFalso como OpenCageGeocode; el test configura sus respuestas."""
    falso = ClienteFalso()
    monkeypatch.setattr(geocodificacion, "OpenCageGeocode", falso)
    return falso


def desplazado(poligonos, geometria, metros):
    """Punto WGS84 a `metros` exactos de `geometria` (desplazamiento medido en EPSG:9377).

    Se parte del vertice mas al este y se avanza hacia el este: ningun punto de la geometria
    tiene una x mayor, asi que ese vertice es el mas cercano.
    """
    x, y = max(shapely.get_coordinates(geometria), key=lambda punto: punto[0])
    return poligonos.a_wgs84(shapely.Point(x + metros, y))


def _prohibido(*args, **kwargs):
    raise RuntimeError("Los tests no pueden acceder a la API real de OpenCage")


@pytest.fixture(autouse=True)
def sin_red_ni_esperas(monkeypatch):
    """Garantiza que ningun test llama a la API real ni espera entre consultas.

    Tambien elimina OPENCAGE_API_KEY para que ningun test herede la llave real
    de la sesion; cada test la define explicitamente si la necesita.
    """
    monkeypatch.setattr(geocodificacion, "OpenCageGeocode", _prohibido)
    monkeypatch.setattr(geocodificacion.time, "sleep", lambda segundos: None)
    monkeypatch.delenv("OPENCAGE_API_KEY", raising=False)


def escribir_configuracion(ruta, *reemplazos):
    """Escribe en `ruta` la configuracion incluida con los reemplazos (viejo, nuevo) aplicados una vez.

    Sin la seccion [puntos_municipios] del usuario, si la tiene: los tests usan puntos sinteticos.
    """
    texto = re.sub(r"(?ms)^\[puntos_municipios\]\n.*?(?=^\[|\Z)", "",
                   RUTA_CONFIGURACION.read_text(encoding="utf-8"))
    for viejo, nuevo in reemplazos:
        assert viejo in texto, viejo
        texto = texto.replace(viejo, nuevo, 1)
    # Los datos de referencia se leen del repositorio aunque el test trabaje en un directorio temporal.
    texto = texto.replace('= "data/', f'= "{RAIZ_REPO.as_posix()}/data/')
    Path(ruta).write_text(texto, encoding="utf-8")
    return Path(ruta)


@pytest.fixture
def configuracion():
    """Configuracion incluida (config/georef.toml), con las rutas de referencia absolutas.

    Asi las etapas encuentran `data/` aunque el test trabaje en un directorio temporal.
    """
    configuracion = cargar_configuracion(RUTA_CONFIGURACION)
    referencia = configuracion.referencia
    absolutas = dataclasses.replace(
        referencia,
        geojson=RAIZ_REPO / referencia.geojson,
        alias_barrios=RAIZ_REPO / referencia.alias_barrios,
        alias_comunas=RAIZ_REPO / referencia.alias_comunas,
    )
    return dataclasses.replace(configuracion, referencia=absolutas)


@pytest.fixture
def df_original():
    return pd.DataFrame(
        {
            "CODIGO": [f"E{i:03d}" for i in range(len(DIRECCIONES))],
            "Programa Admision": ["Programa sintetico"] * len(DIRECCIONES),
            "Ciudad Residencia": list(DIRECCIONES.values()),
            "Direccion de residencia": list(DIRECCIONES.keys()),
        }
    )


@pytest.fixture
def sin_dialogo(monkeypatch):
    """Sustituye `tk.Tk` para que el test falle si se intentara abrir el dialogo de tkinter."""

    def _sin_dialogo(*args, **kwargs):
        raise AssertionError("No debe abrirse el dialogo de tkinter")

    monkeypatch.setattr(archivos.tk, "Tk", _sin_dialogo)


@pytest.fixture
def directorio_trabajo(tmp_path, monkeypatch, df_original, sin_dialogo):
    """Directorio temporal con un Excel sintetico en `original/` y la configuracion incluida en `config/`.

    Con `original/` no vacio, el dialogo de tkinter nunca se abre.
    """
    monkeypatch.chdir(tmp_path)
    (tmp_path / "original").mkdir()
    df_original.to_excel(tmp_path / "original" / "base.xlsx", index=False)
    (tmp_path / "config").mkdir()
    escribir_configuracion(tmp_path / "config" / "georef.toml")
    return tmp_path


def seccion_puntos(municipios):
    """Seccion [puntos_municipios] con puntos sinteticos (6.00, 6.01, ... de latitud; no son los reales)."""
    lineas = ["", "[puntos_municipios]"]
    for i, municipio in enumerate(municipios):
        lineas.append(f'"{municipio}" = {{ latitud = {6 + i / 100}, longitud = -75.5, fuente = "prueba", '
                      'fecha = "2026-10-12" }')
    return "\n".join(lineas) + "\n"


@pytest.fixture
def con_puntos(directorio_trabajo):
    """Anade puntos sinteticos de los municipios a `config/georef.toml` del directorio de trabajo y la devuelve cargada."""
    ruta = directorio_trabajo / "config" / "georef.toml"
    with open(ruta, "a", encoding="utf-8") as archivo:
        archivo.write(seccion_puntos(cargar_configuracion(ruta).area_metropolitana))
    return cargar_configuracion(ruta)


@pytest.fixture
def ejecutar_main(monkeypatch):
    """Ejecuta georef.cli.main(argv) respondiendo al menu con `opcion` (o la lista de respuestas)."""

    def _ejecutar(opcion=None, argv=()):
        if opcion is None:
            respuestas = []
        elif isinstance(opcion, (list, tuple)):
            respuestas = [str(r) for r in opcion]
        else:
            respuestas = [str(opcion)]
        respuestas = iter(respuestas)
        monkeypatch.setattr("builtins.input", lambda *a, **k: next(respuestas))
        cli.main(list(argv))

    return _ejecutar
