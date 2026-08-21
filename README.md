# Colegios de Chile — Buscador

Dataset de establecimientos educacionales de Chile extraído desde la API pública del MINEDUC (SAE). Pipeline ETL a Parquet + persistencia PostgreSQL para un buscador público.

**7,673 colegios · 344 comunas · 16 regiones · 3 tipos de dependencia**

> 📐 **Arquitectura**: ver [docs/ARCHITECTURE_v2.md](docs/ARCHITECTURE_v2.md) para el plan completo
> (PostgreSQL + FastAPI + Astro). Estado: F0 ✅ · F1 ✅ · F2 ✅ · F3 ✅ · F4 pendiente.

## Quick Start

```bash
# 1. Instalar dependencias
make install

# 2. Levantar PostgreSQL (Podman) y cargar el dataset
make db-up init-db migrate load-db
```

El ETL produce 6 Parquet (`make all` ejecuta `discover → etl → transform → validate → db-up → init-db → migrate → load-db`). Para más detalle: `make help`.

## Persistencia (PostgreSQL)

```bash
make db-up      # postgres:15-alpine en Podman (compose.yml)
make init-db    # crea rol + DB (idempotente)
make migrate    # alembic upgrade head (schema + full-text search + staging)
make load-db    # Parquet → PostgreSQL (staging + swap transaccional)
```

El loader es **atómico e idempotente**: reejecutar `load-db` produce los mismos
conteos y una interrupción a mitad de carga no deja la base inconsistente.
Ver [docs/DATA_LOADING.md](docs/DATA_LOADING.md).

## API REST (FastAPI)

```bash
make backend     # uvicorn en http://localhost:8000
make seed-demo   # 50 colegios demo determinísticos (para reviewers sin ETL)
```

Documentación interactiva: `/docs` (Swagger UI) y `/redoc`. Endpoints principales:

| Endpoint | Descripción |
|---|---|
| `GET /api/v1/health` | Health check + `dataset_version` |
| `GET /api/v1/stats` | Conteos globales |
| `GET /api/v1/regiones` | Lista de regiones (cacheada 24h) |
| `GET /api/v1/comunas?region=` | Comunas por región (filtro en cascada, cacheada 24h) |
| `GET /api/v1/search?q=&comuna=&dependencia=&regimen=&nivel=&copago_max=&etiquetas=` | Búsqueda full-text + filtros |
| `GET /api/v1/establecimientos` / `/{rbd}` | Listado paginado / ficha completa |
| `GET /api/v1/{sedes,cursos,indicadores,actividades,imagenes}?rbd=` | Sub-recursos |
| `GET /api/v1/cursos/resumen?rbd=` | Resumen de cursos (payload liviano) |
| `GET /api/v1/compare?rbds=1,2,3` | Comparación (máx. 10) |

Ver [docs/API_CONVENTIONS.md](docs/API_CONVENTIONS.md) para paginación, errores, filtros y rate limiting.

## Frontend (Astro)

```bash
cd frontend && npm install
make frontend    # levanta Astro en http://localhost:4321
```

- **Astro 7** + `@astrojs/node` (SSR) + React islands + Tailwind CSS v4.
- **SSR** para la ficha (`/colegio/[rbd]`) y la home; **SSG** para `/acerca`.
- React islands para búsqueda (con filtro en cascada región→comuna) y comparador.
- Tipos generados con `openapi-typescript` (`npm run gen:types`).

Requiere el backend corriendo (`make backend`). Ver [docs/SECURITY.md](docs/SECURITY.md).

## Qué obtengo

6 archivos Parquet en `data/processed/latest/` listos para leer con Polars, DuckDB o Pandas:

| Tabla | Filas | Descripción |
|---|---|---|
| `establecimientos.parquet` | 7,673 | 1 fila por colegio (RBD, nombre, dependencia, director, matrícula...) |
| `sedes.parquet` | 7,912 | 1 fila por sede (dirección, coordenadas, región, comuna) |
| `cursos.parquet` | 77,540 | 1 fila por curso/nivel (copago, vacantes, postulantes, repitentes) |
| `actividades.parquet` | 206,041 | Actividades extraprogramáticas, deportes, apoyo académico |
| `indicadores.parquet` | 49,830 | Resultados SIMCE y clasificaciones de desempeño |
| `imagenes.parquet` | 77,421 | Imágenes de infraestructura por colegio |

### Ejemplo rápido

```python
import polars as pl

df = pl.read_parquet("data/processed/latest/establecimientos.parquet")
print(df.select("nombre", "dependencia", "alumnos_matriculados").head(5))
```

## Estructura

