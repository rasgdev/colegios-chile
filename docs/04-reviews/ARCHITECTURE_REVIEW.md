# Revisión de Arquitectura v2.0

> Análisis técnico de `docs/ARCHITECTURE_v2.md` contra el estado real del repositorio.  
> Objetivo: identificar gaps, riesgos y acciones concretas antes de comenzar la implementación.

---

## 1. Resumen Ejecutivo

El plan de arquitectura es **direccionalmente correcto**: PostgreSQL + FastAPI + Astro SSR es una pila defendible para un buscador de catálogo. Sin embargo, **no está listo para implementación directa**. Los problemas más graves no son de framework, sino de **datos, operabilidad y coherencia de dependencias**.

| Aspecto | Estado | Riesgo |
|---------|--------|--------|
| Dataset ETL | Parcial (11/346 comunas, datos de 2026-08-02) | **Alto** |
| Dependencias de backend | No instaladas | Medio |
| Frontend | No existe | Medio |
| Reglas de Clean Architecture | Tabla de dependencias invertida | Medio |
| Estrategia de carga DB | No definida | **Alto** |
| Docker / reproducibilidad | Ausente | Medio |
| Documentación de arquitectura | Dos versiones contradictorias (v1 SQLite, v2 PostgreSQL) | Medio |

**Veredicto**: aprobado con correcciones obligatorias antes de F1.

---

## 2. Estado Actual vs. Estado Deseado

### 2.1 Repositorio actual (snapshot 2026-08-20)

```
colegios-chile/
├── src/extract/         # HTTP client + rate limiter para API MINEDUC
├── src/transform/       # Normalizadores + modelos Pydantic
├── src/load/            # Escritura Parquet
├── src/api/             # Únicamente rate_limiter.py y client.py (HTTP, no REST)
├── src/validation/      # DuckDB checks sobre Parquet
├── scripts/             # run_etl.py, discover_comunas.py
├── data/processed/      # 6 archivos Parquet (2026-08-02)
├── tests/               # Tests de transformación y API client
├── Makefile             # Targets: discover, etl, transform, validate, test
└── pyproject.toml       # Solo config de pytest
```

**Dataset disponible**:

| Tabla | Filas | Fuente |
|-------|-------|--------|
| establecimientos | 7,673 | Parquet 2026-08-02 |
| sedes | 7,912 | Parquet 2026-08-02 |
| cursos | 77,540 | Parquet 2026-08-02 |
| actividades | 206,041 | Parquet 2026-08-02 |
| indicadores | 49,830 | Parquet 2026-08-02 |
| imagenes | 77,421 | Parquet 2026-08-02 |

**Problema**: el reporte `data/processed/2026-08-02/report.json` indica **346 comunas totales, 11 exitosas, 1 fallida**. Si el ETL no procesó el 96 % de las comunas, el dataset no representa un catálogo nacional usable. Antes de diseñar la API pública hay que resolver si esto fue un error transitorio, un filtro intencional o un bug del pipeline.

### 2.2 Estado deseado según ARCHITECTURE_v2.md

- PostgreSQL 15+ con FTS, arrays y asyncpg.
- FastAPI 0.110+ con routers, DTOs Pydantic v2 y OpenAPI auto-generado.
- Astro 4 con SSR para fichas y React islands para búsqueda.
- Clean Architecture de 4 capas.
- ~32 h de trabajo en 4 fases.

---

## 3. Issues Críticos (Severidad: HIGH)

> Bloqueantes para comenzar F1. Deben resolverse antes de cualquier implementación.

### 3.1 Dataset incompleto / sin validación de frescura

**Descripción**: El ETL actual produjo 7,673 establecimientos a partir de solo 11 comunas exitosas. No hay garantía de que este sea un snapshot representativo del catálogo nacional.

**Impacto**: Un buscador público con datos parciales genera desconfianza y puede excluir colegios reales.

**Acción requerida**:
1. Reejecutar `make all` y verificar que `report.json` reporte un número razonable de comunas exitosas (>300).
2. Si el ETL falla sistemáticamente en comunas específicas, documentarlas como `KNOWN_ISSUES.md`.
3. Añadir una etapa de **validación de completitud** al pipeline: comparar conteo de RBDs por comuna contra un valor de referencia (ej. MINEDUC abierto).
4. Definir una **política de snapshots**: ¿se ejecuta mensualmente? ¿se versionan? ¿qué fecha muestra el frontend?

**Verificación**:
- `report.json` contiene `comunas_exitosas >= 300`.
- `report.json` contiene `fecha_ejecucion` y `version_dataset`.

---

### 3.2 Ausencia de estrategia de carga atómica en PostgreSQL

**Descripción**: El plan menciona `loader.py` (Parquet → PostgreSQL) pero no define qué ocurre si la carga se interrumpe, si se repite, ni cómo se versiona el contenido de la base de datos.

**Impacto**: Cargas parciales corrompen la base de datos. Sin idempotencia, reejecutar el loader duplica datos.

**Acción requerida**:
1. **Tablas staging**: cargar Parquet a tablas temporales (`establecimientos_staging`, etc.).
2. **Validación post-carga**: ejecutar los mismos checks DuckDB pero contra PostgreSQL (conteos, integridad referencial, nulos en claves).
3. **Swap transaccional** (opción A): dentro de una transacción, `TRUNCATE` tablas productivas e `INSERT INTO ... SELECT * FROM staging`. Esto bloquea lecturas momentáneamente pero garantiza atomicidad.
4. **Versión activa** (opción B): añadir columna `dataset_version INTEGER NOT NULL` a todas las tablas. La API filtra por la versión más reciente. Las cargas nuevas insertan con `version + 1`; un job posterior elimina versiones viejas. Permite lecturas sin downtime.
5. Documentar la estrategia elegida en `docs/DATA_LOADING.md`.

**Verificación**:
- Ejecutar `python scripts/load_to_db.py` dos veces seguidas produce el mismo conteo de filas.
- Interrumpir el script a mitad de carga no deja la base de datos en estado inconsistente.

---

### 3.3 Regla de dependencias invertida en la tabla de capas

**Descripción**: En la tabla de la sección 2.1 (`ARCHITECTURE_v2.md`, líneas 21-26), `infrastructure` se describe como importando `application` y `domain`. En Clean Architecture, `infrastructure` solo debe depender de `domain` (implementa los puertos/definidos en domain). Los casos de uso (`application`) nunca son importados por la infraestructura.

**Impacto**: Si se implementa literalmente, se generan import cycles y se rompe la testabilidad (la infraestructura no puede instanciarse sin los use cases).

**Acción requerida**:
1. Corregir la tabla:
   - `domain`: cero imports de frameworks.
   - `application`: solo importa `domain`.
   - `infrastructure`: solo importa `domain` (implementa `Protocol`s definidos ahí).
   - `api`: importa `application` e `infrastructure` para hacer *wiring* (inyección de dependencias).
2. El *wiring* concreto (ej. `repo = PostgresEstablecimientoRepo(engine)`) debe vivir en `api/` o en un módulo `composition.py` dentro de `api/`, nunca en `infrastructure/`.

