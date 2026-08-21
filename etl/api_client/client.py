import time
from typing import Any

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from config.settings import settings
from etl.api_client.rate_limiter import RateLimiter

logger = structlog.get_logger()


class APIError(Exception):
    pass


class APIClient:
    def __init__(self) -> None:
        self.rate_limiter = RateLimiter(
            max_concurrent=settings.max_concurrent_requests,
            base_delay=settings.request_delay_seconds,
        )
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=settings.api_base_url,
                timeout=httpx.Timeout(settings.request_timeout),
                headers={
                    "User-Agent": settings.user_agent,
                    "Accept": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError, APIError)),
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential_jitter(initial=1, max=60, jitter=2),
        reraise=True,
    )
    async def _request(self, path: str, **kwargs: Any) -> httpx.Response:
        await self.rate_limiter.acquire()
        try:
            await self.rate_limiter.delay()
            client = await self._get_client()

            start = time.monotonic()
            response = await client.get(path, **kwargs)
            duration_ms = (time.monotonic() - start) * 1000

            self.rate_limiter.record_response(response.status_code, duration_ms)

            logger.debug(
                "api_request",
                path=path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 1),
            )

            if response.status_code == 429:
                raise APIError(f"Rate limited on {path}")

            response.raise_for_status()
            return response

        finally:
            self.rate_limiter.release()

    async def get_comunas(self) -> list[dict[str, Any]]:
        client = await self._get_client()
        response = await client.get(settings.comunas_api_url)
        response.raise_for_status()
        return response.json()

    async def get_establecimientos_por_comuna(self, comuna: str) -> list[dict[str, Any]]:
        response = await self._request(f"/sae-api-vitrina/v1/establecimientos?comuna={comuna}")
        return response.json()

    async def get_detalle_establecimiento(self, rbd: int) -> dict[str, Any]:
        response = await self._request(f"/sae-api-vitrina/v1/establecimientos/{rbd}")
        return response.json()
