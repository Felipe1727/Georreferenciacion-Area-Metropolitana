# Spec Delta

## MODIFIED Requirements

### Requirement: Extracción de un subconjunto sin consultar al proveedor
Al extraer un subconjunto, el sistema SHALL tomar de `coordenadas/coordenadas_area_metropolitana.xlsx` los registros cuyo municipio pertenece al subconjunto. Debe escribirlos en `coordenadas/coordenadas_<nombre>.xlsx`, conservando columnas e índice, y generar su mapa con capas en `mapas/<nombre>/`, más los separados que se pidan. No consulta al proveedor ni exige la llave.

#### Scenario: Subconjunto de Medellín
- **WHEN** existe `coordenadas_area_metropolitana.xlsx` con registros de Medellín y de Bello, y el usuario extrae el subconjunto `medellin`
- **THEN** `coordenadas/coordenadas_medellin.xlsx` contiene solo los registros de Medellín, con las mismas columnas y el mismo índice que en el archivo del área metropolitana

#### Scenario: Mapas del subconjunto
- **WHEN** el usuario extrae el subconjunto `medellin`
- **THEN** el sistema escribe `mapas/medellin/mapa.html` con los mismos criterios que el mapa del área metropolitana, y con las capas de comunas y barrios porque el subconjunto incluye Medellín

#### Scenario: Separados del subconjunto
- **WHEN** el usuario ejecuta `python -m georef subconjunto --area medellin --separado puntos`
- **THEN** el sistema escribe además `mapas/medellin/separados/puntos.html`

#### Scenario: Sin llamadas al proveedor
- **WHEN** `OPENCAGE_API_KEY` no está definida y el usuario extrae un subconjunto
- **THEN** la extracción termina con normalidad y no se hace ninguna consulta al proveedor
