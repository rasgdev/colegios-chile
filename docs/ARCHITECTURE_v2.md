# Buscador de Colegios de Chile — Arquitectura Final v2.0

> Plan consolidado post-evaluación (5 iteraciones). Optimizado para impacto social + valor de portafolio profesional.

---

## 1. Resumen Ejecutivo

**Objetivo**: Buscador web para familias chilenas que consume datos públicos del MINEDUC.

**Filosofía**: Arquitectura enterprise-grade justificada para portafolio, sin over-engineering por vanidad. Cada capa de abstracción tiene una razón de ser defendible en entrevista técnica.

**Horas estimadas**: ~45-55h (5 fases: F0–F4).

---

## 2. Decisiones Arquitectónicas Clave

### 2.1 Patrón: Clean Architecture (pragmática)

| Capa | Responsabilidad | Regla de dependencia |
|---|---|---|
| **domain** | Entidades flat (`dataclasses` stdlib), contratos de repositorio (`Protocol`) | Cero imports de frameworks |
| **application** | Casos de uso (`search`, `compare`, `ficha`) | Solo importa `domain` |
| **infrastructure** | SQLAlchemy ORM, repositorios, `SearchService` (FTS), loader ETL | Solo importa `domain` (implementa Protocols definidos ahí) |
| **api** | FastAPI routers, Pydantic DTOs, deps, errores | Importa `application`, `infrastructure` |

**Justificación para portafolio**: "Separé el dominio para que sea testeable sin base de datos. Usé dataclasses en vez de Pydantic en domain para mantenerlo framework-free. Las entidades son flat porque es un catálogo, no un dominio con reglas de negocio complejas."

> **Nota**: El wiring de dependencias (inyección) ocurre en `src/api/deps.py` o `src/api/composition.py`, que es la única capa que importa `application` e `infrastructure`.

### 2.2 Base de datos: PostgreSQL 15+

**Justificación**: "PostgreSQL me da FTS nativo (`tsvector`), arrays (`TEXT[]`), y async real con `asyncpg`. SQLite con `aiosqlite` es un wrapper sobre threads, no verdadero async."

### 2.3 Full-Text Search: `tsvector` + GIN index

Implementado en `infrastructure/search_service.py` con SQL crudo.

**Justificación**: "FTS es inherentemente acoplado al motor de búsqueda. Un Repository genérico sería una falsa abstracción. Si migráramos a Elasticsearch, cambiaríamos el `SearchService`, no todo el repositorio."

### 2.4 Frontend: Astro 5 + React islands

- **SSR** para fichas de colegio (`/colegio/[rbd].astro`).
- **React islands** para búsqueda interactiva.
- **SSG** solo para páginas estáticas (`/acerca`).
- **`@astrojs/node`** requerido para SSR en producción.

**Justificación**: "Evalué SSG vs SSR. SSG de 7,673 páginas requeriría rebuilds masivos. SSR nos da SEO igual de bueno sin ese costo operacional. Astro islands minimiza JS enviado al cliente. Astro 5 es la versión LTS actual."

### 2.5 Caching: HTTP ETag + memoización en lifespan

- **Datos de referencia estáticos** (comunas, regiones): `Cache-Control: public, max-age=86400`. Poblados en `lifespan` de FastAPI (dict en memoria; no `@lru_cache` que bloquea el event loop async).
- **Datos de establecimientos**: `ETag` basado en hash del dataset o fecha de última carga. Cliente envía `If-None-Match`; servidor responde 304 si no ha cambiado.
- **App-level**: `dataset_version` en memoria para comparar antes de devolver caché.

**Justificación**: "`@lru_cache` bloquea el event loop en async. `Cache-Control: max-age=3600` sirve datos viejos tras ETL. ETag permite invalidación instantánea cuando cambia el dataset."

> **Nota**: `/search` y `/compare` (consultas con filtros) no se cachean a nivel HTTP; son consultas específicas. El ETag aplica solo a recursos estables (`/establecimientos/{rbd}`, sedes, cursos, indicadores).

