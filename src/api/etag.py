"""Caché HTTP basada en ETag para endpoints de lectura estables.

El ETag se deriva de `dataset_version + path + query string`, NO del cuerpo de
la respuesta. Así, un request condicional (`If-None-Match`) puede responderse
con `304 Not Modified` **antes** de tocar PostgreSQL (decisión #12 de
ARCHITECTURE_v2: la invalidación es instantánea al re-ejecutar el ETL, porque
cambia `dataset_version`).

Queda fuera de alcance `search`: es una query dinámica (FTS + paginación) con
un hit-rate de caché cercano a cero.
"""
from __future__ import annotations

import hashlib

from fastapi import Request, Response

# Política por defecto para datos dinámicos (ficha, listados, compare):
# cacheable pero revalidar en cada uso. Los datos de referencia usan una
# caché pública larga (ver `src/api/routers/referencia.py`).
REVALIDATE = "public, max-age=0, must-revalidate"


def build_etag(request: Request) -> str:
    """ETag estable por recurso: versiona por dataset y URL (path + query)."""
    version = getattr(request.app.state, "dataset_version", "unknown")
    query = request.scope.get("query_string", b"").decode()
    raw = f"{version}|{request.url.path}|{query}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return f'"{digest}"'


def apply_etag(
    request: Request,
    response: Response,
    *,
    cache_control: str = REVALIDATE,
) -> Response | None:
    """Fija `ETag` + `Cache-Control` y devuelve `Response(304)` si hay match.

    Devuelve `None` cuando el request debe continuar normalmente. El handler
    debe retornar el `Response` devuelto por esta función sin tocarlo.
    """
    tag = build_etag(request)
    response.headers["ETag"] = tag
    response.headers["Cache-Control"] = cache_control
    if request.headers.get("if-none-match") == tag:
        return Response(status_code=304, headers={"ETag": tag})
    return None
