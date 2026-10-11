# Tasks

## 1. Línea base y entorno

- [x] 1.1 Con el `main.py` actual, ejecutar la opción 1 sobre una copia de `original/` en un directorio temporal fuera del repositorio y guardar ahí los cuatro archivos de `estandarizado/` como línea base (sin API y sin versionar datos). Verificar que existen los cuatro archivos y que `python -m pytest` pasa completo antes de empezar
- [x] 1.2 Añadir `pdoc=16.0.0` a la sección de desarrollo de `environment.yml` (D9) y ejecutar `conda env update -f environment.yml -n medellin-analysis312`. Verificar que `pdoc --version` informa 16.0.0 con el entorno activado

## 2. Configuración

- [x] 2.1 Crear `config/georef.toml` con los valores actuales de `main.py`: los 10 municipios, el subconjunto `medellin`, las columnas `Ciudad Residencia` y `Direccion de residencia`, tipos de vía, palabras clave y equivalencias como lista ordenada de pares (D2, D4), con comentarios en español sobre el formato exacto de los municipios y la importancia del orden. Verificar que `python -c "import tomllib; tomllib.load(open('config/georef.toml','rb'))"` no da error
- [x] 2.2 Crear `georef/__init__.py` y `georef/config.py`: dataclasses congeladas, `cargar_configuracion(ruta)` y una validación que acumule todos los errores con la ruta de su clave (D2). Escribir `tests/test_configuracion.py` con:
  - un test de regresión que copie literalmente las constantes antiguas de `main.py` y compruebe que la configuración incluida produce los mismos valores en el mismo orden;
  - los escenarios de `specs/configuracion`: clave desconocida, clave ausente o lista vacía, valores repetidos, varios errores a la vez, archivo inexistente y sintaxis inválida con su línea;
  - los escenarios de validación de subconjuntos de `specs/areas-geograficas`: nombre no válido y municipio fuera del área.

  Verificar que `python -m pytest tests/test_configuracion.py` pasa

## 3. Módulos de dominio

- [x] 3.1 Crear `georef/direcciones.py` moviendo las funciones de dirección y de separación por área con parámetros explícitos de vocabulario, municipios y columnas (D7). Migrar `tests/test_estandarizacion.py` a `georef.direcciones`, con el vocabulario de la fixture `configuracion` y **sin cambiar ningún valor esperado** (incluidos los `defecto_conocido`). Verificar que el test pasa
- [x] 3.2 Crear `georef/geocodificacion.py` con `obtener_llave`, `geocodificar_direcciones` (columnas como parámetro), `rellenar_por_barrio`, `BARRIOS_MEDELLIN` y `CENTROIDE_MEDELLIN`, sin cambiar su lógica ni sus parámetros (`n=300`, `n=400`, consulta y pausa). Actualizar la fixture automática de `tests/conftest.py` para sustituir `georef.geocodificacion.OpenCageGeocode` y `georef.geocodificacion.time.sleep` (D8), y migrar `test_geocodificacion.py`, `test_mejora_barrio.py` y `test_credenciales.py` sin cambiar sus valores esperados. Verificar que pasan
- [x] 3.3 Crear `georef/mapas.py` con `visualizar(df, carpeta)`, que escribe los cuatro mapas en `carpeta/` y `carpeta/filtrados/` con la misma lógica. Migrar `tests/test_mapas.py` con los mismos conteos de marcadores. Verificar que pasa
- [x] 3.4 Crear `georef/archivos.py`:
  - rutas de `estandarizado/`, `ruta_coordenadas(area)` y `carpeta_mapas(area)`;
  - estructura de directorios con `mapas/area_metropolitana/filtrados/`;
  - lectura de `original/` que ignora subdirectorios, ocultos y `~$*`, y termina con mensaje si no queda ningún archivo o queda más de uno;
  - diálogo de tkinter;
  - comprobación de `principales_area_metropolitana.xlsx`;
  - aviso del nombre antiguo `coordenadas.xlsx` (D5);
  - comprobación de las columnas configuradas.

  Escribir `tests/test_archivos.py` con los escenarios de `specs/archivos-de-salida`:
  - estructura sin `llave/`;
  - bloqueo de LibreOffice y de Excel, más de un archivo y ningún archivo;
  - archivo antiguo solo, y los dos archivos a la vez sin modificar el antiguo.

  Verificar que pasa

## 4. Etapas y subconjuntos

- [x] 4.1 Crear `georef/etapas.py` con una función por etapa: estandarizar, geocodificar, mejorar y mapas del área metropolitana. Cada una lee y escribe con las rutas de `archivos.py`, usa el nombre nuevo de coordenadas y aplica el aviso del nombre antiguo antes de cualquier consulta. Escribir `tests/test_etapas.py` con:
  - los escenarios de `specs/areas-geograficas`: separación por municipio, registro sin municipio, ninguna consulta para registros de fuera;
  - de `specs/configuracion`: nuevo municipio añadido en una configuración temporal, columna ausente sin escribir archivos;
  - la conversión reanudada desde `coordenadas_area_metropolitana.xlsx`.

  Verificar que pasa
