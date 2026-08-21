"""Endpoint de búsqueda: GET /api/v1/search."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from src.api.limiter import limiter
from src.api.schemas.establecimientos import EstablecimientoListItem
from src.api.schemas.search import SearchResponse
from src.api.deps import get_search_use_case
from src.application.search import SearchUseCase
from src.domain.entities import SearchQuery

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResponse)
@limiter.limit("30/minute")
async def search(
    request: Request,
    q: str | None = None,
    comuna: str | None = None,
    region: int | None = Query(default=None, ge=1),
    dependencia: str | None = None,
    regimen: str | None = None,
    nivel: str | None = None,
    copago_max: int | None = Query(default=None, ge=0),
    etiquetas: list[str] | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    use_case: SearchUseCase = Depends(get_search_use_case),
) -> SearchResponse:
    page = await use_case.execute(
        SearchQuery(
            q=q,
            comuna=comuna,
            region=region,
            dependencia=dependencia,
            regimen=regimen,
            nivel=nivel,
            copago_max=copago_max,
            etiquetas=etiquetas or [],
            limit=limit,
            offset=offset,
        )
    )
    return SearchResponse(
        results=[EstablecimientoListItem.model_validate(e) for e in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )
