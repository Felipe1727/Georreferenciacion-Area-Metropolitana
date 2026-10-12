# configuracion Specification

## Purpose

Define el archivo de configuración del proyecto: dónde está, qué valores del dominio contiene (área metropolitana, subconjuntos, columnas de entrada y vocabulario de direcciones), cómo se valida al arrancar y cómo se usa un archivo alternativo, para que esos valores cambien sin editar el código.

## Requirements

### Requirement: Archivo de configuración versionado
El sistema SHALL leer su configuración de `config/georef.toml`, un archivo TOML en UTF-8 versionado en el repositorio. Debe contener la lista de municipios del área metropolitana, los subconjuntos con nombre, los nombres de las columnas de ciudad y dirección del archivo de entrada, el vocabulario de direcciones (tipos de vía, palabras clave y equivalencias) y las referencias geográficas (rutas del GeoJSON y de las tablas de alias, y el municipio al que corresponden los polígonos).

#### Scenario: Ejecución con la configuración incluida
- **WHEN** el usuario ejecuta cualquier operación sin indicar otra configuración
- **THEN** el sistema usa los valores de `config/georef.toml`

#### Scenario: Valores y texto en español
- **WHEN** la configuración contiene municipios, equivalencias o columnas con tildes (por ejemplo `NÚMERO`)
- **THEN** el sistema los usa tal como están escritos, sin quitar tildes ni otros caracteres

### Requirement: Cambios del dominio sin editar el código
Añadir o quitar un municipio del área metropolitana, definir un subconjunto o cambiar el vocabulario de direcciones SHALL requerir solo editar la configuración.

#### Scenario: Nuevo municipio en el área metropolitana
- **WHEN** el usuario añade `RIONEGRO - ANTIOQUIA` a los municipios del área metropolitana y ejecuta la estandarización
- **THEN** los registros de Rionegro se incluyen en los archivos del área metropolitana y dejan de aparecer en `fuera_area_metropolitana.xlsx`

#### Scenario: Nuevo subconjunto
- **WHEN** el usuario define un subconjunto `sur` con municipios del área metropolitana y extrae ese subconjunto
- **THEN** el sistema genera sus archivos sin que haya que modificar el código

### Requirement: Configuración alternativa
El usuario SHALL poder indicar otro archivo de configuración con la opción `--config <ruta>`. Si el archivo indicado, o `config/georef.toml` cuando no se indica ninguno, no existe o no es TOML válido, el sistema MUST terminar con código distinto de cero y un mensaje que nombre el archivo, sin leer datos ni escribir archivos.

#### Scenario: Archivo alternativo
- **WHEN** el usuario ejecuta una operación con `--config otra.toml` y ese archivo es válido
- **THEN** el sistema usa los valores de `otra.toml`

#### Scenario: Archivo inexistente
- **WHEN** el usuario indica `--config no_existe.toml`
- **THEN** el sistema termina con código distinto de cero, el mensaje nombra `no_existe.toml` y no se crea ni modifica ningún archivo de salida

#### Scenario: Sintaxis TOML inválida
- **WHEN** el archivo de configuración tiene un error de sintaxis
- **THEN** el sistema termina con un mensaje que indica el archivo y la línea del error

### Requirement: Validación de la configuración al arrancar
Antes de leer datos o consultar al proveedor, el sistema SHALL validar la configuración y, si hay errores, MUST terminar con código distinto de cero mostrando todos los errores encontrados a la vez, cada uno con la clave a la que se refiere.

#### Scenario: Clave desconocida
- **WHEN** la configuración tiene una clave que el sistema no reconoce (por ejemplo, una errata como `municipio` en lugar de `municipios`)
- **THEN** el sistema termina con un mensaje que nombra la clave desconocida

#### Scenario: Clave obligatoria ausente o lista vacía
- **WHEN** falta la lista de municipios del área metropolitana, o está vacía
- **THEN** el sistema termina con un mensaje que nombra esa clave

#### Scenario: Valores repetidos
- **WHEN** un municipio aparece dos veces en la misma lista, o una palabra tiene dos equivalencias
- **THEN** el sistema termina con un mensaje que nombra el valor repetido

#### Scenario: Varios errores a la vez
- **WHEN** la configuración tiene una clave desconocida y además una lista vacía
- **THEN** el mensaje informa de los dos errores en la misma ejecución

#### Scenario: Ningún efecto con configuración inválida
- **WHEN** la configuración es inválida y el usuario ejecuta la conversión de coordenadas
- **THEN** el sistema no consulta al proveedor y no modifica ningún archivo

### Requirement: Columnas configuradas presentes en el archivo de entrada
Si el archivo de entrada no tiene alguna de las columnas de ciudad o dirección configuradas, el sistema MUST terminar con código distinto de cero y un mensaje que nombre la columna que falta, sin escribir archivos de salida.

#### Scenario: Columna ausente
- **WHEN** la configuración indica la columna de ciudad `Ciudad Residencia` y el archivo de entrada no la tiene
- **THEN** el sistema termina con un mensaje que nombra `Ciudad Residencia` y `estandarizado/` queda sin cambios

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
