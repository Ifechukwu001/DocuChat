import json
from enum import StrEnum
from typing import Any
from datetime import datetime, UTC

from app.lib.events import APP_EVENTS
from app.orm.models import UsageLog


class DocEvents(StrEnum):
    """Document Events Enum."""

    DOCUMENT_CREATED = "doc:created"
    DOCUMENT_PROCESSED = "doc:processed"
    DOCUMENT_DELETED = "doc:deleted"


@APP_EVENTS.on(DocEvents.DOCUMENT_CREATED)
async def handle_log_creation(data: dict[str, Any]) -> None:
    """Handle document created event."""
    try:
        await UsageLog.create(
            user_id=data.get("user_id"),
            action="document_created",
            tokens=0,
            cost_usd=0,
            metadata=json.dumps(
                {
                    "document": data.get("document_id"),
                    "title": data.get("title"),
                    "file_size_bytes": data.get("file_size_bytes"),
                }
            ),
        )
    except Exception as e:
        print(f"Failed to log document creation: {e}")


@APP_EVENTS.on(DocEvents.DOCUMENT_DELETED)
async def handle_log_deletion(data: dict[str, Any]) -> None:
    """Handle document deleted event."""
    try:
        await UsageLog.create(
            user_id=data.get("deleted_by"),
            action="document_deleted",
            tokens=0,
            cost_usd=0,
            metadata=json.dumps(
                {
                    "document": data.get("document_id"),
                    "title": data.get("title"),
                    "deleted_at": datetime.now(UTC).isoformat(),
                }
            ),
        )
    except Exception as e:
        print(f"Failed to log document deletion: {e}")