---

## 3. Stack Tecnológico Final

| Capa | Tecnología | Justificación |
|---|---|---|
| DB | PostgreSQL 15+ | FTS nativo, arrays, async real |
| Driver | `asyncpg` | Async nativo, más rápido que psycopg async |
| ORM | SQLAlchemy 2.0 async | Estándar, type-safe |
| Migraciones | Alembic | Versionado de schema |
| Backend | FastAPI 0.110+ | Async, OpenAPI, Pydantic nativo |
| DTOs / validación | Pydantic v2 | API layer únicamente |
| Frontend | Astro 5 (LTS) | SSR + islands; `@astrojs/node` para SSR en producción |
| HTTP cliente FE | TanStack Query | Cache, retries, suspense |
| Tipos FE↔BE | `openapi-typescript` | Genera TS desde OpenAPI |
| Caching | HTTP ETag + lifespan dict | Sin infra extra; invalidación instantánea post-ETL |
| Logging | structlog | JSON estructurado con correlation_id |
| Tests BE | pytest + pytest-asyncio + httpx | Testing pyramid |
| Tests FE | Vitest + Playwright | E2E opcional |
| Linting | ruff + mypy + ESLint | Modern stack |
| CI | GitHub Actions | Tests + lint + type-check |

---

## 4. Modelo Relacional (PostgreSQL)

