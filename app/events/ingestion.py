import json
from typing import Any

from app.lib.events import APP_EVENTS
from app.orm.models import UsageLog
from app.lib.logging import logger
from app.lib.metrics import document_processed

from .document import DocEvents


@APP_EVENTS.on(DocEvents.DOCUMENT_PROCESSED)
async def handle_log_processed(data: dict[str, Any]) -> None:
    """Handle document processed event."""
    try:
        await UsageLog.create(
            user_id=data.get("user_id"),
            action="document_ingested",
            tokens=0,
            cost_usd=0,  # Will be updated by embedding events
            metadata=json.dumps(
                {
                    "document_id": data.get("document_id"),
                    "chunk_count": data.get("chunk_count"),
                    "duration_seconds": data.get("duration_seconds"),
                    "format": data.get("format"),
                    "page_count": data.get("page_count"),
                }
            ),
        )
        document_processed.labels(status="success").inc()
        logger.info(
            "Ingestion logged",
            document_id=data.get("document_id"),
            chunk_count=data.get("chunk_count"),
            correlation_id=data.get("correlation_id"),
        )
    except Exception as e:
        logger.error("Failed to log ingestion", exc_info=e)
