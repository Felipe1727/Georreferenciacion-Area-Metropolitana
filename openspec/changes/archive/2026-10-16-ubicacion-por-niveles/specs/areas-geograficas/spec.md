# Spec Delta

## MODIFIED Requirements

### Requirement: Área metropolitana como universo de trabajo
La estandarización SHALL separar los registros según el municipio de residencia: los que figuran en la lista de municipios del área metropolitana de la configuración forman el área metropolitana, y todos los demás, incluidos los que no tienen municipio, quedan fuera. Solo los registros del área metropolitana, de vía principal y especiales, pasan a las etapas de ubicación y mapas.

#### Scenario: Separación por municipio
- **WHEN** el archivo de entrada tiene registros de Medellín, Envigado, Rionegro y Montería, y la configuración incluida define el área metropolitana
- **THEN** los registros de Medellín y Envigado van a los archivos del área metropolitana, y los de Rionegro y Montería a `estandarizado/fuera_area_metropolitana.xlsx`

#### Scenario: Registro sin municipio
- **WHEN** un registro tiene vacía la columna de ciudad
- **THEN** el registro va a `fuera_area_metropolitana.xlsx`

#### Scenario: Registros especiales en la ubicación
- **WHEN** el área metropolitana tiene registros en `especiales_area_metropolitana.xlsx` y el usuario ejecuta la ubicación
- **THEN** esos registros aparecen en el archivo de coordenadas con un punto y su nivel de ubicación
