# Spec Delta

## MODIFIED Requirements

### Requirement: Archivo de configuración versionado
El sistema SHALL leer su configuración de `config/georef.toml`, un archivo TOML en UTF-8 versionado en el repositorio. Debe contener la lista de municipios del área metropolitana, los subconjuntos con nombre, los nombres de las columnas de ciudad y dirección del archivo de entrada, el vocabulario de direcciones (tipos de vía, palabras clave y equivalencias) y las referencias geográficas (rutas del GeoJSON y de las tablas de alias, y el municipio al que corresponden los polígonos).

#### Scenario: Ejecución con la configuración incluida
- **WHEN** el usuario ejecuta cualquier operación sin indicar otra configuración
- **THEN** el sistema usa los valores de `config/georef.toml`

#### Scenario: Valores y texto en español
- **WHEN** la configuración contiene municipios, equivalencias o columnas con tildes (por ejemplo `NÚMERO`)
- **THEN** el sistema los usa tal como están escritos, sin quitar tildes ni otros caracteres

## ADDED Requirements

### Requirement: Vocabulario incluido
La configuración incluida SHALL conservar los 10 municipios del área metropolitana, los tipos de vía, las palabras clave y las equivalencias que tenía el código antes de `modularizacion-config`, más la equivalencia `CRRA` → `CR`, que aparece en los datos. La forma de aplicar las equivalencias la define la especificación `normalizacion-direcciones`.

#### Scenario: Mismos valores
- **WHEN** se compara la configuración incluida con las constantes que tenía `main.py`
- **THEN** los municipios, tipos de vía y palabras clave son los mismos, y las equivalencias son las mismas más `CRRA` → `CR`

### Requirement: Referencias geográficas configurables
La sección `[referencia]` SHALL indicar las rutas del GeoJSON de barrios, de `alias_barrios.csv` y de `alias_comunas.csv`, y el municipio con polígonos, que MUST pertenecer al área metropolitana. Si alguno de esos archivos no existe al estandarizar, el sistema MUST terminar con un mensaje que nombre el archivo, sin escribir salidas.

#### Scenario: Referencias incluidas
- **WHEN** se usa la configuración incluida
- **THEN** el GeoJSON es `data/limite_barrio_vereda_cata.geojson`, las tablas son `data/alias_barrios.csv` y `data/alias_comunas.csv`, y el municipio con polígonos es `MEDELLIN - ANTIOQUIA`

#### Scenario: Municipio con polígonos fuera del área
- **WHEN** el municipio con polígonos no está en la lista del área metropolitana
- **THEN** la validación de la configuración falla con un mensaje que nombra `referencia.municipio_con_poligonos`

#### Scenario: Archivo de referencia inexistente
- **WHEN** la ruta del GeoJSON apunta a un archivo que no existe y el usuario ejecuta la estandarización
- **THEN** el sistema termina con código distinto de cero, el mensaje nombra la ruta y `estandarizado/` queda sin cambios

## REMOVED Requirements

### Requirement: La configuración incluida reproduce el comportamiento anterior
**Reason**: `normalizacion-direcciones` cambia a propósito la estandarización: las equivalencias pasan a aplicarse a palabras completas y solo a la vía y la numeración, y se añaden las columnas de barrio, comuna y zona. La salida ya no es igual a la anterior.
**Migration**: Los valores del vocabulario se conservan (requisito "Vocabulario incluido"). Para el nuevo comportamiento, ver la especificación `normalizacion-direcciones`. Hay que volver a ejecutar la estandarización; no consume la API.
