"""Manejo centralizado de errores (formato consistente `{error, detail, status_code}`)."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.domain.exceptions import (
    CompareMissingRbdError,
    CompareTooManyError,
    DomainError,
    EstablecimientoNotFound,
)


def _error(status_code: int, error: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": error, "detail": detail, "status_code": status_code},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(EstablecimientoNotFound)
    async def not_found_handler(request: Request, exc: EstablecimientoNotFound) -> JSONResponse:
        return _error(404, "establecimiento_no_encontrado", str(exc))

    @app.exception_handler(CompareTooManyError)
    async def compare_too_many_handler(request: Request, exc: CompareTooManyError) -> JSONResponse:
        return _error(400, "demasiados_colegios", str(exc))

    @app.exception_handler(CompareMissingRbdError)
    async def compare_missing_handler(request: Request, exc: CompareMissingRbdError) -> JSONResponse:
        return _error(404, "colegios_no_encontrados", str(exc))

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        return _error(400, "peticion_invalida", str(exc))

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _error(400, "peticion_invalida", str(exc.errors()))
