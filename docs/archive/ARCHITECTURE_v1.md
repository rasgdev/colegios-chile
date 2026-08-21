# Buscador de Colegios de Chile — Arquitectura (v1)

> **DEPRECADO — SUPERSEDED por [ARCHITECTURE_v2.md](../ARCHITECTURE_v2.md).**
> Este documento describe la versión v1 (SQLite + FTS5 + Astro 4). La versión
> vigente usa PostgreSQL + tsvector + Astro 5. Conservado solo como referencia
> histórica; no implementar a partir de este documento.

> Documento de arquitectura y plan de ejecución. Define cómo evolucionar el
> pipeline ETL actual hacia un servicio consultable por la comunidad, con
> separación clara entre dominio, persistencia, API y frontend.

---

## 1. Contexto y objetivos

### Estado actual

| Aspecto | Valor |
|---|---|
| Pipeline ETL | Operativo (`make all` → Parquet en `data/processed/latest/`) |
| Visualización | `app.py` (Streamlit) lee Parquet directamente |
| Datos | 7,673 establecimientos · 7,912 sedes · 77,540 cursos · ~500K filas |
| Volumen | < 100 MB en Parquet |
| Perfil de uso | 99% lectura (catálogo), 1% escritura (snapshot ETL) |

### Objetivo

Construir un **buscador de colegios para familias chilenas** con:

1. Persistencia en base de datos relacional (no Parquet para servir).
2. API HTTP tipada y documentada.
3. Frontend público moderno, con SEO y mínimo JavaScript.
4. Arquitectura con buenas prácticas, justificada para un mini proyecto pero
   profesional.

### Fuera de alcance (explícito)

- Deploy público en cloud (esta fase es local).
- Autenticación, roles, tracking.
- Histórico / series temporales (requeriría snapshots versionados).
- Notificaciones, bots, app móvil nativa.
- Versionado de API más allá de `/api/v1`.

---

## 2. Decisiones arquitectónicas

### 2.1 Patrón: Clean Architecture (4 capas)

| Capa | Responsabilidad | Dependencias |
|---|---|---|
| **domain** | Entidades de negocio, value objects, contratos de repositorio (Protocols) | Ninguna (Pydantic puro) |
| **application** | Casos de uso (search, compare, ficha) | domain |
| **infrastructure** | Adaptadores: SQLAlchemy, sesión DB, loader Parquet → SQLite | domain, application |
| **api** | FastAPI: routers, schemas DTO, deps, manejo de errores | application, infrastructure (para wiring) |

**Justificación**: el costo marginal es bajo (los modelos Pydantic ya existen
en `src/transform/models.py` y se mueven a `domain/`). El dominio queda
100% testeable sin DB ni FastAPI, los repositorios se mockean con Protocols,
y si mañana hay deploy o cambio de DB, el núcleo no se toca.

### 2.2 Base de datos: SQLite

| Criterio | SQLite | PostgreSQL |
|---|---|---|
| Tamaño del dataset | ✅ Perfecto | ✅ Sobra |
| Ops / instalación | ✅ Cero (archivo) | ❌ Requiere servicio |
| Concurrencia lectura | ✅ Excelente (WAL) | ✅ Excelente |
| Concurrencia escritura | ⚠️ 1 writer (suficiente para ETL) | ✅ Ilimitada |
| Full-text search | ⚠️ FTS5 disponible | ✅ Más maduro |
| Migración futura | 🆗 `sqlite→postgres` factible | ✅ Nativo |

**Decisión**: SQLite. Justifica el caso (read-heavy, snapshot ocasional,
mini proyecto). Migración a Postgres directa si crece (mismos modelos
SQLAlchemy).

### 2.3 ORM y migraciones

- **SQLAlchemy 2.0 async** + **aiosqlite**: estándar de la industria Python,
  async nativo, type hints.
- **Alembic**: migraciones versionadas desde el inicio para no acumular
  deuda técnica.

### 2.4 Backend: FastAPI

- Async nativo, Pydantic v2 nativo.
- OpenAPI auto-generado (`/docs`, `/redoc`, `/openapi.json`).
- Dependency injection built-in (`Depends`).
- Ecosistema amplio (`slowapi` para rate limiting opcional).

