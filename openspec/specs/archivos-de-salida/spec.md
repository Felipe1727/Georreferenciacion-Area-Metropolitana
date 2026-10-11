# archivos-de-salida Specification

## Purpose

Define la estructura de directorios que crea el sistema, los nombres de los archivos que genera y lee entre etapas, y la exclusión de credenciales y datos personales del control de versiones.

## Requirements

### Requirement: Nombres de archivos generados en ASCII
Todos los nombres de archivos y directorios que el sistema genera SHALL estar formados solo por caracteres ASCII. La estandarización SHALL escribir en `estandarizado/` los archivos `total_area_metropolitana.xlsx`, `principales_area_metropolitana.xlsx`, `especiales_area_metropolitana.xlsx` y `fuera_area_metropolitana.xlsx`.

#### Scenario: Estandarización
- **WHEN** el usuario ejecuta la estandarización de direcciones
- **THEN** `estandarizado/` contiene exactamente esos cuatro archivos y ningún archivo cuyo nombre tenga caracteres no ASCII

#### Scenario: Archivos de coordenadas y mapas
- **WHEN** el usuario ejecuta la conversión de coordenadas y luego la generación de mapas
- **THEN** el sistema escribe `coordenadas/coordenadas.xlsx`, `mapas/individual.html`, `mapas/clusters.html`, `mapas/filtrados/individual_filtrados.html` y `mapas/filtrados/clusters_filtrados.html`

### Requirement: Lectura entre etapas con nombres ASCII
Cuando no existe `coordenadas/coordenadas.xlsx`, la conversión de coordenadas SHALL leer sus registros de `estandarizado/principales_area_metropolitana.xlsx`. Si ese archivo tampoco existe, el sistema MUST terminar con un mensaje que indique que primero debe ejecutarse la estandarización, en lugar de una traza de error.

#### Scenario: Primera conversión tras estandarizar
- **WHEN** existe `estandarizado/principales_area_metropolitana.xlsx`, no existe `coordenadas/coordenadas.xlsx` y el usuario ejecuta la conversión
- **THEN** el sistema geocodifica los registros de `principales_area_metropolitana.xlsx`

#### Scenario: Solo existen archivos con el nombre antiguo
- **WHEN** en `estandarizado/` solo existe `principales_área_metropolitana.xlsx` (nombre anterior) y no existe `coordenadas/coordenadas.xlsx`
- **THEN** el sistema termina con un mensaje que pide ejecutar la estandarización y no consulta al proveedor

### Requirement: Estructura de directorios de trabajo
Al iniciar, el sistema SHALL crear, si no existen, los directorios `original/`, `estandarizado/`, `coordenadas/` y `mapas/filtrados/`, y MUST NOT crear el directorio `llave/`.

#### Scenario: Primera ejecución en un directorio limpio
- **WHEN** el usuario ejecuta el programa en un directorio sin carpetas de trabajo
- **THEN** existen `original/`, `estandarizado/`, `coordenadas/` y `mapas/filtrados/`, y no existe `llave/`

### Requirement: Datos sensibles excluidos del control de versiones
El repositorio SHALL ignorar en git los directorios de datos y salidas (`original/`, `estandarizado/`, `coordenadas/`, `mapas/`), el directorio heredado `llave/` y los archivos de variables de entorno locales (`.env`), para que credenciales y datos personales de estudiantes no puedan añadirse por accidente.

#### Scenario: Archivos de datos sin seguimiento
- **WHEN** existen archivos dentro de `original/`, `estandarizado/`, `coordenadas/`, `mapas/` o `llave/`
- **THEN** `git status` no los lista como archivos sin seguimiento y `git check-ignore` confirma que están ignorados

#### Scenario: Archivo de credenciales local
- **WHEN** existe un archivo `.env` en la raíz del repositorio
- **THEN** `git check-ignore` confirma que está ignorado, mientras que la plantilla `.env.example` (sin ninguna llave) sí está versionada

#### Scenario: Datos versionados del proyecto
- **WHEN** se consulta el estado de `data/limite_barrio_vereda_cata.geojson`
- **THEN** el archivo sigue versionado y no lo afecta ninguna regla de exclusión
