"""Crea el rol y la base de datos de la aplicación, de forma idempotente.

Responsabilidad (ver docs/DATA_LOADING.md):
- `init_db.py`: crea/verifica el **clúster** (rol + base de datos). NO toca schema.
- Alembic: gestiona el **schema** (tablas, índices, constraints, FKs).

Uso:
    python scripts/init_db.py
"""

import asyncio
import sys
from pathlib import Path

# Asegura que los paquetes de ESTE repo (config/) ganen la resolución de imports
# al ejecutar el script directamente (sin `make`/PYTHONPATH).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncpg
from sqlalchemy.engine import make_url

from config.settings import settings


async def init_db() -> None:
    url = make_url(settings.database_url)

    if url.get_backend_name() != "postgresql":
        print(f"ERROR: DATABASE_URL no es PostgreSQL: {settings.database_url}", file=sys.stderr)
        sys.exit(1)

    host = url.host or "localhost"
    port = url.port or 5432
    user = url.username or "postgres"
    password = url.password or ""
    database = url.database or "colegios"

    # Conecta a la base de mantenimiento `postgres`.
    conn = await asyncpg.connect(
        host=host, port=port, user=user, password=password, database="postgres"
    )

    try:
        # Rol (idempotente).
        role_exists = await conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname = $1", user)
        if not role_exists:
            await conn.execute(f'CREATE ROLE "{user}" LOGIN PASSWORD \'{password}\'')
            print(f"Rol creado: {user}")
        else:
            print(f"Rol ya existe: {user}")

        # Base de datos (idempotente).
        db_exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", database)
        if not db_exists:
            # No se puede usar parámetro en CREATE DATABASE; el nombre viene de la config.
            await conn.execute(f'CREATE DATABASE "{database}" OWNER "{user}"')
            print(f"Base de datos creada: {database}")
        else:
            print(f"Base de datos ya existe: {database}")
    finally:
        await conn.close()

    print(f"Conexión verificada: {host}:{port} · db={database} · user={user}")


if __name__ == "__main__":
    asyncio.run(init_db())