### 2.5 Frontend: Astro 4 + React islands

| Opción | SEO | Bundle | Veredicto |
|---|---|---|---|
| **Astro + React islands** | ✅ SSG/SSR | < 100 KB | ✅ Elegido |
| Next.js 14 | ✅ | Medio | Overkill |
| Vite + React SPA | ❌ | Pequeño | Pierde SEO |
| Streamlit (actual) | ❌ | Grande | No es web moderna |

**Justificación**: el sitio es contenido estático + consultas (perfecto para
Astro). SSR/SSG da SEO excelente (Google indexa cada ficha). Islands
architecture minimiza JS: solo donde hay interactividad (mapa, filtros).

### 2.6 Tipos compartidos frontend ↔ backend

`openapi-typescript` genera tipos TypeScript desde `/openapi.json` de
FastAPI → cero desalineación FE/BE. Hook de CI falla si `types.ts`
está desactualizado.

---

## 3. Modelo relacional (SQLite)

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

-- ── Establecimientos (tabla principal) ──
CREATE TABLE establecimientos (
    rbd INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    dependencia TEXT NOT NULL,
    telefono TEXT, mail TEXT, url TEXT,
    habilitado_postular BOOLEAN NOT NULL DEFAULT 1,
    habilitado_vitrina   BOOLEAN NOT NULL DEFAULT 0,
    nivel_minimo TEXT, nivel_maximo TEXT,
    director TEXT,
    etiquetas TEXT,                       -- CSV: "PIE,SEP,GRATUITO"
    resumen_proyecto TEXT,                -- PEI completo (FTS5)
    documento_proyecto TEXT, documento_reglamento TEXT,
    internado BOOLEAN NOT NULL DEFAULT 0,
    integracion BOOLEAN NOT NULL DEFAULT 0,
    subvencion_preferencial BOOLEAN NOT NULL DEFAULT 0,
    peib BOOLEAN NOT NULL DEFAULT 0,
    politica_uniforme TEXT, orientacion_religiosa TEXT,
    alumnos_matriculados INTEGER,
    promedio_alumnos_por_curso REAL,
    cantidad_docentes INTEGER,
    regimen TEXT,                         -- Mixto, Mujeres, Hombres
    id_mongo TEXT
);
CREATE INDEX idx_est_dep       ON establecimientos(dependencia);
CREATE INDEX idx_est_regimen   ON establecimientos(regimen);
CREATE INDEX idx_est_nivel_max ON establecimientos(nivel_maximo);

-- Búsqueda full-text en PEI
CREATE VIRTUAL TABLE establecimientos_fts USING fts5(
    nombre, resumen_proyecto, etiquetas,
    content='establecimientos',
    content_rowid='rbd'
);

-- ── Sedes (con geo) ──
CREATE TABLE sedes (
    codigo_sede INTEGER PRIMARY KEY,
    rbd INTEGER NOT NULL REFERENCES establecimientos(rbd) ON DELETE CASCADE,
    codigo_region INTEGER NOT NULL,
    codigo_comuna INTEGER NOT NULL REFERENCES comunas(codigo),
    region TEXT NOT NULL, comuna TEXT NOT NULL,
    calle TEXT,
    latitud REAL, longitud REAL
);
CREATE INDEX idx_sedes_rbd    ON sedes(rbd);
CREATE INDEX idx_sedes_comuna ON sedes(codigo_comuna);
CREATE INDEX idx_sedes_geo    ON sedes(latitud, longitud);

