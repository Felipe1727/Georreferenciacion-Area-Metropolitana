"""Datos sinteticos y dobles de prueba compartidos.

Ningun valor procede de `original/`: las direcciones son inventadas e imitan
las formas reales (via + numeros + complemento + `BARRIO -*- ZONA`).
"""
import dataclasses
from pathlib import Path

import pandas as pd
import pytest

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

CENTROIDE_MEDELLIN = (6.25184, -75.56359)


def resultado(lat, lng):
    """Respuesta minima de OpenCage con un unico resultado."""
    return [{"geometry": {"lat": lat, "lng": lng}}]


class GeocodificadorFalso:
    """Sustituto de OpenCageGeocode con respuestas guionizadas.

    `respuestas` asocia consulta -> lista de resultados o excepcion a lanzar.
    Las consultas no previstas devuelven `por_defecto`.
    """

    def __init__(self, respuestas=None, por_defecto=None):
        self.respuestas = respuestas or {}
        self.por_defecto = [] if por_defecto is None else por_defecto
        self.consultas = []
        self.llaves = []

    def __call__(self, api_key):
        # Permite usar la instancia como si fuera la clase OpenCageGeocode.
        self.llaves.append(api_key)
        return self

    def geocode(self, consulta, **kwargs):
        self.consultas.append(consulta)
        valor = self.respuestas.get(consulta, self.por_defecto)
        if isinstance(valor, Exception):
            raise valor
        return valor


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


@pytest.fixture
def geocodificador(monkeypatch):
    """Instala un GeocodificadorFalso; el test configura sus respuestas."""
    falso = GeocodificadorFalso()
    monkeypatch.setattr(geocodificacion, "OpenCageGeocode", falso)
    return falso


def escribir_configuracion(ruta, *reemplazos):
    """Escribe en `ruta` la configuracion incluida con los reemplazos (viejo, nuevo) aplicados una vez."""
    texto = RUTA_CONFIGURACION.read_text(encoding="utf-8")
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
