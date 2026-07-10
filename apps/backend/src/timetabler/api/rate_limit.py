from __future__ import annotations

import asyncio
import math
from collections import deque
from collections.abc import Callable
from time import monotonic


class RateLimitExceededError(RuntimeError):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(f"rate limit exceeded; retry after {retry_after_seconds} seconds")
        self.retry_after_seconds = retry_after_seconds


class SlidingWindowRateLimiter:
    """Per-process, per-client admission limiter for expensive public jobs.

    The database active-job cap remains the cross-process safety boundary. This
    limiter sheds repeated requests before they reach PostgreSQL.
    """

    def __init__(
        self,
        *,
        limit: int,
        window_seconds: float,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if limit < 1 or window_seconds <= 0:
            raise ValueError("rate limit and window must be positive")
        self._limit = limit
        self._window_seconds = window_seconds
        self._clock = clock
        self._events: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    async def consume(self, client_key: str) -> None:
        now = self._clock()
        cutoff = now - self._window_seconds
        async with self._lock:
            # Prune every client, not only the current bucket. Otherwise a stream
            # of one-shot unique IPs leaves a permanently growing key map.
            for key, values in list(self._events.items()):
                while values and values[0] <= cutoff:
                    values.popleft()
                if not values:
                    self._events.pop(key, None)
            events = self._events.setdefault(client_key, deque())
            if len(events) >= self._limit:
                retry_after = max(1, math.ceil(events[0] + self._window_seconds - now))
                raise RateLimitExceededError(retry_after)
            events.append(now)


def client_key_from_headers(cloudflare_ip: str | None, peer_host: str | None) -> str:
    """Use Cloudflare's edge-owned client header, then the direct socket peer.

    The public route is Cloudflare Tunnel, which overwrites ``CF-Connecting-IP``.
    The API port is internal-only, so header-bearing direct callers are trusted
    operators. We intentionally do not trust X-Real-IP/X-Forwarded-For because
    the current Nginx deployment does not overwrite those headers.
    """

    edge_client = (cloudflare_ip or "").strip()
    socket_peer = (peer_host or "").strip()
    return (edge_client or socket_peer or "local-unknown")[:128]
