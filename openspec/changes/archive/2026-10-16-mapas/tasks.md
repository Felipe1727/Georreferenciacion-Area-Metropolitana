# Tasks

## 1. Línea base

- [x] 1.1 Verificar que `python -m pytest` pasa completo en la rama `mapas` antes de empezar, y que `conda list -n medellin-analysis312 "folium|branca"` muestra folium 0.20.0 y branca 0.8.2
- [x] 1.2 La regla `mapas/` de `.gitignore` ignora también `openspec/changes/mapas/` y, tras archivar, `openspec/specs/mapas/`. Añadir después de ella la excepción `!openspec/**/mapas/`, con un comentario. Verificar con `git check-ignore -v` el escenario "Artefactos de OpenSpec con el nombre de un directorio de datos" de `specs/archivos-de-salida`, que `git status` muestra `openspec/changes/mapas/` sin seguimiento y que los demás escenarios de "Datos sensibles excluidos del control de versiones" se siguen cumpliendo. Añadir el escenario a los tests de exclusión de `tests/test_credenciales.py` y verificar que pasan

## 2. Geometrías para dibujar

- [x] 2.1 Añadir a `Poligonos` los métodos `geojson(tipo)` y `limites_wgs84()` (D5): simplificación a 5 m en EPSG:9377, transformación a WGS84, precisión 1e-5, propiedades `codigo`/`nombre`/`comuna` en barrios y `nombre` en comunas, y caché por instancia. Ampliar `tests/test_geografia.py`, sobre el GeoJSON real:
  - 349 barrios y 21 comunas;
  - todas las coordenadas en el recuadro de Medellín (latitud de 6 a 6,5 y longitud de −75,8 a −75,4);
  - `codigo` como texto con su cero inicial;
  - serializado en JSON, barrios por debajo de 1 MB y comunas por debajo de 0,3 MB;
  - `limites_wgs84()` contiene `recuadro()`.

  Verificar que pasa

## 3. Puntos, clusters y encuadre

- [x] 3.1 Reescribir `georef/mapas.py` con las constantes de D1 y `mapa_con_capas(df)` sin polígonos (D2, D3, D4 y D7): una capa por nivel con un `Marker`/`DivIcon` por sitio, ventana con datos de ubicación, leyenda, las dos capas de clusters, encuadre con zoom máximo 15 y `LayerControl`. Mantener temporalmente `visualizar` como envoltorio que escribe `mapa.html`, para que las etapas sigan funcionando. Reescribir `tests/test_mapas.py` con estos escenarios de `specs/mapas`:
  - "Mapa del área metropolitana" (nombres de capas);
  - "Clusters con y sin MUNICIPIO";
  - "Nivel sin registros";
  - "Varios registros en el punto de un barrio" (un marcador, `9` en el HTML del icono, diámetro mayor);
  - "Un solo registro";
  - "Mismo punto en distinto nivel";
  - "Ventana de un punto de barrio";
  - "Subconjunto de un municipio" y "Un único punto" (límites y `max_zoom` en el HTML).

  Verificar que pasan y que la suite completa sigue pasando

## 4. Capas de Medellín

- [x] 4.1 Añadir a `mapa_con_capas(df, poligonos)` los contornos y las capas coloreadas (D6): cuentas por `Codigo barrio ubicacion` y `Comuna ubicacion`, gris para los ceros, tooltips y colormaps con su caption. Añadir a `tests/test_mapas.py` estos escenarios:
  - "Área metropolitana" (cuatro capas y solo los contornos de comunas visibles);
  - "Subconjunto sin Medellín" (sin `poligonos`, ninguna capa de polígonos);
  - "Cantidad por barrio y por comuna", con un barrio real y su comuna;
  - "Registros de nivel MUNICIPIO".

  Verificar que pasan

## 5. Mapas separados y escritura

- [x] 5.1 Añadir `mapa_separado(df, vista, poligonos, sin_municipio)` y `generar(df, carpeta, poligonos, separados, sin_municipio)` (D1), con los nombres `<vista>.html` y `<vista>_sin_municipio.html` en `separados/`. Eliminar `visualizar`. Añadir a `tests/test_mapas.py`:
  - "Dos separados";
  - "Sin separados";
  - "Puntos sin MUNICIPIO";
  - separado `clusters_sin_municipio` con 3 puntos;
  - "Sin datos del estudiante": escribe todos los HTML con columnas personales sintéticas y comprueba que ninguno de sus valores aparece;
  - tamaño de `mapa.html` con polígonos por debajo de 3 MB.

  Verificar que pasan

## 6. Etapas y archivos

