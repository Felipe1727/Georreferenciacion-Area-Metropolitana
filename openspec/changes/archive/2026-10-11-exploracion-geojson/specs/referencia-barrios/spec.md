# Spec Delta

## Purpose

Define los datos de referencia geográfica de Medellín que usa el sistema para relacionar el barrio declarado por un estudiante con un polígono oficial: fuente y procedencia, normalización de nombres, tabla de alias y resolución de nombres repetidos.

## ADDED Requirements

### Requirement: Fuente oficial de polígonos con procedencia documentada
El repositorio SHALL versionar los polígonos oficiales de barrios y veredas de Medellín en `data/limite_barrio_vereda_cata.geojson` y documentar en `data/README.md` su fuente (portal de datos abiertos GeoMedellín, Alcaldía de Medellín), la URL del conjunto, la fecha de descarga, la fecha de sincronización, la licencia, el sistema de coordenadas y el significado de los campos que usa el sistema.

#### Scenario: Consulta de procedencia
- **WHEN** alguien abre `data/README.md`
- **THEN** encuentra la URL del conjunto, la licencia, las fechas de descarga y de sincronización (2025-05-02), el sistema de coordenadas EPSG:9377 y la descripción de `codigo`, `nombre_barrio`, `nombre_comuna` e `indicador_ur`

#### Scenario: Identificador estable de cada polígono
- **WHEN** se cargan los polígonos
- **THEN** el campo `codigo` es único en los 349 polígonos y se trata como texto, conservando los ceros a la izquierda (por ejemplo, `0806`)

### Requirement: Convención de normalización de nombres
Para compararse entre sí, los nombres oficiales, los barrios declarados y los alias SHALL normalizarse igual: pasar a mayúsculas, eliminar diacríticos (la `Ñ` pasa a `N`), sustituir los signos de puntuación por espacios, colapsar los espacios repetidos y recortar los extremos.

#### Scenario: Tildes y eñes
- **WHEN** se normalizan `Área de Expansión Pajarito` y `La Cabaña`
- **THEN** el resultado es `AREA DE EXPANSION PAJARITO` y `LA CABANA`

#### Scenario: Puntuación y espacios
- **WHEN** se normaliza `  carlos e.  restrepo `
- **THEN** el resultado es `CARLOS E RESTREPO`

### Requirement: Formato de la tabla de alias
La tabla de alias SHALL ser el archivo `data/alias_barrios.csv`, en UTF-8 con encabezado, y tener exactamente las columnas `alias`, `codigo`, `nombre_oficial` y `nota`. Cada fila asigna una variante normalizada de nombre a un único polígono identificado por `codigo`.

#### Scenario: Lectura de la tabla
- **WHEN** se lee `data/alias_barrios.csv` con `codigo` como texto
- **THEN** cada fila tiene las cuatro columnas, `codigo` conserva los ceros a la izquierda y `nota` indica el motivo del alias (por ejemplo, variante ortográfica, nombre popular o prefijo de vivienda)

### Requirement: Invariantes de la tabla de alias
Cada `alias` MUST estar ya normalizado y ser único, y no debe coincidir con el nombre oficial normalizado de ningún polígono. Cada `codigo` MUST existir en el GeoJSON, y `nombre_oficial` MUST ser el `nombre_barrio` de ese polígono.

#### Scenario: Tabla válida
- **WHEN** se comprueba la tabla contra el GeoJSON
- **THEN** ningún alias está repetido, todos los alias son iguales a su forma normalizada y todos los `codigo` existen, con su `nombre_oficial` correspondiente

#### Scenario: Alias que repite un nombre oficial
- **WHEN** una fila tiene como `alias` el nombre oficial normalizado de algún polígono (por ejemplo, `LAURELES`)
- **THEN** la comprobación la marca como inválida, porque redefiniría un nombre oficial

#### Scenario: Código inexistente
- **WHEN** una fila tiene un `codigo` que no existe en el GeoJSON
- **THEN** la comprobación la marca como inválida

### Requirement: Resolución de nombres de barrio repetidos
Cuando un nombre normalizado corresponde a varios polígonos, el sistema SHALL elegir el polígono cuyo `indicador_ur` coincide con la zona declarada (`URBANO` → `U`, `RURAL` → `R`). Si persiste más de un candidato o no hay zona, el barrio MUST quedar sin resolver.

#### Scenario: Nombre repetido con zona urbana
- **WHEN** el barrio declarado es `LA FLORIDA` y la zona es `URBANO`
- **THEN** se asigna el polígono urbano de la comuna El Poblado

#### Scenario: Nombre repetido con zona rural
- **WHEN** el barrio declarado es `LA FLORIDA` y la zona es `RURAL`
- **THEN** se asigna el polígono rural del corregimiento San Antonio de Prado

#### Scenario: Ambigüedad que la zona no resuelve
- **WHEN** el barrio declarado es `SUBURBANO EL LLANO` y la zona es `RURAL`
- **THEN** el barrio queda sin resolver, porque los dos polígonos con ese nombre son rurales

#### Scenario: Nombre repetido sin zona
- **WHEN** el barrio declarado es `LA FLORIDA` y la dirección no trae zona
- **THEN** el barrio queda sin resolver

#### Scenario: Nombre único
- **WHEN** el barrio declarado corresponde a un solo polígono
- **THEN** se asigna ese polígono aunque su `indicador_ur` no coincida con la zona o esté vacío

### Requirement: Análisis exploratorios sin datos personales en el repositorio
Los notebooks versionados MUST NOT contener salidas de celdas ni contadores de ejecución. Los hallazgos versionados MUST expresarse solo con cifras agregadas y nombres de barrio, sin direcciones, códigos de estudiante ni otros datos de un registro concreto.

#### Scenario: Notebook versionado
- **WHEN** se inspecciona el JSON de cualquier notebook de `notebooks/`
- **THEN** todas las celdas de código tienen `outputs` vacío y `execution_count` nulo

#### Scenario: Documento de hallazgos
- **WHEN** se revisa `notebooks/hallazgos_geojson.md`
- **THEN** contiene conteos, porcentajes y nombres de barrio, y ninguna dirección, código de estudiante ni fila del archivo original
