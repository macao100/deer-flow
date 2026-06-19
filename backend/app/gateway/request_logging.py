"""
HTTP request/response logging middleware.
Logs method, path, status, duration for every request.
On 4xx/5xx: logs request body excerpt to aid debugging.
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("deerflow.http")

# Paths too noisy to log at INFO (Telegram polling, health checks)
_SKIP_PATHS = {"/health", "/api/telegram"}
_SKIP_PREFIXES = ("/api/telegram",)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Skip heartbeat / bot-polling noise
        if path in _SKIP_PATHS or any(path.startswith(p) for p in _SKIP_PREFIXES):
            return await call_next(request)

        start = time.perf_counter()
        body_hint = ""

        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error(
                "%s %s → EXCEPTION %.0f ms | %s: %s",
                request.method,
                path,
                elapsed,
                type(exc).__name__,
                exc,
                exc_info=True,
            )
            raise

        elapsed = (time.perf_counter() - start) * 1000
        status = response.status_code

        if status >= 500:
            level = logging.ERROR
        elif status >= 400:
            level = logging.WARNING
        else:
            level = logging.INFO

        logger.log(
            level,
            "%s %s → %d %.0f ms%s",
            request.method,
            path,
            status,
            elapsed,
            body_hint,
        )
        return response
