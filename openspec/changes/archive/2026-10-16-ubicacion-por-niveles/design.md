# Design

## Context

Para el motivo, ver `proposal.md` (Why). Estado de partida:

- **`georef/geocodificacion.py`** contiene la conversión heredada:
  - `geocodificar_direcciones`, con lote `n=300`, `except: continue`, que se salta la pausa, y guardado solo al final;
  - la mejora `rellenar_por_barrio`, con `BARRIOS_MEDELLIN` y `CENTROIDE_MEDELLIN`.

  `georef/mapas.py` importa `CENTROIDE_MEDELLIN` para los mapas filtrados.
- **`estandarizado/`** ya tiene, desde `normalizacion-direcciones`, las columnas `Complemento`, `Barrio`, `Codigo barrio`, `Comuna` y `Zona`. Cifras con el archivo real (solo agregados):
  - 963 registros del área metropolitana: 935 principales y 28 especiales;
  - Medellín: 693 principales con 621 direcciones distintas, y 13 especiales;
  - otros municipios: 257;
  - cobertura en Medellín: 546 registros con `Codigo barrio`, 74 solo con `Comuna` y 86 sin ninguno.
- **`georef/referencia.py`** lee las propiedades del GeoJSON con `json`, sin geometrías.
- **Librería `opencage` 3.3.0** (revisada en el código instalado):
  - `geocode(query, raw_response=True, **params)` devuelve el JSON completo;
  - 402 y 429 lanzan la misma `RateLimitExceededError`, y 401 y 403 lanzan `NotAuthorizedError` y `ForbiddenError`;
  - `UnknownError` y `requests.RequestException` se reintentan con backoff exponencial (hasta 5 intentos y 120 s);
  - no hay timeout.
- **Entorno.** shapely 2.1.2 y pyproj 3.7.2 están instalados como dependencias de geopandas 1.1.3. Leer el GeoJSON con `geopandas.read_file` sin activar el entorno conda muestra un error de PROJ de GDAL (`proj_create_from_database`), aunque el resultado es correcto. Con `json` + `shapely.geometry.shape` + `pyproj.Transformer` no aparece y tarda unos 1,5 s. Hay 0 de 349 puntos representativos fuera de su polígono y 0 de 21 en las comunas unidas.

## Goals / Non-Goals

**Goals:**
- Una cascada que se pueda probar sin red: la lógica recibe un "resolvedor" de consultas inyectable.
- Que ninguna ejecución pierda trabajo ya pagado en cuota.
- Medir en la primera ejecución real lo que hoy son hipótesis: formato de consulta, umbral de `confidence` y causa del fallo de "~350".

**Non-Goals:**
- Cliente HTTP propio, timeout o paralelismo.
- Reutilizar los puntos del archivo de coordenadas anterior. Se obtuvieron con consultas corrompidas por la estandarización antigua y su calidad medida es baja.
- Cambiar los mapas más allá del criterio de filtrado.

## Decisions

### D1. Tres módulos nuevos o reescritos, dos clases con estado

| Módulo | Contenido | Forma |
|---|---|---|
| `georef/geografia.py` | Polígonos de barrios por código, comunas unidas y municipio unido; puntos representativos, distancias, búsqueda del polígono que contiene un punto y recuadro WGS84 | Clase `Poligonos`, que carga el GeoJSON una vez |
| `georef/geocodificacion.py` | `obtener_llave` (sin cambios), texto de las consultas, sesión de consultas con pausa, caché, registro y paradas | Funciones puras para el texto y clase `SesionConsultas` |
| `georef/ubicacion.py` | La cascada sobre un DataFrame | Funciones; reciben `Poligonos` y un objeto con `resolver(consulta, bounds)` |

**Alternativa descartada:** ampliar `IndiceLugares`. La estandarización no necesita geometrías y no debe cargar shapely ni pagar su tiempo de carga.

### D2. Geometría con shapely y pyproj, sin GDAL

- **Lectura.** `Poligonos` lee el GeoJSON con `json` y construye cada polígono con `shapely.geometry.shape` en EPSG:9377 (el CRS que declara el archivo).
- **Comunas.** Cada comuna es `shapely.union_all` de sus barrios, y Medellín es la unión de todos.
- **Transformaciones.** Dos `pyproj.Transformer` con `always_xy=True` (9377→4326 y 4326→9377).
- **Distancias.** `geometria.distance(punto_9377)` en metros: vale 0 si el punto está dentro.
- **Búsqueda del polígono.** Un `shapely.STRtree` sobre los barrios encuentra el que contiene el punto.
- **Recuadro.** Los `bounds` de la consulta son el recuadro WGS84 de Medellín, en el orden `min_lng,min_lat,max_lng,max_lat`.

