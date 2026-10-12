# Design

## Context

- **La estandarización hoy (`georef/direcciones.py` y `etapas.estandarizar`):**
  1. pasa a mayúsculas;
  2. aplica las equivalencias por subcadena a todo el texto;
  3. separa vía y complemento con `dividir_complemento`, que recorre caracteres: corta en las dos primeras letras seguidas distintas que no son palabra clave;
  4. da formato con `format_dir`.

  El barrio y `-*- ZONA` quedan dentro de `Complemento`.
- **Robustez del separador heredado.** `dividir_complemento` resuelve bien numeraciones como `#99BB-99`. Un primer prototipo que separaba por palabras cambiaba 94 de 935 direcciones, la mayoría para peor, así que el separador se conserva.
- **Equivalencias y nombres oficiales.** 33 nombres oficiales normalizados contienen palabras de las equivalencias (`ASOMADERA NO 1`, `CALLE NUEVA`, `MANRIQUE ORIENTAL`…). Las equivalencias no pueden tocar el barrio ni el complemento.
- **Lo que deja preparado `exploracion-geojson`:**
  - el GeoJSON con `codigo`, `nombre_barrio`, `nombre_comuna` e `indicador_ur`;
  - `data/alias_barrios.csv`, con 27 alias;
  - la convención de normalización;
  - la regla de nombres repetidos por zona;
  - la heurística del sufijo más largo, que mide un 77,8 % de barrios y un 10,5 % de comunas en Medellín (`notebooks/hallazgos_geojson.md`).
- **Volumen del archivo real:** 963 registros del área metropolitana, 935 de vía principal y 706 de Medellín.

## Goals / Non-Goals

**Goals:**
- Una sola función de normalización para todos los registros, la misma para el área metropolitana y para fuera de ella, que no pierda texto.
- Columnas `Barrio`, `Codigo barrio`, `Comuna` y `Zona` listas para que `ubicacion-por-niveles` asigne el punto del barrio o de la comuna.
- Que cada cambio en la salida sea intencionado y revisable.

**Non-Goals:**
- Geometrías. El GeoJSON se lee aquí solo por sus propiedades, con `json`; geopandas y PROJ entran con `ubicacion-por-niveles`.
- Reescribir `dividir_complemento` o `format_dir`. Sus casos raros se documentan, no se corrigen aquí.
- Cambiar el notebook de exploración. Conserva su propia copia de la heurística como registro del análisis.

## Decisions

### D1. Orden del proceso: primero el lugar, después las equivalencias

```
 texto (mayusculas)
   |  1. partir en "-*-":  antes | despues -> Zona si es URBANO/RURAL; si no, al final del complemento
   v
 palabras de "antes"
   |  2. solo municipio con poligonos: lugar = sufijo mas largo (normalizado) que sea
   |     barrio oficial | alias de barrio | comuna sin barrio homonimo | variante de comuna
   |     sin coincidencia -> reintento sin numeros finales (vuelven al complemento)
   v
 resto = palabras sin el lugar
   |  3. equivalencias palabra a palabra (CALLE->CL, NORTE->N, NO->#...)
   |  4. dividir_complemento (heredado) -> direccion | complemento'
   |  5. format_dir (heredado) sobre la direccion
   |  6. complemento = palabras ORIGINALES del resto que corresponden a complemento'
   v     (si el corte no cae entre palabras: complemento' tal cual)
 Direccion de residencia | Complemento | Barrio | Codigo barrio | Comuna | Zona
```

- **Por qué en este orden.** Buscar el lugar antes de las equivalencias protege los nombres oficiales. Aplicar las equivalencias palabra a palabra mantiene el mismo número de palabras, así que el complemento se puede recuperar con su texto original (paso 6).
- **Medición previa sobre el archivo real:**
  - cambian 32 de 935 direcciones: 25 por `NORTE`, 1 por `ORIENTE` y 6 casos a revisar;
  - el complemento se recupera palabra a palabra en 837 de 841 casos.
