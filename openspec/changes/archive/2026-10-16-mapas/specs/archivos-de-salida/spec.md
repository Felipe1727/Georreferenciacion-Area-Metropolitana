# Spec Delta

## MODIFIED Requirements

### Requirement: Nombres de archivos generados en ASCII
Los nombres de los archivos y directorios que genera el sistema SHALL ser solo ASCII. La estandarización SHALL escribir en `estandarizado/` `total_area_metropolitana.xlsx`, `principales_area_metropolitana.xlsx`, `especiales_area_metropolitana.xlsx` y `fuera_area_metropolitana.xlsx`. Las coordenadas y los mapas se nombran con el identificador del área (`area_metropolitana` o un subconjunto). Las consultas al proveedor escriben `cache_consultas.csv` y `registro_consultas.csv` en `coordenadas/`.

#### Scenario: Estandarización
- **WHEN** el usuario ejecuta la estandarización de direcciones
- **THEN** `estandarizado/` contiene exactamente esos cuatro archivos y ningún archivo cuyo nombre tenga caracteres no ASCII

#### Scenario: Archivos de coordenadas y mapas
- **WHEN** el usuario ejecuta la ubicación y luego la generación de mapas
- **THEN** el sistema escribe `coordenadas/coordenadas_area_metropolitana.xlsx`, `coordenadas/cache_consultas.csv`, `coordenadas/registro_consultas.csv` y `mapas/area_metropolitana/mapa.html`

#### Scenario: Mapas separados
- **WHEN** el usuario genera los mapas con `--separado todos --sin-municipio`
- **THEN** el sistema escribe en `mapas/area_metropolitana/separados/` los archivos `puntos_sin_municipio.html`, `clusters_sin_municipio.html`, `barrios_cantidad.html` y `comunas_cantidad.html`

#### Scenario: Archivos de un subconjunto
- **WHEN** el usuario extrae el subconjunto `medellin`
- **THEN** el sistema escribe `coordenadas/coordenadas_medellin.xlsx` y `mapas/medellin/mapa.html`, todos con nombres ASCII

### Requirement: Estructura de directorios de trabajo
Al iniciar, el sistema SHALL crear, si no existen, los directorios `original/`, `estandarizado/`, `coordenadas/` y `mapas/area_metropolitana/`, y MUST NOT crear el directorio `llave/` ni `filtrados/`. Al generar los mapas de un área crea `mapas/<area>/` y, solo si se pide algún separado, `mapas/<area>/separados/`.

#### Scenario: Primera ejecución en un directorio limpio
- **WHEN** el usuario ejecuta el programa en un directorio sin carpetas de trabajo
- **THEN** existen `original/`, `estandarizado/`, `coordenadas/` y `mapas/area_metropolitana/`, y no existen `llave/` ni `mapas/area_metropolitana/filtrados/`

### Requirement: Datos sensibles excluidos del control de versiones
El repositorio SHALL ignorar en git los directorios de datos y salidas (`original/`, `estandarizado/`, `coordenadas/`, `mapas/`), el directorio heredado `llave/` y los archivos de variables de entorno locales (`.env`), para que credenciales y datos personales de estudiantes no puedan añadirse por accidente. Las exclusiones MUST NOT afectar a los artefactos de `openspec/` que comparten nombre con esos directorios.

#### Scenario: Archivos de datos sin seguimiento
- **WHEN** existen archivos dentro de `original/`, `estandarizado/`, `coordenadas/`, `mapas/` o `llave/`
- **THEN** `git status` no los lista como archivos sin seguimiento y `git check-ignore` confirma que están ignorados

#### Scenario: Archivo de credenciales local
- **WHEN** existe un archivo `.env` en la raíz del repositorio
- **THEN** `git check-ignore` confirma que está ignorado, mientras que la plantilla `.env.example` (sin ninguna llave) sí está versionada

#### Scenario: Datos versionados del proyecto
- **WHEN** se consulta el estado de `data/limite_barrio_vereda_cata.geojson`
- **THEN** el archivo sigue versionado y no lo afecta ninguna regla de exclusión

#### Scenario: Artefactos de OpenSpec con el nombre de un directorio de datos
- **WHEN** existen `openspec/changes/mapas/proposal.md` y `openspec/specs/mapas/spec.md`
- **THEN** `git check-ignore` no los marca como ignorados, mientras que `mapas/area_metropolitana/mapa.html` y una carpeta `mapas/` en cualquier otra ruta siguen ignorados
