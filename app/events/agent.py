import json
from enum import StrEnum
from typing import Any

from app.lib.events import APP_EVENTS
from app.orm.models import UsageLog
from app.lib.logging import logger


class AgentEvents(StrEnum):
    """Agent Events Enum."""

    AGENT_COMPLETED = "agent:completed"


@APP_EVENTS.on(AgentEvents.AGENT_COMPLETED)
async def handle_agent_completed(**data: Any) -> None:
    """Handle agent completed event."""
    try:
        await UsageLog.create(
            user_id=data.get("user_id"),
            action="agent_run",
            tokens=data.get("total_tokens", 0),
            cost_usd=data.get("total_cost_usd", 0),
            metadata=json.dumps(
                {
                    "correlation_id": data.get("correlation_id"),
                    "iterations": data.get("iterations"),
                    "termination_reason": data.get("termination_reason"),
                    "tools_used": data.get("tools_used"),
                    "confidence": data.get("confidence"),
                    "duration_secs": data.get("duration_secs"),
                }
            ),
        )
    except Exception as e:
        logger.error("Failed to log agent completion", exc_info=e)
