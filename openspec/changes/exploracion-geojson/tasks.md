# Tasks

## 1. Prerrequisitos y entorno

- [x] 1.1 Verificar que el grupo 1 de `fundamentos` está en la rama de trabajo: `git check-ignore original/x notebooks/.ipynb_checkpoints/x` devuelve ambas rutas, y `pytest.ini` y `environment.yml` existen
- [x] 1.2 Añadir `geopandas=1.1.3` y `jupyterlab=4.5.6` a `environment.yml` (D8), ejecutar `conda env update -f environment.yml -n medellin-analysis312` y verificar, con el entorno activado, que `python -c "import geopandas, pyproj; print(pyproj.datadir.get_data_dir())"` imprime un directorio existente

## 2. Procedencia de la fuente

- [x] 2.1 Obtener del usuario o de la página del conjunto en GeoMedellín la URL, la licencia y la fecha de descarga del GeoJSON, y redactar `data/README.md` con fuente, URL, licencia, fechas de descarga y de sincronización (2025-05-02), EPSG:9377 y la descripción de `codigo`, `nombre_barrio`, `nombre_comuna`, `comuna` e `indicador_ur` (incluido el caso vacío de las "Área de Expansión"). Verificar con el escenario "Consulta de procedencia" de `specs/referencia-barrios`

## 3. Notebook: fuente y nombres oficiales (secciones 1 a 4)

- [x] 3.1 Crear `notebooks/exploracion_geojson.ipynb` con una primera celda que compruebe la base de datos de PROJ y falle con un mensaje claro si no se encuentra. Añadir la sección 1 (esquema, sistema de coordenadas, cobertura, validez, unicidad de `codigo` como texto). Verificar que reproduce 349 polígonos, 0 geometrías inválidas y `codigo` único
- [x] 3.2 Añadir la sección 2: función de normalización según la especificación y colisiones de nombres tras normalizar. Verificar con celdas `assert` los escenarios "Tildes y eñes" y "Puntuación y espacios"
- [x] 3.3 Añadir la sección 3: nombres repetidos con su comuna e `indicador_ur`, y polígonos sin indicador. Verificar que lista los 8 nombres repetidos y los 4 polígonos sin indicador
- [x] 3.4 Añadir la sección 4: `representative_point()` frente a `centroid` en EPSG:9377, transformados a WGS84. Verificar que el notebook muestra cuántos centroides caen fuera de su polígono y que ningún punto representativo cae fuera

## 4. Notebook: barrios declarados (secciones 5 y 6)

- [x] 4.1 Añadir la sección 5 con la heurística de D3 sobre el texto original de los registros de Medellín, y una lista de sufijos con token previo desconocido para revisión manual. Verificar que la cobertura obtenida es coherente con la medición de la exploración (366 de 529 por sufijo) o que la diferencia queda explicada en la celda de conclusión
- [x] 4.2 Añadir la sección 6: tasas de coincidencia exacta y por sufijo, más la aplicación de la regla de nombres repetidos por zona con su número de casos sin resolver. Verificar con celdas `assert` los cinco escenarios de "Resolución de nombres de barrio repetidos"

## 5. Tabla de alias

- [x] 5.1 Añadir la sección 7: candidatos ordenados por frecuencia, con sugerencias de `difflib.get_close_matches`, separando los nombres de comuna sin barrio equivalente (D4). Verificar que la lista se genera y que ningún candidato incluye números de vía ni el separador `-*-`
- [x] 5.2 Revisar los candidatos con el usuario, decidir cada alias y escribir `data/alias_barrios.csv` con `alias`, `codigo` (texto), `nombre_oficial` y `nota`. Verificar que cada fila tiene `nota` y que no se ha creado ningún alias para nombres de comuna o prefijos de vivienda
- [x] 5.3 Crear `tests/test_alias_barrios.py` (D6) con los escenarios "Tabla válida", "Alias que repite un nombre oficial" y "Código inexistente" (los dos últimos sobre tablas sintéticas en `tmp_path`). Verificar que `python -m pytest tests/test_alias_barrios.py` pasa
- [x] 5.4 Volver a ejecutar la sección 6 cargando los alias y añadir la tasa de coincidencia con alias. Verificar que la cobertura mejora respecto a 4.2 y que el notebook muestra ambas cifras

## 6. Notebook: línea base de concordancia con la API (sección 8)

- [x] 6.1 Añadir la sección 8 sobre `coordenadas/coordenadas.xlsx`: puntos que no están en el centroide, unión espacial con los polígonos, coincidencia de barrio y de comuna con el declarado, distancia en metros (EPSG:9377) y curva de tolerancias (0, 100, 250, 500, 1000 y 2000 m). Verificar que las cifras coinciden con las de la exploración (20 y 59 de 162) o que la diferencia, debida a los alias, queda explicada

## 7. Hallazgos, limpieza y documentación

- [x] 7.1 Escribir la sección 9 del notebook y `notebooks/hallazgos_geojson.md` con las cifras agregadas de las secciones 1 a 8 y las recomendaciones para `ubicacion-por-niveles`: tolerancia inicial, tratamiento de los nombres de comuna (posible nivel COMUNA) y tasa esperada de casos sin resolver. Verificar con el escenario "Documento de hallazgos" (sin direcciones, códigos ni filas)
- [x] 7.2 Ejecutar `jupyter nbconvert --execute --to notebook --output /tmp/verificacion.ipynb notebooks/exploracion_geojson.ipynb` para comprobar que se ejecuta de principio a fin, y después `jupyter nbconvert --clear-output --inplace notebooks/exploracion_geojson.ipynb`. Verificar que la ejecución termina sin errores
- [x] 7.3 Crear `tests/test_notebooks_sin_salidas.py` (D6). Verificar que pasa con el notebook limpio y que falla si se vuelve a guardar con salidas (comprobarlo una vez y volver a limpiar)
- [x] 7.4 Añadir `notebooks/` y los archivos de `data/` a la sección de estructura del `README.md`, con el comando para abrir el notebook (`conda activate medellin-analysis312 && jupyter lab`). Verificar que el comando documentado abre el notebook y que este se ejecuta
- [x] 7.5 Ejecutar `python -m pytest` completo y revisar `git status` y `git diff --stat`. Verificar que solo se añaden los archivos previstos en la propuesta y que nada de `original/`, `coordenadas/` ni `.ipynb_checkpoints/` queda preparado para commit

## Workflow follow-up

- Hacer commit en una rama propia (por ejemplo, `exploracion-geojson`) e integrarla tras el grupo 1 de `fundamentos`.
- Archivar con `/opsx:archive exploracion-geojson` para incorporar `referencia-barrios` a `openspec/specs/` antes de proponer `ubicacion-por-niveles`.
