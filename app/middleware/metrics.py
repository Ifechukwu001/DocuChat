import re

from fastapi import Request
from starlette.types import Send, Scope, ASGIApp, Message, Receive

from app.lib.metrics import http_requests_total, http_request_duration


class MetricsMiddleware:
    """Metrics Middleware."""

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the middleware."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Log the incoming request."""
        if scope["type"] == "http":
            request = Request(scope)

            with http_request_duration.labels(
                method=request.method,
                path=self._normalize_path(request.url.path),
            ).time():

                async def send_wrapper(message: Message) -> None:
                    if message["type"] == "http.response.start":
                        http_requests_total.labels(
                            method=request.method,
                            path=self._normalize_path(request.url.path),
                            status_code=int(message.get("status", 0)),
                        ).inc()

                    await send(message)

                await self.app(scope, receive, send_wrapper)

        else:
            await self.app(scope, receive, send)

    def _normalize_path(self, path: str) -> str:
        """Normalize the path for metrics labeling."""
        # Normalize UUID and numeric ID patterns in path
        path = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", ":id", path
        )
        path = re.sub(r"/\d+", "/:num", path)
        return path
