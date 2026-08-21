"""DTO de imágenes."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ImagenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rbd: int
    nombre: str | None = None
    url: str | None = None
    principal: bool = False
