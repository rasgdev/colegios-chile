# Propuestas de Mejora — Correcciones al Plan de Arquitectura v2

> Documento accionable derivado de `docs/ARCHITECTURE_REVIEW.md`.  
> Cada ítem incluye: problema, propuesta concreta, archivos afectados, estimación de esfuerzo y criterio de aceptación.

---

## 0. Nuevas Fases de Trabajo

El plan v2 original tenía 4 fases (~32h). Las correcciones obligan a insertar una **F0** y redistribuir esfuerzo. Total corregido: **~45-55h**.

| Fase | Nombre | Horas | Objetivo |
|------|--------|-------|----------|
| **F0** | Fundamentos de Datos | 3-4h | Dataset completo, diccionario de datos y estrategia de carga |
| **F1** | Infraestructura y Persistencia | 8-10h | PostgreSQL reproducible, migraciones, loader atómico |
| **F2** | Core API | 12-16h | REST funcional con contratos, búsqueda FTS y tests |
| **F3** | Frontend | 10-14h | Sitio navegable con SSR, islands y comparador |
| **F4** | Polish y Entrega | 8-10h | CI, documentación, performance y rate limiting |

---

## 1. Issues Críticos (HIGH) — Bloquean F1

### 1.1 Dataset incompleto / sin validación de frescura

| Campo | Valor |
|-------|-------|
| **Problema** | ETL actual procesó solo 11/346 comunas. El buscador público con 3.2% de cobertura genera desconfianza y excluye colegios reales. |
| **Propuesta** | 1. Reejecutar `make all`.<br>2. Si falla en comunas específicas, documentarlas en `docs/KNOWN_ISSUES.md`.<br>3. Agregar etapa de validación de completitud en el pipeline (conteo de RBDs por comuna vs. referencia).<br>4. Definir política de snapshots (mensual, versionado, fecha visible en frontend). |
| **Archivos** | `Makefile`, `scripts/run_etl.py`, `data/processed/*/report.json`, `docs/KNOWN_ISSUES.md` (nuevo) |
| **Estimación** | 1-2h |
| **Aceptación** | `report.json` contiene `comunas_en_dataset >= 300` y campos `fecha_ejecucion` / `version_dataset`. |

---

### 1.2 Ausencia de estrategia de carga atómica en PostgreSQL

| Campo | Valor |
|-------|-------|
| **Problema** | Cargas parciales corrompen la base. Reejecutar el loader duplica datos. Sin idempotencia ni atomicidad. |
| **Propuesta** | Implementar **staging + swap transaccional** (Opción A):<br>1. Tablas `*_staging` (ej. `establecimientos_staging`).<br>2. Cargar Parquet a staging con SQLAlchemy Core async (bulk insert).<br>3. Validación post-carga: conteos, integridad referencial, nulos en claves.<br>4. Swap atómico: `BEGIN; TRUNCATE establecimientos; INSERT INTO establecimientos SELECT * FROM establecimientos_staging; COMMIT;`.<br>5. Documentar en `docs/DATA_LOADING.md`. |
| **Archivos** | `src/infrastructure/etl/loader.py` (nuevo), `scripts/load_to_db.py` (nuevo), `docs/DATA_LOADING.md` (nuevo) |
| **Estimación** | 2-3h |
| **Aceptación** | Ejecutar `load_to_db.py` dos veces seguidas produce el mismo conteo de filas. Interrumpir a mitad de carga no deja la DB inconsistente. |

---

### 1.3 Regla de dependencias invertida en la tabla de capas

| Campo | Valor |
|-------|-------|
| **Problema** | v2 indica que `infrastructure` importa `application`. En Clean Architecture esto genera ciclos de importación y destruye testabilidad. |
| **Propuesta** | Corregir la tabla y la implementación:<br>- `domain`: cero imports de frameworks.<br>- `application`: solo importa `domain`.<br>- `infrastructure`: solo importa `domain` (implementa Protocols definidos ahí).<br>- `api`: importa `application` e `infrastructure` para hacer wiring (inyección de dependencias) en `deps.py` o `composition.py`. |
| **Archivos** | `docs/ARCHITECTURE_v2.md` (corregir), `src/domain/repositories.py`, `src/application/*.py`, `src/infrastructure/db/repositories.py`, `src/api/deps.py` |
| **Estimación** | 0.5h (documentación + estructura inicial) |
| **Aceptación** | `grep -r "from application" src/infrastructure/` retorna 0 resultados. Tests unitarios de `application/` corren sin importar SQLAlchemy ni FastAPI. |

---

### 1.4 `etiquetas` llega como String, no como lista

