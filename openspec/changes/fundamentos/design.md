# Design

## Context

- Todo el sistema es un único módulo, `main.py`, sin tests. Se ejecuta en el entorno conda `medellin-analysis312` (Python 3.12.13, pandas 3.0.6, folium 0.20.0, opencage 3.3.0, openpyxl 3.1.5; tkinter 8.6 disponible). pytest no está instalado.
- `main()` siempre ejecuta `estructura_programa()`, `verificar_y_copiar_archivo_original()` (abre un diálogo de tkinter si `original/` está vacía) y `leer_archivo_original()` antes del menú. Cualquier test de extremo a extremo necesita un Excel en `original/`.
- La geocodificación instancia `OpenCageGeocode` dentro de `reverse_geocoding` y `rellenar_por_barrio`, y llama a `time.sleep(1)` en cada registro.
- La llave se obtiene en tres puntos: `obtener_llave()` (interactiva, opciones 2 y 3), lectura directa de `llave/llave.txt` en el modo `python main.py c`, y `estructura_programa()`, que crea `llave/`.
- La ruta `principales_área_metropolitana.xlsx` aparece literalmente en tres lugares de `main()`.
- `llave/` y `original/` están sin seguimiento en git, pero no hay `.gitignore`.

## Goals / Non-Goals

**Goals:**
- Poder demostrar con tests automáticos que el renombrado no cambia el comportamiento.
- Que el renombrado sea mecánico: el mapeo de nombres queda fijado aquí.
- Que los tests corran en segundos, sin red y sin datos reales de estudiantes.

**Non-Goals:**
- Corregir defectos conocidos (reemplazo por subcadena en `reemplazar_equivalentes`, `index_col` en el modo `c`, fallback sin `try` en la geocodificación). Los tests los documentan tal como son.
- Reorganizar el código en módulos o introducir configuración externa.
- Cambiar textos de consola en español, nombres de columnas o literales de datos (`'NÚMERO'`, barrios con tildes, la clase `Ñ` de la regex): son datos, no identificadores.

## Decisions

### D1. Tests de caracterización antes del renombrado y con los nombres actuales

Primero se escriben los tests contra el código actual, con sus nombres no ASCII, y se comprueba que pasan. Después se renombra a la vez en código y tests. Si siguen en verde, el renombrado no cambió nada.
- *Alternativa*: escribir los tests ya con los nombres nuevos, después del renombrado. Se descarta porque no probaría la equivalencia: no habría una versión "antes" con la que comparar.
- Los valores esperados se obtienen **ejecutando el código actual** sobre entradas sintéticas, no a partir de lo que "debería" salir. Los casos que reflejan un defecto conocido llevan `defecto_conocido` en el nombre del test, por ejemplo `test_reemplazo_por_subcadena_defecto_conocido_urbano`, para que el cambio `ubicacion-por-niveles` sepa cuáles debe invertir.

### D2. Datos de prueba sintéticos construidos en código

Los DataFrames de prueba se construyen en `tests/conftest.py` con direcciones inventadas que imitan las formas reales: `CL 10 20 30 BARRIO -*- URBANO`, `CR 43 A 1 50 APTO 301 ...`, `VEREDA ...`, `CALLE`/`CARRERA` sin abreviar, `NORTE`/`SUR`. Cuando un flujo necesita un Excel, se escribe en `tmp_path`.
- *Alternativa*: un extracto anonimizado del archivo real. Se descarta porque obliga a anonimizar con cuidado y sigue siendo un derivado de datos personales.
- No se versiona ningún `.xlsx` de prueba.

### D3. Aislamiento de efectos con `monkeypatch`

- `main.OpenCageGeocode` se sustituye por un falso que devuelve respuestas guionizadas (resultado, lista vacía o excepción) y registra las consultas recibidas. `main.time.sleep` se anula.
- Los flujos del menú se prueban con `monkeypatch.chdir(tmp_path)`, `monkeypatch.setattr("builtins.input", ...)`, `monkeypatch.setenv`/`delenv("OPENCAGE_API_KEY")` y `monkeypatch.setattr(sys, "argv", ...)`. Siempre se coloca un Excel sintético en `original/`, de modo que el diálogo de tkinter nunca se abre.
- Los mapas se prueban sobre `tmp_path`: se comprueba que existen los 4 HTML y que el número de marcadores (apariciones de `L.marker(`) del mapa filtrado excluye el centroide fijo.
- *Alternativa*: inyección de dependencias (pasar el geocodificador como parámetro). Exigiría cambiar firmas, lo que es una modificación de diseño propia de `modularizacion-config`. `monkeypatch` no toca el código bajo prueba.

