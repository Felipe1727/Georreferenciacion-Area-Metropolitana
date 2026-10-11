# Design

## Context

- **Estado actual de `main.py` (745 líneas):**
  - constantes del dominio: `area_metropolitana`, `tipo_via_urbana`, `keywords`, `equivalente` y `barrios_medellin`;
  - el menú y el modo `c`;
  - la E/S de Excel;
  - la geocodificación (`geocodificar_direcciones`, `rellenar_por_barrio`) y los mapas (`visualizar`).
- **Funciones de dirección.** Leen esas constantes como globales del módulo. Por eso no se pueden usar con otro vocabulario sin modificarlas.
- **Tests de caracterización de `fundamentos`.** Congelan el comportamiento actual, incluidos los defectos conocidos. Sustituyen `main.OpenCageGeocode`, `main.time.sleep` y `main.tk.Tk`, de modo que ninguna prueba llama a la API real ni abre diálogos.
- **Lectura del archivo de entrada.** El prelude de `main()` crea los directorios, abre el diálogo si `original/` está vacío y lee el archivo de entrada antes del menú, sea cual sea la opción.
  - `Path.glob("*")` cuenta los archivos ocultos. Con el Excel abierto en LibreOffice, el archivo `.~lock.<nombre>#` hace terminar el programa con "Hay más de un archivo" (comprobado).
- **Herramientas disponibles.** Python 3.12 incluye `tomllib`. `pdoc` 16.0.0 está en conda-forge y `docs/` se generó con pdoc 15.0.4.
- **Consumidor externo de un nombre de archivo.** El notebook `exploracion_geojson.ipynb` lee `coordenadas/coordenadas.xlsx`.

## Goals / Non-Goals

**Goals:**
- Cada módulo tiene una responsabilidad y las funciones reciben como parámetros lo que antes leían de globales. Así `ubicacion-por-niveles` puede sustituir el normalizador o la geocodificación sin tocar el resto.
- La misma lógica se usa desde los subcomandos y desde el menú.
- La única forma de comprobar que no cambia el comportamiento son los tests de `fundamentos`, con los mismos valores esperados.

**Non-Goals:**
- Introducir clases con estado. El normalizador, el índice de barrios y el cliente con caché de la exploración llegan con `ubicacion-por-niveles`, que es cuando tendrán estado real.
- Hacer configurables los directorios de trabajo, los parámetros de geocodificación o los mapas (ver D3).
- Empaquetar el proyecto para instalarlo con pip (`pyproject.toml`). Se ejecuta desde la raíz del repositorio, como hasta ahora.

## Decisions

### D1. Paquete `georef/` con dependencias en una sola dirección

```
 main.py ---> georef/__main__.py ---> cli.py  (argparse + menu)
                                        |  carga y valida la config, la pasa hacia abajo
                                        v
                                     etapas.py  (una funcion por etapa: lee/escribe archivos)
                    +-----------+-------+--------+-------------+
                    v           v                v             v
              direcciones.py  geocodificacion.py  mapas.py    archivos.py
              (texto, puro)   (OpenCage)          (folium)    (rutas, original/, avisos)
                    ^
              config.py  (TOML -> dataclasses congeladas; no importa nada del paquete)
```

| Módulo | Contenido que viene de `main.py` | Nuevo |
|---|---|---|
| `config.py` | — | `cargar_configuracion(ruta)`, dataclasses `Configuracion`, `Columnas` y `VocabularioDirecciones`, y `ErrorConfiguracion` con la lista de errores |
| `archivos.py` | `estructura_programa`, `verificar_y_copiar_archivo_original`, `leer_archivo_original`, `verificar_principales_am`, rutas de `estandarizado/` | `ruta_coordenadas(area)`, `carpeta_mapas(area)`, la comprobación del nombre antiguo y el filtro de archivos ocultos y de bloqueo |
| `direcciones.py` | `filtrar_area_metropolitana` (pasa a ser `separar_por_area`), `reemplazar_equivalentes`, `filtrar_vias_principales`, `identificar_vias_principales`, `estandarizar`, `agregar_columna_complemento`, `dividir_complemento`, `format_dir` | Parámetros explícitos de vocabulario y columnas |
| `geocodificacion.py` | `obtener_llave`, `geocodificar_direcciones`, `rellenar_por_barrio`, `barrios_medellin` (pasa a `BARRIOS_MEDELLIN`) | `CENTROIDE_MEDELLIN` como constante con nombre, usada aquí y en `mapas.py` |
| `mapas.py` | `visualizar` | Parámetro `carpeta`, para escribir en `mapas/<area>/` |
| `etapas.py` | El cuerpo de cada `case` de `main()` | `extraer_subconjunto` |
| `cli.py` | `main`, `seleccionar_funcionalidad` | Parser de `argparse`, opción 5 del menú y alias `c` |

