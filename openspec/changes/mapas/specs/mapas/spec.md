# Spec Delta

## Purpose

Define los mapas HTML que el sistema genera para un área a partir de su archivo de coordenadas: el mapa con capas, cómo se dibujan los puntos de cada nivel de ubicación, qué información muestran, las capas de comunas y barrios de Medellín, el encuadre y los mapas separados para compartir.

## ADDED Requirements

### Requirement: Mapa con capas de un área
La generación de mapas SHALL escribir `mapas/<area>/mapa.html`, un único HTML con un control de capas, a partir de `coordenadas/coordenadas_<area>.xlsx`:
- una capa de puntos por nivel (`DIRECCION`, `BARRIO`, `COMUNA` y `MUNICIPIO`), visibles al abrir;
- las capas "Clusters" (todos los registros) y "Clusters sin MUNICIPIO", ocultas al abrir.

No consulta al proveedor ni exige la llave.

#### Scenario: Mapa del área metropolitana
- **WHEN** existe el archivo de coordenadas del área metropolitana y el usuario genera los mapas
- **THEN** el sistema escribe `mapas/area_metropolitana/mapa.html` con las cuatro capas de nivel y las dos de clusters en el control de capas

#### Scenario: Clusters con y sin MUNICIPIO
- **WHEN** el archivo de coordenadas tiene 3 registros a nivel `BARRIO` y 2 a nivel `MUNICIPIO` y el usuario genera los mapas
- **THEN** la capa "Clusters" contiene 5 puntos y la capa "Clusters sin MUNICIPIO" contiene 3

#### Scenario: Nivel sin registros
- **WHEN** ningún registro del área tiene nivel `COMUNA`
- **THEN** el mapa no incluye la capa `COMUNA` y sí las de los demás niveles

### Requirement: Puntos agrupados por sitio
En cada capa de nivel, los registros con la misma latitud y longitud SHALL dibujarse como un solo círculo del color fijo de su nivel. El tamaño del círculo crece con el número de registros y, si hay más de uno, el número se muestra dentro. El mapa incluye una leyenda con los cuatro niveles y sus colores.

#### Scenario: Varios registros en el punto de un barrio
- **WHEN** 9 registros de nivel `BARRIO` tienen el punto representativo del mismo barrio
- **THEN** la capa `BARRIO` tiene un solo círculo en ese punto con el número 9, más grande que el de un punto con un solo registro

#### Scenario: Un solo registro
- **WHEN** un punto de nivel `DIRECCION` corresponde a un único registro
- **THEN** se dibuja un círculo del color de `DIRECCION` sin número

#### Scenario: Mismo punto en distinto nivel
- **WHEN** un registro de nivel `DIRECCION` y otro de nivel `MUNICIPIO` tienen la misma latitud y longitud
- **THEN** se dibujan dos círculos, uno en la capa de cada nivel

### Requirement: Ventana de un punto solo con datos de ubicación
Al hacer clic en un círculo, el mapa SHALL mostrar el nivel, el municipio y, si existen, el barrio y la comuna de ubicación, el número de registros y cuántos hay de cada `Resultado consulta`. Ningún mapa MUST incluir la dirección, el complemento ni ninguna otra columna del archivo de entrada salvo el municipio.

#### Scenario: Ventana de un punto de barrio
- **WHEN** el usuario hace clic en el círculo de un barrio con 5 registros, 3 con `PRECISION_INSUFICIENTE` y 2 con `SIN_CONSULTA`
- **THEN** la ventana muestra el nivel `BARRIO`, el municipio, el nombre del barrio, su comuna, 5 registros y esos dos recuentos

#### Scenario: Sin datos del estudiante
- **WHEN** el archivo de coordenadas tiene columnas con la dirección, el complemento y otros datos de los estudiantes
- **THEN** ningún HTML generado contiene esos valores

### Requirement: Capas de comunas y barrios de Medellín
Si el área incluye el municipio con polígonos de la configuración, el mapa con capas SHALL incluir el contorno de las comunas (visible al abrir), el contorno de los barrios, y los barrios y las comunas coloreados por cantidad de registros (ocultos al abrir). Al pasar el ratón por un polígono se muestra su nombre y, en las capas coloreadas, su cantidad. Si el área no incluye ese municipio, esas capas no se generan.

