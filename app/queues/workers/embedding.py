# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportArgumentType=false
import asyncio
from datetime import UTC, datetime

from bullmq import Job, Worker  # type: ignore

from app.env import settings
from app.lib.logging import logger
from app.queues.jobs import dead_letter_queue
from app.lib.http.openai_breaker import call_openai

worker: Worker | None = None


async def worker_function(job: Job, token: str) -> dict[str, object]:
    """Worker function to process document-processing tasks."""
    return call_openai(
        "/embeddings",
        input=job.data.text,
        model="text-embedding-3-small",
    )


def completed_function(job: Job) -> None:
    """Handle successful completion of a job."""
    logger.info(
        f"Job {job.id} completed: {job.returnvalue.get('chunks') if job.returnvalue else ''} chunks"
    )


def failed_function(job: Job | None, error: Exception) -> None:
    """Handle failed job attempts."""
    if not job:
        return

    if job.attemptsMade >= job.opts.get("attempts", 3):
        logger.error(f"Job {job.id} permanently failed. Moving to DLQ.")

        asyncio.create_task(
            dead_letter_queue.add(
                "dead-letter",
                {
                    "original_job_id": job.id,
                    "original_queue": "document-processing",
                    "data": job.data,
                    "error": str(error),
                    "failed_at": datetime.now(UTC).isoformat(),
                    "attempts": job.attemptsMade,
                },
            )
        ).result()


def error_function(error: Exception, job: Job) -> None:
    """Handle unexpected errors in the worker."""
    logger.error("Worker error", exc_info=error)


def start_worker() -> Worker:
    """Start and return the document processing worker."""
    global worker

    if worker is not None:
        return worker

    worker = Worker(
        "embedding-generation",
        worker_function,
        {
            "connection": settings.REDIS_URL,
            "concurrency": 5,
            # "limiter": {"max": 100, "duration": 60000},  # noqa: ERA001
        },
    )

    worker.on("completed", completed_function)
    worker.on("failed", failed_function)
    worker.on("error", error_function)

    return worker