-- ── Cursos ──
CREATE TABLE cursos (
    codigo_curso INTEGER PRIMARY KEY,
    rbd INTEGER NOT NULL REFERENCES establecimientos(rbd) ON DELETE CASCADE,
    codigo_sede INTEGER REFERENCES sedes(codigo_sede),
    glosa_grupo_ensenanza TEXT, glosa_ensenanza TEXT,
    glosa_nivel TEXT, etiqueta_nivel TEXT, sexo TEXT,
    glosa_jornada TEXT, glosa_especialidad TEXT, glosa_grupo_pago TEXT,
    codigo_ensenanza INTEGER, codigo_nivel INTEGER,
    codigo_jornada INTEGER, codigo_sexo INTEGER, codigo_especialidad INTEGER,
    unico_comuna BOOLEAN,
    proporcion_excelencia_transicion REAL,
    proporcion_excelencia_regimen REAL,
    proporcion_especializacion_temprana REAL,
    copago_cuotas INTEGER, copago_valor INTEGER,
    cupos_totales INTEGER,
    vacantes_rango_inferior INTEGER, vacantes_rango_superior INTEGER,
    porcentaje_cambio_inferior REAL, porcentaje_cambio_superior REAL,
    repitentes_anio_actual INTEGER, repitentes_nivel_anterior INTEGER,
    pre_inscritos_anio_siguiente INTEGER,
    cambios_inferior INTEGER, cambios_superior INTEGER,
    pre_vacantes_inferior INTEGER, pre_vacantes_superior INTEGER,
    rango INTEGER,
    postulantes_anio_anterior INTEGER,
    movimiento_lista_espera_anterior INTEGER
);
CREATE INDEX idx_cursos_rbd    ON cursos(rbd);
CREATE INDEX idx_cursos_sede   ON cursos(codigo_sede);
CREATE INDEX idx_cursos_copago ON cursos(copago_valor);

-- ── Indicadores (SIMCE + Desarrollo Personal) ──
CREATE TABLE indicadores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rbd INTEGER NOT NULL REFERENCES establecimientos(rbd) ON DELETE CASCADE,
    tipo_indicador TEXT NOT NULL,         -- SIMCE, DESARROLLO_PERSONAL
    titulo_indicador TEXT, nivel_indicador TEXT,
    descripcion_indicador TEXT,
    nombre_indicador TEXT NOT NULL,       -- Lenguaje, Matemática, Autoestima...
    puntaje REAL,
    comparacion_gse_numero INTEGER,
    comparacion_gse_glosa TEXT
);
CREATE INDEX idx_ind_rbd  ON indicadores(rbd);
CREATE INDEX idx_ind_tipo ON indicadores(tipo_indicador);

-- ── Actividades extraprogramáticas ──
CREATE TABLE actividades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rbd INTEGER NOT NULL REFERENCES establecimientos(rbd) ON DELETE CASCADE,
    tipo TEXT, nombre TEXT NOT NULL,
    nivel TEXT, exigencia TEXT
);
CREATE INDEX idx_act_rbd ON actividades(rbd);