| Campo | Valor |
|-------|-------|
| **Problema** | En Parquet, `etiquetas` es String (`'PIE,SEP,GRATUITO'`). El DDL declara `TEXT[]` y el tsvector usa `array_to_string`, que requiere array. |
| **Propuesta** | 1. En `loader.py`, transformar al cargar: `etiquetas.split(',') if etiquetas else []`.<br>2. Validación post-carga: verificar que no haya strings crudos en la columna. |
| **Archivos** | `src/infrastructure/etl/loader.py`, `src/transform/models.py` (verificar tipo) |
| **Estimación** | 0.5h |
| **Aceptación** | `SELECT etiquetas FROM establecimientos LIMIT 5` retorna arrays (`{PIE,SEP,GRATUITO}`), no strings. Búsqueda `@> ARRAY['PIE']` funciona. |

---

### 1.5 Tablas `regiones` y `comunas` no tienen fuente en el ETL

| Campo | Valor |
|-------|-------|
| **Problema** | El ETL produce 6 Parquet pero ninguno para tablas de referencia. Las FKs desde `sedes` fallan si `comunas` está vacía. |
| **Propuesta** | 1. Derivar tablas de referencia desde `sedes.parquet` con `SELECT DISTINCT` sobre `(codigo_region, region)` y `(codigo_comuna, comuna, codigo_region)`.<br>2. Cargar `regiones` → `comunas` → `sedes` (orden por FK). |
| **Archivos** | `src/infrastructure/etl/loader.py` |
| **Estimación** | 1h |
| **Aceptación** | `make load-db` desde base vacía termina sin errores de FK. `SELECT count(*) FROM comunas` retorna 346. |

---

### 1.6 Colisión de nombres: `src/api/` ya existe como cliente HTTP

| Campo | Valor |
|-------|-------|
| **Problema** | `src/api/` contiene `client.py` y `rate_limiter.py` del scraper. v2 quiere usar `src/api/` para FastAPI. |
| **Propuesta** | 1. Renombrar `src/api/` → `src/api_client/`.<br>2. Actualizar imports en `src/api_client/client.py` y tests.<br>3. Ejecutar `pytest` post-renombre. |
| **Archivos** | `src/api/` → `src/api_client/`, `tests/test_api_client.py`, `Makefile` |
| **Estimación** | 0.5h |
| **Aceptación** | `ls src/` muestra `api_client/` (ETL) y `api/` (FastAPI), sin ambigüedad. `pytest tests/test_api_client.py` pasa. |

---

### 1.7 Claves primarias inválidas en `sedes` y `cursos` (NUEVO — detectado 2026-08-20)

| Campo | Valor |
|-------|-------|
| **Problema** | El DDL declaraba `sedes.codigo_sede INTEGER PRIMARY KEY` y `cursos.codigo_curso INTEGER PRIMARY KEY`. Verificado contra `data/processed/latest/*.parquet`: `codigo_sede` tiene 4 valores distintos (1–4) y `codigo_curso` 497 valores distintos. No son únicos globalmente; la carga rompe con violación de PK. |
| **Propuesta** | 1. `sedes`: `PRIMARY KEY (rbd, codigo_sede)`.<br>2. `cursos`: `PRIMARY KEY (rbd, codigo_curso)` + `FOREIGN KEY (rbd, codigo_sede) REFERENCES sedes(rbd, codigo_sede)`.<br>3. Eliminar índices redundantes (`idx_sedes_rbd`, `idx_cursos_rbd`, `idx_cursos_sede`): el PK btree compuesto ya cubre búsquedas por `rbd`. |
| **Archivos** | `docs/ARCHITECTURE_v2.md` (DDL sección 4), primera migración Alembic |
| **Estimación** | 0.25h (documentación; ya verificado contra datos) |
| **Aceptación** | `load_to_db.py` carga 7,912 sedes y 77,540 cursos sin error de PK. `SELECT count(*) FROM (SELECT DISTINCT rbd, codigo_sede FROM sedes)` == filas totales. |

---

## 2. Issues Importantes (MEDIUM) — Deuda técnica inmediata

### 2.1 Schema relacional incompleto

