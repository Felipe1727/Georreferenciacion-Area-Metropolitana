"""Ver los mapas desde un servidor local (specs/mapas: "Ver los mapas con el fondo de OpenStreetMap")."""
import socket
import threading
import urllib.request
from pathlib import Path

import pytest

from georef import visor

MAPA_AM = Path("mapas") / "area_metropolitana" / "mapa.html"


class ServidorFalso:
    """Sustituye a ThreadingHTTPServer: no abre ningún puerto y `serve_forever` simula Ctrl+C."""

    creados = []

    def __init__(self, direccion, manejador):
        self.direccion = direccion
        self.manejador = manejador
        self.server_address = (direccion[0], 54321)
        self.cerrado = False
        ServidorFalso.creados.append(self)

    def serve_forever(self):
        raise KeyboardInterrupt

    def server_close(self):
        self.cerrado = True


@pytest.fixture
def falsos(monkeypatch):
    ServidorFalso.creados = []
    abiertas = []
    monkeypatch.setattr(visor, "ThreadingHTTPServer", ServidorFalso)
    monkeypatch.setattr(visor.webbrowser, "open", abiertas.append)
    return abiertas


@pytest.fixture
def con_mapa(directorio_trabajo):
    MAPA_AM.parent.mkdir(parents=True)
    MAPA_AM.write_text("<html>mapa sintetico</html>", encoding="utf-8")


def test_ver_el_mapa_del_area_metropolitana(con_mapa, falsos, ejecutar_main, capsys):
    ejecutar_main(argv=("ver-mapas",))  # termina con normalidad tras Ctrl+C
    (servidor,) = ServidorFalso.creados
    assert servidor.direccion == ("127.0.0.1", 0)  # solo el propio equipo, puerto libre
    assert Path(servidor.manejador.keywords["directory"]) == Path("mapas")
    assert falsos == ["http://127.0.0.1:54321/area_metropolitana/mapa.html"]
    salida = capsys.readouterr().out
    assert "http://127.0.0.1:54321/area_metropolitana/mapa.html" in salida and "Servidor detenido" in salida


def test_ver_el_mapa_de_un_subconjunto(directorio_trabajo, falsos, ejecutar_main):
    ruta = Path("mapas") / "medellin" / "mapa.html"
    ruta.parent.mkdir(parents=True)
    ruta.write_text("<html></html>", encoding="utf-8")
    ejecutar_main(argv=("ver-mapas", "--area", "medellin"))
    assert falsos == ["http://127.0.0.1:54321/medellin/mapa.html"]


def test_mapa_sin_generar(directorio_trabajo, falsos, ejecutar_main):
    with pytest.raises(SystemExit) as salida:
        ejecutar_main(argv=("ver-mapas", "--area", "medellin"))
    assert "subconjunto --area medellin" in salida.value.code
    assert ServidorFalso.creados == [] and falsos == []


def test_area_desconocida(directorio_trabajo, falsos, ejecutar_main):
    with pytest.raises(SystemExit) as salida:
        ejecutar_main(argv=("ver-mapas", "--area", "norte"))
    assert "area_metropolitana" in salida.value.code and "medellin" in salida.value.code
    assert ServidorFalso.creados == []


def test_terminar_el_servidor(con_mapa, falsos):
    url = visor.servir(Path("mapas"), "area_metropolitana/mapa.html")
    assert url.endswith("/area_metropolitana/mapa.html") and ServidorFalso.creados[0].cerrado


def test_el_servidor_real_sirve_el_mapa(tmp_path):
    (tmp_path / "area_metropolitana").mkdir()
    (tmp_path / "area_metropolitana" / "mapa.html").write_text("<html>mapa sintetico</html>", encoding="utf-8")
    (tmp_path.parent / "fuera.txt").write_text("no servir", encoding="utf-8")
    servidor = visor.crear_servidor(tmp_path)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    try:
        direccion, puerto = servidor.server_address
        try:
            socket.create_connection((direccion, puerto), timeout=2).close()
        except OSError:
            pytest.skip("sin interfaz de loopback (por ejemplo, con unshare -rn)")
        assert direccion == "127.0.0.1"
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/area_metropolitana/mapa.html", timeout=5) as r:
            assert r.read() == b"<html>mapa sintetico</html>"
        # Solo sirve la carpeta de mapas.
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(f"http://127.0.0.1:{puerto}/../fuera.txt", timeout=5)
    finally:
        servidor.shutdown()
        servidor.server_close()
