"""DTOs de meta (health y stats)."""
from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    dataset_version: str


class StatsResponse(BaseModel):
    establecimientos: int
    sedes: int
    cursos: int
    comunas: int
    regiones: int
