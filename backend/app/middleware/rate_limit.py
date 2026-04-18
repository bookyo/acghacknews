"""Rate limiting middleware using in-memory sliding window."""

import time
from collections import defaultdict
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimiter:
    """Sliding window rate limiter tracked by client IP."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        # Evict expired entries
        self._hits[key] = [t for t in self._hits[key] if t > cutoff]
        if len(self._hits[key]) >= self.max_requests:
            return False
        self._hits[key].append(now)
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply rate limiting to matching path prefixes."""

    def __init__(
        self,
        app,
        *,
        path_prefixes: list[str] | None = None,
        max_requests: int = 10,
        window_seconds: int = 60,
    ):
        super().__init__(app)
        self._prefixes = path_prefixes or []
        self._limiter = RateLimiter(max_requests, window_seconds)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Only rate-limit paths that match configured prefixes
        if self._prefixes and not any(
            request.url.path.startswith(p) for p in self._prefixes
        ):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        if not self._limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
            )

        return await call_next(request)
