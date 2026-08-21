"""Endpoints de cursos: GET /api/v1/cursos y /api/v1/cursos/resumen."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from src.api.deps import get_curso_repo, get_establecimiento_repo
from src.api.etag import apply_etag
from src.api.limiter import limiter
from src.api.schemas.cursos import CursoOut, CursoResumenOut
from src.domain.exceptions import EstablecimientoNotFound
from src.infrastructure.db.repositories import SqlCursoRepository, SqlEstablecimientoRepository

router = APIRouter(tags=["cursos"])


@router.get("/cursos", response_model=list[CursoOut])
@limiter.limit("60/minute")
async def list_cursos(
    request: Request,
    response: Response,
    rbd: int,
    repo: SqlCursoRepository = Depends(get_curso_repo),
    est_repo: SqlEstablecimientoRepository = Depends(get_establecimiento_repo),
) -> list[CursoOut] | Response:
    if (not_modified := apply_etag(request, response)) is not None:
        return not_modified
    if not await est_repo.exists(rbd):
        raise EstablecimientoNotFound(rbd)
    return [CursoOut.model_validate(c) for c in await repo.by_rbd(rbd)]


@router.get("/cursos/resumen", response_model=list[CursoResumenOut])
@limiter.limit("60/minute")
async def resumen_cursos(
    request: Request,
    response: Response,
    rbd: int,
    repo: SqlCursoRepository = Depends(get_curso_repo),
    est_repo: SqlEstablecimientoRepository = Depends(get_establecimiento_repo),
) -> list[CursoResumenOut] | Response:
    if (not_modified := apply_etag(request, response)) is not None:
        return not_modified
    if not await est_repo.exists(rbd):
        raise EstablecimientoNotFound(rbd)
    return [CursoResumenOut.model_validate(c) for c in await repo.resumen_by_rbd(rbd)]
