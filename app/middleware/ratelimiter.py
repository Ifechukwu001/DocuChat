from collections.abc import Callable

from fastapi import Request, Response
from pyrate_limiter import Rate, Limiter, Duration, RedisBucket
from fastapi_limiter.depends import RateLimiter as BaseRateLimiter

from app.lib.cache import hash_key, sync_cache_redis
from app.lib.exceptions import RateLimitErrorResponse


class RateLimiter:
    """RateLimiter middleware."""

    def __init__(
        self,
        window_sec: int,
        message: str,
        max: int = 0,
        tiers: dict[str, int] | None = None,
        key_generator: Callable[[Request], str] | None = None,
    ) -> None:
        """Initialize RateLimiter."""
        if (not tiers and max <= 0) or (
            tiers and any(limit <= 0 for limit in tiers.values())
        ):
            raise ValueError("Max requests must be greater than 0")

        self.message = message

        if tiers:
            self._tiers: dict[str, BaseRateLimiter] = {}
            for tier, limit in tiers.items():
                self._tiers[tier] = BaseRateLimiter(
                    limiter=Limiter(
                        RedisBucket.init(
                            rates=[Rate(limit, Duration.SECOND * window_sec)],
                            redis=sync_cache_redis,
                            bucket_key=hash_key(message, tier),
                        )  # type: ignore
                    ),
                    identifier=key_generator or self._default_key_generator,
                    callback=self._callback,
                )
        else:
            self._limiter = BaseRateLimiter(
                limiter=Limiter(
                    RedisBucket.init(
                        rates=[Rate(max, Duration.SECOND * window_sec)],
                        redis=sync_cache_redis,
                        bucket_key=hash_key(message),
                    )  # type: ignore
                ),
                identifier=key_generator or self._default_key_generator,
                callback=self._callback,
            )

    async def __call__(
        self,
        request: Request,
        response: Response,
    ) -> None:
        """Apply rate limiting based on user tier or global limit."""
        if hasattr(self, "_tiers"):
            tier = (
                request.state.user_tier
                if hasattr(request.state, "user_tier")
                else "free"
            )
            limiter = self._tiers.get(tier)
            if not limiter:
                return self._callback(request, response)

            await limiter(request, response)

        else:
            await self._limiter(request, response)

    async def _default_key_generator(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0]
        elif request.client:
            ip = request.client.host
        else:
            ip = "anonymous"

        return ip

    def _callback(
        self, *args: object, **kwargs: object
    ) -> None:  # TODO: Add headers to the callback response
        raise RateLimitErrorResponse(status=429, message=self.message)


auth_limiter = RateLimiter(
    window_sec=15 * 60,  # 15 minutes
    max=10,
    message="Too many auth attempts. Please try again later.",
)


api_limiter = RateLimiter(
    window_sec=15 * 60,  # 15 minutes
    tiers={"free": 100, "pro": 500, "enterprise": 2000},
    message="Rate limit exceeded. Please slow down.",
)


upload_limiter = RateLimiter(
    window_sec=60 * 60,  # 1 hour
    tiers={"free": 5, "pro": 50, "enterprise": 500},
    message="Upload limit reached. Please try again later.",
)


chat_limiter = RateLimiter(
    window_sec=60,  # 1 minute
    tiers={"free": 10, "pro": 30, "enterprise": 100},
    message="Too many queries. Please slow down.",
)
