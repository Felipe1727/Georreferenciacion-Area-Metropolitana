# Design

## Context

Para el motivo, ver `proposal.md` (Why). Estado de partida:

- **`georef/mapas.py`** tiene una sola función, `visualizar(df, carpeta)`.
  - Dibuja un `folium.Marker` por registro y un `FastMarkerCluster`.
  - Repite todo para los registros que no son de nivel `MUNICIPIO`.
  - Centra los mapas con `CENTRO_MAPA` y `ZOOM_INICIAL` fijos.
  - La llaman `etapas.generar_mapas` y `etapas.extraer_subconjunto`.
- **`archivos.estructura_programa`** crea `mapas/area_metropolitana/filtrados/` al arrancar.
- **Archivo de coordenadas.** Desde `ubicacion-por-niveles` trae `Latitud`, `Longitud`, `Nivel ubicacion`, `Resultado consulta`, `Barrio ubicacion`, `Codigo barrio ubicacion` y `Comuna ubicacion`, además de las columnas del archivo de entrada (con datos personales). Todos los registros tienen punto.
- **`georef/geografia.py`** (`Poligonos`) tiene las geometrías de 349 barrios y 21 comunas en EPSG:9377 (metros), y un `Transformer` a WGS84.
- **Tamaño de las geometrías.** El GeoJSON pesa 14,8 MB. En WGS84 con 5 decimales mide así:

  | Simplificación | Barrios | Comunas |
  |---|---|---|
  | Sin simplificar | 5,86 MB | 1,61 MB |
  | 2 m | 0,99 MB | 0,28 MB |
  | 5 m | 0,61 MB | 0,17 MB |
  | 10 m | 0,41 MB | 0,11 MB |

- **APIs revisadas** en el entorno instalado (folium 0.20.0, branca 0.8.2):
  - `Map.fit_bounds(bounds, ..., max_zoom=None)`;
  - `FeatureGroup(name, overlay, control, show)`;
  - `FastMarkerCluster(data, ..., name, show)`;
  - `GeoJson(data, style_function, ..., name, show, tooltip)` y `GeoJsonTooltip(fields, aliases)`;
  - `DivIcon(html, icon_size, icon_anchor)`, `Popup(html, max_width)` y `LayerControl(collapsed)`;
  - `branca.colormap.linear.YlOrRd_09`.

  Tras construirlos, los objetos exponen `layer_name`, `show`, `_children`, `DivIcon.options["html"]`, `FastMarkerCluster.data` y `GeoJson.data`, que usarán los tests.
- **Datos de prueba** (solo cifras): 94 registros y 51 puntos distintos. 18 de esos puntos agrupan a 61 registros, con un máximo de 9 en un punto.

## Goals / Non-Goals

**Goals:**
- Que los mapas se puedan probar sin abrir un navegador: la construcción devuelve objetos `folium.Map` y los tests inspeccionan sus capas. Solo se escriben y leen HTML para comprobar los archivos y la ausencia de datos personales.
- Que `mapa.html` del área metropolitana pese menos de 3 MB.

**Non-Goals:**
- Cambiar la ubicación o el archivo de coordenadas.
- Estilo configurable desde `config/georef.toml`: colores, tamaños y tolerancia quedan como constantes del módulo.
- Teselas distintas de las de folium por defecto (OpenStreetMap). Ver D11.

## Decisions

### D1. Estructura de `georef/mapas.py`

- **Constantes:**
  - `VISTAS = ("puntos", "clusters", "barrios_cantidad", "comunas_cantidad")` y `VISTAS_COLOREADAS`;
  - `COLORES_NIVEL`;
  - `ZOOM_MAXIMO = 15`.
- **`mapa_con_capas(df, poligonos=None) -> folium.Map`** devuelve el mapa completo. Los polígonos se dibujan solo si `poligonos` no es None.
- **`mapa_separado(df, vista, poligonos=None, sin_municipio=False) -> folium.Map`** devuelve una vista. Los separados `puntos` y `clusters` llevan además, como referencia, el contorno de las comunas (visible) si el área tiene polígonos.
- **`generar(df, carpeta, poligonos=None, separados=(), sin_municipio=False) -> list[Path]`** escribe `mapa.html` y los separados, y devuelve las rutas escritas.
- **Funciones privadas** para cada pieza, que comparten `mapa_con_capas` y `mapa_separado`:
  - `_capas_puntos`, `_clusters`, `_contornos`, `_coloreada`;
  - `_encuadrar`, `_leyenda_niveles`.

