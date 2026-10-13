# Spec Delta

## MODIFIED Requirements

### Requirement: Archivo de configuración versionado
El sistema SHALL leer su configuración de `config/georef.toml`, un archivo TOML en UTF-8 versionado en el repositorio. Debe contener la lista de municipios del área metropolitana, los subconjuntos con nombre, los nombres de las columnas de ciudad y dirección del archivo de entrada, el vocabulario de direcciones (tipos de vía, palabras clave y equivalencias), las referencias geográficas (rutas del GeoJSON y de las tablas de alias, y el municipio al que corresponden los polígonos), los parámetros de la ubicación y, una vez consultados, los puntos de los municipios.

#### Scenario: Ejecución con la configuración incluida
- **WHEN** el usuario ejecuta cualquier operación sin indicar otra configuración
- **THEN** el sistema usa los valores de `config/georef.toml`

#### Scenario: Valores y texto en español
- **WHEN** la configuración contiene municipios, equivalencias o columnas con tildes (por ejemplo `NÚMERO`)
- **THEN** el sistema los usa tal como están escritos, sin quitar tildes ni otros caracteres

## ADDED Requirements

### Requirement: Parámetros de la ubicación
La sección obligatoria `[ubicacion]` SHALL definir `formato_consulta`, `confianza_minima`, `tipos_rechazados`, `tolerancia_metros`, `pausa_segundos`, `limite_consultas`, `consulta_lugar_complemento`, `palabras_lugar` y `nombres_via`. Si falta alguna de esas claves, la validación MUST fallar con un mensaje que la nombre.

#### Scenario: Valores incluidos
- **WHEN** se usa la configuración incluida
- **THEN** `formato_consulta` es `abreviado`, `tolerancia_metros` es 250, `pausa_segundos` es 1, `consulta_lugar_complemento` es falso y `tipos_rechazados` contiene `city`

#### Scenario: Clave ausente
- **WHEN** `[ubicacion]` no tiene `tolerancia_metros`
- **THEN** la validación falla con un mensaje que nombra `ubicacion.tolerancia_metros`

### Requirement: Valores válidos de la ubicación
La validación SHALL comprobar los valores de `[ubicacion]`:
- `formato_consulta` es `abreviado` o `expandido`;
- `confianza_minima` es un entero de 0 a 10;
- `tolerancia_metros` y `pausa_segundos` son números no negativos;
- `limite_consultas` es un entero positivo;
- `nombres_via` tiene un nombre para cada tipo de vía configurado.

Cada valor no válido MUST producir un error que nombre su clave.

#### Scenario: Formato desconocido
- **WHEN** `formato_consulta` es `completo`
- **THEN** la validación falla con un mensaje que nombra `ubicacion.formato_consulta` y los valores válidos

#### Scenario: Tipo de vía sin nombre
- **WHEN** `tipos_via` incluye `CIR` y `nombres_via` no tiene nombre para `CIR`
- **THEN** la validación falla con un mensaje que nombra `ubicacion.nombres_via` y `CIR`

### Requirement: Validación de los puntos de los municipios
La sección `[puntos_municipios]` SHALL ser opcional y, si existe, asociar municipios del área metropolitana a tablas con `latitud` (entre -90 y 90), `longitud` (entre -180 y 180), `fuente` y `fecha`. Un municipio que no pertenece al área metropolitana o un valor fuera de rango MUST hacer fallar la validación con un mensaje que nombre la clave.

#### Scenario: Municipio fuera del área
- **WHEN** `[puntos_municipios]` incluye `RIONEGRO - ANTIOQUIA`, que no está en el área metropolitana
- **THEN** la validación falla con un mensaje que nombra `puntos_municipios` y `RIONEGRO - ANTIOQUIA`

#### Scenario: Latitud fuera de rango
- **WHEN** la latitud de un municipio es 95
- **THEN** la validación falla con un mensaje que nombra la clave de esa latitud

#### Scenario: Sección ausente
- **WHEN** la configuración no tiene `[puntos_municipios]` y el usuario ejecuta la estandarización
- **THEN** la configuración es válida y la estandarización termina con normalidad
