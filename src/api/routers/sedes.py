"""Endpoint de sedes: GET /api/v1/sedes?rbd=."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from src.api.deps import get_establecimiento_repo, get_sede_repo
from src.api.limiter import limiter
from src.api.schemas.sedes import SedeOut
from src.domain.exceptions import EstablecimientoNotFound
from src.infrastructure.db.repositories import SqlEstablecimientoRepository, SqlSedeRepository

router = APIRouter(tags=["sedes"])


@router.get("/sedes", response_model=list[SedeOut])
@limiter.limit("60/minute")
async def list_sedes(
    request: Request,
    rbd: int,
    repo: SqlSedeRepository = Depends(get_sede_repo),
    est_repo: SqlEstablecimientoRepository = Depends(get_establecimiento_repo),
) -> list[SedeOut]:
    if not await est_repo.exists(rbd):
        raise EstablecimientoNotFound(rbd)
    return [SedeOut.model_validate(s) for s in await repo.by_rbd(rbd)]