Se descarta mantener `visualizar`: cambian su contrato y sus archivos, y un nombre nuevo hace evidente el cambio en las etapas.

### D2. Puntos: un `Marker` con `DivIcon` por sitio y nivel

- **Agrupación.** Se agrupa con `groupby(["Nivel ubicacion", "Latitud", "Longitud"])`. Cada grupo produce un `folium.Marker` con un `DivIcon` cuyo HTML es un círculo:
  - **diámetro:** `min(14 + 6·√(n−1), 44)` px, con `icon_anchor` en el centro;
  - **relleno:** el color del nivel, con borde blanco y opacidad 0,85;
  - **número:** dentro del círculo si `n > 1`.
- **Capas.** Cada nivel es un `FeatureGroup` llamado `"<NIVEL> (<n> registros)"`. Los niveles sin registros no tienen capa.
- **Alternativa descartada: `CircleMarker`.** Escala en píxeles, pero no admite texto dentro. Un tooltip permanente con el número llena el mapa de etiquetas superpuestas.
- **Colores** (paleta Okabe-Ito, distinguible con daltonismo):

  | Nivel | Color | Número |
  |---|---|---|
  | `DIRECCION` | `#009E73` (verde) | blanco |
  | `BARRIO` | `#0072B2` (azul) | blanco |
  | `COMUNA` | `#E69F00` (naranja) | negro, por contraste |
  | `MUNICIPIO` | `#7F7F7F` (gris) | blanco |

- **Leyenda.** Un bloque HTML fijo, abajo a la izquierda, añadido con `folium.Element` a `get_root().html`, con los cuatro niveles y una línea: "El número indica cuántos registros comparten el punto".

### D3. Ventana del punto

`folium.Popup(html, max_width=300)`. El HTML se compone con `html.escape` sobre cada valor:
- nivel;
- municipio: la columna de ciudad de la configuración, el único valor del archivo de entrada que se muestra (es el de ubicación en el nivel MUNICIPIO);
- `Barrio ubicacion` y `Comuna ubicacion` del grupo, si no son nulos;
- `Registros: n`;
- recuento por `Resultado consulta`.

Se construye solo con esas columnas. Ninguna otra llega a `mapas.py`: `generar` recibe un DataFrame recortado a las columnas que usa (ver D8).

### D4. Clusters

`FastMarkerCluster(data=[[lat, lon], ...], name=..., show=False)` dos veces: "Clusters" con todos los registros y "Clusters sin MUNICIPIO". `data` solo contiene coordenadas.

### D5. Geometrías para dibujar, en `Poligonos`

- **Método nuevo.** `Poligonos.geojson(tipo)`, con `tipo` `"barrios"` o `"comunas"`, devuelve un FeatureCollection en WGS84. Cada geometría se procesa así:
  1. simplificar con `geometria.simplify(5)` en metros, sobre el CRS del archivo;
  2. transformar con el `Transformer` existente;
  3. ajustar con `shapely.set_precision(…, 1e-5)`.
- **Propiedades.** Barrios: `codigo`, `nombre` y `comuna`. Comunas: `nombre`.
- **Caché.** Se calcula una vez por instancia, que ya está en caché por proceso.
- **Límites.** `Poligonos.limites_wgs84()` devuelve `[[min_lat, min_lon], [max_lat, max_lon]]` del municipio.
- **Alternativas descartadas:**
  - incrustar el GeoJSON original: 14,8 MB y en un CRS que Leaflet no entiende;
  - `geopandas.to_json`: el aviso de PROJ ya descrito en `ubicacion-por-niveles`.

  Con 5 m, los contornos de barrios vecinos pueden diferir unos metros en la frontera. A escala de ciudad no se nota.

### D6. Contornos y capas coloreadas

- **Contornos.** `folium.GeoJson` sin relleno:
  - comunas: grosor 2, gris oscuro, `show=True`;
  - barrios: grosor 1, gris, `show=False`;
  - `GeoJsonTooltip` con el nombre (y la comuna en los barrios).