- **Por qué no se reparten de otra forma.** `etapas.py` concentra la E/S de cada etapa, de modo que `direcciones.py` sigue siendo puro (DataFrame a DataFrame) y se prueba sin archivos.
- **`main.py`** queda en unas 5 líneas que llaman a `georef.cli.main()`.
- *Alternativa:* mantener un solo archivo y solo parametrizarlo. Se descarta porque `ubicacion-por-niveles` necesita sustituir piezas sueltas y probarlas aisladas.
- *Alternativa:* un módulo por función o una clase `Etapa` abstracta. Se descarta por sobredimensionada para cinco etapas lineales (D6 de la exploración: arquitectura sencilla).

### D2. TOML leído con `tomllib` y validado con código propio

- **Lectura.** `cargar_configuracion` lee el archivo con `tomllib` y comprueba la estructura con una función de validación propia. Esa función **acumula todos los errores**, cada uno con la ruta de su clave (`subconjuntos.sur.municipios[1]`), y al final lanza `ErrorConfiguracion`.
- **Presentación de errores.** `cli.py` la convierte en un mensaje y en `sys.exit` con código 1.
- **Orden de arranque.** La validación ocurre antes de crear directorios, leer datos o pedir la llave.
- **Qué se valida:**
  - claves desconocidas o ausentes;
  - tipos;
  - listas y cadenas vacías;
  - valores repetidos: municipios, palabras de las equivalencias, y tipos de vía frente a palabras clave;
  - el formato del nombre de los subconjuntos (`^[a-z0-9_]+$`, distinto de `area_metropolitana`);
  - que los municipios de cada subconjunto estén en el área metropolitana.
- **Resultado.** Los valores se devuelven en dataclasses `frozen=True` con tuplas, de modo que ninguna etapa puede modificar la configuración.
- *Alternativa:* YAML. Añade una dependencia, y YAML 1.1 convierte la clave `NO` (que es una equivalencia real) en el booleano `false`.
- *Alternativa:* JSON. No admite comentarios, y esta configuración la editarán personas que necesitan explicaciones junto a los valores.
- *Alternativa:* pydantic o jsonschema. Son una dependencia más para unas 10 claves.

Estructura del archivo (ilustrativa):

```toml
# Municipios que se estandarizan y geocodifican, escritos exactamente
# como aparecen en la columna de ciudad del archivo de entrada.
[area_metropolitana]
municipios = ["MEDELLIN - ANTIOQUIA", "ITAGUI - ANTIOQUIA", ...]

# Subconjuntos del área metropolitana: python -m georef subconjunto --area medellin
[subconjuntos.medellin]
municipios = ["MEDELLIN - ANTIOQUIA"]

[columnas]
ciudad = "Ciudad Residencia"
direccion = "Direccion de residencia"

[direcciones]
tipos_via = ["CL", "CR", "AV", "CIR", "DG", "TV"]
palabras_clave = ["BIS", "KM"]          # se suman a los tipos de vía
# Se aplican en este orden y por subcadena (comportamiento heredado).
equivalencias = [
  ["CALLE", "CL"],
  ["CARRERA", "CR"],
  ...
]
```

### D3. Qué pasa a la configuración y qué queda en el código

| Valor | Destino | Motivo |
|---|---|---|
| Municipios del área metropolitana, subconjuntos | Configuración | Es el caso que motivó el cambio: depende de requisitos de negocio. |
| Columnas de ciudad y dirección del archivo de entrada | Configuración | Dependen de la exportación del sistema académico. |
| Tipos de vía, palabras clave, equivalencias | Configuración | Son vocabulario ampliable. La semántica de cómo se aplican se queda en el código. |
| Columnas que crea el programa (`Complemento`, `Latitud`, `Longitud`) | Código | Son el contrato entre etapas, no un dato de entrada. |
| Directorios de trabajo y nombres de archivo | Código (`archivos.py`) | Los fija la especificación `archivos-de-salida`. Hacerlos configurables no lo pide nadie. |
| `barrios_medellin`, `CENTROIDE_MEDELLIN` | Código | `ubicacion-por-niveles` los elimina: los sustituyen el GeoJSON, `confidence` y `_type`. Llevarlos a la configuración sería versionar algo que va a desaparecer. |
| `n=300`, `n=400`, plantilla de consulta, `countrycode`, pausa de 1 s | Código | `ubicacion-por-niveles` rediseña la geocodificación (caché, presupuesto, sin `n`). Sus parámetros entrarán a la configuración en ese cambio, con su diseño definitivo. |
| Centro y zoom de los mapas | Código | El cambio `mapas` los sustituye por `fit_bounds`. |

