# Colegios de Chile — Buscador

Buscador público de establecimientos educacionales de Chile. Datos extraídos de la API pública del MINEDUC (SAE).

**7,673 colegios · 344 comunas · 16 regiones · 3 dependencias**

## Quick Start

```bash
make install              # instalar dependencias
make db-up init-db migrate load-db  # PostgreSQL + dataset
make backend              # API en http://localhost:8000
```

Para el frontend (Astro): `cd frontend && npm install && make frontend` (requiere backend corriendo).

Ver `make help` para la lista completa de comandos.

## API

Documentación interactiva en `/docs` (Swagger) y `/redoc`.

| Endpoint | Descripción |
|---|---|
| `GET /api/v1/search?q=` | Búsqueda full-text + filtros (comuna, dependencia, régimen, nivel, copago, etiquetas) |
| `GET /api/v1/establecimientos/{rbd}` | Ficha completa de un colegio |
| `GET /api/v1/compare?rbds=1,2,3` | Comparación de hasta 10 colegios |
| `GET /api/v1/regiones` | Regiones (cache 24h) |
| `GET /api/v1/comunas?region=` | Comunas por región (cache 24h) |
| `GET /api/v1/stats` | Conteos globales |

Ver [docs/01-architecture/API_CONVENTIONS.md](docs/01-architecture/API_CONVENTIONS.md) para paginación, errores, filtros y rate limiting.

## Stack

| Capa | Tecnología |
|---|---|
| **ETL** | httpx · tenacity · pydantic · polars · duckdb |
| **Backend** | FastAPI · SQLAlchemy (async) · Alembic · PostgreSQL 15 |
| **Frontend** | Astro 7 (SSR) · React islands · Tailwind CSS v4 |
| **Infra** | Podman/Docker · structlog · slowapi |

## Documentación

| Documento | Descripción |
|---|---|
| [Arquitectura](docs/01-architecture/ARCHITECTURE_v2.md) | Clean Architecture, diseño por fases (F0–F4) |
| [API](docs/01-architecture/API_CONVENTIONS.md) | Contrato: paginación, errores, filtros, rate limiting |
| [Carga de datos](docs/01-architecture/DATA_LOADING.md) | Estrategia staging + swap, orden de ejecución |
| [Diccionario de datos](docs/01-architecture/DATA_DICTIONARY.md) | Mapeo JSON → Parquet → PostgreSQL campo a campo |
| [Seguridad](docs/03-operations/SECURITY.md) | Rate limiting, CORS, headers |
| [Issues conocidos](docs/03-operations/KNOWN_ISSUES.md) | Limitaciones del dataset |

## Datos

Los datos se exportan como Parquet en `data/processed/latest/` (Polars, DuckDB o Pandas). Ejecutar `make etl` para regenerar. El loader es atómico e idempotente — ver [DATA_LOADING.md](docs/01-architecture/DATA_LOADING.md).

## Licencia

Datos: API pública del MINEDUC. Uso interno. Revisar términos de `apisae.mineduc.cl` antes de publicar.
