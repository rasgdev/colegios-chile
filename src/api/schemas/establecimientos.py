"""DTOs de establecimientos (listado, detalle y ficha)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from src.api.schemas.actividades import ActividadOut
from src.api.schemas.cursos import CursoResumenOut
from src.api.schemas.imagenes import ImagenOut
from src.api.schemas.indicadores import IndicadorOut
from src.api.schemas.sedes import SedeOut


class EstablecimientoListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rbd: int
    nombre: str
    dependencia: str
    regimen: str | None = None
    nivel_minimo: str | None = None
    nivel_maximo: str | None = None
    etiquetas: list[str] = []
    alumnos_matriculados: int | None = None


class EstablecimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rbd: int
    nombre: str
    dependencia: str
    telefono: str | None = None
    mail: str | None = None
    url: str | None = None
    habilitado_postular: bool = True
    publicado: bool = False
    nivel_minimo: str | None = None
    nivel_maximo: str | None = None
    director: str | None = None
    etiquetas: list[str] = []
    resumen_proyecto: str | None = None
    documento_proyecto: str | None = None
    documento_reglamento: str | None = None
    internado: bool = False
    integracion: bool = False
    subvencion_preferencial: bool = False
    peib: bool = False
    politica_uniforme: str | None = None
    orientacion_religiosa: str | None = None
    alumnos_matriculados: int | None = None
    promedio_alumnos_por_curso: float | None = None
    cantidad_docentes: int | None = None
    regimen: str | None = None


class EstablecimientoListResponse(BaseModel):
    results: list[EstablecimientoListItem]
    total: int
    limit: int
    offset: int


class FichaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    establecimiento: EstablecimientoOut
    sedes: list[SedeOut]
    cursos_resumen: list[CursoResumenOut]
    indicadores: list[IndicadorOut]
    actividades: list[ActividadOut]
    imagenes: list[ImagenOut]
