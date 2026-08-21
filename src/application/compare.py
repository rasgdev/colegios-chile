"""Caso de uso: comparación de hasta 10 colegios."""
from __future__ import annotations

from src.domain.entities import CompareResult, CursoResumen, Indicador, Sede
from src.domain.exceptions import CompareMissingRbdError, CompareTooManyError
from src.domain.repositories import (
    CursoRepository,
    EstablecimientoRepository,
    IndicadorRepository,
    SedeRepository,
)
MAX_RBDS = 10


class CompareUseCase:
    def __init__(
        self,
        establecimientos: EstablecimientoRepository,
        indicadores: IndicadorRepository,
        cursos: CursoRepository,
        sedes: SedeRepository,
    ) -> None:
        self.establecimientos = establecimientos
        self.indicadores = indicadores
        self.cursos = cursos
        self.sedes = sedes

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
        indicadores: dict[int, list[Indicador]] = {rbd: [] for rbd in unique}
        for i in ind:
            indicadores.setdefault(i.rbd, []).append(i)

        cursos_resumen: dict[int, list[CursoResumen]] = {rbd: [] for rbd in unique}
        for rbd in unique:
            cursos_resumen[rbd] = await self.cursos.resumen_by_rbd(rbd)

        sedes: dict[int, list[Sede]] = {rbd: [] for rbd in unique}
        for s in await self.sedes.by_rbds(unique):
            sedes.setdefault(s.rbd, []).append(s)

        return CompareResult(
            establecimientos=ests,
            indicadores=indicadores,
            cursos_resumen=cursos_resumen,
            sedes=sedes,
        )
