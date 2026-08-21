"""DTO de indicadores."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class IndicadorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rbd: int
    tipo_indicador: str
    nombre_indicador: str
    titulo_indicador: str | None = None
    nivel_indicador: str | None = None
    descripcion_indicador: str | None = None
    puntaje: float | None = None
    comparacion_gse_numero: int | None = None
    comparacion_gse_glosa: str | None = None