- **Qué es una palabra completa.** Una secuencia de letras delimitada por espacios, dígitos o signos. Así `CALLE31A` pasa a `CL31A`, `SUR-15` a `S-15` y `CLL.39` a `CL.39`, como hacía el reemplazo antiguo, pero `URBANO` y `SURAMERICA` no cambian. Las equivalencias más largas se aplican primero, así que el orden de la configuración no importa.
- **Espacio final para el separador.** `dividir_complemento` recibe el texto con un espacio final. Sin él, falla en silencio (`IndexError`) cuando el texto acaba en una palabra de dos letras y lo devuelve todo como dirección. Antes no ocurría porque detrás venían el barrio y la zona. Ambos ajustes salieron de la verificación con los datos reales, igual que la equivalencia `CRRA` → `CR`, que el reemplazo antiguo resolvía por casualidad (`CRR` → `CR` y después `CRA` → `CR`).
- **Clasificación en principales y especiales.** Conserva su regla: el texto, con las equivalencias aplicadas, empieza por un tipo de vía.
- *Alternativa:* separar dirección y complemento por palabras con una expresión regular de numeración. Se descarta tras medirla: rompe numeraciones como `#99BB-99`.
- *Alternativa:* aplicar equivalencias por palabra a todo el texto. Se descarta porque convierte `ASOMADERA NO 1` en `ASOMADERA # 1` y `CALLE NUEVA` en `CL NUEVA`.

### D2. Módulo `georef/referencia.py` con el índice de lugares

- **`normalizar(texto)`.** Implementa una sola vez la convención de `referencia-barrios`. `tests/test_alias_barrios.py` deja de tener su copia y la importa, como anticipaba D6 de `exploracion-geojson`.
- **Clase `IndiceLugares`.** Es la primera clase con estado real: se construye una vez por ejecución a partir de la sección `[referencia]` y guarda:
  - nombre normalizado → códigos;
  - código → (nombre oficial, comuna, indicador);
  - alias de barrio → código;
  - comunas sin barrio homónimo;
  - variante de comuna → comuna.
- **Métodos.** `reconocer(palabras, zona)` devuelve el número de palabras reconocidas y el barrio o la comuna. `resolver(nombre, zona)` aplica la regla de repetidos de la especificación.
- **Lectura del GeoJSON.** Solo se leen las propiedades, con `json` de la biblioteca estándar. Es rápido y no necesita PROJ, igual que el test de alias.
- **Errores.** Si falta un archivo o una tabla no tiene sus columnas, se lanza `ErrorReferencia`, que la etapa convierte en un mensaje y `sys.exit`.
- *Alternativa:* cargar el GeoJSON con geopandas desde ya. Se descarta porque añade la dependencia de PROJ a una etapa que no necesita geometrías. `ubicacion-por-niveles` ampliará el índice con los puntos.

### D3. Columnas y tipos de la salida

- **Columnas y posición.** `Direccion de residencia`, `Complemento`, `Barrio`, `Codigo barrio`, `Comuna` y `Zona` van seguidas, en la posición actual de la dirección. Son nombres del programa (contrato entre etapas), así que no van en la configuración.
- **Contenido de cada columna:**
  - `Barrio` guarda el `nombre_barrio` oficial con tildes (`Calasanz`, `Fátima`), no la forma escrita;
  - `Comuna` guarda `nombre_comuna` tal como viene en el GeoJSON (`EL POBLADO`).
- **`Codigo barrio`.** Se escribe como texto. Al leer los Excel, quien lo use debe pasar `dtype={"Codigo barrio": str}`, porque `read_excel` lo convertiría en número y perdería el cero (`0902`). Hay un test que comprueba esa lectura.
- **Espacios.** Los valores vacíos se escriben como celdas vacías. El nombre oficial `El Salado ` (con espacio final) se escribe sin él.

### D4. Variantes de comuna en `data/alias_comunas.csv`

- **Formato.** Columnas `alias`, `comuna` y `nota`, con el mismo estilo que `alias_barrios.csv`.
- **Contenido.** Las cuatro variantes decididas en la revisión de alias. `EL POBLADO` sigue siendo el barrio y `EL RODEO` el barrio de Guayabal, porque el sufijo más largo gana.
- **Validación.** `tests/test_alias_comunas.py` comprueba los invariantes de la especificación, reutilizando las funciones de `test_alias_barrios.py`.
- *Alternativa:* añadir las variantes a la configuración TOML. Se descarta porque son datos de referencia del mismo tipo que los alias de barrio y se revisan igual.

### D5. Sección `[referencia]` de la configuración

```toml
[referencia]
geojson = "data/limite_barrio_vereda_cata.geojson"
alias_barrios = "data/alias_barrios.csv"
alias_comunas = "data/alias_comunas.csv"
municipio_con_poligonos = "MEDELLIN - ANTIOQUIA"
```

