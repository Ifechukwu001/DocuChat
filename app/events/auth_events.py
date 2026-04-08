import json
from enum import StrEnum
from typing import Any
from datetime import datetime

from iso8601 import UTC

from app.lib.events import APP_EVENTS
from app.orm.models import User, UsageLog, Conversation


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
        print(f"Failed to log signup: {e}")


@APP_EVENTS.on(AuthEvents.USER_REGISTERED)
async def handle_conversation(user: User) -> None:
    """Handle user logged in event."""
    try:
        await Conversation.create(user_id=user.id, title="Welcome to DocuChat")
    except Exception as e:
        print(f"Failed to create welcome conversation: {e}")


@APP_EVENTS.on(AuthEvents.USER_LOGGED_IN)
async def handle_log_login(data: Any) -> None:  # noqa: ANN401
    """Handle user logged in event."""
    try:
        await UsageLog.create(
            user_id=data.user_id,
            action="login",
            tokens=0,
            cost_usd=0,
            metadata=json.dumps(
                {
                    "device_info": data.device_info,
                    "login_at": datetime.now(UTC).isoformat(),
                }
            ),
        )
    except Exception as e:
        print(f"Failed to log login: {e}")


@APP_EVENTS.on(AuthEvents.LOGIN_FAILED)
async def handle_log_failed_login(data: Any) -> None:  # noqa: ANN401
    """Handle failed login event."""
    try:
        print(f"Failed login attempt for {data.email} from {data.device_info}")
    except Exception as e:
        print(f"Failed to log failed login: {e}")