| Campo | Valor |
|-------|-------|
| **Problema** | DDL no cubre todos los campos del modelo Pydantic. Faltan FKs, CHECK constraints, índices óptimos y `GENERATED ALWAYS AS IDENTITY`. |
| **Propuesta** | 1. Auditar campo a campo entre `src/transform/models.py` y DDL.<br>2. Agregar FK `sedes.codigo_region → regiones(codigo)`.<br>3. Agregar CHECK constraints: porcentajes (0-100), cupos (>=0), latitud (-90,90), longitud (-180,180).<br>4. Reemplazar `SERIAL` por `GENERATED ALWAYS AS IDENTITY`.<br>5. Agregar índice GIN en `etiquetas TEXT[]`.<br>6. Documentar campos descartados (`resumenProyectoPIE`, `procesosEspeciales`, `especialidades`, `id_mongo`).<br>7. Eliminar `id_mongo` del schema. |
| **Archivos** | Primera migración Alembic, `src/transform/models.py`, `docs/DATA_DICTIONARY.md` |
| **Estimación** | 2-3h |
| **Aceptación** | `\d establecimientos` en psql no muestra columna `distancia` ni `id_mongo`. `INSERT` con valores inválidos en CHECK retorna error. |

---

### 2.2 Sin Docker ni entorno reproducible

| Campo | Valor |
|-------|-------|
| **Problema** | Un reviewer no puede levantar el proyecto en <5 minutos. No hay `docker-compose.yml` ni scripts de inicialización. |
| **Propuesta** | 1. Crear `docker-compose.yml` con `postgres:15-alpine` y volumen persistente.<br>2. Crear `.env.example` con `DATABASE_URL`, `API_PORT`, `FRONTEND_PORT`.<br>3. Crear `scripts/init_db.py` (crea DB y rol, idempotente).<br>4. Crear `scripts/seed_demo.py` (50 colegios determinísticos).<br>5. Actualizar `Makefile`: `db-up`, `db-down`, `migrate`, `backend`, `frontend`, `seed-demo`. |
| **Archivos** | `docker-compose.yml`, `.env.example`, `scripts/init_db.py`, `scripts/seed_demo.py`, `Makefile` |
| **Estimación** | 2h |
| **Aceptación** | `make db-up && make migrate && make seed-demo` levanta PostgreSQL con datos de prueba en <2 minutos. |

---

### 2.3 API sin contratos suficientemente definidos

| Campo | Valor |
|-------|-------|
| **Problema** | Endpoints listan rutas pero omiten reglas de paginación, ordenamiento, búsqueda vacía, ficha completa, formato de error y límites de comparación. |
| **Propuesta** | Documentar y implementar cada endpoint con:<br>1. **Paginación**: `limit` máximo 100, default 20. Si `offset >= total`, retornar `results: []` (no error).<br>2. **Ordenamiento**: search ordena por `ts_rank_cd` DESC, luego por `nombre` ASC (estable).<br>3. **Búsqueda vacía** (`q=`): retornar todos los resultados paginados (no error).<br>4. **Ficha completa**: Opción A (backend agregador) con DTO enriquecido que incluye sedes, cursos resumen, indicadores clave, actividades e imágenes. No devolver modelo ORM completo.<br>5. **Compare**: máximo 10 RBDs. Si uno no existe, retornar 404 con lista de RBDs inválidos.<br>6. **Errores**: usar formato propio consistente (no RFC 7807 por simplicidad de MVP): `{ "error": "...", "detail": "...", "status_code": 400 }`. |
| **Archivos** | `docs/API_CONVENTIONS.md` (nuevo), `src/api/routers/*.py`, `src/api/exceptions.py`, `src/api/schemas/*.py` |
| **Estimación** | 2-3h |
| **Aceptación** | Tests de API validan límites (`limit=1000` → 400), búsqueda vacía devuelve 200 con paginación, y ficha carga en <1 query (usando `selectinload` o DTO plano). |

---

### 2.4 FTS sin semántica de ranking ni manejo de tildes

| Campo | Valor |
|-------|-------|
| **Problema** | `to_tsvector('spanish', ...)` sin `ts_rank_cd` devuelve resultados en orden de inserción. No maneja búsqueda sin tilde vs. con tilde (ej. "aleman" no encuentra "Alemán"). |
| **Propuesta** | 1. Ordenar por `ts_rank_cd` (densidad de cobertura) combinado con coincidencia exacta en nombre.<br>2. `CREATE EXTENSION IF NOT EXISTS unaccent;`<br>3. Crear configuración de texto custom: `spanish_unaccent` combinando `spanish` + `unaccent` en la primera migración Alembic.<br>4. Usar esa configuración en `busqueda_tsvector` y en `to_tsquery`/`websearch_to_tsquery`.<br>5. Documentar que autocompletado y fuzzy están **fuera de alcance MVP**.<br>6. Tests de integración: "aleman" debe encontrar "Alemán". |
| **Archivos** | Migración Alembic inicial, `src/infrastructure/search_service.py`, `tests/integration/test_search.py` |
| **Estimación** | 1.5h |
| **Aceptación** | `GET /api/v1/search?q=aleman` retorna colegios con "Alemán" en el nombre. Resultados ordenados por relevancia. |

---