```sql
-- ── Tablas de referencia ──
CREATE TABLE regiones (
    codigo INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE
);

CREATE TABLE comunas (
    codigo INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    codigo_region INTEGER NOT NULL REFERENCES regiones(codigo),
    UNIQUE(nombre, codigo_region)
);
CREATE INDEX idx_comunas_region ON comunas(codigo_region);

-- ── Establecimientos ──
CREATE TABLE establecimientos (
    rbd INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    dependencia TEXT NOT NULL,
    telefono TEXT, mail TEXT, url TEXT,
    habilitado_postular BOOLEAN NOT NULL DEFAULT TRUE,
    publicado BOOLEAN NOT NULL DEFAULT FALSE,
    nivel_minimo TEXT, nivel_maximo TEXT,
    director TEXT,
    etiquetas TEXT[],                       -- ARRAY nativo PostgreSQL; Parquet=string CSV, loader hace split(',')
    resumen_proyecto TEXT,
    documento_proyecto TEXT, documento_reglamento TEXT,
    internado BOOLEAN NOT NULL DEFAULT FALSE,
    integracion BOOLEAN NOT NULL DEFAULT FALSE,
    subvencion_preferencial BOOLEAN NOT NULL DEFAULT FALSE,
    peib BOOLEAN NOT NULL DEFAULT FALSE,
    politica_uniforme TEXT, orientacion_religiosa TEXT,
    alumnos_matriculados INTEGER,
    promedio_alumnos_por_curso FLOAT,
    cantidad_docentes INTEGER,
    regimen TEXT,
    busqueda_tsvector tsvector GENERATED ALWAYS AS (
        to_tsvector('spanish_unaccent',
            coalesce(nombre, '') || ' ' ||
            coalesce(resumen_proyecto, '') || ' ' ||
            coalesce(array_to_string(etiquetas, ' '), '')
        )
    ) STORED
);
CREATE INDEX idx_est_dep ON establecimientos(dependencia);
CREATE INDEX idx_est_regimen ON establecimientos(regimen);
CREATE INDEX idx_est_nivel_max ON establecimientos(nivel_maximo);
CREATE INDEX idx_est_fts ON establecimientos USING GIN(busqueda_tsvector);
CREATE INDEX idx_est_etiquetas ON establecimientos USING GIN(etiquetas);

-- ── Sedes ──
CREATE TABLE sedes (
    rbd INTEGER NOT NULL REFERENCES establecimientos(rbd) ON DELETE CASCADE,
    codigo_sede INTEGER NOT NULL,               -- ordinal de sede por colegio (1–4); NO es único globalmente
    codigo_region INTEGER NOT NULL,
    codigo_comuna INTEGER NOT NULL REFERENCES comunas(codigo),
    region TEXT NOT NULL, comuna TEXT NOT NULL,  -- denormalizado intencional; snapshots del ETL, se sobreescriben en cada recarga
    calle TEXT,
    latitud FLOAT, longitud FLOAT,
    PRIMARY KEY (rbd, codigo_sede)
);
CREATE INDEX idx_sedes_comuna ON sedes(codigo_comuna);

-- ── Cursos ──
CREATE TABLE cursos (
    rbd INTEGER NOT NULL REFERENCES establecimientos(rbd) ON DELETE CASCADE,
    codigo_curso INTEGER NOT NULL,              -- código de nivel/curso; se repite entre colegios, NO es único globalmente
    codigo_sede INTEGER NOT NULL,               -- FK compuesta hacia sedes(rbd, codigo_sede)
    glosa_grupo_ensenanza TEXT, glosa_ensenanza TEXT,
    glosa_nivel TEXT, etiqueta_nivel TEXT, sexo TEXT,
    glosa_jornada TEXT, glosa_especialidad TEXT, glosa_grupo_pago TEXT,
    codigo_ensenanza INTEGER, codigo_nivel INTEGER,
    codigo_jornada INTEGER, codigo_sexo INTEGER, codigo_especialidad INTEGER,
    unico_comuna BOOLEAN,
    proporcion_excelencia_transicion FLOAT,
    proporcion_excelencia_regimen FLOAT,
    proporcion_especializacion_temprana FLOAT,
    copago_cuotas INTEGER, copago_valor INTEGER,
    cupos_totales INTEGER,
    vacantes_rango_inferior INTEGER, vacantes_rango_superior INTEGER,
    porcentaje_cambio_inferior FLOAT, porcentaje_cambio_superior FLOAT,
    repitentes_anio_actual INTEGER, repitentes_nivel_anterior INTEGER,
    pre_inscritos_anio_siguiente INTEGER,
    cambios_inferior INTEGER, cambios_superior INTEGER,
    pre_vacantes_inferior INTEGER, pre_vacantes_superior INTEGER,
    rango INTEGER,
    postulantes_anio_anterior INTEGER,
    movimiento_lista_espera_anterior INTEGER,
    PRIMARY KEY (rbd, codigo_curso),
    FOREIGN KEY (rbd, codigo_sede) REFERENCES sedes(rbd, codigo_sede)
);
CREATE INDEX idx_cursos_copago ON cursos(copago_valor);

-- ── Indicadores (EAV — set dinámico) ──
CREATE TABLE indicadores (
    id SERIAL PRIMARY KEY,
    rbd INTEGER NOT NULL REFERENCES establecimientos(rbd) ON DELETE CASCADE,
    tipo_indicador TEXT NOT NULL,
    titulo_indicador TEXT, nivel_indicador TEXT,
    descripcion_indicador TEXT,
    nombre_indicador TEXT NOT NULL,
    puntaje FLOAT,
    comparacion_gse_numero INTEGER,
    comparacion_gse_glosa TEXT
);
CREATE INDEX idx_ind_rbd ON indicadores(rbd);
CREATE INDEX idx_ind_tipo ON indicadores(tipo_indicador);

-- ── Actividades ──
CREATE TABLE actividades (
    id SERIAL PRIMARY KEY,
    rbd INTEGER NOT NULL REFERENCES establecimientos(rbd) ON DELETE CASCADE,
    tipo TEXT, nombre TEXT NOT NULL,
    nivel TEXT, exigencia TEXT
);
CREATE INDEX idx_act_rbd ON actividades(rbd);

-- ── Imágenes ──
CREATE TABLE imagenes (
    id SERIAL PRIMARY KEY,
    rbd INTEGER NOT NULL REFERENCES establecimientos(rbd) ON DELETE CASCADE,
    nombre TEXT,
    url TEXT,                               -- MVP: filesystem local + StaticFiles; futuro: S3/R2
    principal BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_img_rbd ON imagenes(rbd);
```

