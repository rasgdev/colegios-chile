"""Endpoint de comparación: GET /api/v1/compare?rbds=1,2,3."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response

from src.api.deps import get_compare_use_case
from src.api.etag import apply_etag
from src.api.limiter import limiter
from src.api.schemas.compare import CompareResponse
from src.api.schemas.cursos import CursoResumenOut
from src.api.schemas.establecimientos import EstablecimientoListItem
from src.api.schemas.indicadores import IndicadorOut
from src.api.schemas.sedes import SedeOut
from src.application.compare import CompareUseCase
from src.domain.exceptions import DomainError

router = APIRouter(tags=["compare"])


@router.get("/compare", response_model=CompareResponse)
@limiter.limit("30/minute")
async def compare(
    request: Request,
    response: Response,
    rbds: str = Query(..., description="RBDs separados por coma (máx. 10)"),
    use_case: CompareUseCase = Depends(get_compare_use_case),
) -> CompareResponse | Response:
    if (not_modified := apply_etag(request, response)) is not None:
        return not_modified
    try:
        rbd_list = [int(x.strip()) for x in rbds.split(",") if x.strip()]
    except ValueError as exc:
        raise DomainError("El parámetro 'rbds' debe ser una lista de enteros separados por coma") from exc

    result = await use_case.execute(rbd_list)
    return CompareResponse(
        establecimientos=[
            EstablecimientoListItem.model_validate(e) for e in result.establecimientos
        ],
        indicadores={
            rbd: [IndicadorOut.model_validate(i) for i in inds]
            for rbd, inds in result.indicadores.items()
        },
        cursos_resumen={
            rbd: [CursoResumenOut.model_validate(c) for c in cursos]
            for rbd, cursos in result.cursos_resumen.items()
        },
        sedes={
            rbd: [SedeOut.model_validate(s) for s in sedes]
            for rbd, sedes in result.sedes.items()
        },
    )
