import json
from enum import StrEnum
from typing import Any
from datetime import UTC, datetime

from app.lib.events import APP_EVENTS
from app.orm.models import User, UsageLog, Conversation
from app.lib.logging import logger


class AuthEvents(StrEnum):
    """Auth Events Enum."""

    USER_REGISTERED = "auth:user-registered"
    USER_LOGGED_IN = "auth:user-logged-in"
    USER_LOGGED_OUT = "auth:user-logged-out"
    TOKEN_REFRESHED = "auth:token-refreshed"  # noqa: S105
    LOGIN_FAILED = "auth:login-failed"


@APP_EVENTS.on(AuthEvents.USER_REGISTERED)
async def handle_log_registration(user: User) -> None:
    """Handle user registered event."""
    try:
        await UsageLog.create(
            user_id=user.id,
            action="signup",
            tokens=0,
            cost_usd=0,
            metadata=json.dumps(
                {
                    "email": user.email,
                    "tier": user.tier,
                    "registered_at": datetime.now(UTC).isoformat(),
                }
            ),
        )
    except Exception as e:
        logger.error("Failed to log signup", exc_info=e)


@APP_EVENTS.on(AuthEvents.USER_REGISTERED)
async def handle_conversation(user: User) -> None:
    """Handle user logged in event."""
    try:
        await Conversation.create(user_id=user.id, title="Welcome to DocuChat")
    except Exception as e:
        logger.error("Failed to create welcome conversation", exc_info=e)


@APP_EVENTS.on(AuthEvents.USER_LOGGED_IN)
async def handle_log_login(**data: Any) -> None:
    """Handle user logged in event."""
    try:
        await UsageLog.create(
            user_id=data.get("user_id"),
            action="login",
            tokens=0,
            cost_usd=0,
            metadata=json.dumps(
                {
                    "device_info": data.get("device_info"),
                    "login_at": datetime.now(UTC).isoformat(),
                }
            ),
        )
    except Exception as e:
        logger.error("Failed to log login", exc_info=e)


@APP_EVENTS.on(AuthEvents.LOGIN_FAILED)
async def handle_log_failed_login(**data: Any) -> None:
    """Handle failed login event."""
    try:
        logger.error(
            f"Failed login attempt for {data.get('email')} from {data.get('device_info')}"
        )
    except Exception as e:
        logger.error("Failed to log failed login", exc_info=e)