#### Scenario: Área metropolitana
- **WHEN** el usuario genera los mapas del área metropolitana
- **THEN** `mapa.html` incluye las capas de contorno de comunas, contorno de barrios, barrios por cantidad y comunas por cantidad, y solo la de contorno de comunas está visible al abrir

#### Scenario: Subconjunto sin Medellín
- **WHEN** un subconjunto solo contiene `BELLO - ANTIOQUIA` y el usuario lo extrae
- **THEN** su `mapa.html` no incluye ninguna capa de polígonos

### Requirement: Cantidades de las capas coloreadas
La cantidad de un barrio SHALL ser el número de registros cuyo `Codigo barrio ubicacion` es el de ese barrio, y la de una comuna el número de registros cuya `Comuna ubicacion` es esa comuna. Los polígonos sin registros se distinguen de los que tienen alguno, y cada capa coloreada tiene una escala con el rango de cantidades.

#### Scenario: Cantidad por barrio y por comuna
- **WHEN** en Laureles hay 3 registros de nivel `BARRIO` y 1 de nivel `DIRECCION`, y en su comuna hay además 1 registro de nivel `COMUNA`
- **THEN** la cantidad de Laureles es 4 y la de su comuna es 5

#### Scenario: Registros de nivel MUNICIPIO
- **WHEN** un registro de Medellín tiene nivel `MUNICIPIO`
- **THEN** no cuenta en ningún barrio ni en ninguna comuna

### Requirement: Encuadre a los datos
Cada mapa SHALL abrirse encuadrado en sus datos, en lugar de un centro y un zoom fijos: los mapas de puntos y de clusters, en los puntos dibujados, y los mapas coloreados, en los polígonos de Medellín. Si los datos ocupan un área muy pequeña, como un único punto, el encuadre no supera el nivel de zoom 15.

#### Scenario: Subconjunto de un municipio
- **WHEN** todos los registros de un subconjunto están en Barbosa y el usuario lo extrae
- **THEN** su mapa se abre encuadrado en el rectángulo que contiene esos puntos

#### Scenario: Un único punto
- **WHEN** el área tiene un solo punto
- **THEN** el mapa se abre centrado en ese punto con zoom 15 como máximo

### Requirement: Mapas separados a elección
Con `--separado <vista>` (repetible), la generación de mapas SHALL escribir además `mapas/<area>/separados/<vista>.html`, un HTML autónomo con su leyenda y su encuadre. Las vistas son:
- `puntos`: las cuatro capas de nivel;
- `clusters`: todos los registros;
- `barrios_cantidad` y `comunas_cantidad`: las capas coloreadas.

`todos` equivale a todas las vistas disponibles para el área. `mapa.html` se genera siempre.

#### Scenario: Dos separados
- **WHEN** el usuario ejecuta `python -m georef mapas --separado puntos --separado comunas_cantidad`
- **THEN** el sistema escribe `mapa.html`, `separados/puntos.html` y `separados/comunas_cantidad.html` en `mapas/area_metropolitana/`, y ningún otro separado

#### Scenario: Sin separados
- **WHEN** el usuario ejecuta `python -m georef mapas`
- **THEN** el sistema escribe solo `mapa.html` y no crea `separados/`

#### Scenario: Vista desconocida
- **WHEN** el usuario ejecuta `python -m georef mapas --separado calor`
- **THEN** el sistema termina con código distinto de cero, lista las vistas válidas y no escribe ningún mapa

### Requirement: Separados sin el nivel MUNICIPIO
Con `--sin-municipio`, los separados `puntos` y `clusters` SHALL excluir los registros de nivel `MUNICIPIO` y escribirse como `puntos_sin_municipio.html` y `clusters_sin_municipio.html`. La opción no cambia `mapa.html` ni los separados coloreados. Usarla sin `--separado` termina con un mensaje, sin escribir mapas.

#### Scenario: Puntos sin MUNICIPIO
- **WHEN** el archivo tiene 3 registros a nivel `BARRIO` y 2 a nivel `MUNICIPIO` y el usuario ejecuta `python -m georef mapas --separado puntos --sin-municipio`
- **THEN** `separados/puntos_sin_municipio.html` no incluye la capa `MUNICIPIO` y no se escribe `separados/puntos.html`

