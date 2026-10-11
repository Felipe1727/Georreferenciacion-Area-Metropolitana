# linea-de-comandos Specification

## Purpose

Define cómo se ejecuta el programa: los subcomandos y opciones no interactivos, el menú interactivo cuando no se pasan argumentos, la compatibilidad con `python main.py` y su modo `c`, y la respuesta ante argumentos inválidos.

## Requirements

### Requirement: Subcomandos no interactivos
El programa SHALL ejecutarse como `python -m georef <subcomando>` con los subcomandos `estandarizar`, `geocodificar`, `mejorar`, `mapas` y `subconjunto --area <nombre>`. Cada subcomando ejecuta solo su etapa, sin mostrar el menú ni hacer preguntas por consola, y termina con código 0 si la etapa se completa.

#### Scenario: Estandarizar
- **WHEN** `original/` contiene un archivo de entrada y el usuario ejecuta `python -m georef estandarizar`
- **THEN** el sistema genera los cuatro archivos de `estandarizado/` sin pedir ninguna entrada por consola

#### Scenario: Geocodificar
- **WHEN** existe `estandarizado/principales_area_metropolitana.xlsx`, la llave está definida y el usuario ejecuta `python -m georef geocodificar`
- **THEN** el sistema hace la conversión de coordenadas igual que la opción 2 del menú

#### Scenario: Mejorar y mapas
- **WHEN** el usuario ejecuta `python -m georef mejorar` o `python -m georef mapas`
- **THEN** el sistema hace lo mismo que las opciones 3 y 4 del menú, respectivamente

#### Scenario: Subconjunto
- **WHEN** el usuario ejecuta `python -m georef subconjunto --area medellin`
- **THEN** el sistema extrae el subconjunto `medellin`

#### Scenario: Estandarizar sin archivo de entrada
- **WHEN** `original/` está vacío y el usuario ejecuta `python -m georef estandarizar`
- **THEN** el sistema termina con un mensaje que pide colocar el archivo en `original/`, sin abrir ningún diálogo gráfico

### Requirement: Opción global de configuración
Todos los subcomandos y el menú SHALL aceptar `--config <ruta>` para usar un archivo de configuración distinto de `config/georef.toml`.

#### Scenario: Subcomando con otra configuración
- **WHEN** el usuario ejecuta `python -m georef --config otra.toml estandarizar`
- **THEN** la estandarización usa los municipios y el vocabulario de `otra.toml`

### Requirement: Menú interactivo sin argumentos
Si se ejecuta sin subcomando, el programa SHALL mostrar el menú interactivo con las opciones 1 a 4 de siempre (estandarización, conversión de coordenadas, mejora de coordenadas y mapas) y una opción 5 para extraer un subconjunto. Esta última lista los subconjuntos configurados y pide elegir uno. Una opción inválida se vuelve a pedir, como hasta ahora.

#### Scenario: Opción de estandarización con `original/` vacío
- **WHEN** `original/` está vacío y el usuario elige la opción 1 del menú
- **THEN** el sistema abre el diálogo para elegir el archivo de entrada, como hasta ahora

#### Scenario: Opciones que no leen el archivo de entrada
- **WHEN** `original/` está vacío y el usuario elige la opción 4 del menú
- **THEN** el sistema genera los mapas sin abrir el diálogo de selección de archivo

#### Scenario: Extraer un subconjunto desde el menú
- **WHEN** el usuario elige la opción 5 y después el subconjunto `medellin` de la lista
- **THEN** el sistema extrae el subconjunto `medellin`

#### Scenario: Opción inválida
- **WHEN** el usuario escribe `9` en el menú
- **THEN** el sistema indica que la opción es inválida y la vuelve a pedir

### Requirement: Compatibilidad con `python main.py`
`python main.py` SHALL comportarse igual que `python -m georef` con los mismos argumentos. `python main.py c` SHALL ser equivalente a `python -m georef geocodificar`.

#### Scenario: Menú desde `main.py`
- **WHEN** el usuario ejecuta `python main.py` sin argumentos
- **THEN** el sistema muestra el mismo menú que `python -m georef`

#### Scenario: Modo `c`
- **WHEN** la llave está definida y el usuario ejecuta `python main.py c`
- **THEN** el sistema hace la conversión de coordenadas sin mostrar el menú, y el archivo de coordenadas resultante no gana columnas `Unnamed`

### Requirement: Argumentos inválidos y ayuda
Ante un subcomando u opción desconocidos, o si falta un argumento obligatorio, el sistema MUST terminar con código distinto de cero, mostrar el uso correcto y no ejecutar ninguna etapa. `--help` SHALL listar los subcomandos con una descripción en español.

#### Scenario: Subcomando desconocido
- **WHEN** el usuario ejecuta `python -m georef exportar`
- **THEN** el sistema termina con código distinto de cero, muestra los subcomandos válidos y no crea ni modifica archivos de salida

#### Scenario: Falta el subconjunto
- **WHEN** el usuario ejecuta `python -m georef subconjunto` sin `--area`
- **THEN** el sistema termina con código distinto de cero e indica que falta `--area`

#### Scenario: Ayuda
- **WHEN** el usuario ejecuta `python -m georef --help`
- **THEN** la salida lista `estandarizar`, `geocodificar`, `mejorar`, `mapas` y `subconjunto` con su descripción
