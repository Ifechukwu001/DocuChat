import json
import asyncio
import hashlib
from enum import IntEnum
from typing import cast
from collections.abc import Callable, Awaitable

from redis.asyncio import StrictRedis

from app.env import settings

cache_redis = StrictRedis.from_url(settings.REDIS_URL, decode_responses=True)  # type: ignore


class CACHE_TTL(IntEnum):
    """TTL constants in seconds."""

    PERMISSIONS = 300  # 5 minutes
    DOCUMENT = 600  # 10 minutes
    CONVERSATION_LIST = 120  # 2 minutes
    EMBEDDING = 604800  # 7 days
    RAG_RESULT = 3600  # 1 hour


def prefix_key(key: str) -> str:
    """Prefix the cache key to avoid collisions."""
    return f"docuchat:{key}"


async def cache_get[T](key: str, type: type[T]) -> T | None:
    """Get a value from the cache."""
    prefixed_key = prefix_key(key)
    raw = await cache_redis.get(prefixed_key)
    if not raw:
        return None

    try:
        return cast(T, json.loads(raw))
    except Exception:
        return None


async def cache_set(key: str, value: object, ttl_seconds: int) -> None:
    """Set a value in the cache with a TTL."""
    prefixed_key = prefix_key(key)
    raw = json.dumps(value)
    await cache_redis.set(prefixed_key, raw, ex=ttl_seconds)


async def cache_del(key: str) -> None:
    """Delete a value from the cache."""
    prefixed_key = prefix_key(key)
    await cache_redis.delete(prefixed_key)


async def cache_del_pattern(pattern: str) -> None:
    """Delete multiple keys from the cache matching a pattern.

    Use SCAN, never KEYS (KEYS blocks Redis on large datasets)
    """
    prefixed_pattern = prefix_key(pattern)
    stream = cache_redis.scan_iter(prefixed_pattern, count=100)  # type: ignore
    pipline = cache_redis.pipeline()

    async for keys in stream:  # type: ignore
        for key in keys:  # type: ignore
            pipline.delete(key)  # type: ignore

    await pipline.execute()


def hash_key(*args: str) -> str:
    """Create a cache key by hashing the input arguments."""
    data = ":".join(args)
    return hashlib.sha256(data.encode()).hexdigest()[:16]


async def cache_get_or_set[T](
    key: str, type: type[T], ttl_seconds: int, fetch_func: Callable[[], Awaitable[T]]
) -> T:
    """Get a value from the cache or compute and set it if not present."""
    cached = await cache_get(key, type)
    if cached is not None:
        return cached

    lock_key = f"lock:{prefix_key(key)}"
    acquired = await cache_redis.set(lock_key, "1", ex=5, nx=True)  # type: ignore

    if acquired:
        try:
            value = await fetch_func()
            await cache_set(key, value, ttl_seconds)
            return value
        finally:
            await cache_redis.delete(lock_key)

    await asyncio.sleep(0.1)

    retried = await cache_get(key, type)
    if retried is not None:
        return retried

    return await fetch_func()
