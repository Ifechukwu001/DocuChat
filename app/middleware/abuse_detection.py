import re
from typing import Annotated

from fastapi import Depends, Request

from app.lib.cache import cache_redis
from app.lib.logging import logger
from app.middleware.auth import UserInfo, authenticate


async def track_suspicious_activity(
    user: Annotated[UserInfo, Depends(authenticate)], request: Request
) -> None:
    """Middleware to track suspicious activity based on document access patterns."""
    user_id = user["id"]

    if re.match(r"/documents/[\w-]+$", request.url.path):
        key = f"access_pattern:{user_id}"
        doc_id = request.path_params.get("id")

        if doc_id:
            await cache_redis.sadd(key, doc_id)  # type: ignore
            await cache_redis.expire(key, 300)  # 5 minute window

            unique_docs = await cache_redis.scard(key)  # type: ignore
            if unique_docs > 50:
                # Flag user for review - In production, this could trigger an alert or further investigation
                logger.warning(
                    f"Suspicious: user {user_id} accessed {unique_docs} unique documents in 5 min"
                )