- **Coloreadas.** Se cuentan los registros con `value_counts` de `Codigo barrio ubicacion` y de `Comuna ubicacion`, y la cuenta se copia en la propiedad `registros` de cada feature (de una copia profunda del FeatureCollection).
  - **Color de relleno:** `style_function` con `branca.colormap.linear.YlOrRd_09.scale(1, max)`. Los polígonos con 0 registros van en `#d9d9d9` con opacidad 0,3.
  - **Tooltip:** nombre y registros.
  - **Leyenda:** el colormap, con `caption` "Registros por barrio" o "Registros por comuna", se añade al mapa.
  - **Visibilidad:** en `mapa.html`, `show=False`.
- **Alternativa descartada: `folium.Choropleth`.** No controla directamente el color de los ceros, y añadir el tooltip con la cuenta exige tocar su `geojson` interno.

### D7. Encuadre

- **Encuadre.** `_encuadrar(mapa, limites)` llama a `fit_bounds(limites, max_zoom=ZOOM_MAXIMO)`. Los límites dependen del mapa:
  - puntos y clusters: mínimo y máximo de latitud y longitud de los registros dibujados;
  - coloreadas: `poligonos.limites_wgs84()`;
  - `mapa.html`: los de los puntos.
- **Construcción.** El mapa se crea con `location` en el centro de esos límites y `zoom_start=12`, para que folium tenga un estado inicial válido, y después se encuadra.

### D8. Etapas

`etapas.generar_mapas(configuracion, separados=(), sin_municipio=False)` y `etapas.extraer_subconjunto(configuracion, nombre, separados=(), sin_municipio=False)` hacen lo siguiente:

1. **Comprobaciones previas, antes de escribir nada.** Además de las actuales:
   1. `--sin-municipio` sin separados: termina con un mensaje.
   2. Se resuelve `todos` a las vistas disponibles.
   3. Si el área no incluye el municipio con polígonos y se pidió por su nombre una vista coloreada: termina con un mensaje. En el subconjunto, antes de escribir `coordenadas_<nombre>.xlsx`.
2. **¿Tiene polígonos el área?** Sí si `configuracion.referencia.municipio_con_poligonos` está en sus municipios, que son `configuracion.area_metropolitana` o `configuracion.subconjuntos[nombre]`. Solo en ese caso se carga `Poligonos.cargar(...)`, y un `ErrorReferencia` termina con su mensaje.
3. **Recorte de columnas.** El DataFrame se recorta a las columnas de ubicación y la de ciudad antes de llamar a `mapas.generar`.
4. **Aviso de mapas anteriores.** Si existen `individual.html`, `clusters.html` o `filtrados/` en la carpeta del área, se imprime un aviso que los nombra, sin borrarlos.
5. **Salida.** Se imprimen las rutas escritas. Con `todos` en un área sin polígonos, se indica que las vistas coloreadas no aplican.

`archivos.estructura_programa` crea `mapas/area_metropolitana/` en lugar de `.../filtrados/`.

### D9. CLI y menú

- **Subcomandos.** `mapas` y `subconjunto` reciben:
  - `--separado`, con `action="append"`, `choices=VISTAS + ("todos",)` y `metavar="VISTA"`. argparse rechaza una vista desconocida con código 2 y lista las válidas, antes de cargar nada.
  - `--sin-municipio`, con `action="store_true"`.
- **Menú.** Las opciones 3 y 4 llaman a `preguntar_separados()`:
  - pregunta "Mapas separados para compartir (puntos, clusters, barrios_cantidad, comunas_cantidad o todos; varios separados por comas; Enter para ninguno)";
  - un nombre inválido se indica y se vuelve a preguntar;
  - si hay alguno, pregunta "¿Quitar el nivel MUNICIPIO de los separados de puntos y clusters? (s/N)".

  Devuelve `(separados, sin_municipio)`.

### D10. Tests

- **`tests/test_mapas.py` se reescribe** contra `mapa_con_capas`, `mapa_separado` y `generar`, con DataFrames sintéticos y los polígonos reales de `data/` (se cargan una vez por proceso). Inspecciona:
  - nombres y visibilidad de las capas (`layer_name`, `show`);
  - número de marcadores por capa y HTML de su `DivIcon`;
  - `FastMarkerCluster.data`;
  - propiedades `registros` de las capas coloreadas.

  Comprueba también el contenido de la ventana. Un test de privacidad escribe los HTML con columnas personales sintéticas y comprueba que sus valores no aparecen. Un test de tamaño comprueba que `mapa.html` con todos los polígonos pesa menos de 3 MB.
