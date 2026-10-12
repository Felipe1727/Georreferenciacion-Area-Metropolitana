# normalizacion-direcciones Specification

## Purpose

Define cómo la estandarización divide y normaliza el texto de la dirección de cada registro en vía y numeración, complemento, barrio, código de barrio, comuna y zona, de forma que ninguna parte del texto se pierda y que el barrio de Medellín quede ligado a un polígono oficial.

## Requirements

### Requirement: Columnas de la dirección normalizada
La estandarización SHALL escribir, para cada registro, las columnas `Direccion de residencia` (vía y numeración), `Complemento`, `Barrio`, `Codigo barrio`, `Comuna` y `Zona`, en ese orden y a continuación de las columnas que preceden a la dirección. El resto de columnas del archivo de entrada y el índice de cada registro se conservan.

#### Scenario: Dirección completa de Medellín
- **WHEN** se estandariza `CALLE 45 SUR 12 15 APARTAMENTO 301 BUENOS AIRES -*- URBANO`, de Medellín
- **THEN** `Direccion de residencia` es `CL 45S #12-15`, `Complemento` es `APARTAMENTO 301`, `Barrio` es `Buenos Aires`, `Codigo barrio` es el de ese polígono, `Comuna` es `BUENOS AIRES` y `Zona` es `URBANO`

#### Scenario: Columnas e índice conservados
- **WHEN** el archivo de entrada tiene columnas como `CODIGO` o `Programa Admision`
- **THEN** los archivos de `estandarizado/` las conservan con sus valores y cada registro mantiene el número de fila del archivo de entrada como índice

### Requirement: Equivalencias solo en la vía y la numeración
Las equivalencias de la configuración SHALL aplicarse solo a palabras completas (secuencias de letras delimitadas por espacios, dígitos o signos) y solo a la parte de la vía y la numeración. MUST NOT aplicarse dentro de otras palabras ni al complemento, al barrio, a la comuna o a la zona. El orden de las equivalencias no cambia el resultado.

#### Scenario: Palabras que contienen una equivalencia
- **WHEN** se estandariza `CL 10 20 30 UNIDAD LOS PINOS -*- URBANO`, de Envigado
- **THEN** `Complemento` es `UNIDAD LOS PINOS` y `Zona` es `URBANO`, sin `PI#S` ni `URBA#`

#### Scenario: Orientación de la vía
- **WHEN** se estandariza `CR 50 NORTE 30 20 -*- URBANO`
- **THEN** `Direccion de residencia` es `CR 50N #30-20`

#### Scenario: Abreviatura pegada a números o signos
- **WHEN** se estandariza `CALLE31A 45 12`
- **THEN** `CALLE` se reconoce como palabra completa (la delimitan los dígitos), el registro es de vía principal y `Direccion de residencia` es `CL 31A #45-12`

#### Scenario: Nombre oficial con una palabra de las equivalencias
- **WHEN** se estandariza una dirección de Medellín que termina en `ASOMADERA NO 1 -*- URBANO`
- **THEN** `Barrio` es el nombre oficial `Asomadera No. 1`, sin convertir `NO` en `#`

### Requirement: Zona tomada del separador
El texto que sigue al separador `-*-` SHALL asignarse a `Zona` cuando, normalizado, es `URBANO` o `RURAL`. Si es otro texto, MUST pasar al final de `Complemento`. Si no hay separador, `Zona` queda vacía.

#### Scenario: Zona rural
- **WHEN** se estandariza `VEREDA EL PLAN -*- RURAL`, de Medellín
- **THEN** `Zona` es `RURAL`

#### Scenario: Sin separador
- **WHEN** se estandariza `CL 50 40 30`
- **THEN** `Zona` queda vacía y `Complemento` también

### Requirement: Reconocimiento del barrio en el municipio con polígonos
Para los registros del municipio configurado como municipio con polígonos (Medellín), la estandarización SHALL buscar el barrio en el texto anterior a `-*-` como el sufijo más largo que, normalizado, coincide con un nombre oficial, un alias o un nombre de comuna. Si no hay coincidencia, se reintenta sin los números finales, que pasan a `Complemento`.

#### Scenario: Barrio con complemento delante
- **WHEN** se estandariza `TV 32 B 75 20 CASA 2 CALASANZ -*- URBANO`, de Medellín
- **THEN** `Complemento` es `CASA 2` y `Barrio` es `Calasanz`

#### Scenario: Alias
- **WHEN** el texto termina en `CALAZANS` y la tabla de alias asigna esa variante a Calasanz
- **THEN** `Barrio` es `Calasanz` y `Codigo barrio` es el código de Calasanz

#### Scenario: Sufijo más largo
- **WHEN** el texto termina en `SAN ANTONIO DE PRADO`
- **THEN** se reconoce la comuna San Antonio de Prado y no el barrio `Prado`

