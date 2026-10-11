# Proposal

## Why

La ubicación por niveles necesita relacionar el barrio que escribe cada estudiante con un polígono oficial de Medellín. Esa ubicación es el nivel BARRIO: el "punto cero del barrio" y la validación de los puntos de la API. El GeoJSON oficial (`data/limite_barrio_vereda_cata.geojson`, del portal de datos abiertos GeoMedellín) está versionado pero el código no lo usa, y la lista de barrios escrita a mano en `main.py` es incompleta y en buena parte no es válida.

Una medición preliminar hecha durante la exploración encontró que solo 163 de 492 barrios declarados coinciden exactamente con un nombre oficial. Antes de diseñar ese emparejamiento hay que conocer a fondo la fuente y construir los datos de referencia que lo hagan fiable.

## What Changes

- Añadir un notebook exploratorio (`notebooks/exploracion_geojson.ipynb`) que analice el GeoJSON: esquema, sistema de coordenadas, cobertura, nombres, duplicados, zonas urbano/rural y puntos representativos. También debe medir cuántos barrios declarados por los estudiantes coinciden con los oficiales y cuántos más se recuperan con alias.
- Producir una **tabla de alias de barrios** versionada (`data/alias_barrios.csv`) que asigne cada variante escrita por los estudiantes al código oficial (`codigo`) de un polígono, revisada a mano.
- Fijar y documentar la **convención de normalización de nombres** y las **reglas de desambiguación** de los nombres repetidos (9 nombres en 18 polígonos tras normalizar), usando la zona `URBANO`/`RURAL` de la dirección.
- Documentar la **procedencia** del GeoJSON (`data/README.md`): fuente, URL, fecha de descarga y de sincronización, licencia, sistema de coordenadas y significado de cada campo.
- Registrar los **hallazgos** en un documento de texto con cifras agregadas (`notebooks/hallazgos_geojson.md`): tasas de coincidencia, cobertura estimada del nivel BARRIO, casos ambiguos y la línea base de concordancia entre los puntos actuales de la API y el barrio declarado (que servirá para evaluar la prueba A/B de `ubicacion-por-niveles`).
- Declarar en `environment.yml` las dependencias que usa el análisis (`geopandas`, `jupyterlab`), ya instaladas en el entorno.

## Capabilities

### New Capabilities

- `referencia-barrios`: datos de referencia geográfica de Medellín que consume el sistema. Incluye la fuente oficial de polígonos y su procedencia, la convención de normalización de nombres, la tabla de alias (formato e invariantes) y la regla para resolver nombres de barrio repetidos.

### Modified Capabilities

Ninguna.

## Impact

- **Archivos nuevos**: `notebooks/exploracion_geojson.ipynb` (versionado sin salidas), `notebooks/hallazgos_geojson.md`, `data/alias_barrios.csv`, `data/README.md`, y los tests `tests/test_alias_barrios.py` (invariantes de la tabla) y `tests/test_notebooks_sin_salidas.py`.
- **Archivos modificados**: `environment.yml` (se añaden `geopandas` y `jupyterlab`). No se modifica `main.py` ni ningún otro código de producción.
- **Dependencia con `fundamentos`**: este cambio asume que ya existen el `.gitignore` (incluye `.ipynb_checkpoints/` y `original/`) y el `environment.yml` del grupo 1 de `fundamentos`. Ese grupo debe estar en la rama principal antes de aplicar este cambio. El resto de `fundamentos` es independiente.
- **Datos personales**: el notebook lee `original/` en local para medir coincidencias. En el repositorio solo entran el notebook sin salidas, cifras agregadas y la tabla de alias (variantes de nombres de barrio, sin identificadores ni datos de ningún registro).
- **Consumidores posteriores**: `ubicacion-por-niveles` usará la tabla de alias, la normalización y la regla de desambiguación. `modularizacion-config` decidirá cómo se referencia la tabla desde la configuración.
- **Fuera de alcance**: implementar el emparejamiento de barrios en el código, la geocodificación, la cascada de niveles y cualquier llamada a la API de OpenCage.
