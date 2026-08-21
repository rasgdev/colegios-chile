"""Routers de la API."""
from __future__ import annotations

from src.api.routers import (
    actividades,
    compare,
    cursos,
    establecimientos,
    imagenes,
    indicadores,
    meta,
    referencia,
    search,
    sedes,
)

ALL_ROUTERS = [
    meta.router,
    referencia.router,
    search.router,
    establecimientos.router,
    sedes.router,
    cursos.router,
    indicadores.router,
    actividades.router,
    imagenes.router,
    compare.router,
]
