"""Contratos de repositorio (Protocols async).

Definen la interfaz que la capa `application` consume. Las implementaciones
concretas viven en `src/infrastructure/db/repositories.py` (SQLAlchemy).
"""
from __future__ import annotations

from typing import Protocol

from src.domain.entities import (
    Actividad,
    Comuna,
    Curso,
    CursoResumen,
    Establecimiento,
    Imagen,
    Indicador,
    Region,
    SearchPage,
    SearchQuery,
    Sede,
)


class RegionRepository(Protocol):
    async def list_all(self) -> list[Region]: ...


class ComunaRepository(Protocol):
    async def list_all(self) -> list[Comuna]: ...


class EstablecimientoRepository(Protocol):
    async def get_by_rbd(self, rbd: int) -> Establecimiento | None: ...

    async def get_many(self, rbds: list[int]) -> list[Establecimiento]: ...

    async def exists(self, rbd: int) -> bool: ...

    async def list_paginated(
        self,
        limit: int,
        offset: int,
        *,
        dependencia: str | None = None,
        regimen: str | None = None,
    ) -> tuple[list[Establecimiento], int]: ...

    async def total(self) -> int: ...


class SedeRepository(Protocol):
    async def by_rbd(self, rbd: int) -> list[Sede]: ...


class CursoRepository(Protocol):
    async def by_rbd(self, rbd: int) -> list[Curso]: ...

    async def resumen_by_rbd(self, rbd: int) -> list[CursoResumen]: ...


class IndicadorRepository(Protocol):
    async def by_rbd(self, rbd: int) -> list[Indicador]: ...

    async def by_rbds(self, rbds: list[int]) -> list[Indicador]: ...


class ActividadRepository(Protocol):
    async def by_rbd(self, rbd: int) -> list[Actividad]: ...


class ImagenRepository(Protocol):
    async def by_rbd(self, rbd: int) -> list[Imagen]: ...


class SearchRepository(Protocol):
    async def search(self, query: SearchQuery) -> SearchPage: ...
