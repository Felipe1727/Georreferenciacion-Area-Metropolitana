# Tasks

## 1. Protección del repositorio y entorno

- [x] 1.1 Crear `.gitignore` con las entradas de design.md (D10) y verificar con `git check-ignore -v llave/llave.txt original/x estandarizado/x coordenadas/x mapas/x .env .idea/x` que todas están ignoradas, que `git check-ignore data/limite_barrio_vereda_cata.geojson` no devuelve nada y que `git status --short` ya no lista `llave/`, `original/`, `estandarizado/`, `coordenadas/`, `.idea/` ni `__pycache__/`
- [x] 1.2 Crear `environment.yml` (D8), ejecutar `conda env update -f environment.yml -n medellin-analysis312` y verificar que `python -m pytest --version` responde y que pandas, folium, opencage y openpyxl mantienen las versiones fijadas
- [x] 1.3 Crear `pytest.ini` (D9) y verificar que `python -m pytest` se ejecuta desde la raíz sin errores de configuración (código 5, "no tests ran", es aceptable en este punto)
- [x] 1.4 Actualizar la sección de requisitos e instalación del `README.md` (Python 3.12, `conda env update -f environment.yml`, línea `pip install` equivalente, `python -m pytest`) y verificar que los comandos documentados funcionan tal como están escritos

## 2. Tests de caracterización (contra los nombres actuales)

- [x] 2.1 Crear `tests/conftest.py` con DataFrames sintéticos (D2) que cubran: municipios dentro y fuera del área metropolitana, vías principales y especiales (`VEREDA`, `FINCA`), `CALLE`/`CARRERA` sin abreviar, sufijos `NORTE`/`SUR`, letras (`43 A`), complementos (`APTO`, `UNIDAD`) y el patrón `BARRIO -*- URBANO|RURAL`. Verificar que ningún valor procede de `original/`
- [x] 2.2 Escribir tests de `reemplazar_equivalentes`, `identificar_vías_principales`, `filtrar_vías_principales`, `filtrar_área_metropolitana`, `dividir_complemento`, `format_dir` y `estandarización`, con los valores obtenidos ejecutando el código actual. Incluir los casos `defecto_conocido` (`URBANO` → `URBA#`, `NORTE` → `#RTE`, `BUENOS` → `BUE#S`). Verificar que todos pasan sobre el código sin modificar
- [x] 2.3 Escribir tests de `reverse_geocoding` con un `OpenCageGeocode` falso y `time.sleep` anulado (D3): resultado encontrado, lista vacía con fallback por ciudad (2 consultas extra), excepción que deja el registro vacío, tope `n`, inicio en la primera fila sin coordenadas y reordenación de columnas tras `Complemento`. Verificar que pasan
- [x] 2.4 Escribir tests de `rellenar_por_barrio` con el geocodificador falso: solo se reconsultan filas en el centroide `6.25184, -75.56359` cuyo complemento contiene un barrio de la lista, con la consulta `"<barrio>, MEDELLIN"` y el tope `n`. Verificar que pasan
- [x] 2.5 Escribir un test de `visualizar` sobre `tmp_path`: se generan los 4 HTML y el mapa filtrado tiene tantos `L.marker(` como filas fuera del centroide. Verificar que pasa
- [x] 2.6 Escribir tests de extremo a extremo de `main()` en `tmp_path` con un Excel sintético en `original/`: opción 1 (genera los 4 archivos con los nombres actuales), opciones 2 y 3 (con `obtener_llave` sustituida y el geocodificador falso), opción 4 y modo `python main.py c`. Verificar que pasan y que en ningún caso se abre el diálogo de tkinter

## 3. Renombrado ASCII de identificadores

- [x] 3.1 Aplicar el mapeo de design.md (D4) en `main.py` (identificadores, docstrings y comentarios que los nombran) y en los tests. Verificar que la suite completa sigue en verde sin cambiar ningún valor esperado
- [x] 3.2 Crear `tests/test_identificadores_ascii.py` (D5) con un comprobador basado en `ast` y dos tests: uno que lo aplica a todos los `.py` del repositorio y debe pasar, y otro que lo aplica a un fragmento con un identificador no ASCII y debe detectarlo. Verificar que ambos pasan
- [x] 3.3 Verificar con `grep -nP '[^\x00-\x7F]' main.py` que los caracteres no ASCII restantes están solo en literales de texto, comentarios o docstrings en español (datos o mensajes), no en identificadores

