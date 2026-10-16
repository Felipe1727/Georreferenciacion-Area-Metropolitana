# ubicacion-por-niveles Specification

## Purpose

Define qué punto recibe cada registro del área metropolitana y con qué precisión: los niveles de ubicación, la validación del punto de la API con el lugar que declaró el estudiante, las columnas del archivo de coordenadas y los puntos fijos de los municipios.

## Requirements

### Requirement: Niveles de ubicación
La ubicación SHALL asignar a cada registro del área metropolitana, tanto de vía principal como especial, un punto y un `Nivel ubicacion`. Se usa el primer nivel disponible de este orden: `DIRECCION` (punto de la API validado), `BARRIO` (barrio declarado con código), `COMUNA` (comuna declarada) y `MUNICIPIO` (punto del municipio). Ningún registro del área queda sin punto.

#### Scenario: Barrio declarado sin consulta aceptada
- **WHEN** un registro de Medellín tiene `Codigo barrio` y su consulta a la API no se acepta
- **THEN** su punto es el punto representativo del polígono de ese barrio y `Nivel ubicacion` es `BARRIO`

#### Scenario: Solo comuna
- **WHEN** un registro de Medellín no tiene `Codigo barrio`, tiene `Comuna` igual a `EL POBLADO` y no tiene consulta aceptada
- **THEN** su punto es el punto representativo de la unión de los polígonos de la comuna El Poblado y `Nivel ubicacion` es `COMUNA`

#### Scenario: Sin lugar reconocido
- **WHEN** un registro de Medellín no tiene ni `Codigo barrio` ni `Comuna`, o su barrio es un nombre repetido sin resolver, y no tiene consulta aceptada
- **THEN** su punto es el de Medellín en `[puntos_municipios]` y `Nivel ubicacion` es `MUNICIPIO`

#### Scenario: Registro especial de Medellín
- **WHEN** se ubica `VEREDA EL PLAN -*- RURAL`, de Medellín, con `Barrio` igual a `El Plan`
- **THEN** no se consulta a la API y `Nivel ubicacion` es `BARRIO`

### Requirement: Solo las vías principales de Medellín se consultan
La ubicación SHALL consultar a la API solo los registros de vía principal del municipio con polígonos. Los registros de los otros municipios del área MUST recibir el punto de su municipio, con `Nivel ubicacion` igual a `MUNICIPIO`, sin ninguna consulta.

#### Scenario: Registro de Envigado
- **WHEN** se ubica `CR 43A #1-50`, de Envigado
- **THEN** no se hace ninguna consulta, el punto es el de `ENVIGADO - ANTIOQUIA` en `[puntos_municipios]` y `Resultado consulta` es `SIN_CONSULTA`

### Requirement: Punto representativo dentro del polígono
El punto de los niveles `BARRIO` y `COMUNA` SHALL ser el punto representativo del polígono (o de la unión de los polígonos de la comuna), calculado en EPSG:9377 y transformado a WGS84. Ese punto está siempre dentro de su polígono, a diferencia del centroide.

#### Scenario: Barrio de forma cóncava
- **WHEN** se ubica a nivel `BARRIO` un registro de un barrio cuyo centroide cae fuera de su polígono
- **THEN** el punto asignado está dentro del polígono del barrio

### Requirement: Aceptación del punto de la API
Un resultado de la API SHALL aceptarse como `DIRECCION` solo si cumple todo esto:
- su tipo no está en `tipos_rechazados`;
- su `confidence` es al menos `confianza_minima`;
- está a `tolerancia_metros` o menos de Medellín;
- si el registro declara un barrio con código, o en su defecto una comuna, está a `tolerancia_metros` o menos de ese polígono.

Las distancias se miden en EPSG:9377.

#### Scenario: Resultado de nivel ciudad
- **WHEN** la API devuelve para un registro un resultado de tipo `city`
- **THEN** el resultado se rechaza, `Resultado consulta` es `PRECISION_INSUFICIENTE` y el registro pasa al nivel siguiente

#### Scenario: Confianza insuficiente
- **WHEN** la `confidence` del resultado es menor que `confianza_minima`
- **THEN** el resultado se rechaza con `PRECISION_INSUFICIENTE`

#### Scenario: Punto fuera de Medellín
- **WHEN** el punto devuelto está a más de `tolerancia_metros` del límite de Medellín
- **THEN** el resultado se rechaza con `FUERA_DEL_MUNICIPIO`

#### Scenario: Punto dentro de la tolerancia del barrio declarado
- **WHEN** el registro declara el barrio Laureles y el punto devuelto, de tipo y confianza aceptables, cae a 120 m del polígono de Laureles, con una tolerancia de 250 m
- **THEN** el punto se acepta, `Nivel ubicacion` es `DIRECCION` y `Resultado consulta` es `ACEPTADA`

#### Scenario: Prevalece el lugar declarado
- **WHEN** el registro declara el barrio Laureles y el punto devuelto cae a 2 km de su polígono
- **THEN** el resultado se rechaza con `LEJOS_DEL_LUGAR_DECLARADO` y el registro se ubica en el punto representativo de Laureles con `Nivel ubicacion` igual a `BARRIO`

