# Proposal

## Why

El proyecto va a pasar por una refactorización por etapas (modularización, configuración externa y ubicación por niveles), pero hoy no tiene ninguna red de seguridad: no hay tests, no hay un entorno declarado y no hay `.gitignore`. La API key y los datos personales de estudiantes (`llave/`, `original/`, salidas) solo están fuera del repositorio porque nadie ha hecho `git add .`. Además, 11 identificadores del código y los nombres de los archivos generados usan caracteres no ASCII, y la API key se guarda en texto plano en `llave/llave.txt`, mediante un flujo interactivo. Este cambio prepara el terreno para que las etapas siguientes se hagan con seguridad y sin regresiones silenciosas.

## What Changes

- Añadir un `.gitignore` que excluya las credenciales, los datos de entrada, las salidas generadas y los artefactos locales (cachés de Python, IDE, checkpoints de notebooks).
- Declarar el entorno reproducible (`environment.yml`) con las versiones que se usan hoy (Python 3.12, pandas 3.0, folium 0.20, opencage 3.3, openpyxl 3.1) y añadir pytest como dependencia de desarrollo.
- Crear una suite de **tests de caracterización** que congele el comportamiento actual de la estandarización, la clasificación por área, la geocodificación (con un geocodificador falso, sin red), la mejora por barrio y la generación de mapas. Usa datos sintéticos, nunca datos reales de estudiantes.
- Renombrar los 11 identificadores no ASCII a ASCII sin cambiar el comportamiento. En la misma pasada se corrigen erratas y nombres engañosos: `aldready` → `already`, `map`/`map2` (que sombrean el builtin) y `reverse_geocoding` (en realidad hace geocodificación directa).
- Añadir un test que impida volver a introducir identificadores no ASCII.
- **BREAKING**: los archivos generados pasan a tener nombres ASCII (`total_area_metropolitana.xlsx`, `principales_area_metropolitana.xlsx`, `especiales_area_metropolitana.xlsx`, `fuera_area_metropolitana.xlsx`). Los archivos existentes con tilde no se leerán: hay que volver a ejecutar la estandarización o renombrarlos.
- **BREAKING**: la API key de OpenCage se lee de `OPENCAGE_API_KEY`, ya sea del entorno o de un archivo `.env` local ignorado por git (con python-dotenv), con una plantilla `.env.example` versionada. Se eliminan `llave/llave.txt`, la carpeta `llave/` de la estructura creada y el flujo interactivo que preguntaba, pedía y guardaba la llave. Si la variable falta, el programa termina con un mensaje que explica cómo definirla.
- Actualizar el README: requisitos reales (Python 3.12; `match` exige ≥ 3.10), instalación con `environment.yml`, definición de `OPENCAGE_API_KEY` (archivo `.env` o entorno) y nuevos nombres de archivo.

## Capabilities

### New Capabilities

- `credenciales-geocodificacion`: cómo obtiene el sistema la credencial del proveedor de geocodificación y cómo se comporta cuando falta.
- `archivos-de-salida`: estructura de directorios que crea el sistema, convención de nombres de los archivos que genera y exclusión de datos sensibles del control de versiones.

### Modified Capabilities

Ninguna: `openspec/specs/` todavía no contiene especificaciones. El resto del comportamiento (estandarización, clasificación, geocodificación, mejora y mapas) se conserva y queda protegido por los tests de caracterización. Sus especificaciones se escribirán en los cambios que lo modifiquen.

## Impact

- **Código**: `main.py` (renombrados, rutas de salida, obtención de la llave en el menú y en el modo `python main.py c`, `estructura_programa`). No cambia la lógica de estandarización, clasificación, geocodificación, mejora ni visualización.
- **Archivos nuevos**: `.gitignore`, `.env.example`, `environment.yml`, `tests/` (tests y datos sintéticos), configuración mínima de pytest.
- **Dependencias**: se añade `python-dotenv` (ejecución, para leer `.env`) y `pytest` (solo desarrollo).
- **Operación**: hay que crear `.env` con `OPENCAGE_API_KEY` (o definir la variable en el entorno) y regenerar o renombrar los Excel de `estandarizado/`.
- **Documentación**: `README.md` se actualiza. `docs/main.html` (pdoc) quedará con los nombres antiguos; se regenerará en el cambio `modularizacion-config`, cuando la estructura de módulos sea definitiva.
- **Fuera de alcance**: corregir los defectos conocidos de la estandarización (reemplazo por subcadena), el bug de `index_col` del modo `c`, la modularización, la configuración externa y cualquier cambio en la geocodificación. Los tests de caracterización documentan estos defectos tal como son hoy.