## 4. Nombres de archivo ASCII

- [x] 4.1 Introducir las constantes de nombres de salida (D6) y usarlas en la opción 1, la opción 2 y el modo `c`. Actualizar los tests de 2.6 a los nombres `total_area_metropolitana.xlsx`, `principales_area_metropolitana.xlsx`, `especiales_area_metropolitana.xlsx` y `fuera_area_metropolitana.xlsx`. Verificar que pasan y que en `estandarizado/` no se crea ningún nombre no ASCII
- [x] 4.2 Añadir la comprobación de existencia de `principales_area_metropolitana.xlsx`, con mensaje y salida sin traza, cuando no hay `coordenadas/coordenadas.xlsx`. Escribir el test del escenario "Solo existen archivos con el nombre antiguo" (termina sin consultar al geocodificador falso). Verificar que pasa
- [x] 4.3 Documentar en el `README.md` los nuevos nombres de archivo y la migración (renombrar o reejecutar la opción 1; `coordenadas.xlsx` no cambia). Verificar que la estructura de directorios descrita coincide con la que crea `estructura_programa()`

## 5. Credencial en variable de entorno

- [x] 5.1 Reescribir `obtener_llave()` según D7, llamarla desde la opción 2, la opción 3 y el modo `c` antes de cualquier lectura o escritura de coordenadas, y eliminar `llave/` de `estructura_programa()`. Sustituir en los tests de 2.6 el parche de `obtener_llave` por `monkeypatch.setenv("OPENCAGE_API_KEY", ...)`. Verificar que pasan
- [x] 5.2 Escribir los tests de `specs/credenciales-geocodificacion`: variable definida, valor con espacios, modo `c` sin archivo de llave, variable ausente (código distinto de cero, mensaje con `OPENCAGE_API_KEY`, `coordenadas.xlsx` sin cambios), variable vacía, sin `llave/` creado y sin la llave en la salida (`capsys`), y estandarización sin variable. Verificar que todos pasan
- [x] 5.3 Escribir el test de `specs/archivos-de-salida` "Primera ejecución en un directorio limpio" (se crean los cuatro directorios y no `llave/`). Verificar que pasa
- [x] 5.4 Documentar en el `README.md` la definición de `OPENCAGE_API_KEY` (`export`, `conda env config vars set ... -n medellin-analysis312` y variables de entorno de la configuración de ejecución de PyCharm) y eliminar las referencias a `llave/llave.txt`. Verificar con `grep -n llave README.md` que solo queda la nota de migración
- [x] 5.5 Leer `OPENCAGE_API_KEY` también de `.env` (D7): añadir `python-dotenv=1.2.4` a `environment.yml` e instalarlo, usar `dotenv_values` en `obtener_llave()` con prioridad del entorno, actualizar el mensaje de error, crear `.env.example` y añadir los tests de `.env` (solo en `.env`, prioridad del entorno, `.env` vacío, entorno sin modificar, `.env.example` versionado y `.env` ignorado). Documentar en el `README.md` el uso de `.env` y `chmod 600`. Verificar que la suite completa pasa sin red

## 6. Verificación integrada y migración

- [x] 6.1 Ejecutar `python -m pytest` completo en `medellin-analysis312` y verificar que todo pasa sin acceso a red (por ejemplo, con la conexión desactivada o comprobando que el geocodificador falso está siempre activo)
- [x] 6.2 Prueba de no regresión con los datos reales, solo en local y sin versionar: guardar una copia de los Excel actuales de `estandarizado/`, ejecutar la opción 1 y verificar con pandas que cada archivo nuevo es igual (`DataFrame.equals`) a su equivalente con tilde. No ejecutar las opciones 2 ni 3 para no consumir cuota
- [x] 6.3 Verificar con `git log --all --oneline -- llave` que la llave nunca se versionó (si aparece, rotarla en el panel de OpenCage). Crear `.env` con `OPENCAGE_API_KEY` y borrar `llave/`. Verificar que `python main.py` llega al menú y que la opción 2 ya no pregunta por la llave (interrumpir antes de geocodificar si no se quiere consumir cuota)

## Workflow follow-up

- Revisar el diff y hacer commit en una rama propia (por ejemplo, `fundamentos`).
- Archivar con `/opsx:archive fundamentos` para incorporar `credenciales-geocodificacion` y `archivos-de-salida` a `openspec/specs/`.
