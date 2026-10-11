# Proyecto de Estandarización y Geocodificación de Direcciones

Este repositorio contiene un script en Python (`main.py`) que permite:

- **Estandarizar direcciones**: Normaliza y formatea direcciones en mayúsculas, aplica abreviaturas y separa complementos.
- **Conversión de coordenadas**: Obtiene latitud y longitud de cada dirección usando la API de OpenCage Geocode.
- **Mejora de coordenadas**: Rellena coordenadas faltantes basándose en áreas o barrios.
- **Generación de mapas interactivos**: Crea mapas HTML con marcadores individuales y clusters.

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
pip install pandas==3.0.6 folium==0.20.0 opencage==3.3.0 openpyxl==3.1.5 python-dotenv==1.2.4 geopandas==1.1.3 jupyterlab==4.5.6 "pytest>=8"
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
│   └── coordenadas.xlsx
├── mapas/                   # Mapas HTML generados
│   └── filtrados/           # Mapas con coordenadas filtradas
├── data/                    # Datos de referencia versionados
│   ├── limite_barrio_vereda_cata.geojson   # Polígonos oficiales de barrios y veredas de Medellín
│   ├── alias_barrios.csv    # Variantes de nombres de barrio -> código oficial (revisada a mano)
│   └── README.md            # Procedencia y significado de los campos
├── notebooks/               # Análisis exploratorios (versionados sin salidas)
│   ├── exploracion_geojson.ipynb
│   └── hallazgos_geojson.md # Cifras agregadas y recomendaciones
├── tests/                   # Pruebas automáticas (pytest)
├── .env.example             # Plantilla para el archivo .env con la llave de OpenCage
└── main.py                  # Script principal
```

Las carpetas de datos (`original/`, `estandarizado/`, `coordenadas/`, `mapas/`) contienen datos personales y, junto con el archivo `.env` (que contiene la llave), están excluidas de git mediante `.gitignore`.

### Migración desde versiones anteriores

Los archivos de `estandarizado/` se llamaban antes `*_área_metropolitana.xlsx` (con tilde) y ya no se leen. Puedes renombrarlos a `*_area_metropolitana.xlsx` o volver a ejecutar la opción 1 (estandarización), que no consume la API. `coordenadas/coordenadas.xlsx` conserva su nombre, así que **no es necesario volver a geocodificar**.


## Llave de la API de OpenCage

La conversión y la mejora de coordenadas leen la llave de la variable `OPENCAGE_API_KEY`. El programa la busca primero en las variables de entorno y, si no la encuentra, en el archivo `.env` de la carpeta desde la que se ejecuta (la raíz del proyecto). Nunca la guarda en archivos ni la pide por consola; si falta, termina con un mensaje que explica cómo definirla. La estandarización y la generación de mapas funcionan sin ella.

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

El script crea automáticamente la estructura de carpetas y permite seleccionar el archivo de direcciones en tiempo de ejecución; **no es necesario** configurar previamente un entorno virtual ni copiar manualmente el archivo de entrada.

1. **Ejecutar el script**
   ```bash
   python main.py
   ```
   - Si la carpeta `original/` está vacía, se abrirá un diálogo para elegir el archivo Excel con las direcciones.
   - El entorno (carpetas `original/`, `estandarizado/`, `coordenadas/`, `mapas/`, etc.) se genera automáticamente.
   - Verás un menú con 4 opciones:
     1. Estandarización de direcciones.
     2. Conversión de coordenadas.
     3. Mejora de coordenadas (requiere haber corrido la opción de conversión primero).
     4. Generación de mapas.

3. **Salida**
   - Archivos Excel en `estandarizado/` y `coordenadas/`.
   - Mapas HTML en `mapas/` y `mapas/filtrados/`.

## Notebooks de análisis

`notebooks/exploracion_geojson.ipynb` analiza el GeoJSON de barrios y mide cuántos barrios declarados coinciden con los oficiales. Ábrelo desde la raíz del repositorio con el entorno activado (la reproyección necesita la base de datos de PROJ que configura `conda activate`):

```bash
conda activate medellin-analysis312 && jupyter lab
```

Las secciones 5 a 8 leen `original/` y `coordenadas/coordenadas.xlsx`, que contienen datos personales. **Antes de cada commit** limpia las salidas; el test `tests/test_notebooks_sin_salidas.py` falla si se te olvida:

```bash
jupyter nbconvert --clear-output --inplace notebooks/exploracion_geojson.ipynb
```

## Documentación

Puedes consultar la documentación completa del proyecto en el siguiente enlace:

🔗 [Documentación del módulo `main.py`](https://felipe1727.github.io/Georreferenciacion-Area-Metropolitana/main.html)
