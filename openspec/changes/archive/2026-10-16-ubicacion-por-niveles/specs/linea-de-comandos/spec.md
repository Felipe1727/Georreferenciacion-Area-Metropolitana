# Spec Delta

## MODIFIED Requirements

### Requirement: Subcomandos no interactivos
El programa SHALL ejecutarse como `python -m georef <subcomando>` con los subcomandos `estandarizar`, `ubicar` (con la opción `--sin-consultas`), `mapas`, `subconjunto --area <nombre>`, `consultar-municipios` y `comparar-consultas --muestra <N>`. Cada subcomando ejecuta solo su operación, sin mostrar el menú ni hacer preguntas por consola, y termina con código 0 si la operación se completa.

#### Scenario: Estandarizar
- **WHEN** `original/` contiene un archivo de entrada y el usuario ejecuta `python -m georef estandarizar`
- **THEN** el sistema genera los cuatro archivos de `estandarizado/` sin pedir ninguna entrada por consola

#### Scenario: Ubicar
- **WHEN** existen los archivos de `estandarizado/`, la llave está definida y el usuario ejecuta `python -m georef ubicar`
- **THEN** el sistema ubica a los registros del área metropolitana igual que la opción 2 del menú

#### Scenario: Geocodificar
- **WHEN** el usuario ejecuta `python -m georef geocodificar`, el nombre anterior de la ubicación
- **THEN** el sistema termina con código distinto de cero, muestra los subcomandos válidos, entre ellos `ubicar`, y no hace ninguna consulta

#### Scenario: Mejorar y mapas
- **WHEN** el usuario ejecuta `python -m georef mejorar` o `python -m georef mapas`
- **THEN** `mejorar` termina con código distinto de cero y muestra los subcomandos válidos sin hacer ninguna consulta, y `mapas` hace lo mismo que la opción 3 del menú

#### Scenario: Subconjunto
- **WHEN** el usuario ejecuta `python -m georef subconjunto --area medellin`
- **THEN** el sistema extrae el subconjunto `medellin`

#### Scenario: Diagnóstico de formatos
- **WHEN** el usuario ejecuta `python -m georef comparar-consultas --muestra 50`
- **THEN** el sistema compara los dos formatos de consulta sobre una muestra de hasta 50 consultas

#### Scenario: Estandarizar sin archivo de entrada
- **WHEN** `original/` está vacío y el usuario ejecuta `python -m georef estandarizar`
- **THEN** el sistema termina con un mensaje que pide colocar el archivo en `original/`, sin abrir ningún diálogo gráfico

### Requirement: Menú interactivo sin argumentos
Si se ejecuta sin subcomando, el programa SHALL mostrar el menú interactivo con cuatro opciones: 1 estandarización, 2 ubicación, 3 mapas y 4 extracción de un subconjunto. La opción 4 lista los subconjuntos configurados y pide elegir uno. Una opción inválida se vuelve a pedir. Los diagnósticos (`consultar-municipios` y `comparar-consultas`) solo están disponibles como subcomandos.

#### Scenario: Opción de estandarización con `original/` vacío
- **WHEN** `original/` está vacío y el usuario elige la opción 1 del menú
- **THEN** el sistema abre el diálogo para elegir el archivo de entrada, como hasta ahora

#### Scenario: Opciones que no leen el archivo de entrada
- **WHEN** `original/` está vacío y el usuario elige la opción 3 del menú
- **THEN** el sistema genera los mapas sin abrir el diálogo de selección de archivo

#### Scenario: Ubicación desde el menú
- **WHEN** el usuario elige la opción 2 del menú
- **THEN** el sistema hace lo mismo que `python -m georef ubicar`

#### Scenario: Extraer un subconjunto desde el menú
- **WHEN** el usuario elige la opción 4 y después el subconjunto `medellin` de la lista
- **THEN** el sistema extrae el subconjunto `medellin`

#### Scenario: Opción inválida
- **WHEN** el usuario escribe `5` en el menú
- **THEN** el sistema indica que la opción es inválida y la vuelve a pedir

### Requirement: Compatibilidad con `python main.py`
`python main.py` SHALL comportarse igual que `python -m georef` con los mismos argumentos. `python main.py c` SHALL ser equivalente a `python -m georef ubicar`.

#### Scenario: Menú desde `main.py`
- **WHEN** el usuario ejecuta `python main.py` sin argumentos
- **THEN** el sistema muestra el mismo menú que `python -m georef`

#### Scenario: Modo `c`
- **WHEN** la llave está definida y el usuario ejecuta `python main.py c`
- **THEN** el sistema ubica a los registros sin mostrar el menú, y el archivo de coordenadas resultante no gana columnas `Unnamed`

### Requirement: Argumentos inválidos y ayuda
Ante un subcomando u opción desconocidos, o si falta un argumento obligatorio, el sistema MUST terminar con código distinto de cero, mostrar el uso correcto y no ejecutar ninguna etapa. `--help` SHALL listar los subcomandos con una descripción en español.

#### Scenario: Subcomando desconocido
- **WHEN** el usuario ejecuta `python -m georef exportar`
- **THEN** el sistema termina con código distinto de cero, muestra los subcomandos válidos y no crea ni modifica archivos de salida

#### Scenario: Falta el subconjunto
- **WHEN** el usuario ejecuta `python -m georef subconjunto` sin `--area`
- **THEN** el sistema termina con código distinto de cero e indica que falta `--area`

#### Scenario: Muestra no válida
- **WHEN** el usuario ejecuta `python -m georef comparar-consultas --muestra 0`
- **THEN** el sistema termina con código distinto de cero e indica que la muestra debe ser un entero positivo

#### Scenario: Ayuda
- **WHEN** el usuario ejecuta `python -m georef --help`
- **THEN** la salida lista `estandarizar`, `ubicar`, `mapas`, `subconjunto`, `consultar-municipios` y `comparar-consultas` con su descripción
