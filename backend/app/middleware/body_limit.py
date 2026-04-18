"""Request body size limit middleware."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

DEFAULT_MAX_BODY_BYTES = 1 * 1024 * 1024  # 1 MB


class BodyLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length exceeds the configured limit."""

    def __init__(self, app, *, max_bytes: int = DEFAULT_MAX_BODY_BYTES):
        super().__init__(app)
        self._max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit():
            if int(content_length) > self._max_bytes:
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Request body too large. Limit is {self._max_bytes} bytes."},
                )
        return await call_next(request)
