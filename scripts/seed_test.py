"""Carga datos de prueba determinísticos en PostgreSQL.

Uso:
    python scripts/seed_test.py

Requiere que la base de datos exista y tenga el schema aplicado
(alembic upgrade head).
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.infrastructure.db.session import async_session_factory
from tests.fixtures.seed import seed_test_dataset


async def main() -> None:
    async with async_session_factory() as session:
        await seed_test_dataset(session)
    print("Datos de prueba cargados.")


if __name__ == "__main__":
    asyncio.run(main())
