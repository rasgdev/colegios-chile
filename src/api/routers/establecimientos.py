"""Endpoints de establecimientos: listado paginado y ficha completa."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response

from src.api.deps import get_establecimiento_repo, get_ficha_use_case
from src.api.etag import apply_etag
from src.api.limiter import limiter
from src.api.schemas.establecimientos import (
    EstablecimientoListItem,
    EstablecimientoListResponse,
    FichaOut,
)
from src.application.ficha import FichaUseCase
from src.infrastructure.db.repositories import SqlEstablecimientoRepository

router = APIRouter(tags=["establecimientos"])


@router.get("/establecimientos", response_model=EstablecimientoListResponse)
@limiter.limit("60/minute")
async def list_establecimientos(
    request: Request,
    response: Response,
    dependencia: str | None = None,
    regimen: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    repo: SqlEstablecimientoRepository = Depends(get_establecimiento_repo),
) -> EstablecimientoListResponse | Response:
    if (not_modified := apply_etag(request, response)) is not None:
        return not_modified
    items, total = await repo.list_paginated(
        limit,
        offset,
        dependencia=dependencia.upper() if dependencia else None,
        regimen=regimen.upper() if regimen else None,
    )
    return EstablecimientoListResponse(
        results=[EstablecimientoListItem.model_validate(e) for e in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/establecimientos/{rbd}", response_model=FichaOut)
@limiter.limit("60/minute")
async def get_ficha(
    request: Request,
    response: Response,
    rbd: int,
    use_case: FichaUseCase = Depends(get_ficha_use_case),
) -> FichaOut | Response:
    if (not_modified := apply_etag(request, response)) is not None:
        return not_modified
    ficha = await use_case.execute(rbd)
    return FichaOut.model_validate(ficha)
