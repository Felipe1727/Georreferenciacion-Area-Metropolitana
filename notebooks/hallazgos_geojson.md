# Hallazgos: GeoJSON de barrios y barrios declarados

Resumen de `notebooks/exploracion_geojson.ipynb`, ejecutado el 2026-10-11. Solo contiene cifras agregadas y nombres de
barrio. Los datos de entrada son:
- `data/limite_barrio_vereda_cata.geojson`, sincronizado el 2025-05-02;
- el archivo de `original/` del periodo 202510, con 1284 registros;
- `coordenadas/coordenadas.xlsx`, que solo cubre una parte de esos registros (ver la sección 8).

Si cambian los datos de entrada, las cifras absolutas cambian; lo que orienta las decisiones son las proporciones.

## 1-4. El GeoJSON

- **Contenido.** 349 polígonos (338 `Polygon` y 11 `MultiPolygon`), todos válidos, en EPSG:9377 (metros). Cubren 16
  comunas y 5 corregimientos, solo de Medellín.
- **Códigos.** `codigo` es único y tiene 4 caracteres; 144 empiezan por `0`, así que hay que leerlo como texto.
- **Normalización.** 341 nombres oficiales distintos quedan en 340 al normalizar: `El Salado` y `El Salado ` (con
  espacio final) son el mismo nombre.
- **Nombres repetidos.** 8 en el campo original y 9 en 18 polígonos tras normalizar. En 8 de ellos hay un polígono
  urbano y otro rural, así que la zona `URBANO`/`RURAL` de la dirección los distingue. La excepción es *Suburbano El
  Llano*, con dos polígonos rurales.
- **Polígonos sin `indicador_ur`.** 4, todos "Área de Expansión". Ninguno tiene nombre repetido.
- **Punto cero del barrio.** 8 centroides caen fuera de su polígono y ningún `representative_point()` lo hace. La
  distancia entre ambos tiene una mediana de 58 m y un máximo de 1295 m.
- **Comunas sin barrio homónimo.** Doce de Octubre, Manrique, Palmitas, San Antonio de Prado, San Cristóbal, San Javier y
  Santa Elena.

## 5-6. Barrio declarado por los estudiantes

- **Registros de Medellín.** 706 de 1284 (55,0 %). 704 tienen texto entre la vía y `-*-`, y 536 traen zona (516
  `URBANO` y 20 `RURAL`).
- **Comparación con la exploración.** Contando solo los registros con `-*-`, como entonces, 368 de 536 tienen un nombre
  oficial como sufijo (68,7 %). La exploración midió 366 de 529 (69,2 %), así que el resultado es consistente.
- **Estandarización.** La estandarización actual sigue corrompiendo nombres: 16 registros contienen `BUE#S`. Por eso el
  análisis parte del texto original.

Sobre los 704 registros de Medellín con texto:

| Medida | Sin alias | Con alias |
|---|---|---|
| Coincidencia exacta | 62 (8,8 %) | 69 (9,8 %) |
| Barrio oficial como sufijo | 461 (65,5 %) | 551 (78,3 %) |
| **Barrio resuelto a un polígono** | 458 (65,1 %) | **548 (77,8 %)** |
| Sin resolver por nombre repetido | 3 (0,4 %) | 3 (0,4 %) |
| **Solo nombran una comuna** | 27 (3,8 %) | **74 (10,5 %)** |
| **Sin barrio ni comuna** | 219 (31,1 %) | **82 (11,6 %)** |

- **Ganancia de los alias.** "Con alias" usa los 27 alias de `data/alias_barrios.csv` y las variantes de comuna
  decididas en la misma revisión. Con ambos, el 88,4 % de los registros con texto queda ubicado en un barrio o en una
  comuna.
- **Registros que solo nombran una comuna.** El Poblado 32, Belén 15, San Javier 9, Manrique 5, Doce de Octubre 4, San
  Cristóbal 3, San Antonio de Prado 3 y Santa Elena 3.
  - En El Poblado son los textos que acaban en `POBLADO` sin artículo. `EL POBLADO`, con artículo, se asigna al barrio.
  - En Belén son los sectores `RODEO`, `RODEO ALTO` y `RODEO SUR`, que no tienen polígono propio.
- **Nombres repetidos sin resolver.** Los 3 casos son *Las Palmas* (2) y *Pajarito* (1) sin zona en la dirección. Los
  repetidos con zona se resolvieron todos.
