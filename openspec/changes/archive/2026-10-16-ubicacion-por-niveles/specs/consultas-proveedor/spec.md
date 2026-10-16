# Spec Delta

## Purpose

Define cómo consulta el sistema al proveedor de geocodificación (OpenCage) dentro de la cuota del free trial: el texto de cada consulta, el ritmo de las peticiones, la caché que evita repetirlas, las paradas ante cuota agotada o errores, el registro de diagnóstico y los subcomandos que consultan los municipios y comparan formatos.

## ADDED Requirements

### Requirement: Texto de la consulta
La consulta de un registro SHALL formarse con su `Direccion de residencia`, seguida del municipio y el departamento de la columna de ciudad y de `Colombia`: `CL 10 #20-30, MEDELLIN, ANTIOQUIA, Colombia`. Nunca incluye `Complemento`, `Barrio` ni `Zona`. El formato `expandido` sustituye el tipo de vía por su nombre de `nombres_via` y separa `#` del número.

#### Scenario: Formato abreviado
- **WHEN** `formato_consulta` es `abreviado` y el registro de Medellín tiene la dirección `CL 10 #20-30` y el complemento `APTO 301`
- **THEN** la consulta es `CL 10 #20-30, MEDELLIN, ANTIOQUIA, Colombia`

#### Scenario: Formato expandido
- **WHEN** `formato_consulta` es `expandido` y la dirección es `CL 10 #20-30`
- **THEN** la consulta es `Calle 10 # 20-30, MEDELLIN, ANTIOQUIA, Colombia`

#### Scenario: Departamento sin repetir
- **WHEN** se forma cualquier consulta de un registro de `MEDELLIN - ANTIOQUIA`
- **THEN** `ANTIOQUIA` aparece una sola vez en la consulta

### Requirement: Parámetros de la petición
Cada petición SHALL pedir un único resultado, limitado a Colombia y sin anotaciones. Las peticiones de registros de Medellín se limitan además al recuadro que contiene sus polígonos. Se usa el primer resultado devuelto.

#### Scenario: Petición de un registro de Medellín
- **WHEN** se consulta un registro de Medellín
- **THEN** la petición lleva `countrycode` igual a `co`, `limit` igual a `1`, `no_annotations` igual a `1` y `bounds` con el recuadro de los polígonos de Medellín

#### Scenario: Petición de un municipio
- **WHEN** `consultar-municipios` consulta `BELLO - ANTIOQUIA`
- **THEN** la petición lleva `countrycode`, `limit` y `no_annotations`, pero no `bounds`

### Requirement: Pausa entre peticiones
Entre el inicio de dos peticiones consecutivas cualesquiera SHALL pasar al menos `pausa_segundos` (1 s en la configuración incluida), también cuando la petición anterior terminó en error.

#### Scenario: Petición tras un error
- **WHEN** una petición lanza un error transitorio y el proceso sigue con la consulta siguiente
- **THEN** la siguiente petición empieza al menos `pausa_segundos` después del inicio de la anterior

### Requirement: Caché de consultas
Cada respuesta correcta del proveedor, con resultado o sin él, SHALL guardarse en `coordenadas/cache_consultas.csv` en cuanto se recibe, una línea por consulta. Una consulta que ya está en la caché MUST NOT repetirse. Las respuestas con error no se guardan y se reintentan en la ejecución siguiente.

#### Scenario: Misma dirección en dos registros
- **WHEN** dos registros de Medellín producen la misma consulta
- **THEN** se hace una sola petición y los dos registros reciben el mismo resultado

#### Scenario: Ejecución interrumpida
- **WHEN** el usuario interrumpe la ubicación después de 40 peticiones y la vuelve a ejecutar
- **THEN** esas 40 consultas se resuelven desde la caché sin ninguna petición

#### Scenario: Consulta sin resultado
- **WHEN** el proveedor responde sin resultados a una consulta
- **THEN** la consulta queda en la caché como sin resultado, el registro tiene `Resultado consulta` igual a `SIN_RESULTADO` y la ejecución siguiente no la repite

### Requirement: Paradas sin pérdida
El proceso SHALL dejar de hacer peticiones, sin perder lo ya obtenido, en tres casos:
- el proveedor indica cuota o ritmo excedidos;
- se producen `3` errores seguidos;
- se alcanza `limite_consultas` en la ejecución.

Las consultas no hechas quedan con `Resultado consulta` igual a `PENDIENTE`, sus registros reciben el nivel siguiente disponible y el archivo de coordenadas se escribe igualmente.

#### Scenario: Cuota agotada a mitad de la ejecución
- **WHEN** el proveedor rechaza una petición por cuota o ritmo excedidos
- **THEN** no se hace ninguna petición más, el archivo de coordenadas se escribe con los registros restantes como `PENDIENTE` y el mensaje indica que volver a ejecutar continuará desde ese punto

#### Scenario: Errores seguidos
- **WHEN** tres peticiones seguidas terminan en error
- **THEN** el proceso deja de consultar y el resumen informa de la parada por errores

#### Scenario: Límite por ejecución
- **WHEN** `limite_consultas` es 100 y hay 300 consultas que no están en la caché
- **THEN** se hacen 100 peticiones y 200 consultas quedan `PENDIENTE`

