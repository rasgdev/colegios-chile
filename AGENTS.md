# AGENTS.md — Colegios de Chile

Guía para agentes de IA que trabajen en este repositorio. Es un índice: los
detalles de cada decisión viven en `docs/`. Aquí está lo que un agente necesita
saber **antes** de tocar código.

---

## 1. Identidad del proyecto

Buscador público de colegios de Chile con datos del MINEDUC (API SAE).

- **Datos**: 7,673 colegios · 344 comunas · 16 regiones · 3 dependencias.
- **Stack**: Python 3.12 + PostgreSQL 15 + FastAPI + Astro 7 (SSR + React islands).
- **Pipeline**: ETL (httpx/polars/duckdb) → Parquet → PostgreSQL (staging + swap) → API → frontend.
- **Arquitectura**: Clean Architecture en `src/` (detalle en `docs/01-architecture/ARCHITECTURE_v2.md`).

## 2. Principios de calidad

- **Calidad > rapidez.** Preferir soluciones bien diseñadas sobre soluciones rápidas.
- Toda feature de backend/ETL requiere tests (unitarios + integración).
- El código debe pasar `mypy strict` sin errores. Sin `Any` salvo en fronteras de
  I/O no tipadas (ahí usar `cast(...)`); los `# type: ignore[code]` puntuales con
  motivo están permitidos, los ignores globales no.
- Seguir Clean Architecture: `domain → application → infrastructure → api`.
- Funciones no triviales requieren docstring.

## 3. Arquitectura (Clean Architecture)

La dependencia va en una sola dirección. `src/api/deps.py` es la **única** capa
que importa `application` e `infrastructure` (wiring de DI).

```
src/domain/          # dataclasses frozen=True + contratos (Protocol). Sin frameworks.
src/application/     # casos de uso: search, compare, ficha.
src/infrastructure/  # SQLAlchemy, repositorios, SearchService (FTS), loader.
src/api/             # FastAPI: routers, schemas (DTOs), deps, exceptions, etag, limiter.
```

- **domain**: entidades `frozen=True` (inmutables), 0 imports de frameworks. El
  dominio es read-only (los datos vienen del ETL y solo se consultan).
- **repositorios**: contratos en `domain/repositories.py` (`Protocol` async);
  implementación SQLAlchemy en `infrastructure/db/repositories.py`.
- **errores**: excepciones de dominio en `src/domain/exceptions.py`
  (`DomainError`); se traducen a HTTP en `src/api/exceptions.py`
  (`register_exception_handlers`).
