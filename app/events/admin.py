import json
from enum import StrEnum
from typing import Any
from datetime import UTC, datetime

from app.lib.events import APP_EVENTS
from app.orm.models import UsageLog


class AdminEvents(StrEnum):
    """Admin Events Enum."""

    ROLE_ASSIGNED = "admin:role_assigned"
    ROLE_REVOKED = "admin:role_revoked"


@APP_EVENTS.on(AdminEvents.ROLE_ASSIGNED)
async def handle_log_registration(**data: Any) -> None:
    """Handle user registered event."""
    try:
        await UsageLog.create(
            user_id=data.get("assigned_by"),
            action="role_assigned",
            tokens=0,
            cost_usd=0,
            metadata=json.dumps(
                {
                    "target_user_id": data.get("target_user_id"),
                    "role_name": data.get("role_name"),
                    "assigned_at": datetime.now(UTC).isoformat(),
                }
            ),
        )
    except Exception as e:
        print(f"Failed to log role assignment: {e}")


@APP_EVENTS.on(AdminEvents.ROLE_REVOKED)
async def handle_role_revocation(**data: Any) -> None:
    """Handle role revoked event."""
    try:
        await UsageLog.create(
            user_id=data.get("revoked_by"),
            action="role_revoked",
            tokens=0,
            cost_usd=0,
            metadata=json.dumps(
                {
                    "target_user_id": data.get("target_user_id"),
                    "role_name": data.get("role_name"),
                    "revoked_at": datetime.now(UTC).isoformat(),
                }
            ),
        )
    except Exception as e:
        print(f"Failed to log role revocation: {e}")