#### Scenario: Sin lugar declarado
- **WHEN** el registro no declara ni barrio con código ni comuna, y el resultado tiene tipo y confianza aceptables y cae en Medellín
- **THEN** el punto se acepta como `DIRECCION`

### Requirement: Consulta con el lugar del complemento
Si `consulta_lugar_complemento` está activada, la consulta de un registro no se acepta y su `Complemento` contiene una de las `palabras_lugar`, la ubicación SHALL hacer una segunda consulta con el texto del complemento desde esa palabra, seguido del barrio o la comuna declarados, si los hay, y del municipio. Ese resultado se acepta con los mismos criterios y queda como `ACEPTADA_LUGAR`. La opción está desactivada en la configuración incluida.

#### Scenario: Opción desactivada
- **WHEN** se usa la configuración incluida y la consulta de un registro con `Complemento` igual a `APTO 301 UNIDAD LOS PINOS` se rechaza
- **THEN** no se hace ninguna segunda consulta

#### Scenario: Opción activada
- **WHEN** la opción está activada, la consulta de ese registro se rechaza y su barrio declarado es Laureles
- **THEN** se hace una segunda consulta que empieza por `UNIDAD LOS PINOS, LAURELES` y no contiene `APTO 301`

### Requirement: Columnas del archivo de coordenadas
El archivo de coordenadas SHALL conservar todas las columnas e índices de `estandarizado/` y añadir `Latitud`, `Longitud`, `Nivel ubicacion`, `Resultado consulta`, `Barrio ubicacion`, `Codigo barrio ubicacion` y `Comuna ubicacion`. Las columnas `... ubicacion` indican el polígono de Medellín que contiene el punto asignado.

#### Scenario: Registro a nivel de dirección
- **WHEN** un registro se ubica a nivel `DIRECCION` y su punto cae en el barrio Laureles
- **THEN** `Barrio ubicacion` es `Laureles`, `Codigo barrio ubicacion` es su código como texto y `Comuna ubicacion` es su comuna

#### Scenario: Registro a nivel de comuna
- **WHEN** un registro se ubica a nivel `COMUNA`
- **THEN** `Comuna ubicacion` es esa comuna y `Barrio ubicacion` y `Codigo barrio ubicacion` quedan vacíos

#### Scenario: Registro a nivel de municipio
- **WHEN** un registro se ubica a nivel `MUNICIPIO`
- **THEN** las tres columnas `... ubicacion` quedan vacías

#### Scenario: Metadatos de la API fuera del Excel
- **WHEN** se abre el archivo de coordenadas
- **THEN** no contiene ni la `confidence`, ni el tipo, ni el texto devuelto por la API

### Requirement: Valores de `Resultado consulta`
`Resultado consulta` SHALL tomar uno de estos valores: `ACEPTADA`, `ACEPTADA_LUGAR`, `SIN_RESULTADO`, `PRECISION_INSUFICIENTE`, `FUERA_DEL_MUNICIPIO`, `LEJOS_DEL_LUGAR_DECLARADO`, `PENDIENTE` o `SIN_CONSULTA`. `SIN_CONSULTA` corresponde a los registros que no se consultan: otros municipios y registros especiales.

#### Scenario: Valores posibles
- **WHEN** se ubica cualquier archivo de entrada
- **THEN** cada registro tiene en `Resultado consulta` exactamente uno de esos ocho valores

#### Scenario: Registro especial
- **WHEN** se ubica un registro especial de Medellín
- **THEN** su `Resultado consulta` es `SIN_CONSULTA`

### Requirement: Puntos de los municipios
La sección `[puntos_municipios]` de la configuración SHALL dar a cada municipio del área metropolitana una latitud, una longitud, una fuente y una fecha. Si falta el punto de algún municipio del área, la ubicación MUST terminar antes de consultar a la API, con un mensaje que nombre los municipios que faltan y el subcomando `consultar-municipios`.

#### Scenario: Municipio sin punto
- **WHEN** `[puntos_municipios]` no tiene `CALDAS - ANTIOQUIA` y el usuario ejecuta `ubicar`
- **THEN** el sistema termina con código distinto de cero, el mensaje nombra `CALDAS - ANTIOQUIA` y `consultar-municipios`, y no se hace ninguna consulta ni se escribe el archivo de coordenadas

#### Scenario: Punto corregido a mano
- **WHEN** el usuario cambia a mano la latitud de `BELLO - ANTIOQUIA` en la configuración y vuelve a ejecutar `ubicar`
- **THEN** los registros de Bello reciben el punto nuevo sin ninguna consulta a la API

### Requirement: Resumen de la ubicación
Al terminar, la ubicación SHALL mostrar solo cifras agregadas:
- registros por `Nivel ubicacion`;
- registros por `Resultado consulta`;
- peticiones hechas y consultas resueltas desde la caché;
- consultas pendientes y, si lo hay, el motivo por el que se dejó de consultar.

MUST NOT mostrar direcciones ni otros datos de un registro.

#### Scenario: Ejecución completa
- **WHEN** termina una ubicación sin paradas
- **THEN** la consola muestra el número de registros por nivel y por resultado, y ninguna dirección
