# Proposal

## Why

La conversión de coordenadas actual no sirve para ubicar a los estudiantes:
- **Calidad de los resultados.** Toma el primer resultado de OpenCage sin mirar su precisión. En la exploración, el 41 % de los puntos caía en el centroide de Medellín (la API solo había resuelto la ciudad), y solo entre el 12 % y el 22 % de los puntos "precisos" caía en el barrio que declaró el estudiante.
- **Proceso por lotes.** Procesa lotes fijos de 300 registros y guarda solo al final.
- **Errores sin rastro.** Los errores dejan vacíos sin explicación.
- **Mejora poco fiable.** La "mejora" vuelve a consultar la API con una lista de barrios escrita a mano, incompleta y en buena parte inválida.

`normalizacion-direcciones` ya dejó el barrio, su código, la comuna y la zona de cada estudiante de Medellín como columnas fiables, y el GeoJSON oficial está en el repositorio. Con eso, cada estudiante del área metropolitana puede recibir la mejor ubicación disponible y quedar marcado con su precisión. La API se usa solo donde puede aportar algo: direcciones de vía principal de Medellín. Todo cabe en la cuota diaria del free trial: unas 620 consultas distintas.

## What Changes

- **Nueva etapa `ubicar`, que sustituye a la conversión de coordenadas.** Asigna a cada registro del área metropolitana (principales y especiales) un punto por niveles:
  - **DIRECCION:** punto de la API, solo para las vías principales de Medellín y solo si pasa la validación.
  - **BARRIO:** punto representativo del polígono del barrio declarado.
  - **COMUNA:** punto representativo de la unión de los polígonos de la comuna declarada.
  - **MUNICIPIO:** punto fijo del municipio. Es el único nivel de los otros 9 municipios del área, que nunca se consultan.
- **Validación del punto de la API:**
  - el tipo de resultado (`_type`) no es de ciudad o superior y la `confidence` llega a un mínimo configurable;
  - el punto cae en Medellín;
  - si el estudiante declaró un barrio (o, si no, una comuna), el punto está a 250 m como máximo de su polígono (tolerancia configurable). Si no, prevalece el lugar declarado.

  Desaparece la coordenada fija del centroide de Medellín.
- **Columnas nuevas en el archivo de coordenadas.**
  - `Nivel ubicacion` y `Resultado consulta`: por qué se aceptó o rechazó la consulta, o por qué quedó pendiente.
  - `Barrio ubicacion`, `Codigo barrio ubicacion` y `Comuna ubicacion`: polígono oficial en el que cae el punto asignado.

  Los metadatos de la API quedan en la caché, no en el Excel.
- **Consultas robustas y reanudables:**
  - **Caché.** Una caché CSV por consulta evita repetir peticiones; dos estudiantes con la misma dirección comparten una sola.
  - **Ritmo.** La pausa de al menos 1 s se aplica antes de cada petición, también después de un error.
  - **Paradas limpias.** Ante cuota agotada, demasiados errores seguidos o el límite de consultas por ejecución, el proceso deja de consultar sin perder lo obtenido. Los registros afectados reciben su ubicación de respaldo, marcada como pendiente, y volver a ejecutar continúa donde se quedó.
  - **BREAKING:** desaparecen `n=300` y la reanudación desde el Excel de coordenadas. El Excel se regenera entero en cada ejecución a partir de `estandarizado/` y la caché.
- **Registro de diagnóstico** por petición: hora, duración, resultado o tipo de error y peticiones restantes, si la API lo informa. Sirve para medir la causa del fallo histórico de "~350 registros" sin cliente HTTP propio.
- **Constructor de consultas** con dos formatos, elegibles en la configuración: abreviado (`CL 10 #20-30, MEDELLIN, ANTIOQUIA, Colombia`) y expandido (`Calle 10 # 20-30, ...`). La consulta nunca incluye el complemento de vivienda. Opcionalmente, desactivada por defecto, hay una segunda consulta con el lugar con nombre del complemento (`UNIDAD LOS PINOS`).
- **Nuevos subcomandos:**
  - `consultar-municipios`: consulta una sola vez los 10 municipios (10 peticiones) y añade sus puntos a `config/georef.toml`, con fuente y fecha, para revisarlos o corregirlos a mano.
  - `comparar-consultas --muestra 50`: diagnóstico A/B de los dos formatos, de unas 100 peticiones, que solo informa cifras agregadas.
  - `ubicar --sin-consultas`: ubica usando solo la caché, sin llave ni peticiones.
