"""Fixtures compartidas de tests."""
from __future__ import annotations

import socket

import pytest


def _db_reachable() -> bool:
    """Verifica que PostgreSQL esté disponible sin usar asyncio.

    Se usa socket en lugar de asyncpg para evitar conflictos con el event loop
    cuando esta función es llamada desde fixtures síncronos mientras otros
    fixtures async están activos.
    """
    try:
        with socket.create_connection(("localhost", 5432), timeout=2):
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


@pytest.fixture(scope="session", autouse=True)
async def seed_test_data():
    """Carga datos de prueba en PostgreSQL antes de ejecutar la suite.

    Se crea un engine propio para el seed y se dispone inmediatamente después,
    evitando que conexiones creadas en el loop de pytest se mezclen con el
    loop que usa TestClient para ejecutar la aplicación.
    """
    if not _db_reachable():
        pytest.skip("PostgreSQL no disponible; omite tests de API/integración")

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from config.settings import settings
    from tests.fixtures.seed import seed_test_dataset

    engine = create_async_engine(settings.database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as session:
        await seed_test_dataset(session)

    await engine.dispose()