- [x] 6.1 Cambiar `etapas.generar_mapas` y `etapas.extraer_subconjunto` según D8:
  - comprobaciones previas;
  - carga de `Poligonos` solo si el área incluye el municipio con polígonos;
  - recorte de columnas;
  - aviso de los mapas anteriores;
  - salida con las rutas escritas.

  Cambiar `archivos.estructura_programa` para crear `mapas/area_metropolitana/`. Adaptar `tests/test_etapas.py`, `tests/test_subconjuntos.py` y `tests/test_archivos.py` a estos escenarios:
  - "Archivo de coordenadas anterior" y "Mapas anteriores presentes" (el archivo sigue existiendo);
  - "Opción sin separados";
  - "Vista coloreada pedida para otra área" (no se escribe `coordenadas_<nombre>.xlsx`);
  - "Todos en un área sin polígonos";
  - de `specs/archivos-de-salida`, "Archivos de coordenadas y mapas", "Mapas separados", "Archivos de un subconjunto" y "Primera ejecución en un directorio limpio";
  - de `specs/areas-geograficas`, "Mapas del subconjunto" y "Separados del subconjunto".

  Verificar que pasan y que `grep -rn "filtrados\|individual.html\|CENTRO_MAPA" georef tests` solo encuentra el aviso de D8 y sus tests

## 7. Línea de comandos, menú y README

- [x] 7.1 Añadir `--separado` y `--sin-municipio` a `mapas` y `subconjunto`, y `preguntar_separados()` a las opciones 3 y 4 del menú (D9). Adaptar `tests/test_cli.py` y `tests/test_flujo_principal.py` a estos escenarios de `specs/linea-de-comandos`:
  - "Mapas con separados";
  - "Vista desconocida" (código 2 y vistas listadas);
  - "Mejorar y mapas";
  - "Separados desde el menú";
  - "Sin separados desde el menú";
  - "Separado inválido en el menú";
  - "Extraer un subconjunto desde el menú";
  - "Opciones que no leen el archivo de entrada".

  Verificar que pasan
- [x] 7.2 Actualizar el README:
  - características y estructura de carpetas;
  - "Uso", con los ejemplos de `--separado` y `--sin-municipio`;
  - una sección nueva "Mapas", con capas, colores, número de los círculos, ventana, capas coloreadas y separados;
  - un aviso de privacidad antes de compartir un HTML;
  - "Migración", con los HTML anteriores que se pueden borrar.

  Actualizar la docstring de `georef/__init__.py`. Verificar que los comandos del README coinciden con `python -m georef mapas --help` y `python -m georef subconjunto --help`

## 8. Verificación final

- [x] 8.1 Verificar con los datos reales en una copia, sin tocar `mapas/` del repositorio. Copiar `coordenadas/coordenadas_area_metropolitana.xlsx` y `config/` a un directorio temporal fuera del repositorio y ejecutar allí `python -m georef mapas --separado todos` y `python -m georef subconjunto --area medellin`. Comprobar solo con cifras agregadas:
  - la suma de los números de los círculos de cada capa es igual a los registros de ese nivel;
  - el número de círculos es igual al de puntos distintos;
  - `mapa.html` pesa menos de 3 MB;
  - 0 valores de `Direccion de residencia` y `Complemento` aparecen en los HTML.

  Borrar la copia al terminar
- [x] 8.2 Ejecutar `python -m pytest` completo, también sin red (`unshare -rn`), y `openspec validate mapas --type change --strict`. Regenerar `docs/` con `pdoc georef -o docs`. Revisar `git status` y verificar que nada de `original/`, `estandarizado/`, `coordenadas/`, `mapas/` ni `.env` queda preparado para commit

## 9. Ver los mapas con el fondo de OpenStreetMap

- [x] 9.1 Crear `georef/visor.py` y `etapas.ver_mapas` (D11), y el subcomando `ver-mapas --area`. Añadir `tests/test_visor.py` con los escenarios de "Ver los mapas con el fondo de OpenStreetMap" de `specs/mapas`:
  - "Ver el mapa del área metropolitana", con un servidor y un navegador falsos y una prueba real por loopback que se salta si no hay red local;
  - "Ver el mapa de un subconjunto";
  - "Mapa sin generar";
  - "Área desconocida";
  - "Terminar el servidor".

  Actualizar en `test_cli.py` y `test_ejecucion.py` la lista de subcomandos del escenario "Ayuda". Verificar que pasan
- [x] 9.2 Documentar en el README:
  - por qué el fondo no se ve con doble clic;
  - `ver-mapas`;
  - la alternativa `python -m http.server 8000 --bind 127.0.0.1 --directory mapas` para quien reciba un HTML.

  Actualizar la docstring de `georef/__init__.py`. Ejecutar de nuevo la suite completa, también sin red, `openspec validate mapas --type change --strict` y `pdoc georef -o docs`. Verificar que pasan

## Workflow follow-up

- Revisión visual a cargo del usuario: `python -m georef mapas` y `python -m georef ver-mapas`. Comprobar los colores, los números, las capas y el encuadre, y borrar los HTML anteriores que avise el programa.
- Commit en la rama `mapas`, fusión en `main` y `/opsx:archive mapas`.
