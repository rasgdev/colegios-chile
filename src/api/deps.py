"""Wiring de dependencias (única capa que importa `application` e `infrastructure`)."""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.compare import CompareUseCase
from src.application.ficha import FichaUseCase
from src.application.search import SearchUseCase
from src.infrastructure.db.repositories import (
    SqlActividadRepository,
    SqlComunaRepository,
    SqlCursoRepository,
    SqlEstablecimientoRepository,
    SqlImagenRepository,
    SqlIndicadorRepository,
    SqlRegionRepository,
    SqlSedeRepository,
)
from src.infrastructure.db.session import get_session
from src.infrastructure.search_service import SearchService


def get_region_repo(session: AsyncSession = Depends(get_session)) -> SqlRegionRepository:
    return SqlRegionRepository(session)


def get_comuna_repo(session: AsyncSession = Depends(get_session)) -> SqlComunaRepository:
    return SqlComunaRepository(session)


def get_establecimiento_repo(
    session: AsyncSession = Depends(get_session),
) -> SqlEstablecimientoRepository:
    return SqlEstablecimientoRepository(session)


def get_sede_repo(session: AsyncSession = Depends(get_session)) -> SqlSedeRepository:
    return SqlSedeRepository(session)


def get_curso_repo(session: AsyncSession = Depends(get_session)) -> SqlCursoRepository:
    return SqlCursoRepository(session)


def get_indicador_repo(session: AsyncSession = Depends(get_session)) -> SqlIndicadorRepository:
    return SqlIndicadorRepository(session)


def get_actividad_repo(session: AsyncSession = Depends(get_session)) -> SqlActividadRepository:
    return SqlActividadRepository(session)


def get_imagen_repo(session: AsyncSession = Depends(get_session)) -> SqlImagenRepository:
    return SqlImagenRepository(session)


def get_search_use_case(session: AsyncSession = Depends(get_session)) -> SearchUseCase:
    return SearchUseCase(SearchService(session))


def get_ficha_use_case(session: AsyncSession = Depends(get_session)) -> FichaUseCase:
    return FichaUseCase(
        SqlEstablecimientoRepository(session),
        SqlSedeRepository(session),
        SqlCursoRepository(session),
        SqlIndicadorRepository(session),
        SqlActividadRepository(session),
        SqlImagenRepository(session),
    )


def get_compare_use_case(session: AsyncSession = Depends(get_session)) -> CompareUseCase:
    return CompareUseCase(
        SqlEstablecimientoRepository(session),
        SqlIndicadorRepository(session),
        SqlCursoRepository(session),
    )
