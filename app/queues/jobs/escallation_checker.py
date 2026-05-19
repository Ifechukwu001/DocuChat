import asyncio

from bullmq import Queue  # type: ignore

from app.env import settings

escallation_queue = Queue(
    "escalation-checker",
    {"connection": settings.REDIS_URL},
)


asyncio.create_task(
    escallation_queue.add(  # pyright: ignore[reportUnknownMemberType]
        name="process-document",
        data={},
    )
).result()