#### Scenario: Números finales
- **WHEN** el texto termina en `FATIMA 4` y `FATIMA 4` no es un nombre oficial
- **THEN** `Barrio` es `Fátima` y `Complemento` termina en `4`

### Requirement: Barrio resuelto a un polígono
Cuando el nombre reconocido corresponde a un único polígono, o la regla de nombres repetidos de `referencia-barrios` lo resuelve con la zona, la estandarización SHALL rellenar `Barrio` con el `nombre_barrio` oficial, `Codigo barrio` con su `codigo` como texto y `Comuna` con su `nombre_comuna`. Si el nombre sigue siendo ambiguo, `Barrio` lleva el nombre oficial y `Codigo barrio` y `Comuna` quedan vacíos.

#### Scenario: Nombre repetido resuelto por la zona
- **WHEN** el texto termina en `LA FLORIDA -*- URBANO`
- **THEN** `Codigo barrio` es el del polígono urbano de El Poblado y `Comuna` es `EL POBLADO`

#### Scenario: Nombre repetido sin zona
- **WHEN** el texto termina en `LA FLORIDA` y no hay `-*-`
- **THEN** `Barrio` es `La Florida` y `Codigo barrio` y `Comuna` quedan vacíos

#### Scenario: Código con cero a la izquierda
- **WHEN** el barrio reconocido tiene el código `0902`
- **THEN** `Codigo barrio` es el texto `0902` en los archivos de `estandarizado/`

### Requirement: Registros que solo nombran una comuna
Si lo reconocido es el nombre de una comuna o corregimiento que no es nombre de ningún barrio, o una variante de la tabla de variantes de comuna, la estandarización SHALL rellenar `Comuna` con el nombre oficial de la comuna y dejar vacíos `Barrio` y `Codigo barrio`.

#### Scenario: Corregimiento
- **WHEN** el texto de un registro de Medellín termina en `SAN ANTONIO DE PRADO -*- RURAL`
- **THEN** `Comuna` es `SAN ANTONIO DE PRADO` y `Barrio` queda vacío

#### Scenario: Variante de comuna
- **WHEN** el texto termina en `TORRE 3 POBLADO -*- URBANO`
- **THEN** `Comuna` es `EL POBLADO`, `Barrio` queda vacío y `Complemento` es `TORRE 3`

#### Scenario: Nombre de barrio con artículo
- **WHEN** el texto termina en `EL POBLADO`
- **THEN** `Barrio` es el barrio `El Poblado`, porque es un nombre oficial de barrio

### Requirement: Regla sin pérdida
Si no se reconoce ni barrio ni comuna, todo el texto que sigue a la vía y la numeración SHALL quedar en `Complemento`. Ninguna palabra del texto de la dirección MUST perderse: cada una queda en la dirección, el complemento, el barrio reconocido, la comuna reconocida o la zona.

#### Scenario: Barrio no reconocido
- **WHEN** se estandariza `CL 10 20 30 TORRE 2 SENDEROS DEL MONTE -*- URBANO`, de Medellín, y ninguna de sus terminaciones es un nombre reconocido
- **THEN** `Complemento` es `TORRE 2 SENDEROS DEL MONTE` y `Barrio`, `Codigo barrio` y `Comuna` quedan vacíos

#### Scenario: Registro sin vía
- **WHEN** se estandariza `FINCA LA ESPERANZA -*- RURAL`, de Copacabana
- **THEN** `Direccion de residencia` queda vacía, `Complemento` es `FINCA LA ESPERANZA` y `Zona` es `RURAL`

### Requirement: Otros municipios sin barrio
Para los registros de municipios distintos del municipio con polígonos, la estandarización SHALL separar la dirección, el complemento y la zona, y MUST dejar vacíos `Barrio`, `Codigo barrio` y `Comuna`.

#### Scenario: Registro de Envigado
- **WHEN** se estandariza `CARRERA 43 A 1 50 UNIDAD LOS PINOS -*- URBANO`, de Envigado
- **THEN** `Direccion de residencia` es `CR 43A #1-50`, `Complemento` es `UNIDAD LOS PINOS`, `Zona` es `URBANO` y `Barrio` queda vacío

### Requirement: Clasificación en vías principales y especiales
Un registro del área metropolitana SHALL clasificarse como de vía principal cuando su texto, con las equivalencias aplicadas, empieza por uno de los tipos de vía configurados. Los demás se clasifican como especiales. Ambos grupos reciben las mismas columnas normalizadas.

#### Scenario: Vía expresada con la palabra completa
- **WHEN** el texto empieza por `CALLE 45`
- **THEN** el registro va a `principales_area_metropolitana.xlsx`

#### Scenario: Vereda
- **WHEN** el texto es `VEREDA EL PLAN -*- RURAL`, de Medellín
- **THEN** el registro va a `especiales_area_metropolitana.xlsx` con `Barrio` igual a `El Plan`, `Complemento` igual a `VEREDA` y `Zona` igual a `RURAL`
