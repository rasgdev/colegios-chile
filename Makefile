.PHONY: help install install-dev test typecheck lint discover etl transform validate load-db all clean \
	db-up db-down init-db migrate seed-demo seed-test backend frontend frontend-lint frontend-typecheck

.DEFAULT_GOAL := help

export PYTHONPATH := .

help:
	@echo "Colegios de Chile — Buscador (ETL + Backend)"
	@echo ""
	@echo "Uso: make [target]"
	@echo ""
	@echo "Pipeline de datos:"
	@echo "  all         Punta a punta: discover → etl → transform → validate → db-up → init-db → migrate → load-db"
	@echo "  discover    Descubre y mapea nombres de comunas contra la API del MINEDUC (UNA sola vez)."
	@echo "  etl         Extrae datos crudos (con checkpointing en data/state.json)."
	@echo "  transform   Lee JSON crudos → 6 archivos Parquet en data/processed/latest/."
	@echo "  validate    Ejecuta 6 queries DuckDB sobre los Parquet (integridad referencial, duplicados, nulos)."
	@echo ""
	@echo "Persistencia (PostgreSQL vía Podman):"
	@echo "  db-up       Levanta PostgreSQL 15 en contenedor (podman compose up -d)."
	@echo "  db-down     Detiene y elimina el contenedor (conserva el volumen)."
	@echo "  init-db     Crea rol + base de datos (idempotente; no toca schema)."
	@echo "  migrate     Aplica migraciones Alembic (alembic upgrade head)."
	@echo "  load-db     Carga Parquet → PostgreSQL (staging + swap transaccional)."
	@echo ""
	@echo "Aplicación:"
	@echo "  backend     Levanta FastAPI en :8000 (uvicorn)."
	@echo "  seed-demo   Inserta 50 colegios demo determinísticos (portafolio)."
	@echo "  seed-test   Inserta datos de prueba determinísticos para tests."
	@echo "  frontend    Levanta Astro en :4321 (disponible en F3)."
	@echo ""
	@echo "Utilidades:"
	@echo "  install     Instala dependencias de runtime (pip install -e .)."
	@echo "  install-dev Instala dependencias de runtime + desarrollo."
	@echo "  test        Ejecuta la suite de tests con pytest."
	@echo "  lint        Lint backend (ruff)."
	@echo "  typecheck   Type-check backend (mypy)."
	@echo "  frontend-lint        Lint frontend (eslint)."
	@echo "  frontend-typecheck   Type-check frontend (astro check)."
	@echo "  clean       Borra data/raw/, data/processed/, data/state.json y logs/."

install:
	python3 -m pip install --break-system-packages -e .

install-dev:
	python3 -m pip install --break-system-packages -e ".[dev]"

test:
	python3 -m pytest

typecheck:
	python3 -m mypy src

lint:
	ruff check src etl config scripts tests

frontend-lint:
	npm --prefix frontend run lint

frontend-typecheck:
	npm --prefix frontend run typecheck

discover:
	python3 scripts/discover_comunas.py

etl:
	python3 scripts/run_etl.py

transform:
	python3 -c "from etl.transform.normalizers import transformar_todo; from etl.load.parquet import guardar_parquets; dfs = transformar_todo(); guardar_parquets(dfs)"

validate:
	python3 -m etl.validation.duckdb_checks

db-up:
	podman compose up -d

db-down:
	podman compose down

init-db:
	python3 scripts/init_db.py

migrate:
	python3 -m alembic upgrade head

load-db:
	python3 scripts/load_to_db.py

seed-demo:
	python3 scripts/seed_demo.py

seed-test:
	python3 scripts/seed_test.py

backend:
	python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

frontend:
	npm --prefix frontend run dev

all: discover etl transform validate db-up init-db migrate load-db

clean:
	rm -rf data/raw data/processed data/state.json logs/*