**Por qué no geopandas:** el error de PROJ de GDAL sin activar el entorno, y que no se necesita ninguna de sus operaciones tabulares. `shapely` y `pyproj` pasan a figurar en `environment.yml` con las versiones instaladas.

### D3. Orden de la cascada y lugar declarado

Para cada registro del área metropolitana, en el orden del índice:

1. **Lugar declarado**, solo en el municipio con polígonos:
   - el polígono de `Codigo barrio`, si existe;
   - si no, la comuna unida de `Comuna`, si existe;
   - un barrio ambiguo (con `Barrio` pero sin código) no da lugar declarado.
2. **Consulta.** Solo si el registro es principal y del municipio con polígonos. Se resuelve la consulta y se evalúa con D4.
3. **Segunda consulta (N1b).** Si la primera no se aceptó por un motivo distinto de `PENDIENTE` y `consulta_lugar_complemento` está activada, se aplica la consulta con el lugar del complemento (D8).
4. **Respaldo.** Si no hay punto aceptado: punto representativo del barrio, si no de la comuna, si no el punto del municipio de `[puntos_municipios]`.
5. **Columnas `... ubicacion`.**
   - Para `DIRECCION`: el barrio que contiene el punto, buscado con STRtree, y su comuna.
   - Para `BARRIO`: el barrio y la comuna declarados.
   - Para `COMUNA`: solo la comuna.
   - Para `MUNICIPIO`: vacías.

Si una consulta está `PENDIENTE` (D6), el registro recibe el respaldo y conserva ese resultado, para reconocerlo y reintentarlo.

### D4. Evaluación de un resultado

Sobre el primer resultado de la respuesta, en este orden:
1. **Sin resultados:** `SIN_RESULTADO`.
2. **Tipo o confianza insuficientes:** `PRECISION_INSUFICIENTE`. El tipo se lee de `components._type` y debe no estar en `tipos_rechazados`; la confianza, de `confidence`, y debe ser al menos `confianza_minima`.
3. **Lejos de Medellín:** distancia a Medellín mayor que `tolerancia_metros` → `FUERA_DEL_MUNICIPIO`.
4. **Lejos del lugar declarado:** si hay lugar declarado y la distancia a ese polígono supera la tolerancia → `LEJOS_DEL_LUGAR_DECLARADO`.
5. **En otro caso:** `ACEPTADA` (o `ACEPTADA_LUGAR` en la segunda consulta).

**Validar también con la comuna** cuando no hay barrio con código extiende la decisión de la exploración ("prevalece el barrio, con tolerancia"). Hay 74 registros que solo nombran una comuna, y aceptar para ellos un punto a kilómetros de esa comuna contradiría el mismo criterio.

**Valores incluidos:**
- `tolerancia_metros = 250`, la decisión de la exploración y de `hallazgos_geojson.md`;
- `tipos_rechazados = ["city", "county", "state", "country"]`;
- `confianza_minima = 8` (recuadro menor de 1 km según la documentación de OpenCage). Es un valor **provisional**, porque la API nunca guardó la `confidence` y no hay medición. `comparar-consultas` la muestra para recalibrarlo.

### D5. Uso de la librería `opencage`

`SesionConsultas.resolver(consulta, bounds=None)` llama a `geocode(consulta, raw_response=True, countrycode="co", limit=1, no_annotations=1[, bounds=...])` y traduce la respuesta y las excepciones:

| Situación | Tratamiento |
|---|---|
| Respuesta con `results` | Se guarda en la caché. Se extraen `geometry`, `confidence`, `components._type` y `formatted` del primero, y `rate.remaining` si existe |
| `RateLimitExceededError` | Parada `CUOTA_O_RITMO` (D6) |
| `NotAuthorizedError`, `ForbiddenError` | `sys.exit` con un mensaje sobre `OPENCAGE_API_KEY`, sin escribir el archivo de coordenadas |
| `UnknownError`, `InvalidInputError`, `requests.RequestException` | Error aislado: la consulta queda `PENDIENTE` y cuenta para la parada por errores seguidos |

