"""DTO de sedes."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SedeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rbd: int
    codigo_sede: int
    codigo_region: int
    codigo_comuna: int
    region: str
    comuna: str
    calle: str | None = None
    latitud: float | None = None
    longitud: float | None = None