**Verificación**:
- `grep -r "from application" src/infrastructure/` debe retornar 0 resultados.
- Los tests unitarios de `application/` corren sin importar SQLAlchemy ni FastAPI.

---

### 3.4 Claves primarias inválidas en `sedes` y `cursos` (NUEVO — detectado 2026-08-20)

**Descripción**: El DDL declaraba `sedes.codigo_sede INTEGER PRIMARY KEY` y `cursos.codigo_curso INTEGER PRIMARY KEY`, asumiendo unicidad global. Verificado contra `data/processed/latest/*.parquet`:
- `sedes.codigo_sede`: solo **4 valores distintos** (1–4) sobre 7,912 filas. Es un ordinal de sede por colegio, no un código único.
- `cursos.codigo_curso`: **497 valores distintos** sobre 77,540 filas. Es un código de nivel que se repite entre colegios.

**Impacto**: La carga (`load_to_db.py`) falla con violación de PK en la primera inserción duplicada.

**Acción requerida** (ya aplicada en `ARCHITECTURE_v2.md`):
1. `sedes`: `PRIMARY KEY (rbd, codigo_sede)`.
2. `cursos`: `PRIMARY KEY (rbd, codigo_curso)` + `FOREIGN KEY (rbd, codigo_sede) REFERENCES sedes(rbd, codigo_sede)`.
3. Índices redundantes (`idx_sedes_rbd`, `idx_cursos_rbd`, `idx_cursos_sede`) eliminados: el PK btree compuesto ya cubre las búsquedas por `rbd`.

**Verificación** (datos): `(rbd, codigo_sede)` es único en `sedes` (7,912/7,912) y `(rbd, codigo_curso)` en `cursos` (77,540/77,540). La FK compuesta cursos→sedes tiene 0 huérfanos.

---

## 4. Issues Importantes (Severidad: MEDIUM)

> No bloquean F1, pero generan deuda técnica si se posponen. Deberían resolverse dentro de F1-F2.

### 4.1 Schema relacional incompleto

**Descripción**: El DDL de la sección 4 no cubre todos los campos del modelo Pydantic (`src/transform/models.py`), ni garantiza integridad referencial completa.

**Gaps identificados**:

| Campo origen | Estado en DDL | Recomendación |
|--------------|---------------|---------------|
| `sedes.codigo_region` | No tiene FK a `regiones(codigo)` | Agregar FK. |
| `director` | Solo `TEXT` | El JSON de origen tiene `director.nombre`; si se descarta la estructura, documentar el motivo. |
| `resumenProyectoPIE` | Ausente | Agregar o documentar exclusión. |
| `procesosEspeciales` | Ausente | Agregar o documentar exclusión. |
| `especialidades` | Ausente | Agregar o documentar exclusión. |
| `establecimientos.id_mongo` | Presente | ¿Se usa realmente? Si no, eliminar para evitar acoplamiento con el sistema de origen. |

**Índices faltantes o subóptimos**:
- `etiquetas TEXT[]` necesita un índice GIN si se filtrará por etiquetas (ej. `WHERE etiquetas @> ARRAY['bilingüe']`).
- `idx_sedes_geo(latitud, longitud)` es un índice B-tree, no geoespacial. Para búsquedas por proximidad (radio de X km) se requiere PostGIS (`GEOGRAPHY` + índice GiST). Si el MVP solo muestra colegios en un mapa sin filtro de distancia, el índice B-tree es suficiente para ordenar, pero debe documentarse la limitación. **Resuelto (2026-08-20)**: índice eliminado del DDL; el mapa queda fuera de alcance MVP.
- Faltan `CHECK constraints` en porcentajes (0-100), cupos (>=0), latitud (-90,90) y longitud (-180,180).
- `SERIAL` debería ser `GENERATED ALWAYS AS IDENTITY` en un diseño nuevo (estándar SQL).

**Acción requerida**:
1. Auditar campo a campo entre `src/transform/models.py` y el DDL.
2. Crear `docs/DATA_DICTIONARY.md` que liste cada campo, su tipo PostgreSQL, si es nullable, su fuente JSON y su propósito de negocio.
3. Añadir constraints e índices faltantes en la primera migración Alembic.

---

### 4.2 Sin Docker ni entorno reproducible

**Descripción**: El plan asume PostgreSQL 15+ pero no provee instrucciones ni infraestructura para levantarlo. Un reviewer del portafolio debe poder ejecutar `make db-up && make migrate && make backend` en menos de 5 minutos.

**Acción requerida**:
1. Crear `docker-compose.yml` con servicio `postgres:15-alpine`.
2. Mapear volumen persistente para no perder datos al detener el contenedor.
3. Variables de entorno en `.env.example` (no commitear `.env`):
   - `DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/colegios`
   - `API_PORT=8000`
   - `FRONTEND_PORT=4321`
4. Scripts de utilidad:
   - `scripts/init_db.py`: crea la base de datos si no existe (útil para PostgreSQL local).
   - `scripts/seed_demo.py`: inserta 50 colegios determinísticos para reviewers sin ejecutar ETL.
5. Actualizar `Makefile`:
   - `make db-up`
   - `make db-down`
   - `make migrate`
   - `make backend`
   - `make frontend`

---

### 4.3 API sin contratos suficientemente definidos

**Descripción**: Los endpoints de la sección 6 listan rutas y parámetros, pero omiten reglas de negocio que afectan performance y UX.

**Preguntas sin respuesta**:

1. **Paginación**: ¿Cuál es el `limit` máximo permitido? ¿Qué pasa si `offset` es mayor que `total`?
2. **Ordenamiento**: ¿Por qué campo se ordenan los resultados de `/search`? ¿Es estable?
3. **Búsqueda vacía**: Si `q=` (vacío), ¿se devuelven todos los resultados paginados o un error?
4. **Ficha completa**: `GET /establecimientos/{rbd}` debe devolver sedes, cursos, indicadores, actividades e imágenes. ¿En una sola query o el frontend hace 5 requests?
   - Opción A (backend agregador): un solo endpoint que hace JOINs o `selectinload`. Riesgo de payload masivo.
   - Opción B (frontend compositor): el frontend llama `/establecimientos/{rbd}` y luego paraleliza `/sedes?rbd=`, `/cursos?rbd=`, etc. Más requests pero payload controlado.
   - **Recomendación**: Opción A con un DTO que incluya solo los campos necesarios para la ficha (no todo el modelo ORM).
5. **Compare**: `GET /compare?rbds=1,2,3` no define el máximo de RBDs, ni si se deduplica, ni el formato de error si un RBD no existe.
6. **Formato de error**: ¿Usa RFC 7807 (`application/problem+json`) o un formato propio? Debe ser consistente en todos los endpoints.

**Acción requerida**:
1. Documentar cada endpoint con:
   - Request: parámetros, tipos, límites, defaults.
   - Response 200: schema JSON completo (incluyendo campos nullable).
   - Responses de error: status codes, body, condiciones de disparo.
2. Implementar `api/exceptions.py` con handlers centralizados para `ValidationError`, `NotFoundError`, `TooManyItemsError`.
3. Añadir tests de API que validen los límites (ej. `limit=1000` debe devolver 400).

---

### 4.4 FTS sin semántica de ranking ni autocompletado

