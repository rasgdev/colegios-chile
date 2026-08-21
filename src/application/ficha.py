"""Caso de uso: ficha completa de un colegio (agregador backend)."""
from __future__ import annotations

from src.domain.entities import Ficha
from src.domain.exceptions import EstablecimientoNotFound
from src.domain.repositories import (
    ActividadRepository,
    CursoRepository,
    EstablecimientoRepository,
    ImagenRepository,
    IndicadorRepository,
    SedeRepository,
)


class FichaUseCase:
    def __init__(
        self,
        establecimientos: EstablecimientoRepository,
        sedes: SedeRepository,
        cursos: CursoRepository,
        indicadores: IndicadorRepository,
        actividades: ActividadRepository,
        imagenes: ImagenRepository,
    ) -> None:
        self.establecimientos = establecimientos
        self.sedes = sedes
        self.cursos = cursos
        self.indicadores = indicadores
        self.actividades = actividades
        self.imagenes = imagenes

    async def execute(self, rbd: int) -> Ficha:
        est = await self.establecimientos.get_by_rbd(rbd)
        if est is None:
            raise EstablecimientoNotFound(rbd)

        # Consultas secuenciales: un mismo AsyncSession no soporta operaciones
        # concurrentes (gather sobre una única sesión provoca IllegalStateChangeError).
        return Ficha(
            establecimiento=est,
            sedes=await self.sedes.by_rbd(rbd),
            cursos_resumen=await self.cursos.resumen_by_rbd(rbd),
            indicadores=await self.indicadores.by_rbd(rbd),
            actividades=await self.actividades.by_rbd(rbd),
            imagenes=await self.imagenes.by_rbd(rbd),
        )
