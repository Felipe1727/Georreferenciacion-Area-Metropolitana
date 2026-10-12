# Spec Delta

## MODIFIED Requirements

### Requirement: Los registros de fuera solo se exportan
Los registros de fuera del área metropolitana SHALL exportarse a `estandarizado/fuera_area_metropolitana.xlsx` con la misma normalización que los del área metropolitana (dirección, complemento y zona, sin barrio ni comuna), y MUST NOT enviarse al proveedor de geocodificación en ninguna operación.

#### Scenario: Geocodificación tras estandarizar
- **WHEN** el usuario estandariza y después ejecuta la conversión de coordenadas
- **THEN** ninguna consulta al proveedor corresponde a un registro de `fuera_area_metropolitana.xlsx`

#### Scenario: Normalización de un registro de fuera
- **WHEN** se estandariza `CR 5 10 20 CENTRO`, de Montería
- **THEN** en `fuera_area_metropolitana.xlsx` su `Direccion de residencia` es `CR 5 #10-20`, su `Complemento` es `CENTRO` y `Barrio`, `Codigo barrio` y `Comuna` quedan vacíos
