from bullmq import Queue  # type: ignore

from app.env import settings

embedding_queue = Queue(
    "embedding-generation",
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
