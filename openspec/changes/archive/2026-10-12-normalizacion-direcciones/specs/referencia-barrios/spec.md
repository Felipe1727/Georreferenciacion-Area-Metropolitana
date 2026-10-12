# Spec Delta

## ADDED Requirements

### Requirement: Tabla de variantes de comuna
Las formas escritas que designan una comuna o corregimiento completo sin ser su nombre oficial SHALL registrarse en `data/alias_comunas.csv`, en UTF-8 con encabezado y con exactamente las columnas `alias`, `comuna` y `nota`. Cada fila asigna una variante normalizada a un `nombre_comuna` del GeoJSON. No asigna ningún barrio.

#### Scenario: Variantes incluidas
- **WHEN** se lee `data/alias_comunas.csv`
- **THEN** contiene `POBLADO` → `EL POBLADO` y `RODEO`, `RODEO ALTO` y `RODEO SUR` → `BELEN`, cada una con su `nota`

### Requirement: Invariantes de la tabla de variantes de comuna
Cada `alias` de `alias_comunas.csv` MUST estar normalizado, ser único y no coincidir con el nombre oficial normalizado de ningún barrio ni comuna, ni con un alias de `alias_barrios.csv`. Cada `comuna` MUST ser un `nombre_comuna` del GeoJSON y cada fila MUST tener `nota`.

#### Scenario: Tabla válida
- **WHEN** se comprueba `alias_comunas.csv` contra el GeoJSON y `alias_barrios.csv`
- **THEN** no hay errores

#### Scenario: Variante que repite un nombre de barrio
- **WHEN** una fila tiene como `alias` `EL POBLADO`, que es el nombre oficial normalizado de un barrio
- **THEN** la comprobación la marca como inválida

#### Scenario: Comuna inexistente
- **WHEN** una fila asigna una variante a la comuna `NORTE`, que no existe en el GeoJSON
- **THEN** la comprobación la marca como inválida
