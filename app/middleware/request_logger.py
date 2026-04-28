from uuid import uuid4
from datetime import UTC, datetime

from fastapi import Request
from starlette.types import Send, Scope, ASGIApp, Message, Receive
from starlette.datastructures import MutableHeaders

from app.lib.logging import logger


class RequestLoggerMiddleware:
    """Request Logger Middleware."""

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the middleware."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Log the incoming request."""
        if scope["type"] == "http":
            request = Request(scope)

            correlation_id = request.headers.get("X-Correlation-ID", uuid4().hex)
            request.state.correlation_id = correlation_id

            start_time = datetime.now(UTC)

            logger.info(
                "Request received",
                correlation_id=correlation_id,
                method=request.method,
                path=request.url.path,
                ip=request.client.host if request.client else "unknown",
                user_agent=str(request.headers.get("User-Agent", "unknown")),
            )

            async def send_wrapper(message: Message) -> None:
                if message["type"] == "http.response.start":
                    headers = MutableHeaders(scope=message)
                    headers["X-Correlation-ID"] = correlation_id

                    duration = (datetime.now(UTC) - start_time).total_seconds()
                    log_data = dict(
                        correlation_id=correlation_id,
                        method=request.method,
                        path=request.url.path,
                        status_code=int(message.get("status", 0)),
                        duration_secs=duration,
                        user_id=getattr(request.state, "user_id", "anonymous"),
                    )

                    if message["status"] >= 500:
                        logger.error("Request failed", **log_data)
                    elif message["status"] >= 400:
                        logger.warning("Request client error", **log_data)
                    else:
                        logger.info("Request completed", **log_data)

                await send(message)

            await self.app(scope, receive, send_wrapper)

        else:
            await self.app(scope, receive, send)
