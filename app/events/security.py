from typing import Any

from app.lib.cache import cache_redis
from app.lib.events import APP_EVENTS
from app.lib.logging import logger

from .auth import AuthEvents


@APP_EVENTS.on(AuthEvents.LOGIN_FAILED)
async def handle_log_failed_login(**data: Any) -> None:
    """Handle failed login event."""
    try:
        key = f"login-failures:{data.get('device_info')}"
        failures = await cache_redis.incr(key)

        if failures == 1:
            await cache_redis.expire(key, 900)  # 15 minute window

        if failures >= 5:
            logger.warning(
                f"Security: {failures} failed logins from {data.get('device_info')} for {data.get('email')}"
            )
            #  Could add the IP to a temporary block list here

        logger.info(
            f"Failed login attempt for {data.get('email')} from {data.get('device_info')}"
        )
    except Exception as e:
        logger.error("Failed to track login failure", exc_info=e)
