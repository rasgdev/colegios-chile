"""DTO de actividades."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ActividadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rbd: int
    nombre: str
    tipo: str | None = None
    nivel: str | None = None
    exigencia: str | None = None