### 2.5 Caching declarado pero sin invalidación

| Campo | Valor |
|-------|-------|
| **Problema** | `@lru_cache` bloquea el event loop en async. `Cache-Control: max-age=3600` sirve datos viejos tras ETL. |
| **Propuesta** | 1. Reemplazar `@lru_cache` por un `dict` poblado en `lifespan` de FastAPI (datos de referencia pequeños: comunas, regiones).<br>2. Para datos estáticos de referencia: `Cache-Control: public, max-age=86400`.<br>3. Para datos de establecimientos: usar `ETag` basado en hash del dataset o fecha de última carga. Cliente envía `If-None-Match`; servidor responde 304 si no ha cambiado.<br>4. Almacenar `dataset_version` en memoria y comparar antes de devolver caché app-level. |
| **Archivos** | `src/api/main.py` (lifespan), `src/api/routers/*.py`, `src/infrastructure/search_service.py` |
| **Estimación** | 1.5h |
| **Aceptación** | Test de carga muestra p99 < 50ms en endpoints cacheados bajo 100 RPS. Segunda request con mismo ETag retorna 304. |

---

### 2.6 Astro 4 desactualizado

| Campo | Valor |
|-------|-------|
| **Problema** | v2 fija Astro 4. A agosto 2026, Astro 5 es estable. Usar v4 genera deuda de actualización. |
| **Propuesta** | 1. Cambiar a Astro 5 (o versión LTS actual).<br>2. Verificar compatibilidad de `@astrojs/react` y modo SSR (`output: 'server'`).<br>3. Documentar que `@astrojs/node` es necesario para SSR en producción. |
| **Archivos** | `frontend/package.json`, `frontend/astro.config.mjs`, `docs/ARCHITECTURE_v2.md` |
| **Estimación** | 0.5h |
| **Aceptación** | `npm create astro@latest` o actualización de `package.json` produce build sin warnings de deprecación. SSR funciona. |

---

### 2.7 Tabla `imagenes` sin estrategia de almacenamiento

| Campo | Valor |
|-------|-------|
| **Problema** | DDL define `nombre` y `principal` pero no `url`, `path` ni `storage_key`. El frontend no puede renderizar imágenes. |
| **Propuesta** | 1. Agregar columna `url TEXT` (o `storage_key TEXT` + base URL configurable).<br>2. Decidir almacenamiento: filesystem local + endpoint FastAPI `StaticFiles` (MVP), o S3/R2 (futuro).<br>3. Documentar en `docs/STORAGE.md`. |
| **Archivos** | Migración Alembic (`imagenes.url`), `src/api/main.py` (`StaticFiles`), `docs/STORAGE.md` |
| **Estimación** | 1h |
| **Aceptación** | La ficha de un colegio renderiza sus imágenes reales sin error 404. |

---

### 2.8 Denormalización en `sedes` sin estrategia de sincronización

| Campo | Valor |
|-------|-------|
| **Problema** | `sedes` almacena `region TEXT` y `comuna TEXT` además de FKs. Si cambian en tablas de referencia, quedan desincronizados. |
| **Propuesta** | Documentar que `sedes.region` y `sedes.comuna` son **snapshots del ETL** y se sobreescriben en cada recarga. No se requiere consistencia fuerte porque los datos de origen (MINEDUC) cambian en ciclos anuales, no transaccionalmente. |
| **Archivos** | `docs/DATA_DICTIONARY.md`, `docs/DATA_LOADING.md` |
| **Estimación** | 0.25h |
| **Aceptación** | Documento explica explícitamente que nombres en `sedes` son snapshots del ETL. |

---

### 2.9 `habilitado_vitrina` — feature flag mal nombrado

| Campo | Valor |
|-------|-------|
| **Problema** | `habilitado_vitrina BOOLEAN` sin justificación clara. Semántica confusa. |
| **Propuesta** | 1. Renombrar a `publicado` (más explícito).<br>2. Documentar que es un filtro a nivel de query para mostrar/ocultar colegios en el buscador público.<br>3. Default `FALSE` hasta que se defina criterio de publicación. |
| **Archivos** | Migración Alembic, `src/transform/models.py`, `docs/DATA_DICTIONARY.md` |
| **Estimación** | 0.25h |
| **Aceptación** | El nombre del campo refleja su semántica sin necesidad de leer código. |

---

### 2.10 `cursos` con ~30 campos nullable genera payloads sparse