- **Rutas.** Son relativas al directorio de trabajo, como las demás.
- **Validación de la configuración.** Es estructural (claves, textos no vacíos y municipio dentro del área metropolitana).
- **Existencia de los archivos.** Se comprueba al construir el índice, solo en la estandarización. Así `mapas` o `subconjunto` no dependen de ellos.

### D6. Registros de fuera con la misma normalización

`normalizar_direcciones(df, …)` se aplica a todo el archivo de entrada antes de separar por área. El reconocimiento de lugares solo actúa en las filas cuya ciudad es el municipio con polígonos. Fuera del área se obtienen las mismas columnas, con `Barrio`, `Codigo barrio` y `Comuna` vacíos, y el reemplazo por subcadena desaparece también ahí.

### D7. La mejora de coordenadas sigue funcionando

`rellenar_por_barrio` busca los nombres de `BARRIOS_MEDELLIN` en el texto normalizado de `Complemento` y, si existe la columna, también en `Barrio`.

- **Archivos antiguos.** Con un archivo de coordenadas antiguo (barrio dentro de `Complemento`), el comportamiento es el mismo.
- **Archivos nuevos.** Con uno nuevo se encuentra el barrio en su columna.

Es un ajuste mínimo y temporal: `ubicacion-por-niveles` elimina la mejora.

### D8. Verificación con los datos reales, sin exponerlos

Al empezar la implementación se guarda la salida actual como línea base, fuera del repositorio. Al terminar se compara con la nueva:

- **Comparaciones automáticas:**
  - filas por archivo, que deben coincidir o tener una explicación;
  - direcciones distintas, clasificadas por causa;
  - complementos sin `#` ni restos de equivalencias;
  - cobertura de `Barrio`, `Codigo barrio` y `Comuna` en Medellín frente a las cifras del notebook.
- **Qué se muestra.** En la conversación solo se muestran cifras agregadas y formas con los dígitos enmascarados.
- **Revisión a mano.** Las filas con cambios se escriben en `estandarizado/revision_normalizacion.xlsx`, con la columna antigua y la nueva lado a lado. Esa carpeta está excluida de git, así que los datos personales no salen del equipo, y el usuario puede revisar cada diferencia.

### D9. Tests

- **Defectos conocidos que se corrigen.** Los tests `*_defecto_conocido` de `test_estandarizacion.py` se convierten explícitamente en tests del comportamiento corregido, con los valores nuevos.
- **`test_estandarizacion_completa` y `test_flujo_principal`.** Cambian sus columnas y complementos esperados.
- **Escenarios nuevos.** `tests/test_normalizacion.py` cubre los escenarios de `specs/normalizacion-direcciones` con direcciones inventadas y el GeoJSON y las tablas reales del repositorio, que no contienen datos personales.
- **Test de regresión de la configuración.** Sigue comprobando que el vocabulario incluido tiene los mismos valores (requisito "Vocabulario incluido").

## Risks / Trade-offs

- [El sufijo más largo asigna un barrio que forma parte de un nombre más largo (por ejemplo, un edificio que acaba en el nombre de un barrio)] → El notebook midió un 24 % de sufijos con una palabra previa desconocida, la mayoría correctos (el nombre de la comuna delante o un edificio). Las palabras previas quedan en `Complemento`, así que no se pierde nada, y `ubicacion-por-niveles` validará el barrio con el punto de la API.
- [Los 6 casos raros de la medición previa y los que aparezcan en la revisión] → La tarea de verificación los lista con los dígitos enmascarados. Se corrigen si el fallo está en el código nuevo; si está en el separador heredado, se documentan.
- [Un consumidor lee `Codigo barrio` como número] → D3 y su test, y el README lo indica.
- [El archivo de coordenadas existente tiene las columnas antiguas] → No se regenera en este cambio. La conversión, la mejora y los subconjuntos siguen funcionando con él. Las columnas nuevas llegan al archivo de coordenadas con `ubicacion-por-niveles`.
- [Las tablas de alias dependen de esta cohorte] → Las palabras que no se reconocen quedan en `Complemento`, y la sección 7 del notebook sirve para ampliar las tablas con cada periodo.

## Migration Plan

1. Volver a ejecutar la estandarización (`python -m georef estandarizar`), que no consume la API.
2. Revisar `estandarizado/revision_normalizacion.xlsx`, si se generó en la verificación.
3. No regenerar el archivo de coordenadas hasta `ubicacion-por-niveles`.

**Vuelta atrás:** revertir el commit y volver a estandarizar.
