"""Motor async + fábrica de sesiones (SQLAlchemy 2.0 + asyncpg)."""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config.settings import settings

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dependencia FastAPI: cede una sesión por request."""
    async with async_session_factory() as session:
        yield session