**Por qué no un cliente propio:** la exploración lo descartó por sencillez. La librería ya reintenta los 5xx y los errores de red, y con `raw_response=True` expone `rate.remaining` para el diagnóstico.

**Coste aceptado:** no hay timeout, y 402 y 429 no se distinguen. Ambos producen la misma parada limpia, y el registro (D7) permite distinguirlos por las peticiones restantes.

### D6. Pausa, límite y paradas en `SesionConsultas`

- **Pausa.** Antes de cada petición, `time.sleep(max(0, pausa - (time.monotonic() - inicio_anterior)))`. El inicio se registra antes de llamar, así que un error no se salta la pausa: corrige la hipótesis A del fallo de "~350".
- **Contadores.** La sesión cuenta las peticiones hechas, las resueltas desde la caché y los errores seguidos. `MAXIMO_ERRORES_SEGUIDOS = 3` es una constante del código y no se configura, porque solo protege la cuota.
- **Paradas.** Con una parada activa (`CUOTA_O_RITMO`, `ERRORES_SEGUIDOS` o `LIMITE_CONSULTAS`), `resolver` devuelve `PENDIENTE` sin hacer la petición. La caché se sigue usando.
- **Límite.** `limite_consultas` cuenta solo peticiones reales; el valor incluido es 1000. Sustituye a `n=300` con un significado claro: el máximo de cuota que puede gastar una ejecución.
- **Sin consultas.** `--sin-consultas` crea la sesión sin cliente: todo lo que no está en la caché es `PENDIENTE`.

### D7. Caché y registro en CSV

- **`coordenadas/cache_consultas.csv`.** Columnas: `consulta, fecha, estado (RESULTADO|SIN_RESULTADO), latitud, longitud, confianza, tipo, texto`.
  - Se carga en un `dict` por `consulta` al crear la sesión.
  - Cada respuesta añade una línea con el módulo `csv` y hace `flush`, así que si el proceso cae se pierde como mucho la línea en curso.
  - La clave es el texto de la consulta, que ya incluye el formato.
  - Los demás parámetros son fijos en el código. Si un día cambian (por ejemplo `bounds`), el README indica borrar la caché.
- **`coordenadas/registro_consultas.csv`.** Columnas: `fecha_hora_utc, operacion, registro, duracion_ms, resultado, restantes, tipo, confianza`.
  - Sin texto de consulta ni llave.
  - `registro` es el índice del registro o el nombre del municipio. En `comparar-consultas` es el índice del primer registro con esa dirección.

**Por qué CSV y no SQLite:** son unas 700 consultas, el usuario puede abrir los archivos en Excel y no hace falta SQL. Las dos rutas están en `coordenadas/`, ya ignorado por git, porque contienen direcciones.

### D8. Texto de las consultas

- **Ciudad.** `"MEDELLIN - ANTIOQUIA"` → `"MEDELLIN, ANTIOQUIA"`: se divide por `" - "` y se une con `", "`. Así se corrige el departamento repetido de la consulta anterior.
- **`abreviado`.** `f"{direccion}, {ciudad}, Colombia"`.
- **`expandido`.** Sustituye el primer token de la dirección (el tipo de vía) por `nombres_via[tipo]` y `#` por `# `: `CL 45S #12-15` → `Calle 45S # 12-15`. La orientación pegada al número (`45S`) no se expande, para no confundirla con la letra de la vía.
- **Segunda consulta (N1b).** Desde la primera palabra de `Complemento` que esté en `palabras_lugar` hasta el final, más `Barrio` o `Comuna` en mayúsculas, si existen, y la ciudad: `UNIDAD LOS PINOS, LAURELES, MEDELLIN, ANTIOQUIA, Colombia`.
- **Valores incluidos:**
  - `palabras_lugar`: `UNIDAD`, `EDIFICIO`, `URBANIZACION`, `URB`, `CONJUNTO`, `CONDOMINIO` y `PARQUE`, los más frecuentes en la exploración;
  - `nombres_via`: `CL` Calle, `CR` Carrera, `AV` Avenida, `CIR` Circular, `DG` Diagonal y `TV` Transversal, el inverso de las equivalencias.
- **Formato por defecto: `abreviado`.** Es el actual y no hay evidencia todavía a favor del otro. Se cambia en la configuración después de `comparar-consultas`.

