# Proyecto de Estandarización y Geocodificación de Direcciones

Este repositorio contiene el paquete de Python `georef/` (con `main.py` como punto de entrada heredado) que permite:

- **Estandarizar direcciones**: Normaliza y formatea direcciones en mayúsculas, aplica abreviaturas y separa la vía, el complemento, el barrio, la comuna y la zona (ver [Columnas de la estandarización](#columnas-de-la-estandarización)).
- **Ubicación por niveles**: Asigna a cada estudiante del área metropolitana el punto más preciso disponible (dirección validada con OpenCage, barrio, comuna o municipio) y deja constancia de esa precisión (ver [Columnas del archivo de coordenadas](#columnas-del-archivo-de-coordenadas)).
- **Generación de mapas interactivos**: Crea un mapa HTML con capas por nivel de ubicación, clusters, comunas y barrios de Medellín coloreados por cantidad, y mapas separados para compartir.
- **Subconjuntos**: Extrae las coordenadas y los mapas de una parte del área metropolitana (por ejemplo, Medellín) sin volver a usar la API.

Los municipios del área metropolitana, los subconjuntos y el vocabulario de direcciones están en `config/georef.toml` (ver [Configuración](#configuración)).

---

## Requisitos

- Python 3.12 (el código usa `match`, disponible desde Python 3.10).

### Usando conda (recomendado)

El archivo `environment.yml` declara el entorno `medellin-analysis312` con las versiones exactas:

```bash
conda env create -f environment.yml        # primera vez
conda env update -f environment.yml -n medellin-analysis312   # para actualizar uno existente
conda activate medellin-analysis312
```

### Usando pip

```bash
pip install pandas==3.0.6 folium==0.20.0 opencage==3.3.0 openpyxl==3.1.5 python-dotenv==1.2.4 geopandas==1.1.3 shapely==2.1.2 pyproj==3.7.2 jupyterlab==4.5.6 "pytest>=8" pdoc==16.0.0
```

`tkinter` no se instala con pip: viene con Python (en Linux puede requerir el paquete del sistema, por ejemplo `python3-tk`).

- `pandas`: manipulación de datos.
- `folium`: visualización de mapas.
- `opencage`: geocodificación de direcciones con la API de OpenCage.
- `openpyxl`: lectura y escritura de Excel.
- `python-dotenv`: lectura de la llave desde el archivo `.env`.
- `tkinter`: selección de archivos vía GUI.
- `geopandas`: análisis de los polígonos de barrios (notebooks).
- `shapely` y `pyproj`: polígonos de barrios y comunas, distancias y cambio de sistema de coordenadas en la ubicación por niveles.
- `jupyterlab`: entorno para abrir los notebooks.
- `pytest`: pruebas automáticas (solo desarrollo).
- `pdoc`: generación de la documentación de `docs/` (solo desarrollo).

### Pruebas

```bash
python -m pytest
```

## Estructura de Directorios

```
├── original/                # Carpeta para el archivo de entrada (solo un Excel)
├── estandarizado/           # Resultados de la estandarización de direcciones
│   ├── total_area_metropolitana.xlsx
│   ├── principales_area_metropolitana.xlsx
│   ├── especiales_area_metropolitana.xlsx
│   └── fuera_area_metropolitana.xlsx
├── coordenadas/             # Salida de la ubicación por niveles
│   ├── coordenadas_area_metropolitana.xlsx
│   ├── coordenadas_<subconjunto>.xlsx      # p. ej. coordenadas_medellin.xlsx
│   ├── cache_consultas.csv  # Respuestas de OpenCage (evita repetir peticiones)
│   └── registro_consultas.csv              # Diagnóstico de cada petición
├── mapas/                   # Mapas HTML generados, una carpeta por área
│   ├── area_metropolitana/
│   │   ├── mapa.html        # Mapa con todas las capas
│   │   └── separados/       # Solo si se piden: puntos.html, clusters.html, barrios_cantidad.html...
│   └── <subconjunto>/       # Misma estructura
├── data/                    # Datos de referencia versionados
│   ├── limite_barrio_vereda_cata.geojson   # Polígonos oficiales de barrios y veredas de Medellín
│   ├── alias_barrios.csv    # Variantes de nombres de barrio -> código oficial (revisada a mano)
│   ├── alias_comunas.csv    # Variantes que designan una comuna completa (POBLADO, RODEO...)
│   └── README.md            # Procedencia y significado de los campos
├── notebooks/               # Análisis exploratorios (versionados sin salidas)
│   ├── exploracion_geojson.ipynb
│   └── hallazgos_geojson.md # Cifras agregadas y recomendaciones
├── config/
│   └── georef.toml          # Configuración: municipios, subconjuntos, columnas, vocabulario y ubicación
├── georef/                  # Código del programa
│   ├── cli.py               # Subcomandos y menú interactivo
│   ├── config.py            # Carga y validación de la configuración
│   ├── etapas.py            # Una función por etapa (lee y escribe archivos)
│   ├── archivos.py          # Rutas de trabajo y archivo de entrada
│   ├── direcciones.py       # Separación por área y normalización de direcciones
│   ├── referencia.py        # Índice de barrios y comunas (GeoJSON y tablas de alias)
│   ├── geocodificacion.py   # Llave, texto de las consultas y sesión de consultas a OpenCage
│   ├── geografia.py         # Polígonos de barrios, comunas y municipio (shapely y pyproj)
│   ├── ubicacion.py         # Cascada de niveles DIRECCION, BARRIO, COMUNA y MUNICIPIO
│   └── mapas.py             # Mapas con folium
├── docs/                    # Documentación HTML generada con pdoc
├── tests/                   # Pruebas automáticas (pytest)
├── .env.example             # Plantilla para el archivo .env con la llave de OpenCage
└── main.py                  # Punto de entrada heredado (equivale a python -m georef)
```

Las carpetas de datos (`original/`, `estandarizado/`, `coordenadas/`, `mapas/`) contienen datos personales y, junto con el archivo `.env` (que contiene la llave), están excluidas de git mediante `.gitignore`.

### Migración desde versiones anteriores

- **Archivo de coordenadas.** `coordenadas/coordenadas.xlsx` pasó a llamarse `coordenadas/coordenadas_area_metropolitana.xlsx`. Renómbralo una vez; **no es necesario volver a geocodificar**:
  ```bash
  mv coordenadas/coordenadas.xlsx coordenadas/coordenadas_area_metropolitana.xlsx
  ```
  Mientras solo exista el nombre antiguo, la ubicación, los mapas y los subconjuntos se detienen con un aviso, sin llamar a la API. Así no se vuelve a geocodificar todo por error.
- **Mapas.** Ahora se genera un solo `mapas/<area>/mapa.html` con capas (ver [Mapas](#mapas)) y, si se piden, mapas separados en `mapas/<area>/separados/`. Ya no se generan `individual.html`, `clusters.html` ni la carpeta `filtrados/`: la capa de cada nivel se puede apagar en el mapa, y `--sin-municipio` quita el nivel MUNICIPIO de los separados. El programa avisa de los HTML anteriores que encuentre, pero no los borra: bórralos a mano, igual que los que queden directamente en `mapas/`.
- **Ubicación por niveles.** La conversión de coordenadas (`geocodificar`) pasó a ser `ubicar`, y la mejora de coordenadas (`mejorar`, antigua opción 3 del menú) desapareció: la ubicación ya usa el barrio declarado. El archivo de coordenadas cambia de columnas e incluye los registros especiales. La primera vez que ejecutes `ubicar`, el archivo anterior se conserva como `coordenadas/coordenadas_area_metropolitana_anterior.xlsx`. Antes, añade los puntos de los municipios (ver [Primera ubicación](#primera-ubicación)).
- **Estandarización.** Los archivos de `estandarizado/` se llamaban antes `*_área_metropolitana.xlsx` (con tilde) y ya no se leen. Renómbralos a `*_area_metropolitana.xlsx` o vuelve a ejecutar la estandarización, que no consume la API.


## Llave de la API de OpenCage

La ubicación (`ubicar`), `consultar-municipios` y `comparar-consultas` leen la llave de la variable `OPENCAGE_API_KEY`. El programa la busca primero en las variables de entorno y, si no la encuentra, en el archivo `.env` de la carpeta desde la que se ejecuta (la raíz del proyecto). Nunca la guarda en archivos ni la pide por consola; si falta, termina con un mensaje que explica cómo definirla. La estandarización, `ubicar --sin-consultas`, la generación de mapas y los subconjuntos funcionan sin ella.

### Opción recomendada: archivo `.env`

```bash
cp .env.example .env
chmod 600 .env        # solo tu usuario puede leerlo
```

Abre `.env` con un editor y escribe la llave después del `=`:

```
OPENCAGE_API_KEY=tu-llave
```

`.env` está en `.gitignore`, así que no se sube al repositorio. Es texto plano: no lo compartas ni lo copies fuera del proyecto. Funciona igual desde la terminal y desde PyCharm, siempre que el directorio de trabajo de la ejecución sea la raíz del proyecto (el valor por defecto).

### Alternativa: variable de entorno

Si `OPENCAGE_API_KEY` está definida en el entorno, tiene prioridad sobre `.env`.

- En la sesión actual de la terminal: `export OPENCAGE_API_KEY=<tu-llave>`
- De forma persistente en el entorno conda: `conda env config vars set OPENCAGE_API_KEY=<tu-llave> -n medellin-analysis312` y reactivar el entorno.
- En PyCharm: *Run > Edit Configurations… > Environment variables*.

> Versiones anteriores guardaban la llave en `llave/llave.txt`. Ese archivo ya no se usa: pasa la llave a `.env` y borra la carpeta `llave/`.

## Uso

Ejecuta el programa desde la raíz del repositorio con el entorno activado. Al arrancar lee y valida `config/georef.toml` y crea las carpetas de trabajo (`original/`, `estandarizado/`, `coordenadas/`, `mapas/`) si no existen.

### Menú interactivo

```bash
python -m georef        # o, como hasta ahora: python main.py
```

Verás un menú con 4 opciones:
1. Estandarización de direcciones. Si `original/` está vacía, se abre un diálogo para elegir el archivo Excel.
2. Ubicación por niveles (coordenadas).
3. Generación de mapas.
4. Extracción de un subconjunto: lista los subconjuntos configurados y pide elegir uno.

Las opciones 3 y 4 preguntan además qué mapas separados generar (por ejemplo `puntos, clusters`; Enter para ninguno) y, si se pide alguno, si se quita el nivel MUNICIPIO de los separados de puntos y clusters.

Los diagnósticos (`consultar-municipios` y `comparar-consultas`) solo están disponibles como subcomandos.

### Subcomandos

Cada subcomando ejecuta una sola etapa, sin menú ni preguntas (útil para scripts):

```bash
python -m georef estandarizar                  # original/ -> estandarizado/
python -m georef ubicar                        # -> coordenadas/coordenadas_area_metropolitana.xlsx
python -m georef ubicar --sin-consultas        # igual, sin peticiones ni llave: solo usa la caché
python -m georef mapas                         # -> mapas/area_metropolitana/mapa.html
python -m georef mapas --separado puntos --separado comunas_cantidad   # además, separados/puntos.html y comunas_cantidad.html
python -m georef mapas --separado todos --sin-municipio                # todos los separados; puntos y clusters sin MUNICIPIO
python -m georef subconjunto --area medellin   # -> coordenadas/coordenadas_medellin.xlsx y mapas/medellin/mapa.html
python -m georef subconjunto --area medellin --separado puntos         # además, mapas/medellin/separados/puntos.html
python -m georef consultar-municipios          # puntos de los municipios -> config/georef.toml
python -m georef comparar-consultas --muestra 50   # compara los dos formatos de consulta
python -m georef ver-mapas                     # abre mapa.html en el navegador con el fondo del mapa
python -m georef ver-mapas --area medellin     # abre mapas/medellin/mapa.html
python -m georef --help                        # lista los subcomandos
```

- `python main.py <subcomando>` funciona igual, y `python main.py c` ejecuta la ubicación (`ubicar`) sin menú.
- `--config <ruta>` (antes del subcomando) usa otro archivo de configuración: `python -m georef --config otra.toml estandarizar`.
- `estandarizar` no abre el diálogo: si `original/` está vacía, termina con un mensaje.
- `original/` debe contener un único archivo. Los archivos ocultos y los de bloqueo que crean LibreOffice o Excel mientras el archivo está abierto se ignoran.

### Áreas y salidas

- Solo los registros del **área metropolitana** (de vía principal y especiales) se ubican. Los demás se exportan únicamente a `estandarizado/fuera_area_metropolitana.xlsx`.
- Un **subconjunto** filtra `coordenadas_area_metropolitana.xlsx` por municipio y escribe `coordenadas/coordenadas_<nombre>.xlsx` (mismas columnas y mismo índice) y los mapas en `mapas/<nombre>/`, con las mismas opciones `--separado` y `--sin-municipio` que `mapas`. No llama a la API ni necesita la llave, así que no gasta cuota.

### Columnas del archivo de coordenadas

`ubicar` escribe de nuevo, en cada ejecución, `coordenadas/coordenadas_area_metropolitana.xlsx` con todos los registros del área metropolitana (de vía principal y especiales), sus columnas de `estandarizado/` y, tras `Zona`, estas columnas:

| Columna | Contenido |
|---|---|
| `Latitud`, `Longitud` | Punto asignado (WGS84). |
| `Nivel ubicacion` | Precisión del punto: `DIRECCION`, `BARRIO`, `COMUNA` o `MUNICIPIO` (ver abajo). |
| `Resultado consulta` | Qué pasó con la consulta a OpenCage: `ACEPTADA`, `ACEPTADA_LUGAR` (segunda consulta con el lugar del complemento), `SIN_RESULTADO`, `PRECISION_INSUFICIENTE`, `FUERA_DEL_MUNICIPIO`, `LEJOS_DEL_LUGAR_DECLARADO`, `PENDIENTE` (no se pudo consultar; se reintenta en la siguiente ejecución) o `SIN_CONSULTA` (otros municipios y registros especiales). |
| `Barrio ubicacion`, `Codigo barrio ubicacion`, `Comuna ubicacion` | Polígono oficial de Medellín donde cae el punto asignado (solo el barrio o la comuna que correspondan a su nivel). |

Cada registro recibe el primer nivel disponible:
1. **`DIRECCION`**: solo vías principales de Medellín. Se acepta el punto de OpenCage si su tipo no es de ciudad o superior, su `confidence` llega a `confianza_minima`, cae en Medellín y está a `tolerancia_metros` (250 m) o menos del barrio declarado (o, si no hay barrio, de la comuna declarada). Si está más lejos, **prevalece lo que declaró el estudiante**.
2. **`BARRIO`**: punto representativo del polígono del barrio declarado (siempre cae dentro del polígono, a diferencia del centroide).
3. **`COMUNA`**: punto representativo de la comuna declarada.
4. **`MUNICIPIO`**: punto del municipio en `[puntos_municipios]`. Es el único nivel de los otros 9 municipios, que nunca se consultan a OpenCage.

Los metadatos de OpenCage (`confidence`, tipo, texto devuelto) no van al Excel: quedan en la caché. Al terminar, `ubicar` muestra un resumen con cifras agregadas: registros por nivel y por resultado, peticiones hechas, consultas resueltas desde la caché y pendientes.

### Primera ubicación

Con el free trial de OpenCage (2.500 peticiones al día), el orden recomendado es:

1. `python -m georef consultar-municipios`: consulta una vez los 10 municipios (10 peticiones) y añade sus puntos a `config/georef.toml`. Revisa los puntos que muestra: si alguno es de un municipio homónimo de otro departamento, corrígelo a mano.
2. `python -m georef comparar-consultas --muestra 50`: toma siempre la misma muestra de hasta 50 direcciones distintas de Medellín con barrio declarado y consulta cada una en los dos formatos (hasta 100 peticiones; repetir el comando no gasta cuota). Para cada formato muestra solo cifras agregadas: consultas con resultado, tipos de resultado, `confidence` mediana, porcentaje de puntos dentro del barrio declarado y a `tolerancia_metros` o menos, distancia mediana y cuántos se aceptarían con la configuración actual. Con eso, elige `formato_consulta` y, si hace falta, `confianza_minima` en `[ubicacion]`.
3. `python -m georef ubicar`: unas 620 peticiones, con al menos 1 segundo entre una y otra. Mientras trabaja muestra una línea de avance (`Registro 312 de 963 · peticiones a OpenCage: 140 · …`) y al final un resumen por nivel. Si se para (cuota, errores o límite), vuelve a ejecutarlo: continúa donde se quedó.
4. `python -m georef mapas`.

### Caché y registro de las consultas a OpenCage

Las operaciones que consultan a OpenCage escriben dos archivos en `coordenadas/` (ignorada por git, porque contienen direcciones):

- **`cache_consultas.csv`**: una línea por consulta respondida (con o sin resultado): el texto de la consulta, el punto, la `confidence`, el tipo y el texto que devolvió OpenCage. Una consulta que ya está en la caché **nunca se repite**, así que volver a ejecutar no gasta cuota en lo ya consultado, y dos estudiantes con la misma dirección comparten una sola petición. Las peticiones que fallan no se guardan y se reintentan en la siguiente ejecución.
- **`registro_consultas.csv`**: una línea por petición, para diagnosticar fallos: hora (UTC), operación, número de fila del registro (o municipio), duración, resultado o nombre del error, peticiones restantes del día si OpenCage las informa, tipo y `confidence`. No guarda el texto de la consulta ni la llave.

Entre dos peticiones pasa al menos `pausa_segundos`, también después de un error. Si OpenCage indica cuota o ritmo excedidos, tras 3 errores seguidos o al llegar a `limite_consultas`, el programa deja de consultar sin perder nada: lo que falte queda pendiente para la siguiente ejecución (la cuota del free trial se renueva a las 19:00 de Colombia).

**Cuándo borrar la caché:** solo si cambian parámetros de las peticiones que no forman parte del texto de la consulta (en el código: país, número de resultados o recuadro de Medellín). Cambiar `formato_consulta` no lo requiere, porque el texto de la consulta ya es distinto. Borrarla obliga a repetir todas las peticiones.

### Mapas

`python -m georef mapas` (opción 3 del menú) escribe `mapas/area_metropolitana/mapa.html` a partir del archivo de coordenadas, sin consultar a OpenCage. Para verlo, usa `python -m georef ver-mapas` (ver más abajo). El panel de la esquina superior derecha activa y desactiva cada capa, y el mapa se abre encuadrado en los datos.

**Cómo abrir los mapas.** El fondo del mapa (calles, ríos, nombres) son imágenes de los servidores de OpenStreetMap. Su [política de uso](https://operations.osmfoundation.org/policies/tiles/) exige que el navegador indique desde qué página se piden (la cabecera `Referer`), y un archivo abierto con doble clic (`file://...`) no lo indica. Por eso, abierto así, el fondo aparece como "Access blocked" (los puntos y polígonos sí se ven). Para verlo completo:

```bash
python -m georef ver-mapas                    # o: --area medellin
```

sirve la carpeta `mapas/` solo en tu equipo (`http://127.0.0.1:<puerto>/`, con un puerto libre que elige el sistema) y abre el mapa en el navegador. Mientras el comando siga en marcha puedes abrir también los separados cambiando la dirección (por ejemplo `.../area_metropolitana/separados/puntos.html`). Pulsa Ctrl+C para terminar.

| Capa | Al abrir | Qué muestra |
|------|----------|-------------|
| `DIRECCION`, `BARRIO`, `COMUNA`, `MUNICIPIO` | visibles | Un círculo por punto, del color de su nivel: verde (dirección), azul (barrio), naranja (comuna), gris (municipio). |
| Clusters / Clusters sin MUNICIPIO | ocultas | Agrupaciones de registros que se dividen al acercarse. |
| Contorno de comunas | visible | Límites de las comunas y corregimientos de Medellín, con su nombre al pasar el ratón. |
| Contorno de barrios | oculta | Límites de los barrios y veredas de Medellín. |
| Barrios por cantidad / Comunas por cantidad | ocultas | Cada barrio o comuna coloreado según cuántos registros se ubicaron en él (gris: ninguno), con su escala. |

- **El número de un círculo** indica cuántos registros comparten exactamente ese punto. En los niveles BARRIO, COMUNA y MUNICIPIO todos los registros del mismo lugar reciben el mismo punto (el de su barrio, comuna o municipio, no el de su casa), así que un círculo con un 9 son 9 estudiantes de ese barrio. El tamaño del círculo crece con el número hasta un máximo.
- **Al hacer clic en un círculo** se ve el nivel, el municipio, el barrio y la comuna de ubicación, cuántos registros hay y su resultado de consulta. Nunca se muestran la dirección ni otros datos del estudiante.
- **Barrios y comunas por cantidad** cuentan los registros cuyo barrio de ubicación (niveles DIRECCION y BARRIO) o comuna de ubicación (DIRECCION, BARRIO y COMUNA) es ese polígono. Los registros de nivel MUNICIPIO no cuentan en ninguno. Las escalas de estas dos capas se ven aunque la capa esté apagada.
- Las capas de comunas y barrios solo existen en las áreas que incluyen Medellín (el municipio con polígonos de la configuración).

**Mapas separados.** Para compartir un solo archivo, `--separado <vista>` (se puede repetir) escribe además `mapas/<area>/separados/<vista>.html`:

| Vista | Archivo | Contenido |
|-------|---------|-----------|
| `puntos` | `puntos.html` | Las capas de nivel con su leyenda y el contorno de las comunas. |
| `clusters` | `clusters.html` | Los clusters de todos los registros y el contorno de las comunas. |
| `barrios_cantidad` | `barrios_cantidad.html` | Barrios de Medellín coloreados por cantidad. |
| `comunas_cantidad` | `comunas_cantidad.html` | Comunas de Medellín coloreadas por cantidad. |
| `todos` | — | Todas las vistas disponibles para el área. |

Con `--sin-municipio`, los separados de puntos y clusters excluyen el nivel MUNICIPIO y se llaman `puntos_sin_municipio.html` y `clusters_sin_municipio.html`; la opción no cambia `mapa.html` ni las vistas coloreadas. Las vistas coloreadas solo se pueden pedir para un área que incluya Medellín (con `todos`, en otra área simplemente se omiten). Los separados de ejecuciones anteriores no se borran.

Quien reciba un HTML suelto y no tenga este programa puede verlo con el fondo usando solo Python, desde la carpeta donde guardó el archivo:

```bash
python -m http.server 8000 --bind 127.0.0.1 --directory .
```

y abriendo `http://127.0.0.1:8000/<nombre del archivo>.html`.

> **Antes de compartir un mapa:** los puntos de nivel DIRECCION son la ubicación aproximada de la vivienda de un estudiante, aunque el mapa no muestre su nombre ni su dirección. `--sin-municipio` quita los puntos menos precisos, pero no anonimiza. Para compartir sin ubicaciones individuales, usa los mapas coloreados (`barrios_cantidad` o `comunas_cantidad`).

### Columnas de la estandarización

Los cuatro archivos de `estandarizado/` conservan las columnas del archivo de entrada y su número de fila como índice. La dirección se divide en estas columnas, seguidas:

| Columna | Contenido | Ejemplo |
|---|---|---|
| `Direccion de residencia` | Vía y numeración con formato. Vacía si el texto no empieza por una vía (veredas, fincas…). | `CL 45S #12-15` |
| `Complemento` | Datos de vivienda y lugares con nombre, con las palabras originales. Si no se reconoce barrio ni comuna, todo el texto queda aquí. | `APARTAMENTO 301` |
| `Barrio` | Nombre oficial del barrio o la vereda (solo Medellín). | `Buenos Aires` |
| `Codigo barrio` | `codigo` del polígono en el GeoJSON, como texto. Vacío si el nombre es ambiguo. | `0907` |
| `Comuna` | Comuna o corregimiento del barrio, o el que nombra el estudiante cuando no da barrio. | `BUENOS AIRES` |
| `Zona` | `URBANO` o `RURAL`, tomada de lo que sigue a `-*-`. | `URBANO` |

Para conservar los ceros de `Codigo barrio` al leer los Excel con pandas, hay que indicar su tipo:

```python
pd.read_excel("estandarizado/principales_area_metropolitana.xlsx", index_col=0, dtype={"Codigo barrio": str})
```

El barrio se reconoce como el nombre más largo que coincide con el final del texto (nombres oficiales, `data/alias_barrios.csv`, comunas sin barrio homónimo y `data/alias_comunas.csv`). Los nombres repetidos se resuelven con la zona. Las palabras que no se reconocen nunca se pierden: quedan en `Complemento`.

## Configuración

`config/georef.toml` contiene los valores del dominio, con comentarios que explican cada sección:

| Sección | Contenido |
|---|---|
| `[area_metropolitana]` | `municipios`: los que se estandarizan y ubican. |
| `[subconjuntos.<nombre>]` | `municipios` de cada subconjunto; deben estar en el área metropolitana. |
| `[columnas]` | Nombres de las columnas de ciudad y dirección del archivo de entrada. |
| `[direcciones]` | `tipos_via`, `palabras_clave` y `equivalencias` de la estandarización. |
| `[referencia]` | Rutas del GeoJSON y de las tablas de alias, y el municipio con polígonos de barrio (`MEDELLIN - ANTIOQUIA`). |
| `[ubicacion]` | Parámetros de la ubicación por niveles y de las consultas a OpenCage (ver la tabla siguiente). |
| `[puntos_municipios]` | Punto fijo de cada municipio del área metropolitana (nivel MUNICIPIO). No viene incluida: la añade `python -m georef consultar-municipios`. |

Claves de `[ubicacion]`:

| Clave | Valor incluido | Para qué sirve |
|---|---|---|
| `formato_consulta` | `"abreviado"` | Texto de la consulta: `abreviado` (`CL 10 #20-30, MEDELLIN, ANTIOQUIA, Colombia`) o `expandido` (`Calle 10 # 20-30, ...`). |
| `confianza_minima` | `8` | `confidence` mínima (0 a 10) de un punto de OpenCage. Provisional: recalíbrala con `comparar-consultas`. |
| `tipos_rechazados` | `["city", "county", "state", "country"]` | Tipos de resultado de OpenCage que nunca se aceptan. |
| `tolerancia_metros` | `250` | Distancia máxima del punto a Medellín y al barrio (o comuna) declarado. Más lejos, prevalece lo declarado. |
| `pausa_segundos` | `1` | Tiempo mínimo entre el inicio de dos peticiones. |
| `limite_consultas` | `1000` | Máximo de peticiones por ejecución; las que falten quedan pendientes para la siguiente. |
| `consulta_lugar_complemento` | `false` | Segunda consulta con el lugar con nombre del complemento (`UNIDAD LOS PINOS, LAURELES, ...`). |
| `palabras_lugar` | `["UNIDAD", "EDIFICIO", ...]` | Palabras con las que empieza un lugar con nombre en el complemento. |
| `nombres_via` | `{ CL = "Calle", ... }` | Nombre completo de cada tipo de vía para el formato `expandido`. Debe tener uno por cada `tipos_via`. |

Cada municipio de `[puntos_municipios]` es una línea con su procedencia, que puedes corregir a mano:

```toml
[puntos_municipios]
# Formato de cada línea (los números son de ejemplo, no son el punto real de Bello):
"BELLO - ANTIOQUIA" = { latitud = 6.0, longitud = -75.0, fuente = "OpenCage", fecha = "2026-10-12" }
```

- **Añadir un municipio:** agrégalo a `municipios` de `[area_metropolitana]`, escrito **exactamente** como aparece en la columna de ciudad del archivo de entrada (por ejemplo `"RIONEGRO - ANTIOQUIA"`). Un municipio mal escrito no da error, pero no coincide con ningún registro.
- **Añadir un subconjunto:**
  ```toml
  [subconjuntos.sur]
  municipios = ["ENVIGADO - ANTIOQUIA", "SABANETA - ANTIOQUIA"]
  ```
  El nombre solo puede tener minúsculas sin tildes, dígitos y guiones bajos, porque forma parte de los nombres de archivo. Después: `python -m georef subconjunto --area sur`.
- **Equivalencias:** se aplican solo a **palabras completas** de la vía y la numeración (`CALLE` → `CL`, `NORTE` → `N`, también en `CALLE31A` o `SUR-15`), nunca dentro de otras palabras (`URBANO`, `SURAMERICA`) ni al complemento o al barrio. El orden de la lista no importa.
- **Validación:** si hay errores (una clave desconocida, una lista vacía, un valor repetido, un subconjunto con un municipio fuera del área…), el programa termina antes de leer datos o llamar a la API y muestra todos los errores juntos, cada uno con su clave.

## Notebooks de análisis

`notebooks/exploracion_geojson.ipynb` analiza el GeoJSON de barrios y mide cuántos barrios declarados coinciden con los oficiales. Ábrelo desde la raíz del repositorio con el entorno activado (la reproyección necesita la base de datos de PROJ que configura `conda activate`):

```bash
conda activate medellin-analysis312 && jupyter lab
```

Las secciones 5 a 8 leen `original/` y `coordenadas/coordenadas_area_metropolitana.xlsx`, que contienen datos personales. **Antes de cada commit** limpia las salidas; el test `tests/test_notebooks_sin_salidas.py` falla si se te olvida:

```bash
jupyter nbconvert --clear-output --inplace notebooks/exploracion_geojson.ipynb
```

## Documentación

Puedes consultar la documentación completa del proyecto en el siguiente enlace:

🔗 [Documentación del paquete `georef`](https://felipe1727.github.io/Georreferenciacion-Area-Metropolitana/)

Se genera con pdoc a partir de los docstrings del paquete. Para regenerarla tras cambiar el código:

```bash
pdoc georef -o docs
```
