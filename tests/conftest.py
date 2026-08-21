"""Fixtures compartidas de tests."""
from __future__ import annotations

import asyncio

import pytest


def _db_reachable() -> bool:
    try:
        import asyncpg

        from config.settings import settings

        # asyncpg no entiende el prefijo de driver de SQLAlchemy (+asyncpg).
        dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

        async def _check() -> None:
            conn = await asyncpg.connect(dsn)
            await conn.execute("SELECT 1")
            await conn.close()

        asyncio.run(_check())
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def client():
    """TestClient de la API; omite la suite si PostgreSQL no está disponible."""
    if not _db_reachable():
        pytest.skip("PostgreSQL no disponible; omite tests de API/integración")

    from fastapi.testclient import TestClient

    from src.api.main import app

    with TestClient(app) as c:
        yield c
