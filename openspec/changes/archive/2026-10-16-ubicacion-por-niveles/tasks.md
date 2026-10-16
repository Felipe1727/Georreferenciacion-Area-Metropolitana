# Tasks

## 1. Línea base y dependencias

- [x] 1.1 Verificar que `python -m pytest` pasa completo antes de empezar. Añadir `shapely=2.1.2` y `pyproj=3.7.2` a `environment.yml` y a la línea de `pip` del README (D2). Verificar con `env -u PROJ_DATA python -c "import shapely, pyproj"` que se importan sin activar el entorno, y con `conda list -n medellin-analysis312 "shapely|pyproj"` que las versiones instaladas coinciden con las fijadas

## 2. Configuración

- [x] 2.1 Añadir la sección `[ubicacion]` a `config/georef.toml`, con los valores de D4 y D8 y comentarios en español, y a `georef/config.py` (dataclass y validación de claves y valores). Ampliar `tests/test_configuracion.py` con los escenarios de "Parámetros de la ubicación" y "Valores válidos de la ubicación" de `specs/configuracion`. Verificar que pasan
- [x] 2.2 Añadir la validación de la sección opcional `[puntos_municipios]`: municipios del área, rangos de latitud y longitud, `fuente` y `fecha`. Añadir los escenarios "Municipio fuera del área", "Latitud fuera de rango" y "Sección ausente". Documentar las dos secciones en el apartado "Configuración" del README. Verificar que pasan

## 3. Geografía

- [x] 3.1 Crear `georef/geografia.py` con la clase `Poligonos` (D2): lectura con `json` y `shapely`, comunas y municipio unidos, punto representativo en WGS84, distancia en metros, barrio que contiene un punto y recuadro WGS84. Crear `tests/test_geografia.py`, sobre el GeoJSON real, con:
  - "Barrio de forma cóncava": un barrio cuyo centroide cae fuera;
  - puntos representativos dentro de su polígono para todos los barrios y comunas;
  - distancia 0 dentro y unos 120 m para un punto desplazado en EPSG:9377;
  - `codigo` como texto con su cero inicial;
  - recuadro en el orden `min_lng,min_lat,max_lng,max_lat`.

  Verificar que pasa

## 4. Consultas al proveedor

- [x] 4.1 En `georef/geocodificacion.py`, añadir las funciones que forman el texto de las consultas (D8): abreviado, expandido, lugar del complemento y municipio. Crear `tests/test_consultas.py` con los escenarios de "Texto de la consulta" de `specs/consultas-proveedor`. Verificar que pasan
- [x] 4.2 Añadir `SesionConsultas` (D5, D6, D7): pausa con `time.monotonic`, parámetros de la petición, caché CSV con `flush` por línea, registro CSV, traducción de excepciones de `opencage`, paradas (cuota, 3 errores seguidos y límite) y modo sin cliente. En `tests/conftest.py`, añadir `ClienteFalso` y el reloj falso (D13). Ampliar `tests/test_consultas.py` con los escenarios de:
  - "Parámetros de la petición";
  - "Pausa entre peticiones";
  - "Caché de consultas";
  - "Paradas sin pérdida";
  - "Llave rechazada";
  - "Registro de diagnóstico", comprobando que el registro no contiene ni la llave ni el texto de la consulta.

  Documentar en el README la caché, el registro y cuándo borrar la caché. Verificar que pasan y que ningún test usa la red

## 5. Cascada de ubicación

- [x] 5.1 Crear `georef/ubicacion.py` con la evaluación de D4 y la cascada de D3, incluidas las 7 columnas y su posición (D11). Crear `tests/test_ubicacion.py` con un resolvedor falso y estos escenarios de `specs/ubicacion-por-niveles`:
  - "Niveles de ubicación";
  - "Solo las vías principales de Medellín se consultan";
  - "Aceptación del punto de la API";
  - "Columnas del archivo de coordenadas";
  - "Valores de `Resultado consulta`".

  Los puntos a 120 m y a 2 km se construyen como indica D13. Verificar que pasan
- [x] 5.2 Añadir la consulta con el lugar del complemento (D8) a la cascada y los escenarios "Opción desactivada" y "Opción activada". Verificar que pasan y que con la opción desactivada el resolvedor falso no recibe segundas consultas

## 6. Etapa `ubicar`, línea de comandos y mapas