**Descripción**: `tsvector` + GIN es correcto para búsqueda full-text, pero el plan no define cómo se ordenan los resultados. PostgreSQL devuelve resultados en orden de inserción a menos que se use `ORDER BY ts_rank(...) DESC`.

**Además**, `to_tsvector('spanish', ...)` no maneja:
- Búsqueda por prefijo (autocompletado).
- Tolerancia a faltas de ortografía.
- Sinónimos o variantes ("colegio" vs "liceo" vs "escuela").

**Acción requerida**:
1. Para el MVP: ordenar por `ts_rank_cd` (densidad de cobertura) combinado con un factor de relevancia (ej. coincidencia exacta en nombre pesa más que en resumen).
2. Documentar explícitamente que autocompletado y fuzzy search están **fuera de alcance** del MVP.
3. Si el tiempo lo permite en F4, evaluar `pg_trgm` para búsqueda por similitud.

---

### 4.5 Caching declarado pero sin invalidación

**Descripción**: El plan propone `@lru_cache` para lookups de referencia (comunas, regiones) y `Cache-Control: public, max-age=3600` en endpoints de lectura.

**Problema**: Si se carga un nuevo snapshot de datos, la caché HTTP en navegadores y proxies seguirá sirviendo datos viejos durante 1 hora. `@lru_cache` en el proceso de Python solo se invalida al reiniciar el servidor.

**Acción requerida**:
1. Diferenciar entre:
   - **Datos estáticos de referencia** (comunas, regiones): rara vez cambian. `max-age=86400` es seguro.
   - **Datos de establecimientos**: cambian con cada ETL. Usar `ETag` basado en un hash del dataset o la fecha de última carga. El cliente envía `If-None-Match`; el servidor responde 304 si no ha cambiado.
2. Para `@lru_cache`: añadir un mecanismo de invalidación (ej. almacenar la versión del dataset en memoria y compararla antes de devolver el caché).

---

### 4.6 Astro 4 desactualizado

**Descripción**: El plan fija Astro 4. A fecha de redacción (agosto 2026), Astro 5 ya está estable. Usar una versión anterior genera deuda de actualización innecesaria.

**Acción requerida**:
1. Cambiar a Astro 5 (o la versión LTS actual al momento de implementar).
2. Verificar compatibilidad de `@astrojs/react` y el modo SSR (`output: 'server'`).
3. Documentar que el adapter de Node.js (`@astrojs/node`) es necesario para SSR en producción.

---

## 5. Issues Menores (Severidad: LOW)

> Pueden posponerse a F4 o post-MVP sin riesgo grave.

### 5.1 Documentación de arquitectura duplicada y contradictoria

- `docs/ARCHITECTURE.md` describe SQLite + aiosqlite.
- `docs/ARCHITECTURE_v2.md` describe PostgreSQL + asyncpg.

**Acción**: deprecar `ARCHITECTURE.md` (mover a `docs/archive/`) o actualizarlo para reflejar la versión vigente.

**Resuelto (2026-08-20)**: `ARCHITECTURE.md` movido a `docs/archive/ARCHITECTURE_v1.md` con banner de deprecación. `README.md` ahora enlaza a `ARCHITECTURE_v2.md`.

### 5.2 Sin métricas ni observabilidad

El plan menciona `structlog` y `correlation_id`, pero no define:
- Qué se loguea (requests, errores, performance de queries).
- Dónde se almacenan los logs (stdout es suficiente para local, pero debería documentarse).
- Métricas de negocio: tiempo de respuesta del search, tasa de errores 500, etc.

**Acción**: añadir middleware de FastAPI que loguee `method`, `path`, `status_code`, `duration_ms` y `correlation_id` en cada request.

### 5.3 Riesgos legales y éticos no documentados

El README actual menciona "revisar términos de uso de `apisae.mineduc.cl` antes de publicar". El plan v2 no aborda esto.

**Acción**:
1. Crear `docs/LEGAL.md` con:
   - Atribución requerida por MINEDUC.
   - Política de privacidad: el sitio publicará nombres de directores, teléfonos y correos de colegios públicos. Verificar si esto requiere aviso o consentimiento.
   - Descargo de responsabilidad: "Los datos provienen de fuentes públicas y pueden no estar actualizados."
2. Añadir fecha de última actualización visible en el frontend.

---

## 6. Plan de Ejecución Recomendado

> Reordenado y con estimaciones corregidas. Total: **~45-55 h**.

### F0: Fundamentos de Datos (3-4 h)

**Objetivo**: garantizar que el dataset es completo, fresco y entendido antes de escribir una línea de backend.

- [ ] Reejecutar ETL completo (`make all`) y validar `comunas_exitosas >= 300`.
- [ ] Crear `docs/DATA_DICTIONARY.md`: mapeo completo JSON origen → campo PostgreSQL.
- [ ] Definir estrategia de snapshot: versión, fecha, frecuencia de actualización.
- [ ] Documentar campos descartados (`resumenProyectoPIE`, `procesosEspeciales`, etc.) y el porqué.
- [ ] Crear `docs/DATA_LOADING.md`: estrategia staging + swap vs. versionado.

**Salida**: dataset validado, contrato de datos firme, documentación de carga.

---

### F1: Infraestructura y Persistencia (8-10 h)

**Objetivo**: base de datos reproducible, migraciones versionadas y loader atómico operativo.

