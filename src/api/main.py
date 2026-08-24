"""FastAPI app factory + lifespan + CORS + rate limiting."""
# CI/CD test change — safe to revert
from __future__ import annotations

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config.settings import settings
from src.api.exceptions import register_exception_handlers
from src.api.limiter import limiter
from src.api.routers import ALL_ROUTERS

API_PREFIX = "/api/v1"


def _load_dataset_version() -> str:
    report = settings.latest_processed_dir / "report.json"
    try:
        data = json.loads(report.read_text(encoding="utf-8"))
        return str(data.get("version_dataset", "unknown"))
    except (OSError, json.JSONDecodeError):
        return "unknown"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.dataset_version = _load_dataset_version()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Buscador de Colegios de Chile",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    register_exception_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[f"http://localhost:{settings.frontend_port}", "http://127.0.0.1:4321"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in ALL_ROUTERS:
        app.include_router(router, prefix=API_PREFIX)

    return app


app = create_app()
