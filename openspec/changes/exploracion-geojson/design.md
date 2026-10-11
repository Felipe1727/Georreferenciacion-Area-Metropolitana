# Design

## Context

- `data/limite_barrio_vereda_cata.geojson`: 349 polígonos (338 `Polygon` y 11 `MultiPolygon`, todos válidos) en EPSG:9377 (MAGNA-SIRGAS Origen Nacional, en metros). Tiene 21 comunas y corregimientos, `codigo` único y 341 valores distintos de `nombre_barrio`. `indicador_ur` vale `U` en 267 polígonos, `R` en 78 y está vacío en 4 (las "Área de Expansión"). La fecha de sincronización es 2025-05-02.
- Hay 8 nombres repetidos. En 7 de ellos un polígono es urbano y el otro rural; "Suburbano El Llano" tiene dos polígonos rurales.
- En la exploración se midió, con datos reales y en local:
  - 983 de 1284 direcciones siguen el patrón `... <BARRIO> -*- URBANO|RURAL`.
  - De 529 registros de Medellín con texto entre la vía y `-*-`, 366 tienen un nombre oficial como sufijo.
  - De los 162 puntos actuales de la API con barrio declarado reconocible, solo 20 caen en ese barrio y 59 en su comuna.
- El entorno `medellin-analysis312` ya tiene geopandas 1.1.3, pyproj 3.7.2, shapely 2.1.2, pyogrio 0.12.1 y jupyterlab 4.5.6. pyproj necesita `PROJ_DATA`, que se define al activar el entorno con `conda activate`. Si se invoca el intérprete sin activarlo, la reproyección falla.
- La estandarización actual de `main.py` corrompe nombres de barrio (`BUENOS` → `BUE#S`). Por eso el análisis no puede partir de sus salidas.
- Se asume aplicado el grupo 1 de `fundamentos` (`.gitignore`, `environment.yml`, `pytest.ini`).

## Goals / Non-Goals

**Goals:**
- Obtener cifras reproducibles que respalden las decisiones de `ubicacion-por-niveles`.
- Entregar datos de referencia (alias, procedencia) validables automáticamente.

**Non-Goals:**
- Escribir el analizador de direcciones de producción. El notebook usa una heurística exploratoria cuya precisión mide y documenta.
- Decidir la estructura de configuración, que corresponde a `modularizacion-config`.
- Llamar a la API de OpenCage.

## Decisions

### D1. El notebook parte del texto original, no de las salidas de `main.py`

El notebook lee `original/*.xlsx` y el GeoJSON directamente, y no importa `main.py`. Así se evitan los nombres corrompidos por el reemplazo por subcadena y el notebook no queda atado a un código que cambiará en el siguiente cambio.
- *Alternativa*: usar `estandarizado/principales_area_metropolitana.xlsx`. Se descarta porque su `Complemento` contiene `URBA#`, `BUE#S`, etc.

### D2. Estructura del notebook guiada por preguntas

Cada sección responde una pregunta y termina con una celda markdown con la conclusión:
1. Esquema, sistema de coordenadas, cobertura y validez geométrica.
2. Normalización de nombres oficiales y colisiones tras normalizar.
3. Nombres repetidos, zonas `U`/`R` y polígonos sin indicador.
4. Puntos representativos: `representative_point()` frente a `centroid`, calculados en EPSG:9377 y luego transformados a WGS84.
5. Extracción heurística del barrio declarado (D3) y su cobertura.
6. Coincidencia exacta, con sufijo y con alias. Casos sin resolver por ambigüedad.
7. Candidatos de alias (D4).
8. Línea base de concordancia entre los puntos actuales de la API (`coordenadas/coordenadas.xlsx`) y el barrio declarado: en el barrio, en la comuna y distancia en metros, con la curva de tolerancias.
9. Recomendaciones para `ubicacion-por-niveles`.

El notebook se ejecuta de principio a fin sin intervención: `jupyter nbconvert --execute` debe completarlo.

### D3. Heurística exploratoria de extracción del barrio declarado

Se toma el texto anterior a `-*-` y se quitan la vía y los números iniciales. El barrio declarado es el **sufijo más largo** del resto que coincide, una vez normalizado, con un nombre oficial o con un alias. Lo que queda delante es el complemento.
- *Alternativa*: buscar cualquier nombre oficial **contenido** en el texto. Recupera más (364 frente a 366 por sufijo) pero produce falsos positivos con nombres cortos contenidos en otros, como `COLON` en `COLONIAL`, y no separa el complemento.
- Esta heurística no ve los prefijos legítimos de un barrio (`SEMINARIO CORDOBA` acaba en `CORDOBA`). El notebook lista los sufijos cuyo token anterior no es una palabra de vivienda conocida (`CASA`, `APTO`, `APARTAMENTO`, `UNIDAD`, `EDIFICIO`, `URBANIZACION`…), para revisarlos a mano.

