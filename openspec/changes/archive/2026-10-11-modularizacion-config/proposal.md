# Proposal

## Why

Todo el programa vive en `main.py` (745 líneas). Ahí se mezclan la interfaz de consola, la lectura de Excel, la llamada a la API y los valores del dominio, como la lista de municipios del área metropolitana, las equivalencias de direcciones y los tipos de vía. Cambiar un municipio obliga a editar el código, y no se puede probar ni reutilizar una parte sin cargar todo lo demás. Además, no hay forma de obtener los resultados de un subconjunto del área (por ejemplo, solo Medellín) sin filtrar a mano.

`ubicacion-por-niveles` reescribirá la geocodificación y la extracción del barrio. Antes de eso conviene tener módulos separados y una configuración externa, para que ese cambio toque solo las piezas que le corresponden.

## What Changes

- **Paquete `georef/`.**
  - El código de `main.py` se reparte en módulos con una responsabilidad cada uno: configuración, archivos, direcciones, geocodificación, mapas, etapas e interfaz.
  - La lógica no cambia: los tests de caracterización de `fundamentos` deben seguir pasando con los mismos valores esperados.
- **Configuración en `config/georef.toml`**, versionada y validada al arrancar. Contiene:
  - los municipios del área metropolitana;
  - los subconjuntos con nombre (por ejemplo `medellin`);
  - los nombres de las columnas de entrada;
  - el vocabulario de direcciones: tipos de vía, palabras clave y equivalencias, estas últimas en orden.

  Añadir un municipio o un subconjunto ya no requiere tocar el código. Los errores de configuración se informan todos juntos, con un mensaje claro, antes de leer datos o llamar a la API.
- **Área metropolitana como universo fijo.** Solo los registros del área metropolitana se estandarizan y geocodifican. Los de fuera se siguen exportando únicamente a `estandarizado/fuera_area_metropolitana.xlsx`.
- **Subconjuntos sin gastar cuota.**
  - `python -m georef subconjunto --area medellin` filtra las coordenadas ya obtenidas del área metropolitana.
  - Escribe `coordenadas/coordenadas_medellin.xlsx` y los mapas en `mapas/medellin/`.
  - No llama a la API ni necesita la llave.
- **Interfaz de línea de comandos con `argparse`.**
  - Subcomandos: `estandarizar`, `geocodificar`, `mejorar`, `mapas` y `subconjunto`, más la opción global `--config`.
  - Sin argumentos, se muestra el menú interactivo, con una opción nueva para los subconjuntos.
  - `python main.py` y `python main.py c` siguen funcionando: `main.py` queda como un envoltorio delgado del paquete.
- **BREAKING:** las coordenadas del área metropolitana pasan de `coordenadas/coordenadas.xlsx` a `coordenadas/coordenadas_area_metropolitana.xlsx`, y los mapas pasan de `mapas/` a `mapas/area_metropolitana/`.
  - Si el programa solo encuentra el archivo antiguo, termina con un mensaje que pide renombrarlo, sin llamar a la API.
  - Así se evita volver a geocodificar desde cero por accidente y gastar cuota.
  - Los nombres de `estandarizado/` no cambian.
- **Correcciones menores** que no cambian los resultados:
  - El archivo de entrada se busca ignorando los archivos ocultos y los de bloqueo que crean LibreOffice y Excel mientras el archivo está abierto. Hoy hacen fallar el programa con "Hay más de un archivo".
  - Si `original/` queda vacío, el programa termina con un mensaje en lugar de una traza.
  - Si el archivo de entrada no tiene una columna configurada, el mensaje nombra la columna que falta.
  - El modo `c` deja de añadir la columna `Unnamed: 0` en cada ejecución, porque pasa a usar el mismo código que la opción de geocodificar.
- **Documentación `docs/` regenerada con pdoc** a partir de `georef/`, con un comando documentado en el README. Se añade `pdoc` como dependencia de desarrollo.
- El notebook `exploracion_geojson.ipynb` se actualiza para leer el nuevo nombre del archivo de coordenadas.

## Capabilities

### New Capabilities

- `configuracion`: archivo TOML del proyecto. Cubre su ubicación, su estructura (área metropolitana, subconjuntos, columnas y vocabulario de direcciones), la validación al arrancar, los mensajes de error y el uso de un archivo alternativo.
- `areas-geograficas`: el área metropolitana como universo de estandarización y geocodificación, la exportación de los registros de fuera y la extracción de subconjuntos con nombre a partir de las coordenadas ya obtenidas, sin llamadas a la API.
- `linea-de-comandos`: subcomandos, opciones, menú interactivo, compatibilidad con `python main.py` y su modo `c`, y comportamiento ante argumentos inválidos.

### Modified Capabilities

- `archivos-de-salida`:
  - nombres de los archivos de coordenadas y de mapas por área;
  - lectura entre etapas con el nombre nuevo y aviso ante el nombre antiguo;
  - estructura de directorios con `mapas/<area>/filtrados/`;
  - nuevo requisito sobre el archivo de entrada único en `original/`, ignorando ocultos y bloqueos.
- `credenciales-geocodificacion`:
  - los subcomandos `geocodificar` y `mejorar` exigen la llave, igual que las opciones del menú;
  - `subconjunto` no la exige;
  - el escenario de llave ausente pasa a nombrar el nuevo archivo de coordenadas.

## Impact

- **Código.**
  - Nuevo paquete `georef/` con `__main__.py`, `cli.py`, `config.py`, `archivos.py`, `direcciones.py`, `geocodificacion.py`, `mapas.py` y `etapas.py`.
  - `main.py` se reduce a unas pocas líneas que delegan en el paquete.
- **Configuración:** nuevo `config/georef.toml`. Se lee con `tomllib`, de la biblioteca estándar de Python 3.11+, así que no añade dependencias de ejecución.
- **Tests.**
  - Los tests de `fundamentos` pasan a importar `georef` y a sustituir `georef.geocodificacion.OpenCageGeocode` en lugar de `main.OpenCageGeocode`.
  - Sus valores esperados no cambian, salvo:
    - las rutas de coordenadas y mapas;
    - el defecto conocido del modo `c`, que se corrige.
  - Se añaden tests de configuración, subcomandos, subconjuntos y migración.
- **Dependencias:** `pdoc=16.0.0` (conda-forge) en `environment.yml`, solo para desarrollo.
- **Datos locales del usuario:** hay que renombrar una vez `coordenadas/coordenadas.xlsx` a `coordenadas_area_metropolitana.xlsx`. No hay que volver a geocodificar. Los mapas se regeneran con el subcomando `mapas`.
- **Documentación:** README (uso, configuración, subconjuntos, migración, regenerar `docs/`) y `docs/`.
- **Fuera de alcance.** Todo esto corresponde a `ubicacion-por-niveles` y `mapas`:
  - corregir la estandarización (reemplazo por subcadena, `URBA#`);
  - cambiar la lógica o los parámetros de geocodificación (`n=300`, `n=400`, plantilla de consulta, pausas);
  - sustituir la lista `barrios_medellin` o la coordenada fija del centroide de Medellín;
  - cambiar el contenido de los mapas;
  - geocodificar registros de fuera del área metropolitana.