| Campo | Valor |
|-------|-------|
| **Problema** | Si el endpoint devuelve el modelo ORM tal cual, el JSON es extremadamente sparse (muchos `null`), aumentando tamaño de payload. |
| **Propuesta** | 1. En DTOs Pydantic de salida para cursos, usar `exclude_none=True` o definir schema que agrupe campos relacionados.<br>2. Crear endpoint de resumen `/api/v1/cursos/resumen?rbd=` con solo campos esenciales para la ficha.<br>3. Documentar campos críticos vs. opcionales en `DATA_DICTIONARY.md`. |
| **Archivos** | `src/api/schemas/cursos.py`, `src/api/routers/cursos.py`, `docs/DATA_DICTIONARY.md` |
| **Estimación** | 1h |
| **Aceptación** | Payload de `/cursos` para un RBD típico no excede 20 KB. |

---

### 2.11 Índice geoespacial sin endpoints de proximidad

| Campo | Valor |
|-------|-------|
| **Problema** | `idx_sedes_geo(latitud, longitud)` es B-tree, no permite filtrar por distancia real. El plan no expone parámetros de proximidad. |
| **Propuesta** | 1. Agregar parámetros opcionales `lat`, `lon`, `radius_km` al endpoint `/search`.<br>2. Implementar filtro con fórmula Haversine en SQL (suficiente para <10k registros).<br>3. Si queda fuera de alcance, documentar explícitamente que el índice está reservado para ordenamiento y futuras expansiones. |
| **Archivos** | `src/infrastructure/search_service.py`, `src/api/routers/search.py`, `docs/API_CONVENTIONS.md` |
| **Estimación** | 1-2h (si se implementa) / 0.25h (si se documenta como futuro) |
| **Aceptación** | `GET /search?lat=-33.45&lon=-70.66&radius_km=2` retorna solo colegios dentro del radio (si se implementa). |

> **Resuelto (2026-08-20)**: opción "fuera de alcance" aplicada. `idx_sedes_geo` eliminado del DDL; el mapa queda post-MVP.

---

### 2.12 `GET /compare` vulnerable a límite de URL

| Campo | Valor |
|-------|-------|
| **Problema** | URLs largas con muchos RBDs pueden exceder ~2000 caracteres (error 414 en proxies). |
| **Propuesta** | 1. Validar máximo de RBDs: 10.<br>2. Si `len(rbds) > 10`, retornar `400 Bad Request` con mensaje claro.<br>3. Documentar límite en `API_CONVENTIONS.md`. |
| **Archivos** | `src/api/routers/compare.py`, `docs/API_CONVENTIONS.md` |
| **Estimación** | 0.25h |
| **Aceptación** | `GET /compare?rbds=` con 11 RBDs retorna 400 con mensaje "Máximo 10 colegios por comparación". |

---

### 2.13 Graceful degradation ante datos faltantes

| Campo | Valor |
|-------|-------|
| **Problema** | Un colegio puede existir pero carecer de indicadores, actividades o imágenes. `404` en estos casos es confuso. |
| **Propuesta** | 1. Endpoints de sub-recursos (`/sedes`, `/cursos`, `/indicadores`, `/actividades`, `/imagenes`) retornan `200 OK` con array vacío `[]` cuando no hay datos.<br>2. `404` reservado para cuando el `rbd` no existe en `establecimientos`.<br>3. Documentar en `docs/API_CONVENTIONS.md`. |
| **Archivos** | `src/api/routers/*.py`, `docs/API_CONVENTIONS.md` |
| **Estimación** | 0.5h |
| **Aceptación** | `GET /indicadores?rbd=<rbd_sin_simce>` retorna `200` con `[]`. `GET /indicadores?rbd=<rbd_inexistente>` retorna `404`. |

---

### 2.14 Rate limiting como hardening básico

| Campo | Valor |
|-------|-------|
| **Problema** | Endpoint público sin rate limiting es vulnerable a scraping y agotamiento de conexiones PostgreSQL. |
| **Propuesta** | 1. Agregar `slowapi` con limitador en memoria (suficiente para MVP):<br>- `/search`: 30 req/min por IP.<br>- `/establecimientos/{rbd}`: 60 req/min por IP.<br>- Sub-recursos: 60 req/min por IP.<br>2. Incluir headers `X-RateLimit-Limit` y `X-RateLimit-Remaining`.<br>3. Documentar en README como "defensa en profundidad". |
| **Archivos** | `src/api/main.py`, `src/api/deps.py`, `README.md` |
| **Estimación** | 1h |
| **Aceptación** | 100 requests concurrentes a `/search` desde misma IP; después del límite, recibe `429 Too Many Requests`. |

---

### 2.15 Filtro `copago_max` puede duplicar RBDs en resultados

