import asyncio
import random
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger()


@dataclass
class RateLimiter:
    max_concurrent: int
    base_delay: float
    _5xx_pause: float = 30.0
    semaphore: asyncio.Semaphore = field(init=False)
    _consecutive_429: int = field(default=0, init=False)
    _consecutive_5xx: int = field(default=0, init=False)
    _response_times: list[float] = field(default_factory=list, init=False)

    def __post_init__(self):
        self.semaphore = asyncio.Semaphore(self.max_concurrent)

    @property
    def current_concurrency(self) -> int:
        return self.max_concurrent - self.semaphore._value

    async def acquire(self) -> None:
        await self.semaphore.acquire()

    def release(self) -> None:
        self.semaphore.release()

    def record_response(self, status_code: int, duration_ms: float) -> None:
        self._response_times.append(duration_ms)
        if len(self._response_times) > 50:
            self._response_times.pop(0)

        if status_code == 429:
            self._consecutive_429 += 1
            self._consecutive_5xx = 0
        elif status_code >= 500:
            self._consecutive_5xx += 1
            self._consecutive_429 = 0
        else:
            self._consecutive_429 = 0
            self._consecutive_5xx = 0

    async def delay(self) -> None:
        delay = self.base_delay

        if self._consecutive_429 >= 2:
            delay = max(delay * 4, 5.0)
            logger.warning(
                "rate_limit_backoff",
                consecutive_429=self._consecutive_429,
                delay=delay,
            )

        if self._consecutive_5xx >= 3:
            logger.warning(
                "server_error_pause",
                consecutive_5xx=self._consecutive_5xx,
                pause=self._5xx_pause,
            )
            await asyncio.sleep(self._5xx_pause)
            self._consecutive_5xx = 0
            return

        if self._response_times:
            avg = sum(self._response_times) / len(self._response_times)
            if avg > 2000:
                delay = max(delay * 2, 2.0)

        jitter = random.uniform(0, delay * 0.5)
        await asyncio.sleep(delay + jitter)
