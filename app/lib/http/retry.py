import asyncio
from collections.abc import Callable, Awaitable

import httpx

from app.lib.logging import logger


def is_retriable(error: httpx.HTTPError) -> bool:
    """Determine if an HTTP error is retriable."""
    if isinstance(error, httpx.TimeoutException) or isinstance(
        error, httpx.NetworkError
    ):
        return True

    if isinstance(error, httpx.HTTPStatusError) and (
        error.response.status_code in {408, 429} or error.response.status_code >= 500
    ):
        return True

    return False


async def delay(secs: int) -> None:
    """Delay before retrying a request."""
    await asyncio.sleep(secs)


async def with_retry[T](
    operation: Callable[[], Awaitable[T]],
    max_attempts: int = 3,
    base_delay_secs: int = 1,
) -> T:
    """Execute an operation with retry logic."""
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await operation()
        except Exception as error:
            last_error = error

            if (not isinstance(error, httpx.HTTPError)) or (not is_retriable(error)):
                raise

            if attempt == max_attempts:
                raise

            retry_after = (
                getattr(error, "response", {}).get("headers", {}).get("Retry-After")
            )
            delay_secs = (
                int(retry_after)
                if retry_after and retry_after.isdigit()
                else base_delay_secs * (2 ** (attempt - 1))
            )

            logger.warning(
                f"Attempt {attempt} failed with retriable error: {error}. "
                f"Retrying in {delay_secs} seconds..."
            )

            await delay(delay_secs)

    raise last_error if last_error else Exception("Operation failed after retries")
