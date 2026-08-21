"""DTO de respuesta de comparación."""
from __future__ import annotations

from pydantic import BaseModel

from src.api.schemas.cursos import CursoResumenOut
from src.api.schemas.establecimientos import EstablecimientoListItem
from src.api.schemas.indicadores import IndicadorOut
from src.api.schemas.sedes import SedeOut


class CompareResponse(BaseModel):
    establecimientos: list[EstablecimientoListItem]
    indicadores: dict[int, list[IndicadorOut]]
    cursos_resumen: dict[int, list[CursoResumenOut]]
    sedes: dict[int, list[SedeOut]]