> **Nota**: Los siguientes campos del modelo Pydantic se documentan como **excluidos del schema PostgreSQL**:
> - `resumenProyectoPIE`, `procesosEspeciales`, `especialidades` (no aportan valor al buscador público)
> - `distancia` (artefacto del scrapeo)
> - `id_mongo` (artefacto del scrapeo)

---

## 5. Estructura de Directorios

```
colegios-chile/
├── etl/                              # Pipeline de ingestión (scraper → Parquet)
│   ├── api_client/
│   │   ├── client.py                 # HTTP client MINEDUC + retry/rate-limit
│   │   └── rate_limiter.py
│   ├── extract/
│   │   ├── comunas.py
│   │   └── detalle.py
│   ├── transform/
│   │   ├── models.py                 # Pydantic models
│   │   └── normalizers.py            # JSON → DataFrames Polars
│   ├── load/
│   │   └── parquet.py                # Escritura Parquet + symlink latest/
│   ├── validation/
│   │   └── duckdb_checks.py          # Integridad referencial (DuckDB)
│   └── state.py                      # Checkpointing reanudable
├── src/                              # Aplicación web (Clean Architecture)
│   ├── domain/
│   │   ├── entities.py               # dataclasses flat
│   │   └── repositories.py           # Protocols (async)
│   ├── application/
│   │   ├── search.py                 # SearchUseCase
│   │   ├── compare.py                # CompareUseCase
│   │   └── ficha.py                  # FichaUseCase
│   ├── infrastructure/
│   │   ├── db/
│   │   │   ├── session.py            # async engine + AsyncSession
│   │   │   ├── orm.py                # SQLAlchemy declarative models
│   │   │   └── repositories.py       # Implementaciones de Protocols
│   │   ├── search_service.py         # FTS con tsvector (SQL crudo)
│   │   └── loader.py                 # Parquet → PostgreSQL (SQLAlchemy Core async)
│   └── api/                          # FastAPI app (nueva capa)
│       ├── main.py                   # FastAPI app factory + lifespan + CORS
│       ├── deps.py                   # get_db, get_repo, get_search_service
│       ├── exceptions.py             # Handlers centralizados
│       ├── schemas/                  # Pydantic DTOs (input/output)
│       └── routers/
│           ├── meta.py               # /health, /stats
│           ├── establecimientos.py
│           ├── search.py
│           └── compare.py
├── config/                           # Compartido (pipeline + app)
│   ├── settings.py                   # pydantic-settings (fuente única de verdad)
│   └── logging.py                    # structlog config
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── index.astro           # Home + búsqueda (SSR con islands)
│   │   │   ├── colegio/[rbd].astro   # Ficha (SSR)
│   │   │   ├── comparar.astro        # Comparador (islands)
│   │   │   └── acerca.astro          # SSG estático
│   │   ├── components/               # React islands
│   │   ├── layouts/BaseLayout.astro
│   │   └── lib/
│   │       ├── api.ts
│   │       └── types.ts              # openapi-typescript
│   └── ...
├── alembic/
│   ├── versions/
│   ├── env.py                        # async-compatible
│   └── script.py.mako
├── scripts/
│   ├── discover_comunas.py
│   ├── run_etl.py
│   ├── init_db.py                    # Crea DB PostgreSQL
│   ├── seed_demo.py                  # Demo data para portafolio (F2)
│   ├── load_to_db.py                 # Parquet → PostgreSQL
│   └── validate_api.py
├── tests/
│   ├── unit/                         # domain (in-memory repos)
│   ├── integration/                  # repos con PostgreSQL test DB
│   └── api/                          # TestClient async
├── data/
│   ├── raw/
│   └── processed/latest/*.parquet
├── docs/
│   └── ARCHITECTURE_v2.md
├── pyproject.toml
├── Makefile
└── README.md
```

---

## 6. API Endpoints (Definitivos)

