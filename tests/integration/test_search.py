"""Tests de integración del SearchService (requieren PostgreSQL con datos)."""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from config.settings import settings
from src.domain.entities import SearchQuery
from src.infrastructure.search_service import SearchService


@pytest.fixture
async def search_service():
    engine = create_async_engine(settings.database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield SearchService(session)
    await engine.dispose()


@pytest.mark.asyncio
async def test_fts_aleman_encuentra_aleman(search_service):
    page = await search_service.search(SearchQuery(q="aleman", limit=20))
    assert page.total > 0
    nombres = " ".join(e.nombre for e in page.items).upper()
    assert "ALEMAN" in nombres


@pytest.mark.asyncio
async def test_copago_max_sin_duplicados(search_service):
    page = await search_service.search(SearchQuery(copago_max=50000, limit=100))
    rbds = [e.rbd for e in page.items]
    assert len(rbds) == len(set(rbds))


@pytest.mark.asyncio
async def test_nivel_media_rango(search_service):
    page = await search_service.search(SearchQuery(nivel="MEDIA", limit=10))
    assert page.total > 0
    for e in page.items:
        assert e.nivel_maximo is not None
