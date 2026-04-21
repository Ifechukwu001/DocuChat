from datetime import UTC, datetime

from bullmq import Queue  # type: ignore

from app.env import settings

document_queue = Queue(
    "document-processing",
    {
        "connection": settings.REDIS_URL,
        "defaultJobOptions": {
            "attempts": 3,
            "backoff": {"type": "exponential", "delay": 2000},
            "removeOnComplete": {
                "count": 200  #  set to large number to remove all completed
            },
            "removeOnFail": {
                "count": 500  # Set to 0 or delete config to not remove failed jobs.
            },
        },
    },
)


async def queue_document_for_processing(document_id: str, user_id: str):
    """Add a document to the processing queue."""
    job = await document_queue.add(  # pyright: ignore[reportUnknownMemberType]
        name="process-document",
        data={
            "document_id": document_id,
            "user_id": user_id,
            "queued_at": datetime.now(UTC).isoformat(),
        },
    )

    return job.id