- [ ] `docker-compose.yml` con PostgreSQL 15.
- [ ] `pyproject.toml` con dependencias: `fastapi`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic-settings`, `structlog`.
- [ ] Estructura de carpetas `src/{domain,application,infrastructure,api}/`.
- [ ] Alembic inicializado con `env.py` async-compatible.
- [ ] Primera migración: tablas, constraints, FKs, índices GIN + tsvector.
- [ ] `infrastructure/etl/loader.py`: carga Parquet → tablas staging (SQLAlchemy Core async, bulk insert).
- [ ] `scripts/load_to_db.py`: CLI que ejecuta loader + swap transaccional.
- [ ] `scripts/seed_demo.py`: 50 colegios determinísticos para reviewers.
- [ ] `Makefile` actualizado: `db-up`, `db-down`, `migrate`, `load-db`, `seed-demo`.

**Salida**: `make db-up && make migrate && make seed-demo` levanta la base con datos de prueba.

---

### F2: Core API (12-16 h)

**Objetivo**: API REST funcional con contratos claros, paginación, búsqueda y manejo de errores.

- [ ] Domain entities (`dataclasses` flat, cero imports de frameworks).
- [ ] Repository Protocols en `domain/repositories.py`.
- [ ] Implementaciones SQLAlchemy en `infrastructure/db/repositories.py`.
- [ ] `SearchService` (`infrastructure/search_service.py`) con `tsvector` + `ts_rank_cd`.
- [ ] Use cases: `SearchUseCase`, `FichaUseCase`, `CompareUseCase`.
- [ ] FastAPI app factory (`api/main.py`) con lifespan, CORS, middleware de logging.
- [ ] Routers: `/health`, `/stats`, `/search`, `/establecimientos`, `/compare`.
- [ ] Schemas Pydantic v2 para request/response.
- [ ] `api/exceptions.py`: handlers centralizados.
- [ ] Tests unitarios (domain + use cases con repos in-memory).
- [ ] Tests de integración (repos con PostgreSQL de test).
- [ ] Tests de API (`httpx` + `TestClient`).

**Salida**: `pytest` pasa; `make backend` levanta API en `:8000`; Swagger UI funciona.

---

### F3: Frontend (10-14 h)

**Objetivo**: sitio navegable con búsqueda, resultados y fichas.

- [ ] Setup Astro 5 + React + Tailwind.
- [ ] Layout base (`BaseLayout.astro`).
- [ ] Página home (`index.astro`) con React island `SearchBox`.
- [ ] Página de resultados con filtros y lista.
- [ ] Página de ficha (`colegio/[rbd].astro`) en SSR.
- [ ] Integración con backend (`lib/api.ts` usando `openapi-typescript`).
- [ ] Página `/acerca` (SSG estático).
- [ ] `make frontend` levanta Astro en `:4321`.

**Scope reducido (si el tiempo apremia)**:
- Mapa Leaflet y comparador avanzado se posponen a post-MVP.
- El comparador puede ser una simple tabla en la misma página de resultados.

**Salida**: sitio navegable; búsqueda funcional; fichas cargan en < 200 ms (objetivo).

---

### F4: Polish y Entrega (8-10 h)

**Objetivo**: proyecto portafolio-ready con calidad profesional.

- [ ] CI GitHub Actions: lint (ruff), type-check (mypy), tests (pytest), build frontend.
- [ ] Cache-Control + ETag en endpoints de lectura.
- [ ] `make all` end-to-end: ETL + load DB + tests.
- [ ] README arquitectónico: decisiones, diagrama de capas, cómo levantar.
- [ ] `docs/LEGAL.md` con atribución y descargo.
- [x] Deprecar `ARCHITECTURE.md` o sincronizar con v2. *(hecho: movido a `docs/archive/ARCHITECTURE_v1.md`)*
- [ ] Validación de performance: ficha SSR < 200 ms, search < 500 ms en local.

**Salida**: repo listo para clonar, levantar y revisar en < 10 minutos.

---

## 7. Checklist de Verificación Pre-Implementación

Antes de escribir código de backend o frontend, verificar:

- [ ] ETL produce dataset completo (`comunas_exitosas >= 300`).
- [ ] `docs/DATA_DICTIONARY.md` existe y cubre todos los campos del Parquet.
- [ ] `docs/DATA_LOADING.md` define staging + swap o versionado.
- [ ] `docker-compose.yml` levanta PostgreSQL en un comando.
- [ ] `pyproject.toml` incluye todas las dependencias del stack.
- [ ] La tabla de dependencias de capas está corregida (infraestructura NO importa application).
- [ ] Los endpoints tienen especificación de request/response/error documentada.
- [ ] `seed_demo.py` existe y es determinístico.
- [ ] Estrategia de caché con invalidación está definida.
- [ ] `docs/LEGAL.md` cubre atribución y privacidad.

---

## 8. Decisiones (RESUELTAS en v2 — 2026-08-20)

> Todas quedaron resueltas e incorporadas a `ARCHITECTURE_v2.md`:
> 1. Carga DB → **swap transaccional** (decisión #14 de v2).
> 2. Ficha → **backend agregador con DTO enriquecido** (#15).
> 3. Comparador → tabla comparativa en F3 (endpoint `GET /compare`).
> 4. Mapa → **FUERA de MVP** (confirmado por el usuario 2026-08-20; Leaflet e `idx_sedes_geo` eliminados de v2).
> 5. `id_mongo` → **eliminado** (#17).
> 6. Campos descartados → **documentar exclusión** (#18).

| # | Decisión | Opciones | Recomendación |
|---|----------|----------|---------------|
| 1 | Estrategia de carga DB | A) Swap transaccional, B) Versionado por fila | A para simplicidad; B si se necesita histórico. |
| 2 | Ficha: agregador vs. compositor | A) Backend devuelve todo, B) Frontend hace N requests | A con DTO enriquecido. |
| 3 | Comparador en MVP | A) Tabla comparativa simple, B) Comparador avanzado con gráficos | A en F3; B post-MVP. |
| 4 | Mapa en MVP | A) Leaflet en results, B) Solo en ficha, C) Fuera de MVP | C (fuera de MVP) para respetar las ~45 h. |
| 5 | `id_mongo` | A) Conservar, B) Eliminar | B; no aporta valor al usuario final. |
| 6 | Campos descartados (`PIE`, `especialidades`) | A) Incluir en schema, B) Documentar exclusión | B si no hay requerimiento de negocio claro. |

---

## 9. Apéndice: Comparación de Estimaciones

| Fase | Plan v2 (h) | Revisión (h) | Delta | Motivo del delta |
|------|-------------|--------------|-------|------------------|
| F0 (datos) | — | 3-4 | +4 | El plan omitió validación de dataset. |
| F1 (infra) | 8 | 8-10 | +2 | Docker, seed demo y Makefile. |
| F2 (API) | 10 | 12-16 | +4 | Contratos, tests de integración y manejo de errores. |
| F3 (frontend) | 8 | 10-14 | +4 | Integración real BE-FE y posibles ajustes de SSR. |
| F4 (polish) | 6 | 8-10 | +2 | CI, documentación legal y validación de performance. |
| **Total** | **32** | **~45-55** | **+13-23** | Datos, operabilidad y calidad no estaban contemplados. |

> Para mantenerse en ~32 h, se debe reducir el alcance: eliminar mapa, reducir comparador a tabla simple, omitir CI, y asumir que el dataset ya está validado.

---

## 10. Mejoras del Análisis Complementario

> Hallazgos adicionales identificados en una revisión cruzada del plan v2 contra el estado del repositorio. Cada item indica su severidad y, cuando corresponde, si el hallazgo ya está cubierto en este documento (ver §10.3).

### 10.1 Issues nuevos (Severidad: MEDIUM)

#### 10.1.1 `lru_cache` bloquea el event loop en código async

**Descripción**: El plan propone `@functools.lru_cache` para lookups de referencia (comunas, regiones). `lru_cache` es **síncrono**: ejecuta la función en el thread del event loop de FastAPI. Si la función cacheada realiza I/O (ej. una consulta a PostgreSQL), bloquea todas las corutinas en vuelo hasta completarse.

**Impacto**: Latencia inaceptable bajo carga concurrente. El problema no se detecta en desarrollo local con tráfico bajo.

**Acción requerida**:
1. Usar `async-lru-cache` o `cachetools` con wrapper async explícito.
2. Si el lookup es de un dataset pequeño cargado en memoria al startup, no necesita caché async — un `dict` poblado en `lifespan` es suficiente.
3. Documentar la decisión en el README arquitectónico.

**Verificación**:
- Test de carga (con `locust` o `hey`) muestra p99 < 50 ms en endpoints cacheados bajo 100 RPS concurrentes.

#### 10.1.2 Tabla `imagenes` sin estrategia de almacenamiento

**Descripción**: El DDL define `imagenes(nombre, principal)` pero no especifica **dónde vive el archivo** ni cómo se sirve. Sin columna `path`, `url` o `storage_key`, el frontend no puede renderizar imágenes.

**Acción requerida**:
1. Agregar columna `url TEXT NOT NULL` (o `storage_key TEXT NOT NULL` + base URL configurable).
2. Decidir almacenamiento:
   - **Filesystem local** + endpoint FastAPI con `StaticFiles` (cache headers largos).
   - **S3 / Cloudflare R2** + URL prefirmada o proxy reverso.
3. Documentar la decisión en `docs/STORAGE.md`.

**Verificación**:
- La ficha de un colegio renderiza sus imágenes reales sin error 404.

#### 10.1.3 Denormalización en `sedes` sin estrategia de sincronización

**Descripción**: El DDL almacena `region TEXT` y `comuna TEXT` en la tabla `sedes` además de los FKs `codigo_region` y `codigo_comuna`. No hay mecanismo documentado que mantenga estos campos sincronizados ante cambios en `regiones` o `comunas`.

**Impacto**: Conflicto silencioso entre FK y texto denormalizado. Bug visible en el frontend cuando una comuna es renombrada (ej. cambio político-administrativo).

**Acción requerida**:
1. Documentar que `sedes.region/comuna` son **snapshots del ETL** y se sobreescriten en cada recarga.
2. Si se requiere consistencia fuerte: eliminar las columnas denormalizadas y resolver con `JOIN` en la query (costo: +1 join por sede).
3. Alternativa intermedia: trigger `BEFORE INSERT/UPDATE` que copie el nombre desde `regiones`/`comunas`. Mantiene sincronía sin JOIN.

**Verificación**:
- Caso de prueba explícito: cambiar el nombre de una comuna en `comunas` y verificar si `sedes.comuna` se actualiza o queda desincronizado.

#### 10.1.4 Ambigüedad entre `init_db.py` y Alembic

**Descripción**: El plan menciona ambos scripts: `init_db.py` para "crear DB PostgreSQL" y "Alembic init + primera migración". Las responsabilidades se solapan si no se delimitan.

**Acción requerida**:
1. Definir claramente la separación:
   - **`init_db.py`**: crea el **clúster/base de datos** y el rol. Idempotente. No toca schema.
   - **Alembic**: gestiona el **schema** (tablas, índices, constraints, FKs). Aplica migraciones incrementales.
2. Orden documentado en el Makefile:
   ```
   make db-up      → contenedor PostgreSQL arriba
   make init-db    → init_db.py (crea DB + rol)
   make migrate    → alembic upgrade head
   make load-db    → loader.py (Parquet → staging → swap)
   make seed-demo  → 50 colegios demo (opcional)
   ```
3. `init_db.py` se ejecuta una vez por entorno; `alembic upgrade head` se ejecuta cada vez que hay una migración nueva.

**Verificación**:
- Borrar la base de datos y ejecutar `make all` desde cero produce un entorno funcional sin pasos manuales.

#### 10.1.5 `habilitado_vitrina` — feature flag mal nombrado

**Descripción**: La columna `habilitado_vitrina BOOLEAN` aparece en `establecimientos` sin justificación clara. Si es un feature flag del sistema, pertenece a configuración, no al modelo de dominio. Si representa "este colegio quiere aparecer público", el nombre induce a error (¿vitrina de qué? ¿quién lo habilita?).

**Acción requerida**:
1. Renombrar a `publicado` o `visible_publico` (semántica explícita).
2. Documentar quién lo controla:
   - ¿El colegio lo solicita?
   - ¿El operador del sitio lo activa?
   - ¿Es derivado de otro campo (ej. `habilitado_postular`)?
3. Si termina siendo solo un filtro "mostrar/ocultar", considerar moverlo a una capa de presentación (endpoint de admin o filtro a nivel de query) en lugar del schema.

**Verificación**:
- El nombre del campo refleja su semántica sin necesidad de leer el código.

### 10.2 Issues nuevos (Severidad: LOW)

#### 10.2.1 CI hook de `openapi-typescript` no especificado

**Descripción**: `ARCHITECTURE_v2.md` (sección 8) lista como riesgo "openapi-typescript desincronizado" pero el plan no define el script concreto. Este review tampoco lo aborda explícitamente.

**Acción requerida**:
1. Crear script `scripts/check_openapi_types.sh` (o `.ts`):
   - Genera tipos desde `/openapi.json` con `openapi-typescript`.
   - Compara contra `frontend/src/lib/types.ts` commiteado.
   - Si difieren, exit 1.
2. Integrar como paso de CI antes de `frontend build`.
3. Opcional: ejecutar el mismo script en pre-commit para devs locales.

**Verificación**:
- Cambiar manualmente un DTO de la API y commitear → CI falla con mensaje claro.
- Regenerar tipos con `make generate-types` y commitear → CI pasa.

#### 10.2.2 `regimen` sin CHECK constraint

**Descripción**: La columna `regimen TEXT` acepta cualquier string. Los valores conocidos del dataset son `JEC`, `JECD`, `TRICEL`, etc.

**Acción requerida**:
1. Agregar `CHECK (regimen IN ('JEC', 'JECD', 'TRICEL', ...))` con los valores observados en el Parquet.
2. Documentar valores válidos en `DATA_DICTIONARY.md`.
3. Si hay un valor nuevo en el dataset, el CHECK falla en el loader → problema visible y no data sucia silenciosa.

**Verificación**:
- `INSERT INTO establecimientos (regimen) VALUES ('INVALIDO')` retorna error de constraint.

#### 10.2.3 Indicadores: 4 campos con semántica similar

**Descripción**: La tabla `indicadores` tiene `titulo_indicador`, `nivel_indicador`, `descripcion_indicador` y `nombre_indicador`. La diferencia entre `titulo` y `nombre` no es obvia sin mapear contra el JSON de MINEDUC. Tres de los cuatro podrían ser redundantes o casi siempre nulos.

**Acción requerida**:
1. Auditar el JSON de origen para entender qué representa cada campo.
2. Si 3 de los 4 son siempre nulos o redundantes, consolidar (ej. mover a `metadata JSONB`).
3. Documentar en `DATA_DICTIONARY.md` con un ejemplo real por campo.

**Verificación**:
- Cada campo de `indicadores` tiene descripción de negocio en el data dictionary.

#### 10.2.4 `structlog` + `correlation_id` sin estrategia de propagación async

**Descripción**: El stack menciona `structlog` y `correlation_id`, pero no define cómo se propaga el ID a través del stack async (FastAPI → use case → SQLAlchemy/asyncpg → response).

**Impacto**: Logs no correlacionables entre request, query SQL y respuesta. Debugging post-mortem imposible.

**Acción requerida**:
1. Usar `contextvars.ContextVar` para el `correlation_id`.
2. Middleware ASGI que genera/asigna el ID y lo inyecta en `contextvars`.
3. Hook SQLAlchemy `before_cursor_execute` que añade el ID como comentario SQL (`/* correlation_id=abc */`) — los logs de `asyncpg` lo capturarán.
4. Response header `X-Correlation-Id` para que el cliente pueda reportar bugs.

**Verificación**:
- Hacer una request y verificar que el log de la query SQL contiene el mismo `correlation_id` que el log de la request.

#### 10.2.5 `seed_demo.py` sin estrategia de generación

**Descripción**: `ARCHITECTURE_v2.md` dice "50 colegios demo determinísticos" pero no especifica cómo se generan ni de dónde sale el shape.

**Acción requerida**:
1. Definir el método:
   - **Faker con factories** (`factory-boy`) — flexible pero menos realista.
   - **Plantillas hardcoded** — más realista pero menos varied.
   - **Subset real del Parquet anonimizado** — más realista aún, pero requiere anonimización.
2. Garantizar determinismo: `random.seed(42)` (o equivalente) para reproducibilidad.
3. Cubrir diversidad: público, particular subvencionado, particular pagado, distintos regimenes, distintos niveles.

**Verificación**:
- Dos ejecuciones consecutivas de `seed_demo.py` producen exactamente la misma base de datos (bytewise).

#### 10.2.6 Auth/authorization no documentado

**Descripción**: El plan describe una API pública read-only sin mencionar explícitamente la ausencia de auth. Un reviewer podría asumir que falta y preguntar "¿dónde está el login?".

**Acción requerida**:
1. Documentar en el README: "API pública sin autenticación por diseño. Dataset proviene de fuente pública (MINEDUC)."
2. Si en el futuro se exponen endpoints de admin (recargar ETL, etc.), dejar claro que requerirán auth (API keys o similar).
3. Considerar rate limiting básico (`slowapi`) para evitar abuso del endpoint de búsqueda.

**Verificación**:
- README contiene una sección "Seguridad y autenticación" que explica la decisión.

### 10.3 Hallazgos ya cubiertos en este documento

> Estas mejoras del análisis complementario fueron identificadas pero ya se encuentran planteadas en el cuerpo del documento. Se listan aquí para evitar duplicación.

| # | Mejora del análisis | Sección equivalente | Notas |
|---|---------------------|---------------------|-------|
| 1 | GIN index en `etiquetas TEXT[]` | §4.1 | **Mismo hallazgo** — cubierto tal cual. |
| 2 | F3 (frontend) estimación optimista (8h) | §9 | **Mismo hallazgo** — delta +4h ya justificado por "Integración real BE-FE y posibles ajustes de SSR". |
| 3 | F4 (polish) estimación optimista (6h) | §9 | **Mismo hallazgo** — delta +2-4h ya justificado por "CI, documentación legal y validación de performance". |
| 4 | Estrategia de paginación `limit/offset` | §4.3 | **Mismo hallazgo parcial** — §4.3 pregunta por límites pero no sugiere cursor-based. Considerar añadir: "Para portafolio, cursor-based (más impresionante narrativamente) si el tiempo lo permite." |
| 5 | `structlog` + `correlation_id` (brecha de observabilidad) | §5.2 | **Mismo hallazgo parcial** — §5.2 menciona gap de observabilidad pero no aborda propagación async. Ver §10.2.4 para detalle de propagación. |
| 6 | Esquema de `imagenes` incompleto (sin `url`/`path` ni estrategia de almacenamiento) | §10.1.2 | **Mismo hallazgo** — cubierto en §10.1.2 con la misma observación y acción requerida. |
| 7 | Hook de CI para `openapi-typescript` desincronizado | §10.2.1 | **Mismo hallazgo** — cubierto en §10.2.1 con script concreto y verificación. |

---

## 10.4 Mejoras adicionales del análisis complementario (no cubiertas)

> Hallazgos del análisis cruzado que **no aparecen** en las secciones anteriores de este documento.

### 10.4.1 `cursos` con ~30 campos nullable genera payloads sparse

**Severidad**: MEDIUM

**Descripción**: La tabla `cursos` tiene aproximadamente 30 campos, muchos de ellos nullable según el modelo Pydantic (`src/transform/models.py`). Si el endpoint `/api/v1/cursos?rbd=` devuelve el modelo ORM tal cual, el JSON resultante será extremadamente sparse (muchos `null`), lo cual aumenta el tamaño de payload y dificulta el consumo en el frontend.

**Acción requerida**:
1. En los DTOs Pydantic de salida para cursos, usar `exclude_none=True` o definir un schema que agrupe campos relacionados (ej. `vacantes: {rango_inferior, rango_superior}`).
2. Documentar en `DATA_DICTIONARY.md` qué campos son críticos (siempre presentes) vs. opcionales.
3. Considerar un endpoint de resumen (`/api/v1/cursos/resumen?rbd=`) que devuelva solo los campos esenciales para la ficha, dejando el endpoint completo para el comparador avanzado.

**Verificación**:
- El payload de `/cursos` para un RBD típico no excede los 20 KB.

---

### 10.4.2 Índice geoespacial sin endpoints de proximidad

**Severidad**: MEDIUM

**Descripción**: El DDL define `idx_sedes_geo(latitud, longitud)` pero el endpoint `/api/v1/search` no expone parámetros de proximidad (`lat`, `lon`, `radius_km`). El índice B-tree en `(lat, lon)` solo permite ordenar por coordenadas, no filtrar por distancia real (radio de búsqueda).

**Impacto**: El mapa Leaflet puede mostrar marcadores, pero no hay forma de buscar "colegios dentro de 2 km de mi ubicación".

**Acción requerida**:
1. Agregar parámetros opcionales `lat`, `lon`, `radius_km` al endpoint `/api/v1/search`.
2. Implementar filtro de distancia con fórmula Haversine en SQL (suficiente para <10k registros) o evaluar PostGIS (`GEOGRAPHY` + índice GiST) si el MVP incluye búsqueda por proximidad.
3. Si la búsqueda por proximidad queda fuera de alcance, documentar explícitamente que `idx_sedes_geo` está reservado para ordenamiento y futuras expansiones.

**Resuelto (2026-08-20)**: opción 3 aplicada. Mapa fuera de alcance MVP; `idx_sedes_geo` eliminado del DDL de `ARCHITECTURE_v2.md`.

**Verificación**:
- `GET /api/v1/search?lat=-33.45&lon=-70.66&radius_km=2` retorna solo colegios dentro del radio.

---

### 10.4.3 `GET /compare` vulnerable a límite de URL

**Severidad**: LOW

**Descripción**: El endpoint `GET /api/v1/compare?rbds=1,2,3` es idempotente y cacheable, pero la especificación HTTP recomienda URLs menores a ~2000 caracteres. Si un usuario compara 10+ colegios, la query string puede exceder ese límite (error 414 URI Too Long en algunos proxies/servidores).

**Acción requerida**:
1. Documentar explícitamente el límite máximo de RBDs (recomendado: 5-10).
2. Validar en el endpoint: si `len(rbds) > max_compare`, retornar `400 Bad Request` con mensaje claro.
3. Si en el futuro se soportan comparaciones masivas, migrar a `POST /compare` con body JSON.

**Verificación**:
- `GET /compare?rbds=1,2,3,4,5,6,7,8,9,10,11,12` retorna `400` con mensaje "Máximo 10 colegios por comparación".

---

### 10.4.4 Graceful degradation ante datos faltantes del ETL

**Severidad**: MEDIUM

**Descripción**: El plan no define el comportamiento de la API cuando un colegio existe pero carece de sub-recursos (indicadores SIMCE, actividades, imágenes). Un `404 Not Found` en `/api/v1/indicadores?rbd=12345` cuando el colegio sí existe pero no tiene indicadores es confuso para el frontend.

**Acción requerida**:
1. Los endpoints de sub-recursos (`/sedes`, `/cursos`, `/indicadores`, `/actividades`, `/imagenes`) deben retornar `200 OK` con array vacío `[]` o objeto vacío `{}` cuando no hay datos, en lugar de `404`.
2. `404` debe reservarse para cuando el `rbd` no existe en `establecimientos`.
3. Documentar esta convención en `docs/API_CONVENTIONS.md`.

**Verificación**:
- `GET /api/v1/indicadores?rbd=<rbd_sin_simce>` retorna `200` con `[]`.
- `GET /api/v1/indicadores?rbd=<rbd_inexistente>` retorna `404`.

---

### 10.4.5 Rate limiting como hardening básico del endpoint público

**Severidad**: MEDIUM

**Descripción**: Aunque el plan asume tráfico bajo, un endpoint público como `GET /api/v1/search?q=a` sin rate limiting es vulnerable a scraping y abuso. Esto puede agotar conexiones de PostgreSQL o saturar el event loop de FastAPI.

**Acción requerida**:
1. Agregar rate limiting básico con `slowapi` (limitador basado en Redis o en memoria):
   - `/search`: 30 req/min por IP.
   - `/establecimientos/{rbd}`: 60 req/min por IP.
   - Endpoints de sub-recursos: 60 req/min por IP.
2. Incluir headers `X-RateLimit-Limit` y `X-RateLimit-Remaining` en las respuestas.
3. Documentar en el README que el rate limiting es "defensa en profundidad" para un dataset público.

**Verificación**:
- Ejecutar 100 requests concurrentes a `/search` desde la misma IP; después del límite, recibir `429 Too Many Requests`.

---

## 11. Mejoras del segundo análisis (integración ETL ↔ plan v2)

> Hallazgos de una segunda revisión cruzada, enfocada en la **integración entre el ETL existente y el plan v2**. Verificada contra los Parquet reales en `data/processed/latest/` (2026-08-02). Cada item indica su severidad y, cuando corresponde, si ya está cubierto en este documento (ver §11.2).

### 11.1 Issues nuevos (Severidad: HIGH)

#### 11.1.1 `regiones` y `comunas` no tienen fuente en el ETL

**Descripción**: El DDL del plan v2 define las tablas de referencia `regiones` y `comunas` con FKs desde `sedes`, pero el ETL produce **solo 6 Parquet** (establecimientos, sedes, cursos, actividades, indicadores, imagenes). No existe archivo fuente para las tablas de referencia.

**Impacto**: La primera carga (`load_to_db.py`) falla: `sedes.codigo_comuna REFERENCES comunas(codigo)` no puede satisfacerse si `comunas` está vacía.

**Acción requerida**:
1. El loader debe **derivar** las tablas de referencia desde `sedes.parquet` con `SELECT DISTINCT` sobre `(codigo_region, region)` y `(codigo_comuna, comuna, codigo_region)`.
2. Cargarlas **antes** que `sedes` (orden de inserción por FK).
3. Documentar esta derivación en `docs/DATA_LOADING.md`.

**Verificación**:
- `make load-db` desde base vacía termina sin errores de FK.
- `SELECT count(*) FROM comunas` retorna 346 (o el total de comunas del dataset completo).

#### 11.1.2 `etiquetas` llega como String, no como lista

**Descripción**: En `establecimientos.parquet`, la columna `etiquetas` es de tipo **String** (ej. `'PIE,SEP,GRATUITO'`), no una lista. El DDL del plan declara `etiquetas TEXT[]` y el tsvector generado usa `array_to_string(etiquetas, ' ')`, que **requiere** un array.

**Impacto**: La carga de `establecimientos` se rompe o el tsvector genera resultados incorrectos (toda la cadena como un solo lexema).

**Acción requerida**:
1. En `infrastructure/etl/loader.py`, transformar cada valor al cargar: `etiquetas.split(',') if etiquetas else []` (o `string_to_array(etiquetas, ',')` en SQL).
2. Añadir un check de validación post-carga: `SELECT count(*) FROM establecimientos WHERE array_length(etiquetas, 1) IS NULL AND etiquetas IS NOT NULL` → debe ser 0 para los casos con contenido.

**Verificación**:
- `SELECT etiquetas FROM establecimientos LIMIT 5` retorna arrays (`{PIE,SEP,GRATUITO}`), no strings.
- Búsqueda por etiqueta (`@> ARRAY['PIE']`) retorna resultados.

### 11.2 Issues nuevos (Severidad: MEDIUM)

#### 11.2.1 Colisión de nombres: `src/api/` ya existe como cliente HTTP

**Descripción**: El árbol de directorios del plan v2 asume que el cliente HTTP del MINEDUC vive en `src/api_client/`, pero en el repositorio actual se llama **`src/api/`** (`client.py`, `rate_limiter.py`). La capa FastAPI del plan también se llamaría `src/api/`.

**Impacto**: Confusión de capas y riesgo de imports incorrectos si ambas conviven. Un reviewer del portafolio vería "api" conteniendo un rate limiter del scraper y routers REST mezclados.

**Acción requerida**:
1. Renombrar `src/api/` → `src/api_client/` **antes** de crear la capa FastAPI (refactor mecánico: actualizar imports en `src/api_client/client.py` y en los tests que lo referencian).
2. Ejecutar `pytest` post-renombre para confirmar cero regresiones.

**Verificación**:
- `ls src/` muestra `api_client/` (ETL) y `api/` (FastAPI), sin ambigüedad.
- `pytest tests/test_api_client.py` pasa.

#### 11.2.2 FTS sin manejo de tildes (`unaccent`)

**Descripción**: `to_tsvector('spanish', ...)` **no** matchea consultas sin tilde contra contenido con tilde: buscar "aleman" no encuentra "Colegio Alemán", buscar "tecnico" no encuentra "Técnico". Los usuarios chilenos frecuentemente escriben sin tildes. §4.4 cubre ranking, prefijo y fuzzy, pero no este caso.

**Impacto**: El bug de búsqueda más visible y reportable por usuarios. Afecta directamente la experiencia central del producto.

**Acción requerida**:
1. `CREATE EXTENSION IF NOT EXISTS unaccent;`
2. Crear una configuración de búsqueda custom que combine `spanish` + `unaccent` (diccionario custom en la primera migración Alembic).
3. Usar esa configuración tanto en la columna generada `busqueda_tsvector` como en `to_tsquery`/`websearch_to_tsquery` del `SearchService`.
4. Añadir tests de integración: "aleman" debe encontrar "Alemán".

**Verificación**:
- `GET /api/v1/search?q=aleman` retorna colegios con "Alemán" en el nombre.

#### 11.2.3 Semántica del filtro `nivel=` indefinida

**Descripción**: El endpoint `/search` acepta `nivel=` pero el schema no define qué significa: ¿match exacto contra `nivel_minimo`/`nivel_maximo`? ¿Coincidencia contra `glosa_nivel` en `cursos`? `nivel_minimo` y `nivel_maximo` son TEXT sin orden documentado.

**Impacto**: Implementación ambigua; resultados inconsistentes entre backend y expectativa del frontend. Complementa las preguntas abiertas de §4.3.

**Acción requerida**:
1. Definir semántica explícita (recomendado): el colegio matchea si `nivel ∈ [nivel_minimo .. nivel_maximo]` según un mapa de orden documentado (ej. `PARVULARIO=0, BASICA=1, MEDIA=2, ...`).
2. Documentar el mapa de orden en `DATA_DICTIONARY.md` y en el DTO del endpoint.
3. Test de API: filtrar `nivel=MEDIA` retorna colegios cuyo rango incluye media, aunque su `nivel_minimo` sea `BASICA`.

**Verificación**:
- `GET /api/v1/search?nivel=MEDIA` retorna solo colegios con media en su rango.

#### 11.2.4 Filtro `copago_max` puede duplicar RBGs en resultados

**Descripción**: `copago_valor` vive en la tabla `cursos` (un colegio tiene N cursos). Si el `SearchService` hace JOIN con `cursos` para filtrar por `copago_max`, un colegio con 3 cursos bajo el máximo aparece 3 veces en los resultados y el `total` queda inflado.

**Impacto**: Resultados duplicados y conteo incorrecto — bug visible inmediatamente en el frontend.

**Acción requerida**:
1. Implementar el filtro como subconsulta `EXISTS (SELECT 1 FROM cursos WHERE cursos.rbd = establecimientos.rbd AND copago_valor <= :copago_max)`.
2. Test de integración con un colegio demo que tenga múltiples cursos bajo el umbral: debe aparecer exactamente una vez.

**Verificación**:
- `SELECT count(*) FROM (SELECT DISTINCT rbd FROM resultados_search)` == `total` del response.

#### 11.2.5 CI sin service container de PostgreSQL

**Descripción**: §4.2 y F1 cubren Docker para entorno local, y F4 lista "CI GitHub Actions" sin detalle. Los tests de integración (§F2: "repos con PostgreSQL test DB") requieren una instancia real de PostgreSQL en CI, que GitHub Actions no provee por defecto.

**Impacto**: CI en rojo desde el primer día de F2, o peor: tests de integración silenciosamente omitidos en CI.

**Acción requerida**:
1. En `.github/workflows/ci.yml`, agregar:
   ```yaml
   services:
     postgres:
       image: postgres:15-alpine
       env:
         POSTGRES_USER: colegios
         POSTGRES_PASSWORD: colegios
         POSTGRES_DB: colegios_test
       ports: ["5432:5432"]
       options: >-
         --health-cmd pg_isready --health-interval 10s
         --health-timeout 5s --health-retries 5
   ```
2. Ejecutar `alembic upgrade head` + `seed_demo.py` antes de `pytest` en CI.
3. Variable `DATABASE_URL_TEST` en los secrets/vars del workflow.

**Verificación**:
- Un PR que rompa una query SQL falla en CI, no solo en local.

### 11.3 Issues nuevos (Severidad: LOW)

#### 11.3.1 Columna `distancia` en Parquet no contemplada en el DDL

**Descripción**: `establecimientos.parquet` contiene la columna `distancia`, un artefacto del scrapeo por comuna (distancia al centroide de la comuna consultada). El DDL del plan no la incluye.

**Acción requerida**: El loader debe excluirla explícitamente (columna allowlist o drop previo), y documentar la exclusión en `DATA_DICTIONARY.md` junto con los campos descartados de §4.1.

**Verificación**:
- `\d establecimientos` en psql no muestra columna `distancia`.

#### 11.3.2 `src/config.py` y `src/logging.py` listados como existentes

**Descripción**: El árbol de directorios del plan v2 (sección 5) muestra `src/config.py` (pydantic-settings) y `src/logging.py` (structlog) bajo "ETL existente", pero **no existen** en el repositorio. La configuración actual del ETL vive en `config/` (directorio) y `.env`.

**Acción requerida**:
1. Incluir su creación en F1 (no asumir que ya están).
2. Evaluar consolidar `config/` actual dentro de `src/config.py` para una única fuente de verdad.

**Verificación**:
- `src/config.py` existe, carga `DATABASE_URL` desde `.env`, y `make backend` lo utiliza.

#### 11.3.3 `app.py`: prototipo Streamlit huérfano

**Descripción**: `app.py` (201 líneas) es un dashboard Streamlit+Plotly que lee los Parquet directamente, anterior a la arquitectura v2. Tiene un bug runtime: usa la variable `color_map` (líneas 137 y 166) que **nunca se define** (`NameError` al graficar). Además, sus dependencias (`streamlit`, `plotly`, `pandas`) no están en `requirements.txt`. Queda superseded por F3 (mapa → Leaflet, tabla → search + fichas SSR).

**Acción requerida**:
1. Eliminar `app.py` (no hay referencias en el Makefile ni tests).
2. Rescatar una idea: el scatter "SIMCE Lenguaje vs Matemática por dependencia" es valioso y no está en el plan del frontend — agregarlo como nice-to-have en la ficha o comparador (post-MVP).

**Verificación**:
- `grep -r "app.py" Makefile scripts/ tests/` no retorna referencias.

### 11.4 Hallazgos ya cubiertos en este documento

> Mejoras del segundo análisis que ya se encuentran planteadas en secciones anteriores. Se listan para evitar duplicación.

| # | Mejora del segundo análisis | Sección equivalente | Notas |
|---|-----------------------------|---------------------|-------|
| 1 | Eliminar/cuestionar `idx_sedes_geo` (B-tree no geoespacial) | §4.1 + §10.4.2 | **Mismo hallazgo** — §4.1 lo marca como subóptimo y §10.4.2 analiza el gap de proximidad y las opciones (Haversine/PostGIS o eliminación). |
| 2 | Makefile: redefinir `make all` + targets nuevos (`backend`, `frontend`, `db-up`, etc.) | §4.2 (acción 5) + §10.1.4 | **Mismo hallazgo** — la redefinición de `make all` (hoy `discover etl transform validate`, mañana ETL + carga PG) queda implícita en los flows de Makefile documentados. Añadir nota: actualizar el `help` del Makefile en F1. |
| 3 | Deprecar `docs/ARCHITECTURE.md` v1 (dos versiones contradictorias) | §5.1 | **Mismo hallazgo** — cubierto tal cual (mover a `docs/archive/` o actualizar). |
| 4 | Migrar deps de `requirements.txt` a `[project]` en `pyproject.toml` | §2.1 + F1 | **Mismo hallazgo parcial** — §2.1 observa que `pyproject.toml` solo tiene config de pytest y F1 lista las deps a incluir, pero no decide explícitamente entre migrar `[project]` vs. mantener `requirements.txt`. **Recomendación**: migrar a `[project]` (con `pip install -e .`), dejando `requirements.txt` como thin alias para no romper los targets existentes del Makefile. |

---

*Documento generado: 2026-08-20 (actualizado con segundo análisis de integración ETL ↔ plan v2)*
*Basado en: `docs/ARCHITECTURE_v2.md`, estado real del repositorio al 2026-08-20 (Parquet verificados en `data/processed/latest/`)*
