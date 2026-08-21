"""Endpoints de datos de referencia: GET /regiones y GET /comunas?region=.

Son datos estáticos (no cambian entre recargas del dataset con frecuencia), por lo
que se cachean a nivel HTTP con `Cache-Control: public, max-age=86400` (§2.5).
El filtro de comunas es en cascada: el frontend pide primero una región y luego
solo las comunas de esa región (evita transferir las 344 comunas de una vez).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response

from src.api.deps import get_comuna_repo, get_region_repo
from src.api.limiter import limiter
from src.api.schemas.referencia import ComunaOut, RegionOut
from src.infrastructure.db.repositories import SqlComunaRepository, SqlRegionRepository

router = APIRouter(tags=["referencia"])

_REFERENCE_CACHE = "public, max-age=86400"


@router.get("/regiones", response_model=list[RegionOut])
@limiter.limit("60/minute")
async def list_regiones(
    request: Request,
    response: Response,
    repo: SqlRegionRepository = Depends(get_region_repo),
) -> list[RegionOut]:
    response.headers["Cache-Control"] = _REFERENCE_CACHE
    return [RegionOut.model_validate(r) for r in await repo.list_all()]


@router.get("/comunas", response_model=list[ComunaOut])
@limiter.limit("60/minute")
async def list_comunas(
    request: Request,
    response: Response,
    region: int = Query(..., description="Código de región (filtro en cascada)"),
    repo: SqlComunaRepository = Depends(get_comuna_repo),
) -> list[ComunaOut]:
    response.headers["Cache-Control"] = _REFERENCE_CACHE
    return [ComunaOut.model_validate(c) for c in await repo.list_by_region(region)]
