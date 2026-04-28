from typing import Any
from functools import wraps
from collections.abc import Callable, Awaitable

import httpx
from pybreaker import (
    STATE_OPEN,
    STATE_CLOSED,
    STATE_HALF_OPEN,
    CircuitBreaker,
    CircuitBreakerState,
    CircuitBreakerListener,
)

from app.lib.logging import logger

from .retry import with_retry
from .openai_client import openai_client


class OpenAIBreakerListener(CircuitBreakerListener):
    """Listener for OpenAI circuit breaker state changes."""

    def state_change(
        self,
        cb: CircuitBreaker,
        old_state: CircuitBreakerState | None,
        new_state: CircuitBreakerState,
    ) -> None:
        """Log circuit breaker state changes."""
        if new_state.name == STATE_OPEN:
            logger.warning("⚠️  OpenAI circuit breaker OPENED — requests will fail fast")
        elif new_state.name == STATE_HALF_OPEN:
            logger.info("🔄  OpenAI circuit breaker HALF-OPEN — testing recovery")
        elif new_state.name == STATE_CLOSED:
            logger.info("✅  OpenAI circuit breaker CLOSED — normal operation")


openai_breaker = CircuitBreaker(
    fail_max=5, reset_timeout=30, listeners=[OpenAIBreakerListener()]
)


def _breaker_with_wraps[**P, R](
    func: Callable[P, Awaitable[R]],
) -> Callable[P, Awaitable[R]]:
    protected = openai_breaker(func)  # type: ignore

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return await protected(*args, **kwargs)  # type: ignore

    return wrapper


@_breaker_with_wraps
async def call_openai(path: str, **body: Any) -> httpx.Response:
    """Call OpenAI API with circuit breaker protection."""

    async def call() -> httpx.Response:
        return await openai_client.post(path, json=body)

    return await with_retry(call)
