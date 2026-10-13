"""Estandarización, ubicación por niveles y mapas de las direcciones de residencia de estudiantes.

Se ejecuta desde la raíz del repositorio con `python -m georef` (o `python main.py`).
Módulos:

- `georef.cli`: subcomandos y menú interactivo.
- `georef.config`: carga y validación de `config/georef.toml`.
- `georef.etapas`: una función por etapa del proceso, con la lectura y escritura de archivos.
- `georef.archivos`: rutas de trabajo y lectura del archivo de entrada.
- `georef.direcciones`: separación por área y normalización de direcciones (sin archivos).
- `georef.referencia`: índice de barrios y comunas de Medellín (GeoJSON y tablas de alias).
- `georef.geografia`: polígonos de barrios, comunas y municipio (puntos y distancias).
- `georef.geocodificacion`: llave, texto de las consultas y sesión de consultas a OpenCage.
- `georef.ubicacion`: cascada de niveles DIRECCION, BARRIO, COMUNA y MUNICIPIO.
- `georef.mapas`: mapas HTML con folium.
"""
