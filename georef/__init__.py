"""Estandarización, geocodificación y mapas de las direcciones de residencia de estudiantes.

Se ejecuta desde la raíz del repositorio con `python -m georef` (o `python main.py`).
Módulos:

- `georef.cli`: subcomandos y menú interactivo.
- `georef.config`: carga y validación de `config/georef.toml`.
- `georef.etapas`: una función por etapa del proceso, con la lectura y escritura de archivos.
- `georef.archivos`: rutas de trabajo y lectura del archivo de entrada.
- `georef.direcciones`: separación por área y estandarización de direcciones (sin archivos).
- `georef.geocodificacion`: llave y consultas a OpenCage.
- `georef.mapas`: mapas HTML con folium.
"""
