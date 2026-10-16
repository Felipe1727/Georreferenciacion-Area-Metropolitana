"""Servidor HTTP local para ver los mapas con el fondo de OpenStreetMap.

Las teselas de OpenStreetMap se bloquean si el navegador no envía `Referer`, y una página
abierta como archivo (`file://`) no lo envía. Servida desde `http://127.0.0.1:<puerto>/`, sí.
El servidor solo escucha en el propio equipo y solo sirve la carpeta de mapas.
"""
import functools
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DIRECCION = "127.0.0.1"


class _ManejadorSilencioso(SimpleHTTPRequestHandler):
    """Sirve archivos sin escribir una línea por petición en la terminal."""

    def log_message(self, format, *args):
        pass


def crear_servidor(carpeta):
    """Servidor de `carpeta` en `127.0.0.1`, en un puerto libre que elige el sistema."""
    manejador = functools.partial(_ManejadorSilencioso, directory=str(Path(carpeta)))
    return ThreadingHTTPServer((DIRECCION, 0), manejador)


def servir(carpeta, ruta_inicial: str):
    """
    Sirve `carpeta` hasta Ctrl+C y abre en el navegador `ruta_inicial` (relativa a la carpeta,
    con `/`). Devuelve la URL abierta.
    """
    http = crear_servidor(carpeta)
    puerto = http.server_address[1]
    url = f"http://{DIRECCION}:{puerto}/{ruta_inicial}"
    print(f"Mapa en {url}\nSi el navegador no se abre, copia esa dirección. Pulsa Ctrl+C para terminar.")
    webbrowser.open(url)
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        http.server_close()
    print("Servidor detenido.")
    return url