```
GET    /api/v1/health                      # Health check
GET    /api/v1/stats                       # Stats globales

# Búsqueda principal
GET    /api/v1/search?q=&comuna=&dependencia=&regimen=
                                          &nivel=&copago_max=&etiquetas=
                                          &limit=20&offset=0
                                          Response: { results: [...], total, limit, offset }

# Recursos
GET    /api/v1/establecimientos            # List paginado con filtros
GET    /api/v1/establecimientos/{rbd}      # Ficha completa con sub-recursos
GET    /api/v1/sedes?rbd=                  # Sedes por RBD
GET    /api/v1/cursos?rbd=                 # Cursos por RBD (completo)
GET    /api/v1/cursos/resumen?rbd=          # Resumen de cursos (campos esenciales, payload <20KB)
GET    /api/v1/indicadores?rbd=            # SIMCE y otros por RBD
GET    /api/v1/actividades?rbd=            # Extraprogramáticas por RBD
GET    /api/v1/imagenes?rbd=               # Imágenes por RBD

# Comparación
GET    /api/v1/compare?rbds=1,2,3         # Máximo 10 RBDs. Response: { establecimientos, indicadores, cursos_resumen }

# Documentación
GET    /docs                              # Swagger UI
GET    /redoc                             # ReDoc
GET    /openapi.json                      # OpenAPI spec
```

---

## 7. Plan de Ejecución por Fases (~45–55h)

| Fase | Nombre | Tareas | Salida | Horas |
|---|---|---|---|---|
| **F0** | Fundamentos de Datos | Reejecutar ETL completo; validar dataset (≥300 comunas); crear `docs/KNOWN_ISSUES.md`; renombrar `src/api/` → `src/api_client/`; corregir `etiquetas` string→array | Dataset completo + estructura limpia | 3–4 |
| **F1** | Infraestructura y Persistencia | `pyproject.toml` deps; estructura `src/{domain,application,infrastructure,api}/`; PostgreSQL + Docker; Alembic init; migración inicial (CREATE EXTENSION unaccent + text search config `spanish_unaccent` + tablas + tsvector + GIN + constraints); loader atómico (staging + swap); derivar `regiones`/`comunas` desde `sedes` | Backend base funcional con datos cargados | 8–10 |
| **F2** | Core API | Domain entities (dataclasses flat); Repositories (Protocols + SQLAlchemy impl); `SearchService` (tsvector + unaccent); Use cases (`search`, `compare`, `ficha`); FastAPI routers (`/api/v1/`); Pydantic DTOs; rate limiting (`slowapi`); `seed_demo.py` | API REST completa con demo data | 12–16 |
| **F3** | Frontend | Astro 5 setup; React islands (`SearchBox`, `Filters`, `ResultsList`); SSR fichas (`/colegio/[rbd]`); Comparador; `openapi-typescript` | Sitio navegable con BE integrado | 10–14 |
| **F4** | Polish y Entrega | Tests unit + integration + API; HTTP caching ETag; ruff + mypy + ESLint; GitHub Actions CI (con service container PostgreSQL); README arquitectónico; `make all` end-to-end; documentación legal | Proyecto portafolio-ready | 8–10 |
| **Total** | | | | **~45–55 h** |

---

## 8. Riesgos y Mitigaciones

| Riesgo | Mitigación |
|---|---|
| PostgreSQL requiere servicio | `init_db.py` verifica conexión; README documenta setup |
| `tsvector` en español | Extensión `unaccent` + configuración `spanish_unaccent`; probar búsqueda sin tilde |
| SSR de Astro requiere Node server | Documentado en README; SSG fallback para `/acerca` |
| openapi-typescript desincronizado | CI hook que falle si `types.ts` está outdated |
| Acoplamiento domain ↔ SQLAlchemy | Tests unitarios de domain SIN imports de `infrastructure/` |
| Build de portafolio sin datos MINEDUC | `seed_demo.py` crea 50 colegios demo para reviewers |
| Dataset incompleto (ETL falla en comunas) | `docs/KNOWN_ISSUES.md` documenta comunas problemáticas; `report.json` valida cobertura |
| Carga no atómica corrompe DB | Loader usa staging + swap transaccional; reejecución idempotente |
| Colisión de nombres `src/api/` | Renombrar scraper a `src/api_client/` antes de crear FastAPI |

