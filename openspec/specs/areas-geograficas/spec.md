# areas-geograficas Specification

## Purpose

Define el área metropolitana como el universo de registros que el sistema estandariza y geocodifica, qué ocurre con los registros de fuera, y cómo se obtienen subconjuntos con nombre (por ejemplo, Medellín) a partir de las coordenadas ya calculadas, sin nuevas consultas al proveedor.

## Requirements

### Requirement: Área metropolitana como universo de trabajo
La estandarización SHALL separar los registros según el municipio de residencia: los que figuran en la lista de municipios del área metropolitana de la configuración forman el área metropolitana, y todos los demás, incluidos los que no tienen municipio, quedan fuera. Solo los registros del área metropolitana pasan a las etapas de geocodificación, mejora y mapas.

#### Scenario: Separación por municipio
- **WHEN** el archivo de entrada tiene registros de Medellín, Envigado, Rionegro y Montería, y la configuración incluida define el área metropolitana
- **THEN** los registros de Medellín y Envigado van a los archivos del área metropolitana, y los de Rionegro y Montería a `estandarizado/fuera_area_metropolitana.xlsx`

#### Scenario: Registro sin municipio
- **WHEN** un registro tiene vacía la columna de ciudad
- **THEN** el registro va a `fuera_area_metropolitana.xlsx`

### Requirement: Los registros de fuera solo se exportan
Los registros de fuera del área metropolitana SHALL exportarse a `estandarizado/fuera_area_metropolitana.xlsx` con la misma normalización que los del área metropolitana (dirección, complemento y zona, sin barrio ni comuna), y MUST NOT enviarse al proveedor de geocodificación en ninguna operación.

#### Scenario: Geocodificación tras estandarizar
- **WHEN** el usuario estandariza y después ejecuta la conversión de coordenadas
- **THEN** ninguna consulta al proveedor corresponde a un registro de `fuera_area_metropolitana.xlsx`

#### Scenario: Normalización de un registro de fuera
- **WHEN** se estandariza `CR 5 10 20 CENTRO`, de Montería
- **THEN** en `fuera_area_metropolitana.xlsx` su `Direccion de residencia` es `CR 5 #10-20`, su `Complemento` es `CENTRO` y `Barrio`, `Codigo barrio` y `Comuna` quedan vacíos

### Requirement: Subconjuntos con nombre del área metropolitana
La configuración SHALL poder definir subconjuntos con nombre, cada uno con una lista de municipios. El nombre MUST estar formado solo por letras minúsculas ASCII, dígitos y guiones bajos, y no puede ser `area_metropolitana`. Cada municipio de un subconjunto MUST pertenecer al área metropolitana. Si no se cumple, la validación de la configuración falla.

#### Scenario: Subconjunto incluido
- **WHEN** se usa la configuración incluida
- **THEN** existe el subconjunto `medellin`, formado por `MEDELLIN - ANTIOQUIA`

#### Scenario: Municipio fuera del área metropolitana
- **WHEN** un subconjunto incluye `RIONEGRO - ANTIOQUIA` y ese municipio no está en el área metropolitana
- **THEN** la validación falla con un mensaje que nombra el subconjunto y el municipio

#### Scenario: Nombre no válido
- **WHEN** un subconjunto se llama `Medellín` o `area_metropolitana`
- **THEN** la validación falla con un mensaje que nombra el subconjunto

### Requirement: Extracción de un subconjunto sin consultar al proveedor
Al extraer un subconjunto, el sistema SHALL tomar de `coordenadas/coordenadas_area_metropolitana.xlsx` los registros cuyo municipio pertenece al subconjunto. Debe escribirlos en `coordenadas/coordenadas_<nombre>.xlsx`, conservando columnas e índice, y generar sus cuatro mapas en `mapas/<nombre>/`. No consulta al proveedor ni exige la llave.

#### Scenario: Subconjunto de Medellín
- **WHEN** existe `coordenadas_area_metropolitana.xlsx` con registros de Medellín y de Bello, y el usuario extrae el subconjunto `medellin`
- **THEN** `coordenadas/coordenadas_medellin.xlsx` contiene solo los registros de Medellín, con las mismas columnas y el mismo índice que en el archivo del área metropolitana

#### Scenario: Mapas del subconjunto
- **WHEN** el usuario extrae el subconjunto `medellin`
- **THEN** el sistema escribe `mapas/medellin/individual.html`, `mapas/medellin/clusters.html`, `mapas/medellin/filtrados/individual_filtrados.html` y `mapas/medellin/filtrados/clusters_filtrados.html`, con los mismos criterios que los mapas del área metropolitana

#### Scenario: Sin llamadas al proveedor
- **WHEN** `OPENCAGE_API_KEY` no está definida y el usuario extrae un subconjunto
- **THEN** la extracción termina con normalidad y no se hace ninguna consulta al proveedor

### Requirement: Errores al extraer un subconjunto
Si el subconjunto no existe en la configuración, si aún no hay coordenadas del área metropolitana o si el subconjunto no tiene registros, el sistema MUST terminar con un mensaje claro y no escribir archivos del subconjunto.

#### Scenario: Subconjunto desconocido
- **WHEN** el usuario pide el subconjunto `norte` y la configuración no lo define
- **THEN** el sistema termina con código distinto de cero y un mensaje que lista los subconjuntos disponibles

#### Scenario: Sin coordenadas del área metropolitana
- **WHEN** no existe `coordenadas/coordenadas_area_metropolitana.xlsx` y el usuario extrae un subconjunto
- **THEN** el sistema termina con un mensaje que pide ejecutar primero la conversión de coordenadas

#### Scenario: Subconjunto sin registros
- **WHEN** ningún registro del archivo de coordenadas pertenece a los municipios del subconjunto
- **THEN** el sistema termina con un mensaje que lo indica y no crea `coordenadas_<nombre>.xlsx` ni `mapas/<nombre>/`