- **Se adaptan:** `test_etapas.py`, `test_subconjuntos.py`, `test_cli.py`, `test_flujo_principal.py` (las respuestas del menú incluyen la pregunta de separados) y `test_archivos.py`.

### D11. `ver-mapas`: servidor local para que OpenStreetMap acepte las peticiones

- **Problema.** Al abrir `mapa.html` con doble clic (`file://`), el navegador no envía `Referer`, y `tile.openstreetmap.org` devuelve una imagen 403 "Access blocked", según su política de uso, que exige `Referer`. Comprobado con curl el 2026-10-16:
  - sin `Referer`: imagen de bloqueo;
  - con `Referer` `http://127.0.0.1:<cualquier puerto>/`: la tesela real.
- **Solución.** `georef/visor.py` con `servir(carpeta_mapas, ruta_inicial)`. Usa `ThreadingHTTPServer` y `webbrowser.open` del módulo, que los tests sustituyen con `monkeypatch`:
  - **Servidor.** `ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=carpeta_mapas))`. El puerto 0 deja que el sistema elija uno libre.
  - **Registro.** Un manejador derivado silencia el registro de cada petición.
  - **Arranque.** Imprime la URL, llama a `abrir(url)` y sirve con `serve_forever()` hasta `KeyboardInterrupt`. Después cierra el servidor e imprime "Servidor detenido".
- **Comprobaciones previas en `etapas.ver_mapas(configuracion, area)`:**
  - el área es `area_metropolitana` o un subconjunto configurado;
  - existe `mapas/<area>/mapa.html`.
- **Alternativas descartadas:**
  - **CARTO:** sin llave devuelve "API KEY REQUIRED".
  - **Esri:** responde sin `Referer`, pero no se confirmaron sus condiciones de uso.
  - **OSM Francia:** son servidores voluntarios con política propia, que no se revisó.
  - **Fijar el puerto 8000:** falla si está ocupado.
- **Tests.** Con un servidor y un navegador falsos se comprueban la dirección `127.0.0.1`, el directorio, la URL abierta y el cierre con Ctrl+C. Una prueba real con `urllib` contra el servidor en un hilo se salta si la interfaz de loopback no está disponible, como pasa con `unshare -rn`.

## Risks / Trade-offs

- [Las leyendas de las dos capas coloreadas de `mapa.html` se ven siempre, aunque la capa esté apagada, porque los colormaps de branca no se asocian a una capa] → Captions explícitos ("Registros por barrio", "Registros por comuna"). En los separados solo hay una.
- [Los puntos de nivel DIRECCION son ubicaciones aproximadas de viviendas, y un HTML se comparte con facilidad] → La ventana no muestra datos del estudiante (D3). El README advierte antes de compartir y recuerda que `--sin-municipio` no anonimiza.
- [El tamaño del círculo satura en 44 px: un barrio con 9 y otro con 60 registros se distinguen por el número, no por el tamaño] → Es intencionado, para que un círculo no tape media comuna. El número es la información exacta.
- [Los tests dependen de atributos internos de folium (`_children`)] → La versión está fijada en `environment.yml` (0.20.0). Si cambia, fallan los tests, no los mapas.
- [Un HTML compartido y abierto con doble clic se ve sin fondo (OSM bloquea las teselas sin `Referer`)] → Puntos, contornos y capas coloreadas se dibujan igualmente. El README explica cómo verlo con `ver-mapas` o con `python -m http.server`.
- [La simplificación a 5 m deja huecos de pocos metros entre polígonos vecinos] → Invisible a escala de ciudad. La tolerancia es una constante.

## Migration Plan

1. Tras actualizar, `python -m georef mapas` escribe `mapas/area_metropolitana/mapa.html` y avisa de los HTML anteriores que existan. Se borran a mano.
2. Los subconjuntos se regeneran con `python -m georef subconjunto --area <nombre>`.
3. Para volver atrás basta con la versión anterior del código: no cambia ningún archivo de datos.