---

## 9. Checklist de Verificación Final

- [ ] `make all` corre ETL completo + carga PostgreSQL
- [ ] `pytest` pasa (unit + integration + API)
- [ ] `make backend` levanta FastAPI en `:8000`
- [ ] `make frontend` levanta Astro en `:4321`
- [ ] Buscador combina filtros + full-text con conteo de resultados
- [ ] Ficha SSR carga en `< 200ms`
- [ ] Comparador soporta 1-10 colegios
- [ ] README explica arquitectura, decisiones y cómo levantar
- [ ] CI en GitHub Actions pasa tests + lint

---

## Decisiones Consolidadas

| # | Decisión | Justificación |
|---|---|---|
| 1 | Domain flat (`dataclasses` stdlib, sin anidación) | Catálogo read-only, no dominio rico |
| 2 | Search endpoint separado (`/api/v1/search`) | FTS es caso de uso diferente a listado |
| 3 | Indicadores EAV (dinámicos) | Set de indicadores puede variar |
| 4 | PostgreSQL 15+ como DB | FTS nativo, arrays, async real |
| 5 | Compare como `GET /api/v1/compare?rbds=1,2,3` | Idempotente, cacheable |
| 6 | SQLAlchemy 2.0 async + `asyncpg` | Async nativo, estándar |
| 7 | FTS con `tsvector` + GIN index | Nativo PostgreSQL, no falsa abstracción |
| 8 | Loader con SQLAlchemy Core async (bulk insert) | Performance, no pasa por domain |
| 9 | Astro SSR (no SSG masivo) para fichas | Evita rebuilds, mantiene SEO |
| 10 | React islands para búsqueda/interactividad | Mínimo JS enviado |
| 11 | `TEXT[]` para `etiquetas` (array nativo) | PostgreSQL nativo, búsquedas exactas |
| 12 | HTTP ETag + lifespan dict | Sin Redis; invalidación instantánea post-ETL |
| 13 | `seed_demo.py` para portafolio | Reviewers pueden levantar sin ETL |
| 14 | Carga DB: swap transaccional (staging + TRUNCATE/INSERT) | Atómico, simple, sin downtime de lectura significativo |
| 15 | Ficha completa: backend agregador con DTO enriquecido | Una sola request vs. N requests; mejor UX |
| 16 | Mapa (Leaflet) fuera de alcance MVP | Índice geoespacial reservado para post-MVP; sin dependencia de tiles/servicios geo |
| 17 | Eliminar `id_mongo` del schema | Artefacto del scrapeo, no aporta valor al buscador |
| 18 | Excluir `resumenProyectoPIE`, `procesosEspeciales`, `especialidades` | Campos no críticos para el buscador público |
| 19 | Payload sparse: endpoint `/cursos/resumen` | Reduce payload de ~30 campos nullable a <10 esenciales |
| 20 | Renombrar `habilitado_vitrina` → `publicado` | Semántica explícita; default FALSE |
| 21 | `etiquetas`: Parquet=string CSV, loader hace `split(',')` | Compatibilidad con DDL `TEXT[]` |
| 22 | `regiones`/`comunas` derivadas desde `sedes.parquet` | No requieren fuente separada; verificado 344 comunas / 16 regiones (cubre 344/346; las 2 faltantes no tienen colegios) |
| 23 | Separar pipeline ETL (`etl/`) de la app (`src/`) | Dos entregables distintos (dataset builder vs web service); evita `api`/`api_client` y `load`/`loader` ambiguos |
| 24 | Config compartida en `config/` neutral (no dentro de `src/`) | El ETL y la app comparten `.env`; ninguno es dueño del otro (regla de dependencia entre paquetes) |

---

Guardado: 2026-08-20
Sesión: Planificación arquitectónica (5 iteraciones)
Estado: APROBADO — Listo para implementación