| Campo | Valor |
|-------|-------|
| **Problema** | `copago_valor` vive en `cursos` (N cursos por colegio). JOIN con `cursos` para filtrar duplica resultados. |
| **Propuesta** | Implementar filtro como subconsulta: `EXISTS (SELECT 1 FROM cursos WHERE cursos.rbd = establecimientos.rbd AND copago_valor <= :copago_max)`. |
| **Archivos** | `src/infrastructure/search_service.py` |
| **Estimación** | 0.5h |
| **Aceptación** | Colegio con múltiples cursos bajo umbral aparece exactamente una vez. `count(DISTINCT rbd)` == `total` del response. |

---

### 2.16 Semántica del filtro `nivel=` indefinida

| Campo | Valor |
|-------|-------|
| **Problema** | No está claro qué significa filtrar por `nivel`: ¿match exacto? ¿rango? |
| **Propuesta** | 1. Definir semántica: el colegio matchea si `nivel` está en el rango `[nivel_minimo .. nivel_maximo]`.<br>2. Crear mapa de orden documentado: `PARVULARIO=0, BASICA=1, MEDIA=2, ...`.<br>3. Documentar en `DATA_DICTIONARY.md` y en DTO del endpoint. |
| **Archivos** | `src/infrastructure/search_service.py`, `src/api/schemas/search.py`, `docs/DATA_DICTIONARY.md` |
| **Estimación** | 0.5h |
| **Aceptación** | `GET /search?nivel=MEDIA` retorna colegios cuyo rango incluye media, aunque `nivel_minimo` sea `BASICA`. |

---

### 2.17 Ambigüedad entre `init_db.py` y Alembic

| Campo | Valor |
|-------|-------|
| **Problema** | Responsabilidades solapadas: ambos "crean la base de datos". |
| **Propuesta** | Delimitar claramente:<br>- `init_db.py`: crea **clúster/base de datos** y rol. Idempotente. No toca schema.<br>- Alembic: gestiona **schema** (tablas, índices, constraints, FKs). Migraciones incrementales.<br>Orden: `make db-up` → `make init-db` → `make migrate` → `make load-db` → `make seed-demo`. |
| **Archivos** | `scripts/init_db.py`, `Makefile`, `docs/DATA_LOADING.md` |
| **Estimación** | 0.5h |
| **Aceptación** | Borrar DB y ejecutar `make all` desde cero produce entorno funcional sin pasos manuales. |

---

### 2.18 CI sin service container de PostgreSQL

| Campo | Valor |
|-------|-------|
| **Problema** | Tests de integración requieren PostgreSQL real. GitHub Actions no lo provee por defecto. |
| **Propuesta** | 1. En `.github/workflows/ci.yml`, agregar service container `postgres:15-alpine`.<br>2. Ejecutar `alembic upgrade head` + `seed_demo.py` antes de `pytest`.<br>3. Variable `DATABASE_URL_TEST` en secrets/vars del workflow. |
| **Archivos** | `.github/workflows/ci.yml` |
| **Estimación** | 1h |
| **Aceptación** | Un PR que rompa una query SQL falla en CI, no solo en local. |

---

### 2.19 `regimen` sin CHECK constraint

| Campo | Valor |
|-------|-------|
| **Problema** | `regimen TEXT` acepta cualquier string. Valores conocidos: `JEC`, `JECD`, `TRICEL`, etc. |
| **Propuesta** | 1. Agregar `CHECK (regimen IN ('JEC', 'JECD', 'TRICEL', ...))` con valores observados en Parquet.<br>2. Documentar valores válidos en `DATA_DICTIONARY.md`. |
| **Archivos** | Migración Alembic, `docs/DATA_DICTIONARY.md` |
| **Estimación** | 0.25h |
| **Aceptación** | `INSERT INTO establecimientos (regimen) VALUES ('INVALIDO')` retorna error de constraint. |

---

## 3. Issues Menores (LOW) — Posponibles a F4/post-MVP

### 3.1 Documentación de arquitectura duplicada y contradictoria

| Campo | Valor |
|-------|-------|
| **Problema** | `docs/ARCHITECTURE.md` describe SQLite + aiosqlite. `docs/ARCHITECTURE_v2.md` describe PostgreSQL + asyncpg. |
| **Propuesta** | Mover `docs/ARCHITECTURE.md` a `docs/archive/ARCHITECTURE_v1.md`. Actualizar `docs/ARCHITECTURE_v2.md` para reflejar estado vigente. |
| **Archivos** | `docs/ARCHITECTURE.md` → `docs/archive/ARCHITECTURE_v1.md` |
| **Estimación** | 0.25h |
| **Aceptación** | Solo existe una versión vigente de arquitectura en `docs/`. |

> **Resuelto (2026-08-20)**: `ARCHITECTURE.md` movido a `docs/archive/ARCHITECTURE_v1.md` con banner de deprecación. `README.md` enlaza a `ARCHITECTURE_v2.md`.