### D4. Equivalencias como lista ordenada de pares

- **Por qué importa el orden.** El reemplazo actual es por subcadena y depende del orden: `NO` se aplica antes que `NORTE`, por lo que `NORTE` acaba como `#RTE`.
- **Cómo se fija.** Para reproducir exactamente la salida, el orden debe ser parte explícita de la configuración. Por eso las equivalencias se escriben como un array de pares `["PALABRA", "ABREVIATURA"]`.
- **Comentario en la configuración.** Explica que el orden importa.
- **Sin corregir.** Este cambio no arregla el defecto. Lo hará `ubicacion-por-niveles`, que pasará a palabras completas y dejará el orden como irrelevante.
- *Alternativa:* una tabla TOML (`CALLE = "CL"`). `tomllib` conserva el orden de inserción, pero eso no es visible para quien edita el archivo, y una tabla sugiere que el orden no importa.

### D5. Áreas, nombres de archivo y migración

- **Universo fijo.** El identificador del universo es fijo en el código: `area_metropolitana`. No se configura, porque el proyecto solo geocodifica el área metropolitana. Así los nombres de `estandarizado/` no cambian.
- **Nombres derivados del identificador del área:**
  - `coordenadas/coordenadas_<area>.xlsx`;
  - `mapas/<area>/` y `mapas/<area>/filtrados/`.

  La validación de D2 garantiza que el nombre de un subconjunto sea ASCII, así que la regla de nombres ASCII se cumple por construcción.
- **Extracción de un subconjunto (`extraer_subconjunto`):**
  1. lee el archivo del área metropolitana con `index_col=0`;
  2. filtra por la columna de ciudad;
  3. escribe con el mismo índice;
  4. llama a `visualizar` con la carpeta del subconjunto.

  No importa nada de `geocodificacion.py` que use la API.
- **Migración: se detecta el archivo antiguo y se detiene.** Si solo existe `coordenadas/coordenadas.xlsx`, las etapas que leen coordenadas terminan con un mensaje que pide renombrarlo.
- **Por qué es importante.** Sin esta comprobación, la conversión no encontraría el archivo nuevo y volvería a geocodificar todo desde `principales_area_metropolitana.xlsx`, gastando cuota.
- *Alternativa:* renombrar automáticamente. Se descarta porque mover datos del usuario sin avisar sorprende. Además, si el usuario restaura una copia antigua, el programa la renombraría otra vez.
- *Alternativa:* leer cualquiera de los dos nombres. Se descarta porque mantiene dos convenciones indefinidamente.
- **Mapas antiguos.** Los HTML de `mapas/` con el nombre antiguo no se tocan. El README indica que se pueden borrar.

### D6. Interfaz: `argparse` con subcomandos, menú como alternativa

- **Parser.** `cli.main(argv=None)` construye un parser con `--config` global y los subparsers `estandarizar`, `geocodificar`, `mejorar`, `mapas` y `subconjunto` (este último con `--area` obligatorio).
- **Modo `c`.** Antes de analizar los argumentos, `["c"]` se traduce a `["geocodificar"]`. Así el modo `c` funciona sin aparecer en la ayuda como un subcomando más.
- **Arranque.**
  1. Se carga la configuración. Si falla, termina con código 1.
  2. Se crean los directorios.
  3. Se ejecuta la etapa o, sin subcomando, el menú.
- **Menú.** Mantiene sus textos y la validación de la opción, y añade la opción 5. Solo la opción 1 abre el diálogo de tkinter o lee `original/`.
- **Subcomandos.** Nunca abren diálogos ni hacen preguntas: con `original/` vacío, terminan con un mensaje. Así pueden ejecutarse desde scripts.
- **Errores.** Siguen el estilo actual, `sys.exit("Error: …")`, que escribe en stderr con código 1. Los errores de uso los gestiona `argparse`, con código 2.
- *Alternativa:* Typer o Click. Se descarta por ser una dependencia más con usuarios técnicos que ya conocen el menú (D3 de la exploración).
- *Alternativa:* eliminar `main.py`. Se descarta por decisión del usuario: se mantiene como envoltorio por compatibilidad con la costumbre y con la configuración de PyCharm.

### D7. Parámetros explícitos en lugar de globales

- **Funciones de `direcciones.py`.** Reciben el vocabulario y los nombres de columna: `reemplazar_equivalentes(s, equivalencias)`, `dividir_complemento(s, palabras_clave)`, `format_dir(s, vocabulario)`, `separar_por_area(df, municipios, columna)`, etc.
- **Funciones de `geocodificacion.py`.** Reciben las columnas.
- **Lo que queda en el código** por D3 son constantes en mayúsculas en su módulo.
- **Sin clases nuevas.** No hacen falta, salvo las dataclasses de configuración. `VocabularioDirecciones` agrupa los tres valores relacionados y precalcula `palabras_clave_completas` (tipos de vía más palabras clave, el antiguo `keywords`).

