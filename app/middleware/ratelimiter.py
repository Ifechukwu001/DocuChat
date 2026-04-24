from typing import Annotated
from collections.abc import Callable, Awaitable

from fastapi import Depends, Request
from pyrate_limiter import Rate, Limiter, Duration, RedisBucket
from fastapi_limiter.depends import RateLimiter

from app.lib.cache import hash_key, sync_cache_redis
from app.lib.exceptions import RateLimitErrorResponse
from app.middleware.auth import UserInfo, authenticate


def create_limiter(
    window_sec: int,
    max: int,
    message: str,
    key_generator: Callable[[Request], str] | None = None,
) -> Callable[[], Awaitable[RateLimiter]]:
    """Factory function to create a RateLimiter."""

    async def default_key_generator(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0]
        elif request.client:
            ip = request.client.host
        else:
            ip = "anonymous"

        return ip

    def callback(
        *args: object, **kwargs: object
    ) -> None:  # TODO: Add headers to the callback response
        raise RateLimitErrorResponse(status=429, message=message)

    return RateLimiter(
        limiter=Limiter(
            RedisBucket.init(
                rates=[Rate(max, Duration.SECOND * window_sec)],
                redis=sync_cache_redis,
                bucket_key=hash_key(message),
            )  # type: ignore
        ),
        identifier=key_generator or default_key_generator,
        callback=callback,
    )


auth_limiter = create_limiter(
    window_sec=15 * 60,  # 15 minutes
    max=10,
    message="Too many auth attempts. Please try again later.",
)


def api_tier_max(user: Annotated[UserInfo, Depends(authenticate)]) -> int:
    """Determine max requests based on user tier."""
    tier_limits = {
        "free": 100,
        "pro": 500,
        "enterprise": 2000,
    }
    return tier_limits.get(user["tier"], 100)  # Default to free tier limit


api_limiter = create_limiter(
    window_sec=15 * 60,  # 1 minute
    max=Depends(api_tier_max),
    message="Rate limit exceeded. Please slow down.",
)


def upload_tier_max(user: Annotated[UserInfo, Depends(authenticate)]) -> int:
    """Determine max requests based on user tier."""
    tier_limits = {
        "free": 5,
        "pro": 50,
        "enterprise": 500,
    }
    return tier_limits.get(user["tier"], 5)  # Default to free tier limit


upload_limiter = create_limiter(
    window_sec=60 * 60,  # 1 hour
    max=Depends(upload_tier_max),
    message="Upload limit reached. Please try again later.",
)


def chat_tier_max(user: Annotated[UserInfo, Depends(authenticate)]) -> int:
    """Determine max requests based on user tier."""
    tier_limits = {
        "free": 10,
        "pro": 30,
        "enterprise": 100,
    }
    return tier_limits.get(user["tier"], 10)  # Default to free tier limit


chat_limiter = create_limiter(
    window_sec=60,  # 1 minute
    max=Depends(chat_tier_max),
    message="Too many queries. Please slow down.",
)
