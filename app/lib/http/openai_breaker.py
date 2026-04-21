from typing import Any

from pybreaker import (
    STATE_OPEN,
    STATE_CLOSED,
    STATE_HALF_OPEN,
    CircuitBreaker,
    CircuitBreakerState,
    CircuitBreakerListener,
)

from .retry import with_retry
from .openai_client import openai_client


class OpenAIBreakerListener(CircuitBreakerListener):
    def state_change(
        self,
        cb: CircuitBreaker,
        old_state: CircuitBreakerState | None,
        new_state: CircuitBreakerState,
    ) -> None:
        if new_state.name == STATE_OPEN:
            print("⚠️  OpenAI circuit breaker OPENED — requests will fail fast")
        elif new_state.name == STATE_HALF_OPEN:
            print("🔄  OpenAI circuit breaker HALF-OPEN — testing recovery")
        elif new_state.name == STATE_CLOSED:
            print("✅  OpenAI circuit breaker CLOSED — normal operation")


openai_breaker = CircuitBreaker(
    fail_max=5, reset_timeout=30, listeners=[OpenAIBreakerListener()]
)


@openai_breaker
async def call_openai(path: str, **body: Any):
    async def call():
        await openai_client.post(path, json=body)

    return await with_retry(call)