### D4. Construcción de la tabla de alias: propuesta automática, decisión humana

- Los candidatos son los segmentos de texto que no coinciden con ningún nombre oficial, ordenados por frecuencia. Para cada uno, `difflib.get_close_matches` (biblioteca estándar) sugiere nombres oficiales parecidos.
- **Una persona decide cada fila.** La columna `nota` registra el motivo: variante ortográfica (`CALAZANS` → Calasanz), nombre popular o artículo (`EL POBLADO`), forma abreviada, etc.
- **Qué no es un alias:**
  - Un prefijo de vivienda (`APARTAMENTO LAURELES`): ya lo resuelve el sufijo de D3.
  - **Un nombre de comuna que abarca muchos barrios** (por ejemplo, un nombre que solo existe como comuna): asignarlo a un polígono arbitrario sería inventar precisión. Estos casos se cuentan y se documentan en los hallazgos, como posible nivel COMUNA que valorará `ubicacion-por-niveles`.
- *Alternativa*: emparejamiento difuso automático en producción, sin tabla. Se descarta porque los errores serían silenciosos y no habría revisión. La tabla hace explícita y auditable cada equivalencia.

### D5. CSV para los alias, con `codigo` como clave

Se usa `data/alias_barrios.csv` porque es tabular, se edita y se revisa en cualquier hoja de cálculo y los diffs de git son legibles. La clave es `codigo` y no el nombre, porque `codigo` es único incluso entre los 8 nombres repetidos, de modo que un alias puede fijar un polígono concreto. `codigo` se lee siempre como texto para conservar los ceros (`0806`).
- *Alternativa*: TOML o JSON dentro de la futura configuración. Es menos cómodo para decenas o cientos de filas. `modularizacion-config` solo tendrá que apuntar a este archivo.

### D6. Validación automática con pytest y `json` de la biblioteca estándar

- `tests/test_alias_barrios.py` comprueba los invariantes de la especificación: alias normalizados y únicos, ningún alias igual a un nombre oficial, `codigo` existente y `nombre_oficial` coherente. Lee el GeoJSON con `json`, no con geopandas, porque solo necesita las propiedades. Es rápido y no depende de PROJ.
- `tests/test_notebooks_sin_salidas.py` carga cada `.ipynb` como JSON y exige `outputs == []` y `execution_count is None` en todas las celdas de código.
- La función de normalización se define una vez en el test, idéntica a la del notebook. `ubicacion-por-niveles` la moverá al código de producción, y el test pasará a importarla.
- *Alternativa*: un filtro de git `nbstripout`. Añade una dependencia y configuración por cada clon del repositorio; el test detecta lo mismo sin ellas.

### D7. Limpieza de salidas antes de cada commit

Antes de cada commit se ejecuta `jupyter nbconvert --clear-output --inplace notebooks/exploracion_geojson.ipynb`. Las cifras que deben quedar en el repositorio se copian a `notebooks/hallazgos_geojson.md`, solo agregadas. Esto es necesario porque un notebook limpio no conserva los resultados.

### D8. Dependencias declaradas

Se añaden a `environment.yml` `geopandas=1.1.3` y `jupyterlab=4.5.6`, las versiones instaladas. pyproj, shapely y pyogrio llegan como dependencias de geopandas, y `nbconvert` como dependencia de jupyterlab. geopandas también será una dependencia de ejecución de `ubicacion-por-niveles`, así que se declara ahora.

## Risks / Trade-offs

- [La tabla de alias se ajusta a la ortografía de esta cohorte] → Es aceptable. La tabla crece con nuevos periodos y la `nota` documenta cada decisión.
- [La heurística por sufijo asigna un barrio incorrecto cuando el texto termina en un nombre oficial que forma parte de otro nombre] → Se revisan a mano los sufijos con un token previo desconocido (D3), y la tasa de casos dudosos queda en los hallazgos.
- [Alguien hace commit del notebook con salidas que muestran direcciones] → El test de D6 falla, y el `.gitignore` de `fundamentos` impide versionar `original/`.
- [Una nueva versión del GeoJSON cambia o elimina códigos] → El test de alias detecta los `codigo` inexistentes. `data/README.md` registra la fecha para comparar versiones.
- [Error de PROJ al ejecutar el notebook sin activar el entorno] → La primera celda comprueba que `pyproj` encuentra su base de datos y, si no, indica que hay que lanzar Jupyter desde `conda activate medellin-analysis312`.
- [Este cambio depende del grupo 1 de `fundamentos`] → Ese grupo es pequeño y no toca código. Se integra antes en la rama principal.
