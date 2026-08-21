"""Caso de uso: comparación de hasta 10 colegios."""
from __future__ import annotations

from src.domain.entities import CompareResult
from src.domain.exceptions import CompareMissingRbdError, CompareTooManyError
from src.domain.repositories import (
    CursoRepository,
    EstablecimientoRepository,
    IndicadorRepository,
)

MAX_RBDS = 10


class CompareUseCase:
    def __init__(
        self,
        establecimientos: EstablecimientoRepository,
        indicadores: IndicadorRepository,
        cursos: CursoRepository,
    ) -> None:
        self.establecimientos = establecimientos
        self.indicadores = indicadores
        self.cursos = cursos

    async def execute(self, rbds: list[int]) -> CompareResult:
        unique = list(dict.fromkeys(rbds))
        if not unique:
            raise CompareMissingRbdError([])
        if len(unique) > MAX_RBDS:
            raise CompareTooManyError(len(unique), MAX_RBDS)

        ests = await self.establecimientos.get_many(unique)
        found = {e.rbd for e in ests}
        missing = [r for r in unique if r not in found]
        if missing:
            raise CompareMissingRbdError(missing)

        ind = await self.indicadores.by_rbds(unique)
        indicadores = {rbd: [] for rbd in unique}
        for i in ind:
            indicadores.setdefault(i.rbd, []).append(i)

        cursos_resumen = {rbd: [] for rbd in unique}
        for rbd in unique:
            cursos_resumen[rbd] = await self.cursos.resumen_by_rbd(rbd)

        return CompareResult(
            establecimientos=ests,
            indicadores=indicadores,
            cursos_resumen=cursos_resumen,
        )
