# Tasks

## 1. Línea base

- [x] 1.1 Con el código actual, ejecutar `python -m georef --config <ruta absoluta de config/georef.toml> estandarizar` sobre una copia de `original/` en un directorio temporal fuera del repositorio y conservar los cuatro archivos como línea base (D8). Verificar que existen los cuatro archivos y que `python -m pytest` pasa completo antes de empezar

## 2. Datos de referencia

- [x] 2.1 Crear `data/alias_comunas.csv` con `POBLADO` → `EL POBLADO` y `RODEO`, `RODEO ALTO` y `RODEO SUR` → `BELEN`, cada uno con su `nota` (D4). Crear `tests/test_alias_comunas.py` con los escenarios "Tabla válida", "Variante que repite un nombre de barrio" y "Comuna inexistente" de `specs/referencia-barrios`, estos dos últimos sobre tablas sintéticas en `tmp_path`. Añadir la sección de la tabla a `data/README.md`. Verificar que `python -m pytest tests/test_alias_comunas.py` pasa
- [x] 2.2 Crear `georef/referencia.py` con `normalizar`, `ErrorReferencia` y la clase `IndiceLugares` (D2): lectura de las propiedades del GeoJSON con `json`, de las dos tablas de alias, `resolver(nombre, zona)` y `reconocer(palabras, zona)`. Hacer que `tests/test_alias_barrios.py` importe `normalizar` en lugar de definir la suya. Escribir `tests/test_referencia.py` con:
  - los cinco escenarios de "Resolución de nombres de barrio repetidos" de `referencia-barrios`;
  - el sufijo más largo (`SAN ANTONIO DE PRADO` frente a `PRADO`);
  - alias, comuna sin barrio, variante de comuna, `EL POBLADO` como barrio y números finales;
  - un archivo inexistente que lanza `ErrorReferencia` con su ruta.

  Verificar que pasa

## 3. Configuración

- [x] 3.1 Añadir la sección `[referencia]` a `config/georef.toml` (D5) y a `georef/config.py`: dataclass, claves obligatorias y municipio con polígonos dentro del área metropolitana. Cambiar el comentario de las equivalencias: ahora se aplican a palabras completas y solo a la vía y la numeración, y el orden no importa. Ampliar `tests/test_configuracion.py` con los escenarios "Referencias incluidas" y "Municipio con polígonos fuera del área", y mantener el test de regresión del vocabulario. Verificar que pasa

## 4. Normalización

- [x] 4.1 En `georef/direcciones.py`:
  - hacer que `reemplazar_equivalentes` aplique las equivalencias palabra a palabra;
  - añadir la normalización de una dirección según D1 (zona, lugar, equivalencias, `dividir_complemento`, `format_dir` y complemento con palabras originales);
  - añadir `normalizar_direcciones(df, configuracion, indice)`, que añade las seis columnas en su posición (D3), con `Codigo barrio` como texto, y reconoce lugares solo en el municipio con polígonos (D6).

  Escribir `tests/test_normalizacion.py` con todos los escenarios de `specs/normalizacion-direcciones` sobre direcciones inventadas. Verificar que pasa
- [x] 4.2 Convertir los tests `*_defecto_conocido` de `tests/test_estandarizacion.py` en tests del comportamiento corregido (D9) y actualizar `test_estandarizacion_completa` con las columnas y valores nuevos. Verificar que pasan y que el diff de esos tests solo toca los casos previstos

## 5. Etapas y compatibilidad

- [x] 5.1 Adaptar `etapas.estandarizar`:
  - normaliza todo el archivo de entrada (D6);
  - separa por área;
  - clasifica en vías principales y especiales con la regla de siempre;
  - escribe los cuatro archivos;
  - si falta un archivo de referencia, termina con un mensaje sin escribir salidas.

  Actualizar `tests/test_etapas.py` y `tests/test_flujo_principal.py` (columnas nuevas y mismo reparto de filas) y añadir:
  - el escenario "Archivo de referencia inexistente" de `specs/configuracion`;
  - "Normalización de un registro de fuera" de `specs/areas-geograficas`;
  - un test que lee `Codigo barrio` con `dtype=str` y conserva `0902`.

  Verificar que pasan
- [x] 5.2 Hacer que `rellenar_por_barrio` busque el barrio en `Complemento` y, si existe, en `Barrio` (D7). Añadir a `tests/test_mejora_barrio.py` un caso con el barrio solo en la columna `Barrio`. Verificar que los tests anteriores de la mejora siguen pasando sin cambios

## 6. Verificación con los datos reales

- [x] 6.1 Ejecutar la estandarización nueva sobre la misma copia de la tarea 1.1, en otro directorio temporal, y compararla con la línea base (D8):
  - filas por archivo;
  - direcciones distintas por causa;
  - complementos sin `#`, `URBA#` ni restos de equivalencias;
  - cobertura de `Barrio`, `Codigo barrio` y `Comuna` en Medellín frente a `notebooks/hallazgos_geojson.md`.

  Revisar cada diferencia inesperada con los dígitos enmascarados y corregir las que vengan del código nuevo. Escribir `estandarizado/revision_normalizacion.xlsx` (carpeta excluida de git) con las filas que cambian, antigua y nueva lado a lado. Verificar que todas las diferencias quedan explicadas y que solo se informan cifras agregadas

## 7. Documentación

- [x] 7.1 Actualizar `README.md`:
  - columnas de `estandarizado/`;
  - equivalencias aplicadas solo a palabras completas de la vía;
  - `Codigo barrio` como texto, con el ejemplo `dtype`;
  - `data/alias_comunas.csv` en la estructura.

  Regenerar `docs/` con `pdoc georef -o docs`. Verificar que existe `docs/georef/referencia.html` y que los comandos documentados se ejecutan tal como están escritos

## 8. Verificación final

- [x] 8.1 Ejecutar `python -m pytest` completo y `openspec validate normalizacion-direcciones --strict`, y revisar `git status` y `git diff --stat`. Verificar que solo cambian los archivos previstos y que nada de `original/`, `estandarizado/`, `coordenadas/`, `mapas/` ni `.env` queda preparado para commit

## Workflow follow-up

- El usuario vuelve a estandarizar sus datos (`python -m georef estandarizar`) y revisa `estandarizado/revision_normalizacion.xlsx`.
- Commit en la rama del cambio, fusión en `main` y `/opsx:archive normalizacion-direcciones`, antes de proponer `ubicacion-por-niveles`.
