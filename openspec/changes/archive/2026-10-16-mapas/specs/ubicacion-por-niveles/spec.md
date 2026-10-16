# Spec Delta

## REMOVED Requirements

### Requirement: Mapas filtrados por nivel
**Reason**: Los mapas filtrados (`filtrados/individual_filtrados.html` y `filtrados/clusters_filtrados.html`) desaparecen con el mapa con capas de la spec `mapas`. Ahí, excluir el nivel `MUNICIPIO` se hace apagando su capa o con la capa "Clusters sin MUNICIPIO", y en los separados con `--sin-municipio`. La comprobación de la columna `Nivel ubicacion` pasa al requisito "Archivo de coordenadas con niveles" de `mapas`.
**Migration**: Ejecuta `python -m georef mapas` y abre `mapas/<area>/mapa.html`. Para un archivo suelto sin MUNICIPIO, usa `python -m georef mapas --separado puntos --separado clusters --sin-municipio`. Los HTML anteriores no se borran solos; se pueden borrar a mano.
