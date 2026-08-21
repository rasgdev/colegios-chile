"""Endpoint de actividades: GET /api/v1/actividades?rbd=."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from src.api.deps import get_actividad_repo, get_establecimiento_repo
from src.api.limiter import limiter
from src.api.schemas.actividades import ActividadOut
from src.domain.exceptions import EstablecimientoNotFound
from src.infrastructure.db.repositories import SqlActividadRepository, SqlEstablecimientoRepository

router = APIRouter(tags=["actividades"])


@router.get("/actividades", response_model=list[ActividadOut])
@limiter.limit("60/minute")
async def list_actividades(
    request: Request,
    rbd: int,
    repo: SqlActividadRepository = Depends(get_actividad_repo),
    est_repo: SqlEstablecimientoRepository = Depends(get_establecimiento_repo),
) -> list[ActividadOut]:
    if not await est_repo.exists(rbd):
        raise EstablecimientoNotFound(rbd)
    return [ActividadOut.model_validate(a) for a in await repo.by_rbd(rbd)]
