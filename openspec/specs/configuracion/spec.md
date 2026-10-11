# configuracion Specification

## Purpose

Define el archivo de configuración del proyecto: dónde está, qué valores del dominio contiene (área metropolitana, subconjuntos, columnas de entrada y vocabulario de direcciones), cómo se valida al arrancar y cómo se usa un archivo alternativo, para que esos valores cambien sin editar el código.

## Requirements

### Requirement: Archivo de configuración versionado
El sistema SHALL leer su configuración de `config/georef.toml`, un archivo TOML en UTF-8 versionado en el repositorio. Debe contener la lista de municipios del área metropolitana, los subconjuntos con nombre, los nombres de las columnas de ciudad y dirección del archivo de entrada, y el vocabulario de direcciones: tipos de vía, palabras clave y equivalencias.

#### Scenario: Ejecución con la configuración incluida
- **WHEN** el usuario ejecuta cualquier operación sin indicar otra configuración
- **THEN** el sistema usa los valores de `config/georef.toml`

#### Scenario: Valores y texto en español
- **WHEN** la configuración contiene municipios, equivalencias o columnas con tildes (por ejemplo `NÚMERO`)
- **THEN** el sistema los usa tal como están escritos, sin quitar tildes ni otros caracteres

### Requirement: La configuración incluida reproduce el comportamiento anterior
Los valores de `config/georef.toml` SHALL ser los que tenía el código antes de este cambio: los mismos 10 municipios del área metropolitana, los mismos tipos de vía y palabras clave, y las mismas equivalencias en el mismo orden. Con esa configuración, la estandarización MUST producir los mismos registros y valores que antes.

#### Scenario: Misma estandarización
- **WHEN** se estandariza un mismo archivo de entrada antes y después del cambio, con la configuración incluida
- **THEN** los cuatro archivos de `estandarizado/` tienen las mismas filas, columnas y valores

#### Scenario: El orden de las equivalencias se conserva
- **WHEN** se estandariza la dirección `CR 50 NORTE 30 20` con la configuración incluida
- **THEN** el resultado es el mismo que antes del cambio, porque las equivalencias se aplican en el orden en que aparecen en la configuración

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