### D4. Mapeo de renombrado

Regla: español sin tildes. Cuando quitar la `ñ` da una palabra extraña, se usa un sinónimo.

| Actual | Nuevo |
|---|---|
| `tipo_vía_urbana` | `tipo_via_urbana` |
| `área_metropolitana` | `area_metropolitana` |
| `filtrar_área_metropolitana` | `filtrar_area_metropolitana` |
| `filtrar_vías_principales` | `filtrar_vias_principales` |
| `identificar_vías_principales` | `identificar_vias_principales` |
| `estandarización` | `estandarizar` |
| `añadir_columna_complemento` | `agregar_columna_complemento` |
| `vía` (variable de bucle) | `via` |
| `am_vías_principales` | `am_vias_principales` |
| `am_vías_especiales` | `am_vias_especiales` |
| `am_vías_principales_coordenadas` | `am_vias_principales_coordenadas` |
| `reverse_geocoding` | `geocodificar_direcciones` (hace geocodificación directa, no inversa) |
| `map`, `map2` en `visualizar` | `mapa_marcadores`, `mapa_clusters` (no sombrear el builtin `map`) |
| `num_aldready`, `letter_aldready`, `via_aldready` | `num_already`, `letter_already`, `via_already` |

Se actualizan también los docstrings y comentarios que nombran estos identificadores.

### D5. Guardia ASCII como test, sin herramientas nuevas

`tests/test_identificadores_ascii.py` recorre con `ast` todos los `.py` del repositorio, excluyendo los directorios ignorados. Verifica nombres de funciones, clases, argumentos, variables (`Name`), atributos, alias de importación y nombres de archivo de módulo. Python acepta identificadores Unicode (PEP 3131), así que sin esta guardia nada impide reintroducirlos.
- *Alternativa*: la regla `PLC2401` de ruff. Se descarta por ahora para no introducir un linter solo por esta regla; se puede adoptar más adelante.

### D6. Nombres de archivo en constantes de módulo

Los cuatro nombres de salida de `estandarizado/` se definen como constantes de módulo en `main.py`, junto a las globales existentes, y se usan en todos los puntos de lectura y escritura. Así se elimina la triple repetición de `principales_...`. El cambio `modularizacion-config` las moverá a la configuración. Antes de leer `principales_area_metropolitana.xlsx`, se comprueba si existe y, si no, se termina con un mensaje que pide ejecutar la estandarización (ver `specs/archivos-de-salida`).

### D7. Credencial: entorno del proceso o archivo `.env`, sin preguntas

`obtener_llave()` se reescribe: toma `OPENCAGE_API_KEY` primero de `os.environ` y, si ahí falta o está vacía, de `dotenv_values(".env")` (python-dotenv). En ambos casos aplica `strip()`. Si no queda valor, termina con `sys.exit(<mensaje>)` (código 1). El mensaje nombra la variable y explica las dos vías: crear `.env` a partir de `.env.example` o definir la variable en el entorno (`export`, `conda env config vars set ... -n medellin-analysis312`). El modo `c` y las opciones 2 y 3 la llaman **antes** de leer o escribir archivos de coordenadas. Se eliminan las preguntas por consola, la escritura de `llave.txt` y la entrada `llave/` de `estructura_programa()`.

- **`dotenv_values` y no `load_dotenv`**: `dotenv_values` devuelve un diccionario sin tocar `os.environ`. Así la llave no se hereda a subprocesos y los tests no dejan variables residuales entre casos.
- **`.env` relativo al directorio de trabajo**, como todas las rutas del programa (`original/`, `coordenadas/`…). Los tests se ejecutan con `chdir` a `tmp_path`, de modo que nunca leen el `.env` real del repositorio.
- **El entorno tiene prioridad sobre `.env`**, la convención habitual: permite sustituir la llave puntualmente (por ejemplo, en PyCharm o en CI) sin editar el archivo.
- **Seguridad**: python-dotenv no cifra nada; `.env` es texto plano. La protección viene de que `.env` está en `.gitignore`, de que el programa nunca escribe ni imprime la llave y de que el README recomienda `chmod 600 .env`. Se versiona `.env.example`, sin llave, como plantilla.
- *Alternativa A*: solo variable de entorno (la versión inicial de este diseño). Funciona, pero obliga a configurar conda o PyCharm por separado; `.env` es un único sitio que sirve en terminal y en el IDE.
- *Alternativa B*: mantener `llave.txt` como respaldo. Se descarta: `.env` cubre el mismo caso con una convención estándar, ignorada en git, y sin flujo interactivo.
- *Alternativa C*: `keyring` del sistema operativo (cifrado). Es más seguro en reposo, pero depende del servicio de llavero de escritorio; se descarta para esta etapa.
- *Alternativa D*: pedir la llave en un diálogo tkinter si falta. Se descarta a favor de `.env` por decisión del usuario: escribirla en cada ejecución no aporta frente a un archivo local ignorado.