---

### 3.2 Sin métricas ni observabilidad

| Campo | Valor |
|-------|-------|
| **Problema** | `structlog` y `correlation_id` mencionados pero sin estrategia de qué loguear ni cómo propagar en async. |
| **Propuesta** | 1. Usar `contextvars.ContextVar` para `correlation_id`.<br>2. Middleware ASGI que genera/asigna ID y lo inyecta en `contextvars`.<br>3. Hook SQLAlchemy `before_cursor_execute` que añade ID como comentario SQL.<br>4. Response header `X-Correlation-Id`.<br>5. Loguear en cada request: `method`, `path`, `status_code`, `duration_ms`, `correlation_id`. |
| **Archivos** | `src/logging.py`, `src/api/main.py`, `src/infrastructure/db/session.py` |
| **Estimación** | 1-2h |
| **Aceptación** | Una request genera logs correlacionables desde request hasta query SQL con mismo `correlation_id`. |

---

### 3.3 Riesgos legales y éticos no documentados

| Campo | Valor |
|-------|-------|
| **Problema** | No hay documentación sobre términos de uso de MINEDUC, privacidad de datos públicos de colegios ni descargo de responsabilidad. |
| **Propuesta** | Crear `docs/LEGAL.md` con:<br>1. Atribución requerida por MINEDUC.<br>2. Política de privacidad: datos públicos de establecimientos educacionales.<br>3. Descargo: "Los datos provienen de fuentes públicas y pueden no estar actualizados."<br>4. Fecha de última actualización visible en frontend. |
| **Archivos** | `docs/LEGAL.md` (nuevo), `frontend/src/pages/acerca.astro` |
| **Estimación** | 0.5h |
| **Aceptación** | README enlaza a `docs/LEGAL.md`. Frontend muestra fecha de última actualización. |

---

### 3.4 CI hook de `openapi-typescript` no especificado

| Campo | Valor |
|-------|-------|
| **Problema** | Riesgo de que tipos TypeScript se desincronicen del contrato OpenAPI. |
| **Propuesta** | 1. Crear `scripts/check_openapi_types.sh`: genera tipos desde `/openapi.json`, compara contra `frontend/src/lib/types.ts`.<br>2. Integrar como paso de CI antes de `frontend build`.<br>3. Agregar `make generate-types` para regenerar manualmente. |
| **Archivos** | `scripts/check_openapi_types.sh`, `.github/workflows/ci.yml`, `Makefile` |
| **Estimación** | 1h |
| **Aceptación** | Cambiar un DTO de API y commitear → CI falla. Regenerar tipos y commitear → CI pasa. |

---

### 3.5 Indicadores: 4 campos con semántica similar

| Campo | Valor |
|-------|-------|
| **Problema** | `titulo_indicador`, `nivel_indicador`, `descripcion_indicador`, `nombre_indicador`. Diferencia no es obvia. |
| **Propuesta** | 1. Auditar JSON de origen para entender qué representa cada campo.<br>2. Si 3 de 4 son siempre nulos/redundantes, consolidar en `metadata JSONB`.<br>3. Documentar en `DATA_DICTIONARY.md` con ejemplo real por campo. |
| **Archivos** | `src/transform/models.py`, `docs/DATA_DICTIONARY.md`, migración Alembic |
| **Estimación** | 0.5h |
| **Aceptación** | Cada campo de `indicadores` tiene descripción de negocio en el data dictionary. |

---

### 3.6 `seed_demo.py` sin estrategia de generación

| Campo | Valor |
|-------|-------|
| **Problema** | v2 dice "50 colegios demo determinísticos" pero no especifica cómo se generan. |
| **Propuesta** | 1. Usar **plantillas hardcoded** con `random.seed(42)` para determinismo.<br>2. Cubrir diversidad: público, particular subvencionado, particular pagado, distintos regímenes, distintos niveles.<br>3. Dos ejecuciones consecutivas producen exactamente la misma base de datos. |
| **Archivos** | `scripts/seed_demo.py` |
| **Estimación** | 1h |
| **Aceptación** | `pytest` o diff de dump confirma que dos ejecuciones de `seed_demo.py` son idénticas. |

---

### 3.7 Auth/authorization no documentado

| Campo | Valor |
|-------|-------|
| **Problema** | Plan describe API pública read-only sin mencionar explícitamente ausencia de auth. Reviewer podría asumir que falta. |
| **Propuesta** | 1. Documentar en README: "API pública sin autenticación por diseño. Dataset proviene de fuente pública (MINEDUC)."<br>2. Si en futuro se exponen endpoints de admin, dejar claro que requerirán auth (API keys). |
| **Archivos** | `README.md` |
| **Estimación** | 0.25h |
| **Aceptación** | README contiene sección "Seguridad y autenticación" que explica la decisión. |