- **FTS**: `SearchService` en `src/infrastructure/search_service.py` es SQL crudo
  (`tsvector` + `websearch_to_tsquery('spanish_unaccent', ...)`) acoplado a
  PostgreSQL **a propósito** (decisión #7 de ARCHITECTURE_v2): un repository
  genérico sería una falsa abstracción. Si se migrara a Elasticsearch se
  reemplaza este servicio, no los repositorios.

## 4. Reglas de código

### Backend + ETL (Python)

- **ruff**: `E, F, B` (ignora `E501`, `B008`), `line-length = 100`, `target = py312`.
- **mypy**: `strict = true` sobre `src`, `config` y `etl` (ver `pyproject.toml`).
- **pytest**: `tests/unit/`, `tests/integration/`, `tests/api/`, `tests/etl/`.
  `asyncio_mode = auto`. Los tests de API/integración usan Postgres real y hacen
  skip si no está disponible (`tests/conftest.py::_db_reachable`). Datos de prueba
  determinísticos en `tests/fixtures/` (seed automático vía conftest).
- Configuración: `config/settings.py` (pydantic-settings) es la **fuente única de
  verdad**. Toda config nueva va ahí, nunca hardcodeada.

### Frontend (Astro + React)

- Astro 7 + `@astrojs/node` (SSR) + React islands + Tailwind CSS v4 + Node 22.
- `src/lib/types.ts` es **generado** por `openapi-typescript` (`npm run gen:types`);
  nunca editarlo a mano.
- `output: 'server'` (SSR) para la home, la ficha (`colegio/[rbd]`) y `/comparar`;
  `/acerca` es SSG (`export const prerender = true`).
- Componentes `.astro` para HTML estático; islas React (`.tsx`) solo para
  interactividad (búsqueda, comparador).
- Validación: `eslint` + `astro check` + `astro build`. **Sin tests unitarios en
  frontend** por ahora.

## 5. Convenciones API

- Prefijo `/api/v1`. Paginación, errores y filtros según `docs/01-architecture/API_CONVENTIONS.md`.
- **Rate limiting** (slowapi, en memoria): `30/minute` para `search` y `compare`;
  `60/minute` para el resto de endpoints de datos. `/health` y `/stats` no están
  limitados.
- **FTS**: delegar a `SearchService`; no hardcodear queries FTS en `application`.
- **Carga de datos**: staging + swap transaccional (`src/infrastructure/loader.py`),
  idempotente. Ver `docs/01-architecture/DATA_LOADING.md`.
- Caching: ETag en `src/api/etag.py`; regiones/comunas cacheadas 24h.

## 6. ETL y datos

- `etl/` es el pipeline de ingestión (httpx + rate limiter adaptativo, extract,
  transform con Pydantic→Polars, load a Parquet, validación DuckDB, checkpointing
  en `etl/state.py`).
- `make discover` corre **una sola vez** (mapea comunas SII → MINEDUC).
- `make etl` es reanudable: si se interrumpe, continúa donde quedó.
- `make load-db` es atómico e idempotente; nunca deja la base inconsistente.
- Orden del pipeline: `discover → etl → transform → validate → db-up → init-db → migrate → load-db`.

## 7. Migraciones (Alembic)

Todo cambio de schema exige una migración nueva en `alembic/versions/`
(`alembic upgrade head` / `make migrate`). Los modelos ORM en
`src/infrastructure/db/orm.py` son espejo del DDL y **solo lectura** (quien
escribe es el loader). No modificar el schema sin migración.

## 8. Configuración y secretos

- `.env` está gitignored. `.env.example` documenta todas las variables.
- `DATABASE_URL` en producción usa `postgresql+asyncpg://colegios:${DB_PASSWORD}@...`;
  `DB_PASSWORD` se sustituye en deploy (nunca commitear el valor real).
- Nunca commitear secretos ni claves.

## 9. Idioma y commits

- **Código, docstrings y comentarios en español.** Nombres de dominio/tablas en
  español cuando modelan el dataset (ej. `Establecimiento`, `regiones`).
- **Commits**: Conventional Commits (`feat:`, `fix:`, `test:`, `ci:`, `docs:`, ...).
  El mensaje puede ir en español o inglés.

## 10. Skills del proyecto

Vincular el skill correspondiente a cada tipo de tarea (viven en `.agents/skills/`):

| Tarea | Skill |
|---|---|
| API/backend FastAPI | `fastapi-python` |
| SQL, optimización de queries | `postgres-pro` |
| Auth, validación de input | `secure-code-guardian` |
| Diseño de tests | `test-master` |
| Decisiones de arquitectura | `architecture-patterns` |
| Docker, CI/CD, deployment | `devops-engineer` |
| Contrato de la API | `api-design-principles` |
| PRs, issues, revisión | `github-workflow` |
| Pipelines de CI/CD | `ci-cd-best-practices` |
| Frontend Astro (SSR + islands) | `astro` |
| Estilos, Tailwind CSS | `tailwindcss` |
| Islas React, componentes interactivos | `react` |
| Estado de servidor / data fetching | `tanstack-query` |
| Tipado TypeScript | `typescript` |
| Accesibilidad web (WCAG) | `accessibility-a11y` |
| Backend/ETL en Python | `python` |
| Scripts del pipeline, Makefile | `bash-scripting` |

## 11. Comandos y definition of done

Antes de dar por terminada una tarea, correr (y dejar en verde):

```bash
make lint            # ruff check src etl config scripts tests
make typecheck       # mypy src config etl (strict)
make test            # pytest (requiere Postgres: make db-up init-db migrate; el seed lo hace conftest.py)
make frontend-lint        # eslint
make frontend-typecheck   # astro check
```

Otros comandos frecuentes: `make backend`, `make frontend`, `make migrate`,
`make load-db`, `make seed-demo`, `make seed-test`.

## 12. No hacer

- No tomar atajos "por tiempo" que degraden el diseño o salten tests.
- No mutar entidades de `domain` (son `frozen=True`).
- No usar `asyncpg`/SQL crudo en `domain` ni `application`; usar repositorios
  (salvo `SearchService`, que es la excepción deliberada).
- No hardcodear queries FTS en `application`.
- No editar `frontend/src/lib/types.ts` (generado).
- No commitear `.env` ni secretos.
- No cambiar el schema sin migración Alembic.
