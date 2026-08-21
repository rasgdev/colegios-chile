"""DTO de respuesta de búsqueda."""
from __future__ import annotations

from pydantic import BaseModel

from src.api.schemas.establecimientos import EstablecimientoListItem


class SearchResponse(BaseModel):
    results: list[EstablecimientoListItem]
    total: int
    limit: int
    offset: int