```
colegios-chile/
├── scripts/
│   ├── discover_comunas.py    # Mapea nombres de comuna SII → MINEDUC
│   ├── run_etl.py             # Pipeline ETL (extract → transform → load → validate)
│   ├── init_db.py             # Crea rol + DB (idempotente, no toca schema)
│   ├── load_to_db.py          # Parquet → PostgreSQL (staging + swap)
│   ├── seed_demo.py           # 50 colegios demo determinísticos (portafolio)
│   └── validate_api.py        # Smoke test de endpoints
├── etl/                       # pipeline de ingestión (scraper → Parquet)
│   ├── api_client/            # HTTP client + rate limiting adaptativo
│   ├── extract/               # Descarga JSONs de comunas y RBDs
│   ├── transform/             # Pydantic models + normalizadores a Polars
│   ├── load/                  # Escritura Parquet + symlink latest/
│   ├── validation/            # 6 queries DuckDB de integridad
│   └── state.py               # Checkpointing reanudable
├── src/                       # aplicación web (Clean Architecture)
│   ├── domain/                # entidades (dataclasses) + contratos de repositorio
│   ├── application/           # casos de uso (search, compare, ficha)
│   ├── infrastructure/
│   │   ├── db/                # ORM + repositorios + sesión async
│   │   ├── search_service.py  # FTS tsvector + unaccent (SQL crudo)
│   │   └── loader.py          # Loader atómico Parquet → PostgreSQL
│   └── api/                   # FastAPI (routers, DTOs, deps, rate limiting)
├── frontend/                  # Astro 7 (SSR + React islands + Tailwind v4)
│   ├── src/pages/             # index, colegio/[rbd], comparar, acerca
│   ├── src/components/        # React islands (búsqueda, comparador)
│   └── src/lib/               # api.ts + types.ts (openapi-typescript)
├── config/                    # compartido (settings + logging)
│   ├── settings.py            # pydantic-settings (fuente única de verdad)
│   └── logging.py             # structlog
├── alembic/                   # Migraciones versionadas (env.py async)
├── compose.yml                # PostgreSQL 15 (Podman/Docker)
├── data/
│   ├── raw/comunas/           # JSONs crudos por comuna
│   ├── raw/establecimientos/  # JSONs crudos por RBD
│   └── processed/YYYY-MM-DD/  # Parquet + report.json + symlink latest/
├── logs/                      # JSONL estructurado (timestamp, level, comuna, rbd, duration_ms, error)
├── tests/                     # 21 tests con fixtures reales (API)
├── docs/                      # arquitectura, data loading, data dictionary
└── assets/                    # comunas_mapeo.json
```

## Flujo del pipeline

| Paso | Comando | Descripción |
|---|---|---|
| **Discovery** | `make discover` | Obtiene 346 comunas del SII, normaliza nombres y los mapea contra la API MINEDUC. Se ejecuta una sola vez. |
| **Extracción** | `make etl` | Itera cada comuna, descarga listas de RBDs y el detalle completo de cada colegio. Usa checkpointing: si se interrumpe, continúa donde quedó. |
| **Transformación** | `make transform` | Valida JSONs con Pydantic, aplana estructuras anidadas (sedes→cursos→indicadores...) y escribe 6 Parquet. |
| **Validación** | `make validate` | Ejecuta 6 queries DuckDB: integridad referencial, duplicados, nulos en claves. |

## Stack

| Componente | Uso |
|---|---|
| `httpx` + `asyncio` | Requests HTTP asíncronos con semáforo (5 workers) |
| `tenacity` | Reintentos con backoff exponencial + jitter |
| `pydantic` / `pydantic-settings` | Validación de datos + configuración por `.env` |
| `polars` + `pyarrow` | Transformación y Parquet |
| `duckdb` | Validaciones de calidad |
| `structlog` | Logging estructurado en JSON |
| `sqlalchemy[asyncio]` + `asyncpg` | ORM async + driver PostgreSQL |
| `alembic` | Migraciones versionadas |
| `fastapi` + `uvicorn` | API REST async + servidor ASGI |
| `slowapi` | Rate limiting en memoria |
| `pytest` | 52 tests (unit + integration + API) |

## Validaciones de calidad

Cada corrida verifica:

- [x] Integridad referencial sedes → establecimientos
- [x] Integridad referencial cursos → sedes
- [x] Sin RBDs duplicados
- [x] Todos los establecimientos tienen al menos una sede
- [x] Sin nulos en columnas clave (rbd, nombre, codigo_sede)

Resultados en `data/processed/latest/report.json` y `logs/`.

## Documentación

- [docs/ARCHITECTURE_v2.md](docs/ARCHITECTURE_v2.md) — arquitectura final y plan por fases (F0–F4)
- [docs/API_CONVENTIONS.md](docs/API_CONVENTIONS.md) — contrato de la API (paginación, errores, filtros)
- [docs/DATA_LOADING.md](docs/DATA_LOADING.md) — estrategia de carga (staging + swap) y orden de ejecución
- [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) — mapeo JSON/Parquet → PostgreSQL campo a campo
- [docs/STORAGE.md](docs/STORAGE.md) — estrategia de almacenamiento de imágenes
- [docs/SECURITY.md](docs/SECURITY.md) — seguridad de la API (rate limiting, CORS, X-Forwarded-For)
- [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) — limitaciones del dataset

## Limitaciones conocidas

- **TREHUACO** (Región de Ñuble): no tiene establecimientos en el sistema SAE. Comuna rural de ~5,000 habitantes.
- **ANTARTICA**: aceptada por la API pero devuelve 0 RBDs.
- El dataset representa una instantánea. Ejecutar `make etl` de nuevo para actualizar.

## Licencia y uso

Los datos provienen de la API pública del MINEDUC. Uso interno únicamente. Revisar términos de uso de `apisae.mineduc.cl` antes de publicar el dataset.
