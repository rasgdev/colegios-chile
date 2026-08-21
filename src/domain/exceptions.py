"""Errores de dominio (framework-free)."""
from __future__ import annotations


class DomainError(Exception):
    """Base para errores de dominio/aplicación."""


class EstablecimientoNotFound(DomainError):
    def __init__(self, rbd: int) -> None:
        self.rbd = rbd
        super().__init__(f"Establecimiento {rbd} no encontrado")


class CompareTooManyError(DomainError):
    def __init__(self, count: int, max_rbds: int = 10) -> None:
        self.count = count
        self.max_rbds = max_rbds
        super().__init__(f"Máximo {max_rbds} colegios por comparación (recibidos {count})")


class CompareMissingRbdError(DomainError):
    def __init__(self, rbds: list[int]) -> None:
        self.rbds = rbds
        super().__init__(f"Establecimientos no encontrados: {', '.join(map(str, rbds))}")