---

### 3.8 Columna `distancia` en Parquet no contemplada en el DDL

| Campo | Valor |
|-------|-------|
| **Problema** | `establecimientos.parquet` contiene columna `distancia` (artefacto del scrapeo). DDL no la incluye. |
| **Propuesta** | El loader debe excluirla explícitamente (columna allowlist o drop previo). Documentar exclusión en `DATA_DICTIONARY.md`. |
| **Archivos** | `src/infrastructure/etl/loader.py`, `docs/DATA_DICTIONARY.md` |
| **Estimación** | 0.25h |
| **Aceptación** | `\d establecimientos` en psql no muestra columna `distancia`. |

---

### 3.9 `src/config.py` y `src/logging.py` listados como existentes

| Campo | Valor |
|-------|-------|
| **Problema** | v2 muestra estos archivos bajo "ETL existente" pero no existen en el repositorio. Config actual vive en `config/` y `.env`. |
| **Propuesta** | 1. Incluir creación en F1.<br>2. Consolidar `config/` dentro de `src/config.py` usando `pydantic-settings` para fuente única de verdad. |
| **Archivos** | `src/config.py` (nuevo), `src/logging.py` (nuevo), `.env.example` |
| **Estimación** | 0.5h |
| **Aceptación** | `src/config.py` existe, carga `DATABASE_URL` desde `.env`, y `make backend` lo utiliza. |

---

### 3.10 `app.py`: prototipo Streamlit huérfano

| Campo | Valor |
|-------|-------|
| **Problema** | `app.py` (Streamlit) tiene bug runtime (`NameError` en `color_map`), dependencias no instaladas, y queda superseded por F3. |
| **Propuesta** | 1. Eliminar `app.py`.<br>2. Rescatar idea: scatter "SIMCE Lenguaje vs Matemática" como nice-to-have post-MVP en ficha o comparador. |
| **Archivos** | `app.py` (eliminar) |
| **Estimación** | 0.25h |
| **Aceptación** | `grep -r "app.py" Makefile scripts/ tests/` no retorna referencias. |

---

## 4. Resumen de Estimaciones por Fase

| Fase | Issues cubiertos | Horas acumuladas |
|------|------------------|------------------|
| **F0** | 1.1, 1.4, 1.5, 1.6, 2.8, 2.17, 3.8, 3.9, 3.10 | 4-5h |
| **F1** | 1.2, 1.3, 2.1, 2.2, 2.7, 2.9, 3.1 | 8-10h |
| **F2** | 2.3, 2.4, 2.5, 2.10, 2.11, 2.12, 2.13, 2.14, 2.15, 2.16, 2.18, 2.19, 3.2, 3.5, 3.6, 3.7 | 12-16h |
| **F3** | 2.6 | 10-14h |
| **F4** | 3.3, 3.4 | 8-10h |
| **Total** | **32 propuestas** | **~42-55h** |

---

## 5. Decisiones Pendientes que el Usuario debe Tomar

> **RESUELTAS (2026-08-20)** — todas incorporadas a `ARCHITECTURE_v2.md`:
> 1. Carga DB → **swap transaccional** (decisión #14).
> 2. Ficha → **backend agregador con DTO enriquecido** (#15).
> 3. Mapa → **FUERA de MVP** (confirmado por el usuario; Leaflet e `idx_sedes_geo` eliminados).
> 4. `id_mongo` → **eliminado** (#17).
> 5. Campos descartados → **documentar exclusión** (#18).
> 6. Payload sparse → **endpoint `/cursos/resumen`** (#19).

Antes de comenzar la implementación, se requiere confirmación explícita sobre:

1. **Estrategia de carga DB**: ¿Swap transaccional (simple) o versionado por fila (histórico)?
2. **Ficha completa**: ¿Backend agregador con DTO enriquecido (recomendado) o frontend compositor con N requests?
3. **Mapa en MVP**: ¿Fuera de alcance (recomendado para ~45h) o incluir con Haversine?
4. **`id_mongo`**: ¿Eliminar del schema (recomendado) o conservar?
5. **Campos descartados** (`PIE`, `especialidades`): ¿Incluir en schema o documentar exclusión?
6. **Payload sparse en cursos**: ¿Endpoint de resumen (`/cursos/resumen`) o `exclude_none=True` en DTO actual?

---

*Documento generado: 2026-08-20*  
*Basado en: `docs/ARCHITECTURE_REVIEW.md` y `docs/ARCHITECTURE_v2.md`*
