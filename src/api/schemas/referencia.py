"""DTOs de referencia (regiones y comunas para los filtros en cascada)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RegionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: int
    nombre: str


class ComunaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: int
    nombre: str
    codigo_region: int
