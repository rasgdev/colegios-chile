"""Caso de uso: búsqueda de colegios con filtros + full-text."""
from __future__ import annotations

from src.domain.entities import NIVELES_VALIDOS, SearchPage, SearchQuery
from src.domain.exceptions import DomainError
from src.domain.repositories import SearchRepository

MAX_LIMIT = 100
DEFAULT_LIMIT = 20


class SearchUseCase:
    def __init__(self, search_repo: SearchRepository) -> None:
        self.search_repo = search_repo

    async def execute(self, query: SearchQuery) -> SearchPage:
        q = self._normalize(query)
        return await self.search_repo.search(q)

    def _normalize(self, query: SearchQuery) -> SearchQuery:
        limit = min(max(query.limit, 1), MAX_LIMIT)
        offset = max(query.offset, 0)

        nivel = query.nivel.upper() if query.nivel else None
        if nivel is not None and nivel not in NIVELES_VALIDOS:
            raise DomainError(f"Nivel inválido '{query.nivel}'. Valores: {', '.join(NIVELES_VALIDOS)}")

        dependencia = query.dependencia.upper() if query.dependencia else None
        regimen = query.regimen.upper() if query.regimen else None
        etiquetas = [t.upper() for t in query.etiquetas]

        return SearchQuery(
            q=query.q,
            comuna=query.comuna,
            region=query.region,
            dependencia=dependencia,
            regimen=regimen,
            nivel=nivel,
            copago_max=query.copago_max,
            etiquetas=etiquetas,
            limit=limit,
            offset=offset,
        )
