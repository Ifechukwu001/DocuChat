import json
from typing import Any
from datetime import UTC, datetime

from fastapi import Depends, Request, APIRouter, BackgroundTasks, status

from app.env import settings
from app.orm.models import WebhookEvent
from app.responses.envelope import (
    ErrorResponse,
    ValidationErrorResponse,
)
from app.lib.response_formatter import success_response
from app.middleware.verify_webhook import verify_webhook_signature

router = APIRouter()


@router.post(
    "/example",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ValidationErrorResponse},
    },
    dependencies=[
        Depends(
            verify_webhook_signature(
                settings.EXAMPLE_WEBHOOK_SECRET, "X-Webhook-Signature"
            )
        )
    ],
)
async def example_webhook(request: Request, tasks: BackgroundTasks) -> dict[str, Any]:
    """Example webhook endpoint that verifies the signature and processes the payload."""
    event = await request.json()

    existing = await WebhookEvent.get_or_none(id=event.get("id"))

    if existing and existing.processed_at is not None:
        return success_response("Success", {"received": True, "duplicate": True})

    await WebhookEvent.get_or_create(  # type: ignore
        id=event.get("id"),
        defaults={
            "provider": "example",
            "event_type": event.get("type", "unknown"),
            "payload": json.dumps(event),
        },
    )

    async def process_event() -> None:
        try:
            await process_webhook_event(**event)
            await WebhookEvent.filter(id=event.get("id")).update(
                processed_at=datetime.now(UTC)
            )
        except Exception as e:
            print(f"`Webhook {event.get('id')} processing failed:", e)

    tasks.add_task(process_event)

    return success_response(
        "Webhook received", {"received": True, "duplicate": existing is not None}
    )


async def process_webhook_event(**event: Any) -> None:

    match event.get("type"):
        case "document:imported":
            # Queue document processing job
            pass
        case _:
            print(f"Unhandled webhook event type: {event.get('type')}")