### D8. Tests: los mismos valores esperados, con nuevos puntos de sustitución

- **Fixture de configuración.** `conftest.py` carga la configuración incluida con una fixture `configuracion`. Los tests de caracterización pasan el vocabulario desde ahí y conservan sus valores esperados.
- **Nuevos puntos de sustitución:**
  - `georef.geocodificacion.OpenCageGeocode` y `georef.geocodificacion.time.sleep`;
  - `georef.archivos.tk.Tk`.

  La fixture automática garantiza que ningún test llama a la API real.
- **Test de regresión del valor por defecto.** Contiene una copia literal de las constantes que tenía `main.py` y comprueba que `config/georef.toml` produce exactamente los mismos valores y el mismo orden. Es lo que demuestra que la configuración incluida reproduce el comportamiento anterior.
- **Cambios previstos y únicos en los tests existentes:**
  - las rutas de coordenadas y mapas;
  - `test_modo_c_columna_unnamed_defecto_conocido`, que pasa a comprobar que **no** aparece `Unnamed: 0`;
  - la invocación de `main.main()`, que pasa a `georef.cli.main(argv)`.
- **Tests nuevos:**
  - configuración: válida, inválida con varios errores, inexistente, sintaxis;
  - subcomandos, ayuda y errores de uso;
  - menú con la opción 5;
  - subconjunto: archivos, índice, sin llave, errores;
  - migración del nombre antiguo, archivos de bloqueo en `original/`, columna ausente.
- **Prueba de humo.** Ejecuta en un subproceso `python -m georef --help` y `python main.py --help`.
- **Guardia ASCII.** `test_identificadores_ascii.py` ya recorre todos los `.py` del repositorio, así que cubre `georef/` sin cambios.

### D9. Documentación con pdoc

- **Generación.** `docs/` se regenera con `pdoc georef -o docs`, que sustituye por completo el contenido anterior (`main.html` y `search.js` desaparecen).
- **Dependencia.** `pdoc=16.0.0` se declara en `environment.yml` junto a pytest, como dependencia de desarrollo.
- **Comando y contenido.** El comando queda en el README. pdoc solo publica docstrings y firmas, sin datos.
- **Requisito sobre las importaciones.** pdoc importa los módulos, así que el paquete no debe tener efectos al importarse (abrir ventanas, leer la configuración o crear directorios). Esto también es necesario para los tests.

### D10. Notebook

`notebooks/exploracion_geojson.ipynb` pasa a leer `coordenadas/coordenadas_area_metropolitana.xlsx`. Se edita esa celda y se mantiene el notebook sin salidas. `hallazgos_geojson.md` no cambia, porque describe una ejecución pasada.

## Risks / Trade-offs

- [Un cambio sutil de comportamiento al mover el código] → Los tests de caracterización se migran sin cambiar sus valores esperados. Antes de borrar `main.py`, se ejecuta la estandarización sobre el archivo real con el código antiguo y con el nuevo y se comparan los cuatro archivos de `estandarizado/` (comprobación local, sin API y sin versionar datos).
- [El usuario no renombra `coordenadas.xlsx`] → El aviso de D5 detiene las etapas antes de gastar cuota. El README explica la migración.
- [Un municipio mal escrito en la configuración (por ejemplo, con tilde) deja de coincidir con los datos sin error] → Los subconjuntos sin registros terminan con un mensaje. El comentario de la configuración indica que los municipios se escriben exactamente como en el archivo de entrada.
- [La configuración se busca relativa al directorio de trabajo] → Es la misma convención que `.env`, `original/` y las demás carpetas. Si se ejecuta desde otro directorio, el mensaje nombra la ruta buscada.
- [Seguir usando `main.py` retrasa la adopción de los subcomandos] → Es aceptable: es una decisión del usuario y no duplica lógica.

## Migration Plan

1. Actualizar el entorno: `conda env update -f environment.yml -n medellin-analysis312` (añade pdoc).
2. Renombrar `coordenadas/coordenadas.xlsx` a `coordenadas/coordenadas_area_metropolitana.xlsx`. No hay que volver a geocodificar.
3. Ejecutar `python -m georef mapas` y, si se quiere, `python -m georef subconjunto --area medellin`. Opcionalmente, borrar los HTML antiguos de `mapas/` y `mapas/filtrados/`.

**Vuelta atrás:** revertir el commit y renombrar el archivo de coordenadas a su nombre anterior.
