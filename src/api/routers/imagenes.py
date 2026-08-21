"""Endpoint de imágenes: GET /api/v1/imagenes?rbd=."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from src.api.deps import get_establecimiento_repo, get_imagen_repo
from src.api.etag import apply_etag
from src.api.limiter import limiter
from src.api.schemas.imagenes import ImagenOut
from src.domain.exceptions import EstablecimientoNotFound
from src.infrastructure.db.repositories import SqlEstablecimientoRepository, SqlImagenRepository

router = APIRouter(tags=["imagenes"])


@router.get("/imagenes", response_model=list[ImagenOut])
@limiter.limit("60/minute")
async def list_imagenes(
    request: Request,
    response: Response,
    rbd: int,
    repo: SqlImagenRepository = Depends(get_imagen_repo),
    est_repo: SqlEstablecimientoRepository = Depends(get_establecimiento_repo),
) -> list[ImagenOut] | Response:
    if (not_modified := apply_etag(request, response)) is not None:
        return not_modified
    if not await est_repo.exists(rbd):
        raise EstablecimientoNotFound(rbd)
    return [ImagenOut.model_validate(i) for i in await repo.by_rbd(rbd)]
