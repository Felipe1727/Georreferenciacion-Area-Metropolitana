# Datos de referencia

Datos geográficos versionados que usa el proyecto. No contienen datos personales.

## `limite_barrio_vereda_cata.geojson`

Límite catastral de los barrios (zona urbana) y las veredas (corregimientos) de Medellín.

| | |
|---|---|
| Fuente | GeoMedellín, portal de datos abiertos de la Alcaldía de Medellín |
| URL del conjunto | https://www.medellin.gov.co/geomedellin/datosAbiertos/1043 |
| Licencia | La de GeoMedellín |
| Fecha de descarga | 2026-10-11 |
| Fecha de sincronización | 2025-05-02 (campo `fecha_sincronizacion`, igual en todos los polígonos) |
| Última actualización indicada en la página | 2025-12-16T08:50:55 (consultada el 2026-10-11) |
| Sistema de coordenadas | EPSG:9377, MAGNA-SIRGAS Origen Nacional, en metros |
| Contenido | 349 polígonos (338 `Polygon` y 11 `MultiPolygon`, todos válidos) de 16 comunas y 5 corregimientos |

Solo cubre Medellín: los demás municipios del área metropolitana no tienen polígonos en este archivo.

Las distancias y los puntos representativos se calculan en EPSG:9377. Para obtener latitud y longitud se transforma a
EPSG:4326 (WGS84) al final. La reproyección necesita la base de datos de PROJ, que se configura al activar el entorno
con `conda activate medellin-analysis312`.

### Campos que usa el proyecto

| Campo | Significado |
|---|---|
| `codigo` | Identificador del polígono: texto de 4 caracteres, único. Son los 2 caracteres de `comuna` seguidos de los 2 de `barrio` (`0806`). **Se lee siempre como texto** para no perder los ceros a la izquierda (144 códigos empiezan por `0`). Es la clave de `alias_barrios.csv`. |
| `nombre_barrio` | Nombre oficial del barrio o la vereda, con tildes y eñes. Hay que compararlo siempre normalizado: un nombre trae un espacio final (`El Salado `). |
| `nombre_comuna` | Nombre de la comuna o el corregimiento, en mayúsculas y sin tildes (`LA CANDELARIA`, `SAN ANTONIO DE PRADO`). |
| `comuna` | Código de 2 caracteres de la comuna (`01` a `16`) o el corregimiento (`50`, `60`, `70`, `80` y `90`). |
| `barrio` | Código de 2 caracteres del barrio o la vereda dentro de su comuna o corregimiento. |
| `indicador_ur` | `U` urbano (267 polígonos) o `R` rural (78). Está **vacío** en los 4 polígonos "Área de Expansión" (Pajarito, Belén Rincón, Altavista y El Noral). Se compara con la zona `URBANO`/`RURAL` de la dirección para resolver nombres repetidos. |
| `fecha_sincronizacion` | Milisegundos desde 1970-01-01 (UTC). |

El proyecto no usa los campos `OBJECTID`, `sector`, `Shape_Length` ni `Shape_Area`.

### Nombres repetidos

Tras normalizar, 9 nombres corresponden a 18 polígonos. En 8 de ellos un polígono es urbano y el otro rural, así que la
zona de la dirección los distingue. "Suburbano El Llano" tiene dos polígonos rurales y queda sin resolver por zona. La
regla completa está en la especificación `referencia-barrios` (`openspec/`).

## `alias_barrios.csv`

Variantes de nombres de barrio que escriben los estudiantes, asignadas a un polígono oficial. Está en UTF-8 y tiene
estas columnas:

| Columna | Contenido |
|---|---|
| `alias` | Variante ya normalizada: mayúsculas, sin tildes ni puntuación, con espacios simples (`CALAZANS`). No puede ser igual a un nombre oficial normalizado. |
| `codigo` | `codigo` del polígono, como texto de 4 caracteres. |
| `nombre_oficial` | `nombre_barrio` de ese polígono, copiado exactamente del GeoJSON. |
| `nota` | Motivo del alias: variante ortográfica, error de digitación, nombre sin el artículo, nombre popular… |

Cada fila se decide a mano a partir de los candidatos de la sección 7 de `notebooks/exploracion_geojson.ipynb`. No se
crean alias para los nombres que designan una comuna completa (por ejemplo, `POBLADO`) ni para los nombres que
corresponden a varios polígonos numerados (`SANTO DOMINGO SAVIO` → No. 1 y No. 2).

Después de editar la tabla hay que comprobar sus invariantes:

```bash
python -m pytest tests/test_alias_barrios.py
```

## `alias_comunas.csv`

Formas escritas que designan una comuna o corregimiento **completo** sin ser su nombre oficial. Se usan cuando un
estudiante solo nombra la comuna: la estandarización rellena la columna `Comuna` y deja `Barrio` vacío. Está en UTF-8 y
tiene estas columnas:

| Columna | Contenido |
|---|---|
| `alias` | Variante ya normalizada (`POBLADO`). No puede ser un nombre oficial de barrio o de comuna, ni un alias de `alias_barrios.csv`. |
| `comuna` | `nombre_comuna` del GeoJSON, tal como aparece en él (`EL POBLADO`, `BELEN`). |
| `nota` | Motivo de la variante. |

Las comunas o corregimientos que no tienen ningún barrio con su mismo nombre (por ejemplo, `SAN ANTONIO DE PRADO`) se
reconocen sin necesidad de esta tabla. El reconocimiento elige siempre el nombre más largo que coincide con el final del
texto, así que `EL POBLADO` sigue siendo el barrio El Poblado y `EL RODEO` el barrio de Guayabal.

Después de editar la tabla hay que comprobar sus invariantes:

```bash
python -m pytest tests/test_alias_comunas.py
```
