from bullmq import Queue  # type: ignore


from app.env import settings


dead_letter_queue = Queue("dead-letter", {"connection": settings.REDIS_URL})
