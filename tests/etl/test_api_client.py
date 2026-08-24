import asyncio

import pytest
from etl.api_client.rate_limiter import RateLimiter


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_acquire_release(self):
        rl = RateLimiter(max_concurrent=2, base_delay=0.01)
        assert rl.current_concurrency == 0
        await rl.acquire()
        assert rl.current_concurrency == 1
        rl.release()
        assert rl.current_concurrency == 0

    @pytest.mark.asyncio
    async def test_delay_increases_on_429(self):
        rl = RateLimiter(max_concurrent=5, base_delay=0.01)
        rl.record_response(429, 100)
        rl.record_response(429, 100)
        start = asyncio.get_event_loop().time()
        await rl.delay()
        elapsed = asyncio.get_event_loop().time() - start
        assert elapsed >= 0.04

    @pytest.mark.asyncio
    async def test_pause_on_consecutive_5xx(self):
        rl = RateLimiter(max_concurrent=5, base_delay=0.01, _5xx_pause=0.05)
        for _ in range(3):
            rl.record_response(500, 100)
        start = asyncio.get_event_loop().time()
        await rl.delay()
        elapsed = asyncio.get_event_loop().time() - start
        assert elapsed >= 0.05