- **BREAKING (CLI):**
  - `geocodificar` pasa a llamarse `ubicar`; `python main.py c` lo sigue ejecutando.
  - Se eliminan la mejora de coordenadas (opción 3 y subcomando `mejorar`) y la lista `BARRIOS_MEDELLIN`.
  - El menú queda en 1 estandarizar, 2 ubicar, 3 mapas y 4 subconjunto.
- **Mapas.** Los mapas "filtrados" excluyen los registros de nivel MUNICIPIO en lugar de una coordenada fija. El resto de los mapas queda para el cambio `mapas`.
- **Archivo de coordenadas anterior.** Si `coordenadas_area_metropolitana.xlsx` tiene el formato anterior (sin `Nivel ubicacion`), se conserva como `coordenadas_area_metropolitana_anterior.xlsx` antes de escribir el nuevo.

## Capabilities

### New Capabilities

- `ubicacion-por-niveles`: qué punto recibe cada registro del área metropolitana. Cubre:
  - los niveles DIRECCION, BARRIO, COMUNA y MUNICIPIO;
  - la validación del punto de la API con el lugar declarado;
  - las columnas del archivo de coordenadas;
  - los puntos de los municipios;
  - el criterio de los mapas filtrados.
- `consultas-proveedor`: cómo se consulta a OpenCage. Cubre:
  - formato de las consultas;
  - pausa entre peticiones;
  - caché y reanudación;
  - paradas por cuota, errores o límite;
  - registro de diagnóstico;
  - diagnóstico A/B y consulta única de los municipios.

### Modified Capabilities

- `linea-de-comandos`:
  - subcomandos `ubicar`, `consultar-municipios` y `comparar-consultas`;
  - se eliminan `geocodificar` y `mejorar`;
  - menú de 4 opciones;
  - `python main.py c` ejecuta `ubicar`.
- `configuracion`: el archivo gana la sección `[ubicacion]` (formato de consulta, umbrales, tolerancia, pausa, límite, consulta del complemento y nombres de vía) y la sección `[puntos_municipios]`, con su validación.
- `archivos-de-salida`:
  - la ubicación lee los principales y los especiales de `estandarizado/` y regenera el archivo de coordenadas;
  - nuevos archivos de caché y de registro en `coordenadas/`;
  - el archivo de formato anterior se conserva;
  - el aviso del nombre antiguo ya no menciona la mejora.
- `credenciales-geocodificacion`: las operaciones que exigen la llave pasan a ser `ubicar` (salvo `--sin-consultas`), `comparar-consultas` y `consultar-municipios`.
- `areas-geograficas`: el área metropolitana pasa a las etapas de ubicación y mapas; ya no existe la etapa de mejora.

## Impact

- **Código:**
  - nuevo `georef/geografia.py`: polígonos de barrios, comunas y municipio, con `shapely` y `pyproj`; distancias en EPSG:9377;
  - nuevo `georef/ubicacion.py`: la cascada;
  - `georef/geocodificacion.py` se reescribe: cliente con pausa, caché, registro, paradas y formatos de consulta. Se eliminan `geocodificar_direcciones`, `rellenar_por_barrio`, `BARRIOS_MEDELLIN` y `CENTROIDE_MEDELLIN`;
  - se adaptan `georef/config.py`, `georef/etapas.py`, `georef/cli.py` y `georef/mapas.py`.
- **Dependencias:**
  - `shapely` y `pyproj` pasan a ser dependencias directas en `environment.yml`, con las versiones ya instaladas como parte de geopandas: 2.1.2 y 3.7.2;
  - se sigue usando la librería `opencage` 3.3.0, sin cliente HTTP propio.
- **Configuración:** `config/georef.toml` gana `[ubicacion]`. `[puntos_municipios]` la añade el subcomando `consultar-municipios`.
- **Salidas:**
  - `coordenadas/coordenadas_area_metropolitana.xlsx` cambia de columnas y pasa a incluir los registros especiales;
  - nuevos `coordenadas/cache_consultas.csv` y `coordenadas/registro_consultas.csv`, ignorados por git como todo `coordenadas/`.
- **Cuota de OpenCage.** La implementación y los tests no hacen ninguna petición real. Después, en la primera ejecución real (a cargo del usuario):
  - unas 10 peticiones para los municipios;
  - unas 100 para el diagnóstico A/B;
  - unas 620 para ubicar a todo el área.

  En total caben en un día del free trial (2.500).
- **Fuera de alcance:**
  - registros de fuera del área metropolitana (solo se exportan);
  - polígonos de otros municipios;
  - colores, capas o centrado de los mapas (cambio `mapas`);
  - cliente HTTP propio con timeout.
