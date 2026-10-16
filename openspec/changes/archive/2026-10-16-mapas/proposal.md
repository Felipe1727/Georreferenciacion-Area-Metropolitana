# Proposal

## Why

Desde `ubicacion-por-niveles`, cada registro tiene un punto y un nivel de precisión, pero los mapas siguen siendo los de `main.py`:
- **Archivos sueltos.** Hay 4 archivos por área: individual, clusters y sus versiones "filtradas".
- **Marcadores apilados.** Todos los marcadores son iguales. Los registros que comparten el punto de su barrio, comuna o municipio quedan uno encima de otro. En la base de prueba, 61 de 94 registros comparten punto, con hasta 9 en el mismo sitio, y el mapa los muestra como uno solo.
- **Encuadre fijo.** El mapa siempre se centra en Medellín con un zoom fijo, aunque el área sea otra.
- **Sin divisiones territoriales.** No se ven las comunas ni los barrios, que son la referencia con la que se lee la distribución.

## What Changes

- **Un mapa con capas por área.** `mapas/<area>/mapa.html` reúne lo que hoy está en los 4 archivos:
  - una capa de puntos por nivel (DIRECCION, BARRIO, COMUNA, MUNICIPIO), que se activan y desactivan;
  - dos capas de clusters: todos los registros y sin MUNICIPIO;
  - contornos de comunas y de barrios;
  - barrios y comunas coloreados por cantidad de registros;
  - leyenda de niveles y encuadre automático a los datos.
- **Puntos agrupados por sitio.** Los registros con el mismo punto y nivel se dibujan como un solo círculo del color de su nivel. Su tamaño depende del número de registros, y el número aparece dentro.
- **Ventana solo con datos de ubicación.** Al hacer clic en un punto se ve el nivel, el municipio, el barrio y la comuna de ubicación, el número de registros y sus resultados de consulta. Nunca aparecen la dirección ni ninguna otra columna del estudiante.
- **Mapas separados a elección.** `mapas --separado <vista>` (repetible, o `todos`) escribe además en `mapas/<area>/separados/` un HTML autónomo por vista: `puntos`, `clusters`, `barrios_cantidad` y `comunas_cantidad`. Están pensados para compartir un solo archivo. Con `--sin-municipio`, los separados de puntos y clusters excluyen el nivel MUNICIPIO. `subconjunto` acepta las mismas opciones, y las opciones 3 y 4 del menú preguntan qué separados generar.
- **Ver los mapas con el fondo.** Las teselas de OpenStreetMap se bloquean al abrir un HTML con doble clic, porque su política exige que el navegador envíe `Referer` y una página `file://` no lo envía. Por eso se añade `python -m georef ver-mapas [--area <nombre>]`, que sirve `mapas/` solo en `127.0.0.1` y abre el mapa en el navegador. Se mantiene OpenStreetMap: no se encontraron condiciones de uso confirmadas de otro proveedor que funcione sin llave.
- **Capas de Medellín solo donde aplican.** Los polígonos y las capas coloreadas solo aparecen si el área incluye el municipio con polígonos. Pedir un separado coloreado para otra área termina con un mensaje.
- **BREAKING:** dejan de generarse `individual.html`, `clusters.html` y la carpeta `filtrados/`. Si existen los de una ejecución anterior, se avisa de que ya no se actualizan, pero no se borran. Al arrancar ya no se crea `mapas/area_metropolitana/filtrados/`.

## Capabilities

### New Capabilities
- `mapas`: contenido y archivos de los mapas de un área:
  - mapa con capas;
  - agrupación de puntos y colores por nivel;
  - ventana de cada punto;
  - capas de polígonos y coloreadas de Medellín;
  - encuadre;
  - mapas separados;
  - aviso de los mapas del formato anterior.

### Modified Capabilities
- `ubicacion-por-niveles`: se elimina "Mapas filtrados por nivel". El filtrado por nivel pasa a ser una capa o la opción `--sin-municipio` de `mapas`, y la comprobación de la columna `Nivel ubicacion` se traslada allí.
- `archivos-de-salida`: los nombres de los mapas generados ("Nombres de archivos generados en ASCII") y la carpeta que se crea al arrancar ("Estructura de directorios de trabajo"). Además, la exclusión de `mapas/` en git deja de afectar a los artefactos de `openspec/` llamados `mapas` ("Datos sensibles excluidos del control de versiones").
- `areas-geograficas`: los mapas de un subconjunto ("Extracción de un subconjunto sin consultar al proveedor").
- `linea-de-comandos`: opciones `--separado` y `--sin-municipio` de `mapas` y `subconjunto`, y subcomando `ver-mapas` ("Subcomandos no interactivos", "Argumentos inválidos y ayuda"); preguntas de las opciones 3 y 4 del menú ("Menú interactivo sin argumentos").

## Impact

- **Código:**
  - `georef/mapas.py` se reescribe.
  - `georef/geografia.py` añade las geometrías en WGS84 simplificadas para dibujar.
  - `georef/etapas.py` cambia en `generar_mapas` y `extraer_subconjunto`.
  - `georef/cli.py` gana las opciones y las preguntas del menú.
  - `georef/archivos.py` cambia la estructura de carpetas.
- **Tests:** `test_mapas.py` se reescribe. Se adaptan `test_etapas.py`, `test_subconjuntos.py`, `test_cli.py`, `test_flujo_principal.py` y `test_archivos.py`.
- **Dependencias:** ninguna nueva. Se usan folium 0.20.0 y branca 0.8.2, que ya instala folium, junto con shapely y pyproj, ya presentes.
- **Datos:** solo lectura del archivo de coordenadas y del GeoJSON. No se consulta al proveedor ni hace falta la llave.
- **Privacidad:** los HTML siguen en `mapas/`, ignorada por git. Los puntos de nivel DIRECCION muestran una ubicación aproximada de la vivienda, así que el README advierte de ello antes de compartir un mapa.
- **Repositorio:** `.gitignore` gana la excepción `!openspec/**/mapas/`. Sin ella, la regla `mapas/` ocultaría a git este cambio y su spec.
- **Documentación:** README (uso, mapas, migración) y `docs/`.
- **Fuera de alcance:** mapa de calor, columnas del estudiante en la ventana, filtros por programa u otras variables, y mapas de registros de fuera del área metropolitana.
