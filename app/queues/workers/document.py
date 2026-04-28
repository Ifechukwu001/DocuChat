# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportArgumentType=false
import asyncio
from uuid import UUID
from datetime import UTC, datetime

from bullmq import Job, Worker  # type: ignore
from tortoise import transactions

from app.env import settings
from app.lib.events import APP_EVENTS
from app.orm.models import Chunk, Document
from app.lib.chunker import estimate_tokens, split_into_chunks
from app.lib.logging import logger
from app.queues.jobs import dead_letter_queue

worker: Worker | None = None


async def worker_function(job: Job, token: str) -> dict[str, object]:
    """Worker function to process document-processing tasks."""
    document_id = job.data.get("document_id")
    user_id = job.data.get("user_id")
    logger.info(f"Processing document {document_id} (attempt {job.attemptsMade + 1})")

    document = await Document.get_or_none(id=UUID(str(document_id)))
    if not document:
        raise ValueError(f"Document with ID {document_id} not found")

    document.status = "processing"
    await document.save()

    try:
        await job.updateProgress(10)

        chunks = split_into_chunks(document.content, 500)
        await job.updateProgress(40)

        async with transactions.in_transaction():  # type: ignore
            await Chunk.filter(document_id=document.id).delete()

            await Chunk.bulk_create(
                [
                    Chunk(
                        document_id=document.id,
                        index=index,
                        content=text,
                        token_count=estimate_tokens(text),
                    )
                    for index, text in enumerate(chunks)
                ]
            )

            document.status = "ready"
            document.chunk_count = len(chunks)
            await document.save()

            await job.updateProgress(100)

            APP_EVENTS.emit(
                "doc:processed",
                {
                    "document_id": document_id,
                    "user_id": user_id,
                    "chunk_count": len(chunks),
                },
            )

            return {"status": "ready", "chunks": len(chunks)}

    except Exception as e:
        if job.attemptsMade >= job.opts.get("attempts", 3) - 1:
            document.status = "failed"
            document.error = str(e)
            await document.save()

        logger.error(f"Error processing document {document_id}: {e}")

        raise


def completed_function(job: Job) -> None:
    """Handle successful completion of a job."""
    logger.info(
        f"Job {job.id} completed: {job.returnvalue.get('chunks') if job.returnvalue else ''} chunks"
    )


def failed_function(job: Job | None, error: Exception) -> None:
    """Handle failed job."""
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
        "document-processing",
        worker_function,
        {"connection": settings.REDIS_URL, "concurrency": 3},
    )

    worker.on("completed", completed_function)
    worker.on("failed", failed_function)
    worker.on("error", error_function)

    return worker
