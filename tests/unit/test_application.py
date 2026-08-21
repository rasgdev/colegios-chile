"""Tests de casos de uso con repositorios in-memory (sin base de datos)."""
import pytest

from src.application.compare import CompareUseCase
from src.application.ficha import FichaUseCase
from src.application.search import MAX_LIMIT, SearchUseCase
from src.domain.entities import (
    CursoResumen,
    Establecimiento,
    Indicador,
    SearchPage,
    SearchQuery,
)
from src.domain.exceptions import (
    CompareMissingRbdError,
    CompareTooManyError,
    DomainError,
    EstablecimientoNotFound,
)


class FakeSearchRepository:
    def __init__(self):
        self.captured = None

    async def search(self, query: SearchQuery) -> SearchPage:
        self.captured = query
        return SearchPage(items=[], total=0, limit=query.limit, offset=query.offset)


class FakeEstablecimientoRepository:
    def __init__(self, ests: dict[int, Establecimiento]):
        self.ests = ests

    async def get_by_rbd(self, rbd: int) -> Establecimiento | None:
        return self.ests.get(rbd)

    async def get_many(self, rbds: list[int]) -> list[Establecimiento]:
        return [self.ests[r] for r in rbds if r in self.ests]

    async def exists(self, rbd: int) -> bool:
        return rbd in self.ests

    async def list_paginated(self, *args, **kwargs):
        raise NotImplementedError

    async def total(self) -> int:
        return len(self.ests)


class FakeIndicadorRepository:
    async def by_rbd(self, rbd: int) -> list[Indicador]:
        return []

    async def by_rbds(self, rbds: list[int]) -> list[Indicador]:
        return []


class FakeCursoRepository:
    async def by_rbd(self, rbd: int):
        return []

    async def resumen_by_rbd(self, rbd: int) -> list[CursoResumen]:
        return []


class FakeSedeRepository:
    async def by_rbd(self, rbd: int):
        return []


class FakeActividadRepository:
    async def by_rbd(self, rbd: int):
        return []


class FakeImagenRepository:
    async def by_rbd(self, rbd: int):
        return []


def _est(rbd: int, nombre: str = "Colegio") -> Establecimiento:
    return Establecimiento(rbd=rbd, nombre=nombre, dependencia="PUBLICO")


# ── SearchUseCase ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_search_clampa_limit():
    repo = FakeSearchRepository()
    uc = SearchUseCase(repo)
    await uc.execute(SearchQuery(limit=1000))
    assert repo.captured.limit == MAX_LIMIT


@pytest.mark.asyncio
async def test_search_normaliza_filtros():
    repo = FakeSearchRepository()
    uc = SearchUseCase(repo)
    await uc.execute(
        SearchQuery(
            dependencia="publico",
            regimen="mixto",
            nivel="media",
            etiquetas=["pie"],
        )
    )
    assert repo.captured.dependencia == "PUBLICO"
    assert repo.captured.regimen == "MIXTO"
    assert repo.captured.nivel == "MEDIA"
    assert repo.captured.etiquetas == ["PIE"]


@pytest.mark.asyncio
async def test_search_nivel_invalido():
    uc = SearchUseCase(FakeSearchRepository())
    with pytest.raises(DomainError):
        await uc.execute(SearchQuery(nivel="DOCTORADO"))


# ── CompareUseCase ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_compare_demasiados():
    uc = CompareUseCase(
        FakeEstablecimientoRepository({i: _est(i) for i in range(20)}),
        FakeIndicadorRepository(),
        FakeCursoRepository(),
    )
    with pytest.raises(CompareTooManyError):
        await uc.execute(list(range(11)))


@pytest.mark.asyncio
async def test_compare_rbd_inexistente():
    uc = CompareUseCase(
        FakeEstablecimientoRepository({1: _est(1)}),
        FakeIndicadorRepository(),
        FakeCursoRepository(),
    )
    with pytest.raises(CompareMissingRbdError) as exc:
        await uc.execute([1, 999])
    assert exc.value.rbds == [999]


@pytest.mark.asyncio
async def test_compare_ok():
    uc = CompareUseCase(
        FakeEstablecimientoRepository({1: _est(1), 2: _est(2)}),
        FakeIndicadorRepository(),
        FakeCursoRepository(),
    )
    result = await uc.execute([1, 2])
    assert [e.rbd for e in result.establecimientos] == [1, 2]


# ── FichaUseCase ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ficha_no_encontrado():
    uc = FichaUseCase(
        FakeEstablecimientoRepository({}),
        FakeSedeRepository(),
        FakeCursoRepository(),
        FakeIndicadorRepository(),
        FakeActividadRepository(),
        FakeImagenRepository(),
    )
    with pytest.raises(EstablecimientoNotFound):
        await uc.execute(123)


@pytest.mark.asyncio
async def test_ficha_ok():
    uc = FichaUseCase(
        FakeEstablecimientoRepository({1: _est(1)}),
        FakeSedeRepository(),
        FakeCursoRepository(),
        FakeIndicadorRepository(),
        FakeActividadRepository(),
        FakeImagenRepository(),
    )
    ficha = await uc.execute(1)
    assert ficha.establecimiento.rbd == 1
    assert ficha.sedes == []