- [x] 6.1 Añadir `etapas.ubicar(configuracion, sin_consultas=False)` con las comprobaciones previas en el orden de D11, la lectura de principales y especiales, el renombrado a `_anterior`, la escritura y el resumen agregado. Añadir a `tests/test_etapas.py` los escenarios de:
  - "Lectura entre etapas con nombres ASCII";
  - "Aviso ante el archivo de coordenadas con el nombre anterior";
  - "Conservación del archivo de coordenadas de formato anterior";
  - "Puntos de los municipios";
  - "Resumen de la ubicación";
  - "Ubicación sin consultas";
  - "Registros especiales en la ubicación".

  Verificar que pasan
- [x] 6.2 Cambiar `georef/cli.py` según D12: subcomandos `ubicar --sin-consultas`, `consultar-municipios` y `comparar-consultas --muestra`, de momento conectados a funciones que fallan con "no implementado"; menú de 4 opciones; `c` → `ubicar`. Eliminar `etapas.geocodificar`, `etapas.mejorar`, `geocodificar_direcciones`, `rellenar_por_barrio`, `BARRIOS_MEDELLIN`, `CENTROIDE_MEDELLIN` y `tests/test_mejora_barrio.py`. Adaptar `test_cli.py`, `test_flujo_principal.py`, `test_credenciales.py` y `test_ejecucion.py` a los escenarios de `specs/linea-de-comandos` y `specs/credenciales-geocodificacion`. Actualizar los apartados "Uso" y "Llave de la API" del README. Verificar que la suite completa pasa
- [x] 6.3 Cambiar el filtrado de `georef/mapas.py` a `Nivel ubicacion` y comprobar la columna en `generar_mapas` y `extraer_subconjunto` (D12). Adaptar `tests/test_mapas.py` y `tests/test_subconjuntos.py` con los escenarios de "Mapas filtrados por nivel". Verificar que pasan y que `grep -rn "6.25184" georef tests` no devuelve nada

## 7. Diagnósticos

- [x] 7.1 Implementar `consultar-municipios` (D9). Añadir `tests/test_municipios.py` con:
  - "Petición de un municipio";
  - "Todos los puntos presentes";
  - "Municipio sin resultado";
  - "Primera consulta", comprobando que el resto del archivo no cambia;
  - "Sección ya existente con un municipio nuevo";
  - restauración del archivo si el resultado no fuera válido.

  Documentar el subcomando en el README. Verificar que pasan
- [x] 7.2 Implementar `comparar-consultas` (D10). Añadir `tests/test_comparar_consultas.py` con:
  - "Muestra de 50" (como máximo 2N peticiones);
  - "Muestra repetida" (cero peticiones);
  - "Informe del diagnóstico", comprobando que la salida no contiene ninguna dirección de la muestra;
  - "Muestra no válida".

  Documentar el subcomando en el README. Verificar que pasan

## 8. Verificación final

- [x] 8.1 Verificar con los datos reales sin gastar cuota (D14). Ejecutar `ubicar --sin-consultas` sobre una copia de `estandarizado/` en un directorio temporal fuera del repositorio, con puntos de municipio ficticios, y comprobar solo con cifras agregadas:
  - registros por nivel frente a lo esperado (546 BARRIO, 74 COMUNA, 343 MUNICIPIO);
  - que todo resultado es `PENDIENTE` o `SIN_CONSULTA`;
  - que ningún punto de BARRIO o COMUNA cae fuera de su polígono.

  Borrar la copia al terminar
- [x] 8.2 Ejecutar `python -m pytest` completo, también sin red (`unshare -rn`), y `openspec validate ubicacion-por-niveles --strict`. Regenerar `docs/` con `pdoc georef -o docs` y verificar que existen `docs/georef/geografia.html` y `docs/georef/ubicacion.html`. Revisar `git status` y verificar que nada de `original/`, `estandarizado/`, `coordenadas/`, `mapas/` ni `.env` queda preparado para commit
- [x] 8.3 Añadir la línea de avance de D11 a `ubicar` y `comparar-consultas`, con los tests "Avance de la ubicación", "Avance en una terminal" y "Avance del diagnóstico". Hacer que los tests no dependan de la sección `[puntos_municipios]` de `config/georef.toml`. Verificar que la suite completa pasa

## Workflow follow-up

- Primera ejecución real, a cargo del usuario (unas 730 peticiones):
  1. `python -m georef consultar-municipios`, y revisar los 10 puntos;
  2. `python -m georef comparar-consultas --muestra 50`, y elegir `formato_consulta` y `confianza_minima`;
  3. `python -m georef ubicar`;
  4. `python -m georef mapas`.
- Commit en la rama `ubicacion-por-niveles`, fusión en `main` y `/opsx:archive ubicacion-por-niveles`.
- Después, proponer el cambio `mapas`: colores por nivel, comunas y `fit_bounds`.
