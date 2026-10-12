# Proposal

## Why

La estandarización actual daña las direcciones. Aplica las equivalencias por subcadena, también dentro de otras palabras: `URBANO` pasa a `URBA#`, `BUENOS AIRES` a `BUE#S AIRES` y `NORTE` a `#RTE`, que además corta la dirección. Por otro lado, deja el barrio y la zona mezclados en `Complemento` (`APARTAMENTO 301 BUE#S AIRES -*- URBA#`).

La cascada de `ubicacion-por-niveles` necesita el barrio, la comuna y la zona de cada estudiante de Medellín como datos separados y fiables. `exploracion-geojson` ya dejó preparados el GeoJSON oficial, la tabla de alias y la regla de los nombres repetidos. Este cambio los usa para corregir la estandarización, sin llamar a la API. Así las salidas nuevas se pueden revisar antes de gastar cuota.

## What Changes

- **BREAKING (cambia la salida a propósito):** la estandarización divide el texto de cada dirección en cinco columnas:
  - `Direccion de residencia`: vía y numeración, con el formato de siempre (`CL 10 #20-30`);
  - `Complemento`: datos de vivienda y lugares con nombre, con sus palabras originales;
  - `Barrio` y `Codigo barrio`: nombre oficial y código del polígono del GeoJSON, solo en Medellín;
  - `Comuna`;
  - `Zona`: `URBANO` o `RURAL`, tomada de lo que sigue a `-*-`.
- **Equivalencias solo a palabras completas y solo en la parte de la vía y la numeración.** `URBANO`, `BUENOS AIRES`, `LOS PINOS` y los nombres oficiales como `ASOMADERA NO 1` o `CALLE NUEVA` quedan intactos, y `CR 50 NORTE 30 20` pasa a ser `CR 50N #30-20`.
- **Reconocimiento del barrio en Medellín.** Se busca por el sufijo más largo que coincide con un nombre oficial, un alias o un nombre de comuna. Los nombres repetidos se resuelven con la regla de zona de `referencia-barrios`.
  - **Si solo se nombra una comuna** (por ejemplo `SAN ANTONIO DE PRADO` o la variante `POBLADO`), se rellena `Comuna` y `Barrio` queda vacío.
  - **Si no se reconoce nada**, todo el texto va a `Complemento` (regla sin pérdida).
- **Nueva tabla `data/alias_comunas.csv`** con las variantes de comuna decididas en la revisión de alias: `POBLADO` → El Poblado; `RODEO`, `RODEO ALTO` y `RODEO SUR` → Belén.
- **Nueva sección `[referencia]` en la configuración** con las rutas del GeoJSON y de las dos tablas de alias, y el municipio al que corresponden los polígonos (`MEDELLIN - ANTIOQUIA`).
- **Registros de fuera del área metropolitana:** se normalizan igual (dirección, complemento y zona, sin barrio) y se siguen exportando solo a `fuera_area_metropolitana.xlsx`.
- **La mejora de coordenadas sigue funcionando.** Busca el barrio en `Complemento` y en `Barrio`, porque el barrio ya no está dentro del complemento. Se elimina en `ubicacion-por-niveles`.
- **Los tests de caracterización con `defecto_conocido` se actualizan explícitamente** a los valores corregidos.
- **Revisión con los datos reales.** Se compara la salida nueva con la anterior y se genera un informe local, no versionado, con cada diferencia para revisarla a mano. Una medición previa sobre el archivo real dio 32 de 935 direcciones distintas: 25 por `NORTE`, 1 por `ORIENTE` y 6 casos a revisar.

## Capabilities

### New Capabilities

- `normalizacion-direcciones`: cómo se divide y normaliza el texto de una dirección en dirección, complemento, barrio, código de barrio, comuna y zona. Cubre la aplicación de equivalencias, el reconocimiento del barrio o la comuna, la regla sin pérdida y la clasificación en vías principales y especiales.

### Modified Capabilities

- `configuracion`:
  - se sustituye el requisito "La configuración incluida reproduce el comportamiento anterior" (la estandarización cambia a propósito) por uno sobre el vocabulario incluido;
  - el archivo gana la sección `[referencia]`, con su validación.
- `areas-geograficas`: los registros de fuera reciben la misma normalización que los del área metropolitana, sin barrio, en lugar del reemplazo por subcadena.
- `referencia-barrios`: nueva tabla de variantes de comuna (`data/alias_comunas.csv`) con su formato e invariantes.

## Impact

- **Código.**
  - Nuevo módulo `georef/referencia.py`: índice de barrios y comunas leído del GeoJSON con `json` (sin geopandas todavía), las tablas de alias y la función `normalizar`, que el test de alias pasa a importar.
  - En `georef/direcciones.py`:
    - `reemplazar_equivalentes` aplica palabras completas;
    - se añade la división en cinco columnas;
    - `dividir_complemento` y `format_dir` se conservan.
  - `georef/etapas.py` (estandarización) y `georef/geocodificacion.py` (búsqueda de la mejora) se adaptan.
- **Datos y configuración:**
  - nuevo `data/alias_comunas.csv`;
  - `config/georef.toml` gana `[referencia]` y cambia el comentario de las equivalencias;
  - se actualizan `data/README.md` y `README.md`.
- **Salidas.**
  - Cambian las columnas y algunos valores de los cuatro archivos de `estandarizado/`.
  - El archivo de coordenadas existente no se toca. Conviene no regenerarlo hasta `ubicacion-por-niveles`, que define sus columnas nuevas, aunque la conversión y los subconjuntos siguen funcionando con él.
- **Sin cambios de dependencias** ni llamadas a la API.
- **Fuera de alcance.** Todo esto corresponde a `ubicacion-por-niveles` y `mapas`:
  - geometrías y puntos (punto cero del barrio o de la comuna);
  - cascada de niveles y validación con tolerancia;
  - constructor de consultas;
  - caché y registro;
  - eliminar `n=300` o la mejora;
  - cambiar los mapas.
