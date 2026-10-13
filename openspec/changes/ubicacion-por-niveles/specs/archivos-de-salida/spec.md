# Spec Delta

## MODIFIED Requirements

### Requirement: Nombres de archivos generados en ASCII
Todos los nombres de archivos y directorios que el sistema genera SHALL estar formados solo por caracteres ASCII. La estandarización SHALL escribir en `estandarizado/` los archivos `total_area_metropolitana.xlsx`, `principales_area_metropolitana.xlsx`, `especiales_area_metropolitana.xlsx` y `fuera_area_metropolitana.xlsx`. Las coordenadas y los mapas de un área se nombran con el identificador del área: `area_metropolitana` o el nombre de un subconjunto. Las consultas al proveedor escriben `coordenadas/cache_consultas.csv` y `coordenadas/registro_consultas.csv`.

#### Scenario: Estandarización
- **WHEN** el usuario ejecuta la estandarización de direcciones
- **THEN** `estandarizado/` contiene exactamente esos cuatro archivos y ningún archivo cuyo nombre tenga caracteres no ASCII

#### Scenario: Archivos de coordenadas y mapas
- **WHEN** el usuario ejecuta la ubicación y luego la generación de mapas
- **THEN** el sistema escribe `coordenadas/coordenadas_area_metropolitana.xlsx`, `coordenadas/cache_consultas.csv`, `coordenadas/registro_consultas.csv`, `mapas/area_metropolitana/individual.html`, `mapas/area_metropolitana/clusters.html`, `mapas/area_metropolitana/filtrados/individual_filtrados.html` y `mapas/area_metropolitana/filtrados/clusters_filtrados.html`

#### Scenario: Archivos de un subconjunto
- **WHEN** el usuario extrae el subconjunto `medellin`
- **THEN** el sistema escribe `coordenadas/coordenadas_medellin.xlsx` y los cuatro mapas en `mapas/medellin/` y `mapas/medellin/filtrados/`, todos con nombres ASCII

### Requirement: Lectura entre etapas con nombres ASCII
La ubicación SHALL leer `estandarizado/principales_area_metropolitana.xlsx` y `estandarizado/especiales_area_metropolitana.xlsx`, con `Codigo barrio` como texto, y escribir de nuevo y por completo `coordenadas/coordenadas_area_metropolitana.xlsx` en cada ejecución. Lo ya consultado se recupera de la caché, no del archivo de coordenadas. Los mapas y los subconjuntos leen ese archivo. Si falta un archivo de entrada, el sistema MUST terminar con un mensaje que pida ejecutar primero la estandarización.

#### Scenario: Primera conversión tras estandarizar
- **WHEN** existen los archivos de principales y especiales, no existe `coordenadas/coordenadas_area_metropolitana.xlsx` y el usuario ejecuta la ubicación
- **THEN** la ubicación escribe el archivo de coordenadas con todos los registros de los dos archivos, en el orden de su índice

#### Scenario: Conversión reanudada
- **WHEN** el archivo de coordenadas de una ubicación anterior tiene registros con `Resultado consulta` igual a `PENDIENTE` y el usuario vuelve a ejecutar la ubicación
- **THEN** el archivo se regenera desde `estandarizado/`, solo las consultas pendientes generan peticiones y las ya hechas salen de la caché

#### Scenario: Solo existen archivos con el nombre antiguo
- **WHEN** en `estandarizado/` solo existe `principales_área_metropolitana.xlsx` (nombre anterior)
- **THEN** el sistema termina con un mensaje que pide ejecutar la estandarización y no consulta al proveedor

### Requirement: Aviso ante el archivo de coordenadas con el nombre anterior
Si existe `coordenadas/coordenadas.xlsx` (nombre anterior) y no existe `coordenadas/coordenadas_area_metropolitana.xlsx`, la ubicación, los mapas y los subconjuntos MUST terminar con un mensaje que pida renombrar el archivo, sin consultar al proveedor ni escribir archivos.

#### Scenario: Conversión con el archivo antiguo
- **WHEN** solo existe `coordenadas/coordenadas.xlsx` y el usuario ejecuta la ubicación
- **THEN** el sistema termina con código distinto de cero, el mensaje nombra los dos archivos y no se hace ninguna consulta al proveedor

#### Scenario: Mapas con el archivo antiguo
- **WHEN** solo existe `coordenadas/coordenadas.xlsx` y el usuario genera los mapas
- **THEN** el sistema termina con el mismo mensaje y no escribe mapas

#### Scenario: Los dos archivos existen
- **WHEN** existen `coordenadas/coordenadas.xlsx` y `coordenadas/coordenadas_area_metropolitana.xlsx`
- **THEN** el sistema usa `coordenadas_area_metropolitana.xlsx` y no modifica el archivo antiguo

## ADDED Requirements

### Requirement: Conservación del archivo de coordenadas de formato anterior
Si `coordenadas/coordenadas_area_metropolitana.xlsx` existe y no tiene la columna `Nivel ubicacion`, la ubicación SHALL renombrarlo a `coordenadas/coordenadas_area_metropolitana_anterior.xlsx` antes de escribir el nuevo. Si ese nombre ya está ocupado, MUST terminar con un mensaje que nombre los dos archivos, sin consultar al proveedor ni escribir nada.

#### Scenario: Primera ubicación con coordenadas antiguas
- **WHEN** existe un archivo de coordenadas sin `Nivel ubicacion` y el usuario ejecuta la ubicación
- **THEN** ese archivo pasa a llamarse `coordenadas_area_metropolitana_anterior.xlsx` sin cambios en su contenido, y se escribe el archivo nuevo

#### Scenario: Copia anterior ya existente
- **WHEN** existen un archivo de coordenadas sin `Nivel ubicacion` y `coordenadas_area_metropolitana_anterior.xlsx`
- **THEN** el sistema termina con código distinto de cero, el mensaje nombra los dos archivos y no se hace ninguna consulta