- [x] 4.2 Añadir `extraer_subconjunto` a `georef/etapas.py`: lee `coordenadas_area_metropolitana.xlsx` con `index_col=0`, filtra por municipio, escribe `coordenadas_<nombre>.xlsx` con el mismo índice y columnas, y genera los mapas en `mapas/<nombre>/`. Escribir `tests/test_subconjuntos.py` con los escenarios de extracción y de errores de `specs/areas-geograficas` y `specs/archivos-de-salida`:
  - subconjunto de Medellín y sus mapas;
  - ejecución sin llave y con la API prohibida;
  - subconjunto desconocido (con la lista de disponibles), sin coordenadas, sin registros (sin crear archivos) y archivo antiguo.

  Verificar que pasa

## 5. Interfaz de línea de comandos

- [x] 5.1 Crear `georef/cli.py` y `georef/__main__.py` (D6): parser con `--config` global, subcomandos y `--area` obligatorio en `subconjunto`; alias `c` → `geocodificar`; orden de arranque configuración → directorios → etapa; menú con las opciones 1 a 4 de siempre y la 5 para subconjuntos; diálogo solo en la opción 1 del menú. Migrar `tests/test_flujo_principal.py` a `georef.cli.main(argv)`:
  - solo cambian las rutas de coordenadas y mapas;
  - `test_modo_c_columna_unnamed_defecto_conocido` pasa a comprobar que no aparece `Unnamed: 0`.

  Añadir los escenarios de `specs/linea-de-comandos`:
  - cada subcomando;
  - `estandarizar` con `original/` vacío sin diálogo;
  - `--config` alternativo;
  - opción 4 sin diálogo, opción 5 y opción inválida;
  - subcomando desconocido (código distinto de cero y sin archivos), falta de `--area` y `--help`.

  Añadir también los escenarios de credenciales: `geocodificar` y `mejorar` sin llave terminan sin consultas; `subconjunto` sin llave termina con normalidad. Y el de configuración inválida, que no consulta al proveedor ni modifica archivos.

  Verificar que pasa
- [x] 5.2 Reducir `main.py` a un envoltorio que llame a `georef.cli.main()` y añadir una prueba de humo en subproceso para `python -m georef --help` y `python main.py --help`. Verificar que `python -m pytest` pasa completo, incluida la guardia de identificadores ASCII sobre `georef/`
- [x] 5.3 Ejecutar `python -m georef estandarizar` sobre la misma copia de `original/` de la tarea 1.1, en otro directorio temporal, y comparar los cuatro archivos con la línea base usando `DataFrame.equals` tras leerlos con `index_col=0`. Verificar que los cuatro son idénticos e informar solo del resultado agregado

## 6. Documentación y consumidores

- [x] 6.1 Actualizar `README.md`:
  - estructura con `georef/` y `config/`;
  - uso con el menú, `python main.py`, los subcomandos y `--config`;
  - cómo añadir un municipio o un subconjunto y por qué importa el orden de las equivalencias;
  - nombres de coordenadas y mapas por área;
  - migración: renombrar `coordenadas/coordenadas.xlsx` y regenerar los mapas;
  - comando de pdoc.

  Verificar que los comandos documentados que no usan la API (`--help`, `estandarizar`, `subconjunto` con datos sintéticos) se ejecutan tal como están escritos
- [x] 6.2 Actualizar en `notebooks/exploracion_geojson.ipynb` la ruta de coordenadas a `coordenadas/coordenadas_area_metropolitana.xlsx` (D10), manteniendo el notebook sin salidas. Verificar que `tests/test_notebooks_sin_salidas.py` pasa y, cuando el usuario haya renombrado su archivo local, que `jupyter nbconvert --execute` termina sin errores (salida en el directorio temporal de la sesión)
- [x] 6.3 Regenerar `docs/` con `pdoc georef -o docs` (D9), sustituyendo por completo su contenido anterior. Verificar:
  - que existe la página de cada módulo de `georef`;
  - que `docs/main.html` ya no existe;
  - que generar la documentación no crea directorios de trabajo ni lee la configuración.

## 7. Verificación final

- [x] 7.1 Ejecutar `python -m pytest` completo y `openspec validate modularizacion-config --strict`, y revisar `git status` y `git diff --stat`. Verificar que solo cambian los archivos previstos en la propuesta y que nada de `original/`, `estandarizado/`, `coordenadas/`, `mapas/` ni `.env` queda preparado para commit

## Workflow follow-up

- El usuario renombra su `coordenadas/coordenadas.xlsx` a `coordenadas_area_metropolitana.xlsx` y regenera los mapas con `python -m georef mapas`.
- Commit en la rama `modularizacion-config`, fusión en `main` y `/opsx:archive modularizacion-config`, antes de proponer `ubicacion-por-niveles`.