### D8. Entorno declarado con dependencias directas fijadas

`environment.yml` usa el canal `conda-forge` y el nombre `medellin-analysis312`, para que `conda env update -f environment.yml` actualice el entorno existente. Fija las versiones de las dependencias directas (`python=3.12`, `pandas=3.0.6`, `folium=0.20.0`, `openpyxl=3.1.5`, `python-dotenv=1.2.4`) y `pytest>=8`. `opencage==3.3.0` va en la sección `pip:` porque no se publica en conda-forge; así está instalado hoy en el entorno.
- *Alternativa*: `conda env export` completo. Es más reproducible, pero depende de la plataforma y es ruidoso; se descarta en esta etapa.
- El README incluye además la línea `pip install` equivalente con las mismas versiones.

### D9. Configuración de pytest en `pytest.ini`

`pytest.ini` declara `testpaths = tests` y `pythonpath = .` para poder hacer `import main`. Se evita crear ahora un `pyproject.toml`, que implicaría decisiones de empaquetado propias de `modularizacion-config`.

### D10. Contenido del `.gitignore`

Ignora: `original/`, `estandarizado/`, `coordenadas/`, `mapas/`, `llave/`, `.env`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ipynb_checkpoints/` e `.idea/`. **No** ignora `.env.example` (plantilla sin llave), `data/` (el GeoJSON está versionado), `openspec/`, `.claude/` (contiene los comandos de OpenSpec del proyecto) ni `docs/`.

## Risks / Trade-offs

- [Los tests congelan defectos] → Es intencionado. Llevan `defecto_conocido` en el nombre y un comentario con el comportamiento correcto esperado, para que el cambio que los corrija actualice esos tests de forma explícita.
- [Un renombrado incompleto rompe una rama poco usada, por ejemplo el modo `c`, con `NameError` en ejecución] → Hay al menos un test por cada rama del menú y por el modo `c`, y el test ASCII detecta los nombres no ASCII que queden.
- [PyCharm no hereda `OPENCAGE_API_KEY` definida con `conda env config vars`, según cómo active el intérprete] → `.env` resuelve este caso si el directorio de trabajo de la configuración de ejecución es la raíz del proyecto (el valor por defecto en PyCharm).
- [`.env` es texto plano en disco] → Está en `.gitignore`, el programa no lo escribe ni lo imprime y el README recomienda permisos `600`. Si se sospecha que se filtró, se rota la llave en el panel de OpenCage.
- [Ejecutar `main.py` desde otro directorio no encuentra `.env`] → Es coherente con el resto del programa, que ya depende del directorio de trabajo para `original/` y las salidas. El mensaje de error lo hace visible.
- [Los archivos con tilde de `estandarizado/` dejan de leerse] → El mensaje de error lo explica. La migración consiste en renombrarlos o volver a ejecutar la opción 1, que no consume API. `coordenadas/coordenadas.xlsx` no cambia de nombre, así que **no hace falta volver a geocodificar**.
- [La llave sigue en disco, en `llave/llave.txt`, hasta que el usuario la borre] → Una tarea de migración pide borrarla. Antes se verifica con `git log --all -- llave` que nunca se versionó; si alguna vez se versionó, hay que rotarla en el panel de OpenCage.
- [Contar `L.marker(` en el HTML acopla el test al formato de folium] → Es aceptable con la versión fijada (0.20.0). Si folium cambia, el test fallará de forma visible y se ajusta.

## Migration Plan

1. Actualizar el entorno: `conda env update -f environment.yml`.
2. Definir la llave: `cp .env.example .env`, escribir la llave en `.env` y `chmod 600 .env`. Alternativa: definir `OPENCAGE_API_KEY` en el entorno (conda o PyCharm).
3. Renombrar los Excel existentes de `estandarizado/` a sus nombres ASCII o volver a ejecutar la opción 1.
4. Verificar que `llave/` nunca se versionó y borrar el directorio.

**Rollback**: revertir el commit del cambio. Mientras no se borre `llave/llave.txt`, la versión anterior sigue funcionando sin pasos adicionales.