### D9. `consultar-municipios` escribe texto TOML al final

`tomllib` solo lee. Reescribir el archivo con otra librería perdería los comentarios, así que el subcomando procede así:
1. Consulta los municipios sin punto con `<MUNICIPIO>, <DEPARTAMENTO>, Colombia`, sin `bounds` y sin caché. Las peticiones quedan en el registro con la operación `municipios`.
2. Muestra el punto, el tipo, la confianza y el texto devueltos, para detectar un homónimo de otro departamento.
3. Si `[puntos_municipios]` no existe, añade al final un bloque con comentario de procedencia y una tabla en línea por municipio:
   `"BELLO - ANTIOQUIA" = { latitud = ..., longitud = ..., fuente = "OpenCage", fecha = "2026-10-13" }`.
4. Vuelve a cargar la configuración. Si no es válida, restaura el texto original y termina con un error.
5. Si la sección ya existe, solo imprime las líneas que faltan.

**Alternativa descartada:** un CSV aparte en `data/`. El usuario eligió guardar los puntos en la configuración.

### D10. `comparar-consultas`

- **Muestra.** Registros de Medellín de vía principal con `Codigo barrio`, deduplicados por `Direccion de residencia` y ordenados. `random.Random(0).sample` toma hasta N direcciones, de modo que la muestra es reproducible.
- **Consultas.** Cada dirección se consulta en los dos formatos con la misma sesión: pausa, caché, límite y paradas iguales que en la ubicación.
- **Cifras por formato:**
  - con resultado;
  - recuento por tipo;
  - mediana de `confidence`;
  - porcentaje a 0 m y a `tolerancia_metros` o menos del barrio declarado;
  - mediana de la distancia;
  - también, cuántos pasarían la evaluación de D4 con la configuración actual.

  Si la sesión se para, el informe indica cuántas consultas quedaron pendientes.

### D11. Etapa `ubicar` y archivo de coordenadas

Comprobaciones previas, en este orden, todas antes de cualquier petición:
1. nombre antiguo `coordenadas.xlsx`;
2. archivos de principales y especiales;
3. formato del archivo de coordenadas existente (renombrado a `_anterior` o error si ese nombre ya existe);
4. `[puntos_municipios]` completo;
5. llave (salvo con `--sin-consultas`).

Después:
- **Lectura.** Principales y especiales con `index_col=0` y `dtype={"Codigo barrio": str}`; se concatenan y se ordenan por índice. Se marca cuáles son principales según el archivo del que vienen.
- **Columnas.** Las 7 nuevas se insertan justo después de `Zona`. `Codigo barrio ubicacion` es texto.
- **Escritura.** El archivo se escribe al final de la cascada. Una interrupción con Ctrl+C no lo escribe, pero la caché conserva lo consultado.
- **Avance.** Mientras recorre los registros, escribe en la salida de errores una línea con el número del registro, el total y las cifras de la sesión (peticiones, consultas desde la caché, pendientes), sin datos del registro. En una terminal la línea se reescribe en el mismo sitio; si la salida no es una terminal, se escribe una línea cada 100 registros y la del último. `comparar-consultas` muestra la misma línea por dirección de la muestra (una cada 10 fuera de una terminal).
- **Resumen.** Se imprime el resumen agregado.

### D12. CLI, menú y mapas

- **Subcomandos.** `SUBCOMANDOS` pasa a ser `estandarizar`, `ubicar`, `mapas`, `consultar-municipios` y `comparar-consultas`, más `subconjunto`.
  - `ubicar` recibe `--sin-consultas`.
  - `comparar-consultas` recibe `--muestra`, con un `type` de argparse que rechaza enteros no positivos.
  - `c` se traduce a `ubicar`.
- **Menú.** Cuatro opciones; `input` pide de 1 a 4.
- **Mapas.** `visualizar` filtra por `Nivel ubicacion != "MUNICIPIO"`. `etapas.generar_mapas` y `extraer_subconjunto` comprueban que la columna existe antes de dibujar.
- **Código eliminado.** `CENTROIDE_MEDELLIN` desaparece de `mapas.py` y de `geocodificacion.py`.

### D13. Tests sin red

