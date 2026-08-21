"""Endpoints de meta: /health y /stats."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.etag import apply_etag
from src.api.schemas.meta import HealthResponse, StatsResponse
from src.infrastructure.db import orm
from src.infrastructure.db.session import get_session

router = APIRouter(tags=["meta"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    return HealthResponse(
        status="ok",
        dataset_version=request.app.state.dataset_version,
    )


@router.get("/stats", response_model=StatsResponse)
async def stats(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> StatsResponse | Response:
    if (not_modified := apply_etag(request, response)) is not None:
        return not_modified

    async def _count(model) -> int:
        return (await session.execute(select(func.count()).select_from(model))).scalar_one()

    return StatsResponse(
        establecimientos=await _count(orm.Establecimiento),
        sedes=await _count(orm.Sede),
        cursos=await _count(orm.Curso),
        comunas=await _count(orm.Comuna),
        regiones=await _count(orm.Region),
    )