#### Scenario: Opción sin separados
- **WHEN** el usuario ejecuta `python -m georef mapas --sin-municipio`
- **THEN** el sistema termina con un mensaje que indica que la opción requiere `--separado` y no escribe mapas

### Requirement: Separados coloreados solo con polígonos
Si se pide por su nombre `barrios_cantidad` o `comunas_cantidad` para un área que no incluye el municipio con polígonos, el sistema MUST terminar con un mensaje antes de escribir ningún mapa. Con `todos`, esas vistas se omiten para esa área y la salida indica qué separados se escribieron.

#### Scenario: Vista coloreada pedida para otra área
- **WHEN** un subconjunto solo contiene `BELLO - ANTIOQUIA` y el usuario lo extrae con `--separado barrios_cantidad`
- **THEN** el sistema termina con un mensaje que lo explica y no escribe coordenadas ni mapas del subconjunto

#### Scenario: Todos en un área sin polígonos
- **WHEN** ese mismo subconjunto se extrae con `--separado todos`
- **THEN** se escriben `separados/puntos.html` y `separados/clusters.html`, y la salida indica que las vistas coloreadas no aplican

### Requirement: Archivo de coordenadas con niveles
Si el archivo de coordenadas del área no tiene la columna `Nivel ubicacion`, la generación de mapas y la extracción de subconjuntos MUST terminar con un mensaje que pida ejecutar `ubicar`, sin escribir mapas.

#### Scenario: Archivo de coordenadas anterior
- **WHEN** el archivo de coordenadas no tiene la columna `Nivel ubicacion` y el usuario genera los mapas
- **THEN** el sistema termina con un mensaje que pide ejecutar `ubicar` y no escribe mapas

### Requirement: Aviso de los mapas del formato anterior
Si la carpeta de mapas del área contiene `individual.html`, `clusters.html` o `filtrados/` de una versión anterior, la generación de mapas SHALL avisar de que esos archivos ya no se actualizan y se pueden borrar. MUST NOT borrarlos.

#### Scenario: Mapas anteriores presentes
- **WHEN** existe `mapas/area_metropolitana/individual.html` y el usuario genera los mapas
- **THEN** la salida avisa de que ese archivo ya no se actualiza, y el archivo sigue existiendo

### Requirement: Ver los mapas con el fondo de OpenStreetMap
`python -m georef ver-mapas` SHALL servir `mapas/` por HTTP solo en `127.0.0.1`, en un puerto libre, y abrir en el navegador `mapa.html` del área metropolitana o, con `--area <nombre>`, del subconjunto indicado. Así el navegador envía `Referer` y las teselas no se bloquean. Muestra la dirección y sigue sirviendo hasta Ctrl+C, que termina sin error. Solo sirve archivos de `mapas/`.

#### Scenario: Ver el mapa del área metropolitana
- **WHEN** existe `mapas/area_metropolitana/mapa.html` y el usuario ejecuta `python -m georef ver-mapas`
- **THEN** el sistema sirve `mapas/` en `127.0.0.1`, muestra la dirección `http://127.0.0.1:<puerto>/area_metropolitana/mapa.html`, la abre en el navegador y la página responde con el mapa

#### Scenario: Ver el mapa de un subconjunto
- **WHEN** existe `mapas/medellin/mapa.html` y el usuario ejecuta `python -m georef ver-mapas --area medellin`
- **THEN** el navegador abre `http://127.0.0.1:<puerto>/medellin/mapa.html`

#### Scenario: Mapa sin generar
- **WHEN** no existe `mapas/medellin/mapa.html` y el usuario ejecuta `python -m georef ver-mapas --area medellin`
- **THEN** el sistema termina con un mensaje que pide generar los mapas, sin abrir ningún servidor

#### Scenario: Área desconocida
- **WHEN** el usuario ejecuta `python -m georef ver-mapas --area norte` y `norte` no es un subconjunto de la configuración
- **THEN** el sistema termina con un mensaje que lista las áreas disponibles

#### Scenario: Terminar el servidor
- **WHEN** el servidor está sirviendo y el usuario pulsa Ctrl+C
- **THEN** el servidor se cierra y el programa termina con código 0

