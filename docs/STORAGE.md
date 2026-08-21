# Estrategia de Almacenamiento de Imágenes

## Estado actual (MVP)

La API del MINEDUC **no expone URLs de imágenes** para los colegios. El modelo
de origen solo contiene `nombre` y `principal` (sin `url`, `path` ni `storage_key`).

Por ello:

- La tabla `imagenes` tiene una columna `url TEXT` (nullable) **reservada** para
  el futuro; hoy se carga como `NULL`.
- No se implementa ningún endpoint de imágenes en el MVP (F2).

## Decisión

| Opción | Estado |
|---|---|
| Filesystem local + `StaticFiles` de FastAPI | **Postergado** a post-MVP (cuando existan URLs reales) |
| S3 / R2 (object storage) | Futuro (requiere cuenta + credenciales) |

## Plan futuro

Cuando se disponga de URLs de imágenes (fuente externa o scraping autorizado):

1. Poblar `imagenes.url`.
2. Servir con `StaticFiles` (MVP) o delegar a S3/R2 (producción).
3. Documentar la base URL configurable en `config/settings.py`.
