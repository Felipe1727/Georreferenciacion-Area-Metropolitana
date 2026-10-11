# Spec Delta

## Purpose

Define cómo obtiene el sistema la credencial del proveedor de geocodificación (OpenCage) y cómo se comporta cuando falta. La llave se toma del entorno del proceso o de un archivo `.env` local excluido del control de versiones; el sistema nunca la escribe en archivos ni la solicita de forma interactiva.

## ADDED Requirements

### Requirement: Credencial leída del entorno o de un archivo `.env`
El sistema SHALL obtener la API key del proveedor de geocodificación de la variable `OPENCAGE_API_KEY`, sin espacios al inicio ni al final, en todas las operaciones que consultan al proveedor: conversión de coordenadas (menú y modo `c`) y mejora de coordenadas. La variable se busca primero en el entorno del proceso y, si ahí no está definida o está vacía, en el archivo `.env` del directorio de trabajo. Leer `.env` MUST NOT modificar el entorno del proceso.

#### Scenario: Variable definida en el entorno
- **WHEN** `OPENCAGE_API_KEY` contiene una llave en el entorno y el usuario ejecuta la conversión de coordenadas
- **THEN** el sistema usa esa llave para consultar al proveedor sin hacer ninguna pregunta por consola sobre la llave

#### Scenario: Variable definida solo en `.env`
- **WHEN** `OPENCAGE_API_KEY` no está en el entorno, el archivo `.env` del directorio de trabajo contiene `OPENCAGE_API_KEY=<llave>` y el usuario ejecuta la conversión de coordenadas
- **THEN** el sistema usa la llave de `.env` sin hacer preguntas por consola y el entorno del proceso no gana la variable `OPENCAGE_API_KEY`

#### Scenario: El entorno tiene prioridad sobre `.env`
- **WHEN** `OPENCAGE_API_KEY` está definida tanto en el entorno como en `.env` con valores distintos
- **THEN** el sistema usa el valor del entorno

#### Scenario: Valor con espacios alrededor
- **WHEN** `OPENCAGE_API_KEY` contiene una llave con espacios o un salto de línea al final
- **THEN** el sistema usa la llave sin esos espacios

#### Scenario: Modo no interactivo
- **WHEN** `OPENCAGE_API_KEY` está definida (en el entorno o en `.env`) y el usuario ejecuta `python main.py c`
- **THEN** el sistema geocodifica con esa llave y no lee ningún archivo `llave/llave.txt`

### Requirement: Fallo explícito cuando falta la credencial
Si `OPENCAGE_API_KEY` no está definida o está vacía (incluido un valor formado solo por espacios) ni en el entorno ni en `.env`, el sistema MUST terminar con código distinto de cero antes de hacer cualquier consulta al proveedor. Debe mostrar un mensaje que nombre la variable y explique cómo definirla (incluido el archivo `.env`), y no debe modificar ningún archivo de salida.

#### Scenario: Variable ausente
- **WHEN** `OPENCAGE_API_KEY` no está definida en el entorno, no existe `.env` y el usuario elige la conversión de coordenadas
- **THEN** el sistema termina con código distinto de cero, muestra un mensaje que menciona `OPENCAGE_API_KEY` y `coordenadas/coordenadas.xlsx` queda sin cambios

#### Scenario: Variable vacía
- **WHEN** `OPENCAGE_API_KEY` contiene solo espacios en el entorno, `.env` no la define y el usuario elige la mejora de coordenadas
- **THEN** el sistema se comporta igual que si la variable no estuviera definida

#### Scenario: `.env` con la variable vacía
- **WHEN** `OPENCAGE_API_KEY` no está en el entorno y `.env` contiene `OPENCAGE_API_KEY=` sin valor
- **THEN** el sistema se comporta igual que si la variable no estuviera definida

### Requirement: La credencial no se persiste ni se muestra
El sistema MUST NOT escribir la API key en ningún archivo (tampoco crear ni modificar `.env`, que solo edita el usuario), MUST NOT crear el directorio `llave/` y MUST NOT mostrar el valor de la llave por consola.

#### Scenario: Ejecución completa de la conversión
- **WHEN** el usuario ejecuta la conversión de coordenadas con `OPENCAGE_API_KEY` definida
- **THEN** al terminar no existe un directorio `llave/` creado por el sistema y la salida de consola no contiene el valor de la llave

### Requirement: Operaciones sin proveedor no exigen la credencial
Las operaciones que no consultan al proveedor (estandarización de direcciones y generación de mapas) SHALL ejecutarse aunque `OPENCAGE_API_KEY` no esté definida.

#### Scenario: Estandarización sin credencial
- **WHEN** `OPENCAGE_API_KEY` no está definida ni en el entorno ni en `.env` y el usuario elige la estandarización de direcciones
- **THEN** el sistema genera los archivos de `estandarizado/` con normalidad
