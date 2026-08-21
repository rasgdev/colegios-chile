"""Endpoint de indicadores: GET /api/v1/indicadores?rbd=."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from src.api.deps import get_establecimiento_repo, get_indicador_repo
from src.api.limiter import limiter
from src.api.schemas.indicadores import IndicadorOut
from src.domain.exceptions import EstablecimientoNotFound
from src.infrastructure.db.repositories import (
    SqlEstablecimientoRepository,
    SqlIndicadorRepository,
)

router = APIRouter(tags=["indicadores"])


@router.get("/indicadores", response_model=list[IndicadorOut])
@limiter.limit("60/minute")
async def list_indicadores(
    request: Request,
    rbd: int,
    repo: SqlIndicadorRepository = Depends(get_indicador_repo),
    est_repo: SqlEstablecimientoRepository = Depends(get_establecimiento_repo),
) -> list[IndicadorOut]:
    if not await est_repo.exists(rbd):
        raise EstablecimientoNotFound(rbd)
    return [IndicadorOut.model_validate(i) for i in await repo.by_rbd(rbd)]