#### Scenario: Error aislado
- **WHEN** una petición termina en error y la siguiente responde bien
- **THEN** solo el registro de la petición fallida queda `PENDIENTE` y el proceso continúa

### Requirement: Llave rechazada
Si el proveedor rechaza la llave (no autorizada o bloqueada), el sistema MUST terminar con código distinto de cero y un mensaje que lo indique, sin escribir el archivo de coordenadas y sin mostrar la llave.

#### Scenario: Llave inválida
- **WHEN** la primera petición devuelve que la llave no está autorizada
- **THEN** el sistema termina con un mensaje sobre la llave de `OPENCAGE_API_KEY` y el archivo de coordenadas queda sin cambios

### Requirement: Ubicación sin consultas
`ubicar --sin-consultas` SHALL ubicar todos los registros sin hacer ninguna petición y sin exigir la llave. Las consultas que estén en la caché se usan; las demás quedan `PENDIENTE`.

#### Scenario: Sin llave
- **WHEN** `OPENCAGE_API_KEY` no está definida y el usuario ejecuta `python -m georef ubicar --sin-consultas`
- **THEN** el archivo de coordenadas se escribe con todos los registros ubicados y no se hace ninguna petición

### Requirement: Registro de diagnóstico
Cada petición SHALL añadir una línea a `coordenadas/registro_consultas.csv` con:
- fecha y hora en UTC;
- operación (`ubicar`, `comparar` o `municipios`);
- índice del registro o nombre del municipio;
- duración en milisegundos;
- resultado (con o sin resultado, o nombre del error);
- peticiones restantes, si la respuesta las informa;
- tipo y `confidence` del primer resultado.

MUST NOT contener la llave ni el texto de la consulta.

#### Scenario: Petición correcta
- **WHEN** se hace una petición que devuelve un resultado y la respuesta informa las peticiones restantes
- **THEN** el registro gana una línea con la duración, el tipo, la `confidence` y las peticiones restantes

#### Scenario: Petición con error
- **WHEN** una petición termina en error
- **THEN** el registro gana una línea con el nombre del error

### Requirement: Consulta única de los puntos de los municipios
`python -m georef consultar-municipios` SHALL consultar una vez al proveedor cada municipio del área metropolitana que no tenga punto en `[puntos_municipios]`, con la consulta `<MUNICIPIO>, <DEPARTAMENTO>, Colombia`. Por cada municipio muestra el punto, el tipo y el texto devueltos para que el usuario los revise.

#### Scenario: Todos los puntos presentes
- **WHEN** todos los municipios del área ya tienen punto
- **THEN** no se hace ninguna petición y el mensaje lo indica

#### Scenario: Municipio sin resultado
- **WHEN** el proveedor no devuelve resultado para un municipio
- **THEN** ese municipio no se escribe y el mensaje pide añadir su punto a mano

### Requirement: Escritura de los puntos en la configuración
Si la configuración no tiene `[puntos_municipios]`, `consultar-municipios` SHALL añadir esa sección al final del archivo de configuración, con la latitud, la longitud, la fuente `OpenCage` y la fecha de cada municipio, sin cambiar el resto del archivo. Si la sección ya existe, MUST NOT modificar el archivo: muestra las líneas que hay que añadir a mano.

#### Scenario: Primera consulta
- **WHEN** la configuración no tiene `[puntos_municipios]` y el usuario ejecuta `consultar-municipios`
- **THEN** se hacen 10 peticiones, el archivo de configuración gana la sección con los 10 municipios y sigue siendo válido, y el resto del archivo no cambia

#### Scenario: Sección ya existente con un municipio nuevo
- **WHEN** `[puntos_municipios]` existe pero le falta un municipio añadido al área metropolitana
- **THEN** se hace una sola petición, el archivo no cambia y la consola muestra la línea de ese municipio para copiarla

### Requirement: Diagnóstico de formatos de consulta
`python -m georef comparar-consultas --muestra N` SHALL tomar una muestra reproducible de hasta N consultas distintas de registros de Medellín con barrio declarado con código. Consulta cada una en los formatos `abreviado` y `expandido`, usando y llenando la caché. No escribe el archivo de coordenadas.

#### Scenario: Muestra de 50
- **WHEN** el usuario ejecuta `comparar-consultas --muestra 50` con la caché vacía
- **THEN** se hacen como máximo 100 peticiones

#### Scenario: Muestra repetida
- **WHEN** el usuario repite el mismo comando
- **THEN** se usa la misma muestra, todas sus consultas salen de la caché y no se hace ninguna petición

### Requirement: Cifras del diagnóstico de formatos
Por cada formato, el diagnóstico SHALL mostrar solo cifras agregadas:
- consultas con resultado;
- distribución de tipos y `confidence` mediana;
- porcentaje de puntos dentro del barrio declarado y a `tolerancia_metros` o menos;
- distancia mediana al barrio declarado.

MUST NOT mostrar direcciones ni otros datos de un registro.

#### Scenario: Informe del diagnóstico
- **WHEN** termina `comparar-consultas`
- **THEN** la consola muestra esas cifras para `abreviado` y para `expandido`, y ninguna dirección