- **Sufijos que conviene revisar.** 172 sufijos (24,4 %) tienen delante una palabra desconocida, que no es de vivienda
  ni de numeración. La mayoría son correctos:
  - el nombre de la comuna escrito antes del barrio (*Belén* + *Fátima*, *Robledo* + *Bello Horizonte*);
  - el nombre de un edificio o una urbanización.

  Un analizador de producción debería tratar el nombre de comuna previo como confirmación del barrio.

## 7. Lo que queda sin resolver

- **Volumen.** Quedan 79 registros sin barrio ni comuna. 4 solo tienen complemento de vivienda; el resto suma 64 textos
  distintos.
- **Por qué no son alias:**
  - **Otros municipios** escritos en registros de Medellín: Envigado, La Estrella, Itagüí, Sabaneta, Caldas, Bello…
  - **Nombres de varios polígonos numerados:** *Santo Domingo Savio*, *Manrique Central*, *Las Lomas*, *Los Balsos*. La
    tabla asigna un solo código y no puede elegir entre el No. 1 y el No. 2.
  - **Sectores, conjuntos o lugares sin polígono propio,** y nombres demasiado generales (`CENTRO`, `MEDELLIN`).

## 8. Línea base: puntos actuales de la API

`coordenadas.xlsx` se generó cuando `original/` tenía 299 registros. Por eso solo cubre 218 de los 706 registros de
Medellín (30,9 %), y la línea base es **parcial**.

- **Puntos.** 124 de sus 261 puntos están en el centroide de Medellín, es decir, la API solo resolvió la ciudad.
- **Puntos evaluados.** 78: fuera del centroide y con barrio declarado resuelto.
- **En el barrio declarado:** 17 (21,8 %).
- **En la comuna del barrio declarado:** 32 (41,0 %).
- **Fuera de Medellín:** 2.
- **Distancia al polígono del barrio declarado:** mediana de 1549 m.

| Tolerancia | 0 m | 100 m | 250 m | 500 m | 1000 m | 2000 m |
|---|---|---|---|---|---|---|
| Puntos aceptados | 17 | 21 | 28 | 29 | 34 | 45 |
| Porcentaje | 21,8 % | 26,9 % | 35,9 % | 37,2 % | 43,6 % | 57,7 % |

En la exploración, con todos los registros geocodificados, 20 de 162 puntos (12,3 %) caían en el barrio declarado y 59
(36,4 %) en su comuna. Las dos mediciones coinciden en lo esencial: la mayoría de los puntos de la API no cae en el
barrio que declara el estudiante.

## Recomendaciones para `ubicacion-por-niveles`

1. **Punto cero del barrio:** `representative_point()` en EPSG:9377, transformado a WGS84 al final.
2. **Extracción del barrio declarado:**
   - partir del texto original;
   - aplicar la normalización de `referencia-barrios`, el sufijo más largo y la tabla de alias;
   - resolver los nombres repetidos con la regla de zona;
   - buscar los nombres de comuna junto con los de barrio, para que `SAN ANTONIO DE PRADO` no se asigne al barrio *Prado*.
3. **Nivel COMUNA:** el 10,5 % de los registros con texto solo nombra una comuna. Conviene un nivel entre BARRIO y
   MUNICIPIO, con el punto representativo de la comuna. Ese polígono se obtiene uniendo sus barrios del mismo GeoJSON,
   sin otra fuente. Las variantes `POBLADO` (comuna El Poblado) y `RODEO`, `RODEO ALTO` y `RODEO SUR` (comuna Belén)
   necesitan una tabla propia, porque no son alias de un barrio.
4. **Tolerancia inicial: 250 m.**
   - **Por qué 250 m:** la curva sube rápido hasta esa distancia (puntos junto al borde) y se aplana hasta 500 m. Más
     allá empiezan a entrar barrios vecinos.
   - **Cómo usarla:** como parámetro configurable. Se recalibra cuando `coordenadas.xlsx` cubra todos los registros.
5. **Casos sin resolver:** cabe esperar en torno a un 12 % de registros de Medellín sin barrio ni comuna. Para ellos, el
   nivel siguiente es el punto del municipio. Cada periodo nuevo debería pasar por la sección 7 del notebook para
   ampliar la tabla de alias.
6. **Fuera de Medellín:** el 45 % de los registros es de otros municipios, que este GeoJSON no cubre. Necesitan otra
   fuente o un punto fijo por municipio.
