# Proyecto de Estandarización y Geocodificación de Direcciones

Este repositorio contiene el paquete de Python `georef/` (con `main.py` como punto de entrada heredado) que permite:

- **Estandarizar direcciones**: Normaliza y formatea direcciones en mayúsculas, aplica abreviaturas y separa complementos.
- **Conversión de coordenadas**: Obtiene latitud y longitud de cada dirección del área metropolitana usando la API de OpenCage Geocode.
- **Mejora de coordenadas**: Rellena coordenadas faltantes basándose en áreas o barrios.
- **Generación de mapas interactivos**: Crea mapas HTML con marcadores individuales y clusters.
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
pip install pandas==3.0.6 folium==0.20.0 opencage==3.3.0 openpyxl==3.1.5 python-dotenv==1.2.4 geopandas==1.1.3 jupyterlab==4.5.6 "pytest>=8" pdoc==16.0.0
```

`tkinter` no se instala con pip: viene con Python (en Linux puede requerir el paquete del sistema, por ejemplo `python3-tk`).

- `pandas`: manipulación de datos.
- `folium`: visualización de mapas.
- `opencage`: geocodificación de direcciones con la API de OpenCage.
- `openpyxl`: lectura y escritura de Excel.
- `python-dotenv`: lectura de la llave desde el archivo `.env`.
- `tkinter`: selección de archivos vía GUI.
- `geopandas`: análisis de los polígonos de barrios (notebooks).
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
├── coordenadas/             # Salida con coordenadas obtenidas y mejoradas
│   ├── coordenadas_area_metropolitana.xlsx
│   └── coordenadas_<subconjunto>.xlsx      # p. ej. coordenadas_medellin.xlsx
├── mapas/                   # Mapas HTML generados, una carpeta por área
│   ├── area_metropolitana/
│   │   ├── individual.html, clusters.html
│   │   └── filtrados/       # Sin los puntos en el centroide de Medellín
│   └── <subconjunto>/       # Misma estructura
├── data/                    # Datos de referencia versionados
│   ├── limite_barrio_vereda_cata.geojson   # Polígonos oficiales de barrios y veredas de Medellín
│   ├── alias_barrios.csv    # Variantes de nombres de barrio -> código oficial (revisada a mano)
│   └── README.md            # Procedencia y significado de los campos
├── notebooks/               # Análisis exploratorios (versionados sin salidas)
│   ├── exploracion_geojson.ipynb
│   └── hallazgos_geojson.md # Cifras agregadas y recomendaciones
├── config/
│   └── georef.toml          # Configuración: municipios, subconjuntos, columnas y vocabulario
├── georef/                  # Código del programa
│   ├── cli.py               # Subcomandos y menú interactivo
│   ├── config.py            # Carga y validación de la configuración
│   ├── etapas.py            # Una función por etapa (lee y escribe archivos)
│   ├── archivos.py          # Rutas de trabajo y archivo de entrada
│   ├── direcciones.py       # Separación por área y estandarización
│   ├── geocodificacion.py   # Llave y consultas a OpenCage
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
  Mientras solo exista el nombre antiguo, la conversión, la mejora, los mapas y los subconjuntos se detienen con un aviso, sin llamar a la API. Así no se vuelve a geocodificar todo por error.
- **Mapas.** Ahora se generan en `mapas/area_metropolitana/`. Vuelve a generarlos con `python -m georef mapas`; los HTML antiguos de `mapas/` y `mapas/filtrados/` se pueden borrar.
- **Estandarización.** Los archivos de `estandarizado/` se llamaban antes `*_área_metropolitana.xlsx` (con tilde) y ya no se leen. Renómbralos a `*_area_metropolitana.xlsx` o vuelve a ejecutar la estandarización, que no consume la API.


## Llave de la API de OpenCage

La conversión y la mejora de coordenadas leen la llave de la variable `OPENCAGE_API_KEY`. El programa la busca primero en las variables de entorno y, si no la encuentra, en el archivo `.env` de la carpeta desde la que se ejecuta (la raíz del proyecto). Nunca la guarda en archivos ni la pide por consola; si falta, termina con un mensaje que explica cómo definirla. La estandarización, la generación de mapas y los subconjuntos funcionan sin ella.

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

Verás un menú con 5 opciones:
1. Estandarización de direcciones. Si `original/` está vacía, se abre un diálogo para elegir el archivo Excel.
2. Conversión de coordenadas.
3. Mejora de coordenadas (requiere haber corrido la conversión primero).
4. Generación de mapas.
5. Extracción de un subconjunto: lista los subconjuntos configurados y pide elegir uno.

### Subcomandos

Cada subcomando ejecuta una sola etapa, sin menú ni preguntas (útil para scripts):

```bash
python -m georef estandarizar                  # original/ -> estandarizado/
python -m georef geocodificar                  # -> coordenadas/coordenadas_area_metropolitana.xlsx
python -m georef mejorar                       # mejora por barrio sobre ese mismo archivo
python -m georef mapas                         # -> mapas/area_metropolitana/
python -m georef subconjunto --area medellin   # -> coordenadas/coordenadas_medellin.xlsx y mapas/medellin/
python -m georef --help                        # lista los subcomandos
```

- `python main.py <subcomando>` funciona igual, y `python main.py c` sigue siendo la conversión de coordenadas sin menú.
- `--config <ruta>` (antes del subcomando) usa otro archivo de configuración: `python -m georef --config otra.toml estandarizar`.
- `estandarizar` no abre el diálogo: si `original/` está vacía, termina con un mensaje.
- `original/` debe contener un único archivo. Los archivos ocultos y los de bloqueo que crean LibreOffice o Excel mientras el archivo está abierto se ignoran.

### Áreas y salidas

- Solo los registros del **área metropolitana** se estandarizan y geocodifican. Los demás se exportan únicamente a `estandarizado/fuera_area_metropolitana.xlsx`.
- Un **subconjunto** filtra `coordenadas_area_metropolitana.xlsx` por municipio y escribe `coordenadas/coordenadas_<nombre>.xlsx` (mismas columnas y mismo índice) y los mapas en `mapas/<nombre>/`. No llama a la API ni necesita la llave, así que no gasta cuota.

## Configuración

`config/georef.toml` contiene los valores del dominio, con comentarios que explican cada sección:

| Sección | Contenido |
|---|---|
| `[area_metropolitana]` | `municipios`: los que se estandarizan y geocodifican. |
| `[subconjuntos.<nombre>]` | `municipios` de cada subconjunto; deben estar en el área metropolitana. |
| `[columnas]` | Nombres de las columnas de ciudad y dirección del archivo de entrada. |
| `[direcciones]` | `tipos_via`, `palabras_clave` y `equivalencias` de la estandarización. |

- **Añadir un municipio:** agrégalo a `municipios` de `[area_metropolitana]`, escrito **exactamente** como aparece en la columna de ciudad del archivo de entrada (por ejemplo `"RIONEGRO - ANTIOQUIA"`). Un municipio mal escrito no da error, pero no coincide con ningún registro.
- **Añadir un subconjunto:**
  ```toml
  [subconjuntos.sur]
  municipios = ["ENVIGADO - ANTIOQUIA", "SABANETA - ANTIOQUIA"]
  ```
  El nombre solo puede tener minúsculas sin tildes, dígitos y guiones bajos, porque forma parte de los nombres de archivo. Después: `python -m georef subconjunto --area sur`.
- **Equivalencias:** se aplican **en el orden del archivo** y por subcadena (también dentro de otras palabras), así que cambiar el orden cambia el resultado. Es el comportamiento heredado; se corregirá en el cambio `ubicacion-por-niveles`.
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