- **`conftest.py`.**
  - Gana un `ClienteFalso`: se instala como `OpenCageGeocode`, devuelve respuestas `raw_response` guionizadas (con `rate`) o lanza las excepciones reales de `opencage.geocoder`, y registra los parámetros.
  - Un reloj falso sustituye a `time.monotonic` y `time.sleep` para comprobar la pausa sin esperar.
  - Se elimina `GeocodificadorFalso` y se conserva el bloqueo de la API real.
- **Geometría.** Los tests usan el GeoJSON real. Los puntos "a 120 m" o "a 2 km" de un barrio se construyen desplazando su punto representativo en EPSG:9377 y transformándolo a WGS84. Así no se fijan coordenadas inventadas.
- **Tests heredados.**
  - `test_mejora_barrio.py` se elimina con la mejora.
  - `test_geocodificacion.py` se reescribe para la sesión.
  - `test_mapas.py`, `test_cli.py`, `test_flujo_principal.py`, `test_etapas.py`, `test_credenciales.py` y `test_ejecucion.py` se adaptan a `ubicar` y al menú de 4 opciones.

### D14. Verificación con los datos reales sin gastar cuota

- **Ubicación sin consultas.** La implementación ejecuta `ubicar --sin-consultas` sobre una copia de `estandarizado/` en un directorio temporal fuera del repositorio. Usa una configuración temporal con puntos de municipio ficticios, porque los reales requieren consultar la API.
- **Lo que se comprueba**, solo con cifras agregadas:
  - registros por nivel (se esperan unos 546 BARRIO, 74 COMUNA y 86 + 257 MUNICIPIO);
  - todos `PENDIENTE` o `SIN_CONSULTA`;
  - ningún punto de BARRIO o COMUNA fuera de su polígono.
- **Primera ejecución con la API.** La hace el usuario (ver Migration Plan).

## Risks / Trade-offs

- **[La librería no tiene timeout: una petición colgada bloquea el proceso]** → Ctrl+C no pierde nada gracias a la caché. Si ocurre en la práctica, se escribe un adaptador con `requests` y timeout en un cambio aparte.
- **[`confianza_minima = 8` sin medir puede rechazar demasiado o aceptar puntos malos]** → La validación con el lugar declarado protege a los 620 registros con barrio o comuna. `comparar-consultas` informa la `confidence` para recalibrarla antes de la ubicación completa.
- **[El backoff de la librería puede reintentar un `UnknownError` durante hasta 120 s dentro de una sola llamada]** → Las esperas del backoff son de al menos 1 s y crecientes, así que no violan el ritmo. Si el error persiste, cuenta como uno de los 3 seguidos.
- **[La caché ignora los parámetros que no forman parte del texto]** → Esos parámetros están fijos en el código. El README indica borrar la caché si se cambian.
- **[El punto de un municipio puede ser un homónimo de otro departamento]** → `consultar-municipios` muestra el texto devuelto. El usuario lo revisa y lo corrige a mano en la configuración.
- **[Datos personales en la caché y el registro]** → Ambos están en `coordenadas/` (ignorado por git), el registro no guarda el texto de la consulta y los resúmenes solo muestran agregados.
- **[El archivo de coordenadas cambia de columnas y los análisis que lo lean deben adaptarse]** → `Latitud` y `Longitud` conservan su nombre y el archivo anterior se conserva con el sufijo `_anterior`.

## Migration Plan

1. Implementar y verificar sin cuota (tasks.md).
2. **Primera ejecución real, a cargo del usuario:**
   1. `python -m georef consultar-municipios` (10 peticiones) y revisar los 10 puntos;
   2. `python -m georef comparar-consultas --muestra 50` (hasta 100 peticiones) y elegir `formato_consulta` y, si hace falta, ajustar `confianza_minima`;
   3. `python -m georef ubicar` (unas 620 peticiones; si se interrumpe o se para, volver a ejecutar);
   4. `python -m georef mapas`.

   En total, unas 730 peticiones, dentro de las 2.500 diarias.
3. **Vuelta atrás:** volver al commit anterior y renombrar `coordenadas_area_metropolitana_anterior.xlsx` a su nombre original. La caché y el registro se pueden borrar sin consecuencias.

## Open Questions

- **Valores finales de `formato_consulta` y `confianza_minima`.** Se deciden con el resultado de `comparar-consultas` y solo cambian la configuración.
- **Si conviene activar la consulta con el lugar del complemento.** Se puede medir activándola en una ejecución y contando `ACEPTADA_LUGAR`.