-- ── Imágenes de infraestructura ──
CREATE TABLE imagenes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rbd INTEGER NOT NULL REFERENCES establecimientos(rbd) ON DELETE CASCADE,
    nombre TEXT,                          -- URL
    principal BOOLEAN NOT NULL DEFAULT 0
);
CREATE INDEX idx_img_rbd ON imagenes(rbd);
```

---

## 4. Estructura de directorios

```
colegios-chile/
├── src/
│   ├── domain/                          # Pydantic entities + Protocols
│   │   ├── entities.py
│   │   ├── value_objects.py
│   │   └── repositories.py
│   ├── application/                     # Use cases
│   │   ├── search.py
│   │   ├── compare.py
│   │   └── ficha.py
│   ├── infrastructure/
│   │   ├── db/
│   │   │   ├── session.py               # async engine + get_session
│   │   │   ├── orm.py                   # SQLAlchemy models
│   │   │   ├── mappers.py               # ORM ↔ Domain
│   │   │   └── repositories.py          # Impl de Protocols
│   │   └── etl/
│   │       └── loader.py                # Parquet → SQLite bulk insert
│   ├── api/                             # FastAPI
│   │   ├── main.py                      # app factory + lifespan + CORS
│   │   ├── deps.py                      # get_db, get_repo
│   │   ├── exceptions.py                # handlers centralizados
│   │   ├── schemas/                     # Pydantic DTOs
│   │   └── routers/
│   │       ├── meta.py                  # /health, /stats
│   │       ├── establecimientos.py
│   │       ├── sedes.py
│   │       ├── cursos.py
│   │       ├── indicadores.py
│   │       ├── actividades.py
│   │       ├── imagenes.py
│   │       └── search.py
│   ├── extract/                         # ETL existente (se conserva)
│   ├── api_client/                      # HTTP client (movido desde src/api/)
│   ├── validation/
│   ├── state.py
│   ├── config.py                        # movido desde config/
│   └── logging.py                       # movido desde config/
├── frontend/                            # Astro project
│   ├── src/
│   │   ├── pages/
│   │   │   ├── index.astro              # Home + búsqueda
│   │   │   ├── colegio/[rbd].astro      # Ficha (SSG/SSR)
│   │   │   ├── comparar.astro
│   │   │   └── acerca.astro
│   │   ├── components/                  # React islands
│   │   │   ├── SearchBox.tsx
│   │   │   ├── Filters.tsx
│   │   │   ├── MapView.tsx              # Leaflet
│   │   │   ├── ResultsList.tsx
│   │   │   ├── Ficha.tsx
│   │   │   └── Compare.tsx
│   │   ├── layouts/BaseLayout.astro
│   │   └── lib/
│   │       ├── api.ts                   # fetch a FastAPI
│   │       └── types.ts                 # openapi-typescript output
│   ├── astro.config.mjs
│   ├── package.json
│   └── tsconfig.json
├── alembic/                             # Migraciones
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── alembic.ini
├── scripts/
│   ├── discover_comunas.py              # existente
│   ├── run_etl.py                       # existente
│   ├── load_to_db.py                    # NUEVO: Parquet → SQLite
│   └── validate_api.py                  # NUEVO: httpx contra FastAPI
├── tests/
│   ├── unit/                            # domain + application
│   ├── integration/                     # repos con SQLite in-memory
│   └── api/                             # TestClient + httpx
├── data/
│   ├── raw/
│   ├── processed/latest/*.parquet
│   └── colegios.db                      # SQLite
├── docs/
│   └── ARCHITECTURE.md                  # este archivo
├── pyproject.toml
├── package.json                         # Frontend deps (root)
├── Makefile
└── README.md
```

---

## 5. API Endpoints

```
GET    /api/health                       # Health check
GET    /api/stats                        # Stats globales

# Búsqueda principal
GET    /api/search                       # ?comuna=&dependencia=&regimen=
                                         #   &nivel=&copago_max=&etiquetas=&q
                                         # Response: { results: [...], total: int }

# Recursos
GET    /api/establecimientos             # List paginado con filtros
GET    /api/establecimientos/{rbd}       # Ficha completa con sub-recursos
GET    /api/sedes?rbd=                   # Sedes por RBD
GET    /api/cursos?rbd=                  # Cursos por RBD
GET    /api/indicadores?rbd=             # SIMCE y otros por RBD
GET    /api/actividades?rbd=             # Extraprogramáticas por RBD
GET    /api/imagenes?rbd=                # Imágenes por RBD

# Comparación
POST   /api/compare                      # Body: { rbds: [int, int, int] }
                                         # Response: { info, simce, cursos, ... }

# Documentación
GET    /docs                             # Swagger UI
GET    /redoc                            # ReDoc
GET    /openapi.json                     # OpenAPI spec
```

---

## 6. Flujo end-to-end: búsqueda de colegios

```
[Usuario en /index.astro]
        │
        ▼
[SearchBox.tsx] ──HTTP──▶ GET /api/search?comuna=Maipú&nivel=Pre-Kinder&copago_max=50000
                                │
                                ▼
                       [api/routers/search.py]
                                │
                                ▼
                       [api/deps.py] → get_repo(EstablecimientoRepo)
                                │
                                ▼
                [application/search.py] SearchEstablecimientos.execute(filtros)
                                │
                                ▼
       [infrastructure/db/repositories.py] SQLAlchemyRepo.search()
                                │
                                ▼
   SELECT e.*, MIN(c.copago_valor) AS copago_min
   FROM establecimientos e
   LEFT JOIN cursos c ON c.rbd = e.rbd
   WHERE e.rbd IN (SELECT rbd FROM sedes WHERE comuna = ?)
     AND e.nivel_minimo <= ? AND e.nivel_maximo >= ?
     AND c.copago_valor <= ?
   GROUP BY e.rbd
                                │
                                ▼
                       [mappers.py] ORM rows → Establecimiento entities
                                │
                                ▼
                  [schemas/search.py] entities → SearchResultDTO
                                │
                                ▼
[Response JSON] ──HTTP──▶ [SearchBox.tsx] actualiza UI
```

---

## 7. Stack tecnológico

| Capa | Tecnología | Justificación |
|---|---|---|
| DB | SQLite 3.45+ | Read-heavy, file-based, sin ops |
| ORM | SQLAlchemy 2.0 async | Estándar, maduro, type-safe |
| Driver | aiosqlite | Async driver para SQLite |
| Migraciones | Alembic | Versionado de schema |
| Backend | FastAPI 0.110+ | Async, OpenAPI, Pydantic nativo |
| DTOs / validación | Pydantic v2 | Single source of truth |
| Frontend | Astro 4 | SSR/SSG + islands, SEO, bundle mínimo |
| HTTP cliente FE | TanStack Query | Cache, retries, suspense |
| Mapa | Leaflet + react-leaflet | Open source, sin API key |
| Tipos FE↔BE | openapi-typescript | Genera TS desde OpenAPI |
| Logging | structlog | JSON estructurado con correlation_id |
| Tests BE | pytest + httpx | Estandar |
| Tests FE | Vitest + Playwright | E2E opcional |
| Linting | ruff + mypy + ESLint | Modern stack |
| CI | GitHub Actions | Tests + lint |

---

## 8. Buenas prácticas aplicadas

| Práctica | Implementación |
|---|---|
| 12-factor app | Config por env vars (pydantic-settings) |
| Domain-Driven Design lite | Modelos de dominio separados del ORM |
| Repository pattern | `Protocol` en domain, impl SQLAlchemy en infra |
| Dependency Injection | FastAPI `Depends` |
| API Versioning | `/api/v1/...` desde el inicio |
| Pagination | `limit/offset` + header `X-Total-Count` |
| Error handling | Custom exceptions + handlers centralizados |
| Logging | structlog con `correlation_id` por request |
| Type safety FE↔BE | OpenAPI → TypeScript automático |
| Testing pyramid | Unit (domain) + Integration (repos) + E2E (api) |
| Idempotencia del loader | `INSERT OR REPLACE` o `TRUNCATE+INSERT` |
| Schema versioning | Alembic migrations versionadas |
| CORS | Whitelist explícito de origins |
| Health check | `/api/health` para monitoring |
| OpenAPI docs | `/docs` y `/redoc` automáticos |

---

## 9. Plan de ejecución por fases

| Fase | Tareas | Salida | Horas |
|---|---|---|---|
| **F1** Setup | pyproject.toml con deps; crear estructura `src/{domain,application,infrastructure,api}/`; mover `config/` → `src/config.py` y `src/logging.py` | Estructura base | 2 |
| **F2** Domain | Mover `src/transform/models.py` → `src/domain/entities.py`; crear `value_objects.py` y `repositories.py` con Protocols | Dominio testeable | 3 |
| **F3** ORM + DB | `infrastructure/db/orm.py`, `session.py`, `mappers.py`, `repositories.py` | Capa DB lista | 4 |
| **F4** Alembic | `alembic init`, primera migración creando 8 tablas + FTS5 + índices | DB schema versionado | 2 |
| **F5** Loader | `infrastructure/etl/loader.py`: Parquet → ORM → bulk insert idempotente; `scripts/load_to_db.py` CLI | DB poblada | 2 |
| **F6** Application | `application/search.py`, `compare.py`, `ficha.py` | Use cases | 4 |
| **F7** FastAPI | `api/main.py`, `deps.py`, `exceptions.py`, `schemas/*`, `routers/*`; tests con TestClient + httpx | API funcional | 6 |
| **F8** Astro setup | Crear `frontend/` con `npm create astro`; integrar Tailwind; SSR mode | Frontend base | 2 |
| **F9** Componentes | `SearchBox`, `Filters`, `ResultsList`, `MapView` (Leaflet), `Ficha`, `Compare`; generar types con openapi-typescript | UI completa | 8 |
| **F10** Páginas | `index.astro`, `colegio/[rbd].astro`, `comparar.astro`, `acerca.astro` | Sitio navegable | 4 |
| **F11** Integración | CORS, smoke test full-stack (`make all` end-to-end), README con instrucciones | MVP funcional | 2 |
| **F12** Pulido | Tests unit + integration + API; ruff + mypy + ESLint; CI hook | Listo para entregar | 3 |
| **Total** | | | **~40 h** |

---

## 10. Comandos locales

```bash
# Backend
cd colegios-chile
uv sync                                       # o pip install -r requirements.txt
python scripts/run_etl.py                    # ETL → Parquet
python scripts/load_to_db.py                 # Parquet → SQLite
alembic upgrade head                         # Aplicar migraciones
uvicorn src.api.main:app --reload            # FastAPI en :8000

# Frontend (otra terminal)
cd frontend
npm install
npm run dev                                   # Astro en :4321

# Validación end-to-end
python scripts/validate_api.py               # httpx contra FastAPI
```

### Makefile ampliado

```makefile
backend:        ## Run FastAPI dev server
	uvicorn src.api.main:app --reload --port 8000

frontend:       ## Run Astro dev server
	cd frontend && npm run dev

all: discover etl transform load-db migrate    ## Full pipeline (ETL + DB)

load-db:        ## Load Parquet → SQLite
	python scripts/load_to_db.py

migrate:        ## Apply Alembic migrations
	alembic upgrade head

backend-test:   ## Run backend tests
	pytest tests/unit tests/integration tests/api -v

frontend-test:  ## Run frontend tests
	cd frontend && npm run test

dev:            ## Run both servers (requires 2 terminals)
	@echo "Backend: make backend"
	@echo "Frontend: make frontend"
```

---

## 11. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| SQLite no soporta escrituras concurrentes | Loader usa WAL + checkpoint; API solo lee |
| FTS5 no es estándar en Postgres | Aceptable para SQLite; documentado en migración |
| Astro SSR requiere Node server | Documentado en README; alternativa SSG posible |
| openapi-typescript puede desincronizarse | CI hook que falle si `types.ts` está desactualizado |
| Tamaño del bundle Leaflet | Importar solo `leaflet` core + plugins necesarios |
| Acoplamiento accidental domain ↔ SQLAlchemy | Tests unitarios del domain SIN imports de `infrastructure/` |
| Migración futura a Postgres | Usar solo features SQL estándar + SQLAlchemy portable |

---

## 12. Decisiones de privacidad

- **Mostrar todos los datos** del director, mail y teléfono públicos, tal como
  provienen de MINEDUC.
- **Disclaimer visible** en `pages/acerca.astro`: "Los datos provienen de la
  API pública del MINEDUC. Esta es una herramienta no oficial, sin
  affiliation con MINEDUC."
- **No hay login, tracking ni cookies** en esta fase.

---

## 13. Limitaciones conocidas (a comunicar en UI)

- **TREHUACO** (Región de Ñuble): no tiene establecimientos en SAE. Comuna
  rural de ~5,000 habitantes.
- **ANTARTICA**: aceptada por la API pero devuelve 0 RBDs.
- 2 registros con valores nulos en campos clave (0.01% del total),
  provenientes de la API.
- El dataset representa una **instantánea**. La fecha del snapshot debe
  mostrarse en el footer del sitio.

---

## 14. Próximos pasos

1. Salir de plan mode y ejecutar **F1 → F12** en orden.
2. Después de cada fase: `pytest tests/` (unit + integration + api) y
   smoke test manual.
3. Verificación final:
   - [ ] Las páginas Astro cargan sin error
   - [ ] Filtros del buscador combinables con conteo de resultados
   - [ ] Mapa Leaflet renderiza colegios filtrados con clustering
   - [ ] Ficha muestra todos los tabs (o mensaje claro si no hay datos)
   - [ ] Comparador soporta 1, 2 y 3 colegios y exporta CSV
   - [ ] `pytest` pasa todos los tests
   - [ ] README documenta `uvicorn` + `npm run dev`