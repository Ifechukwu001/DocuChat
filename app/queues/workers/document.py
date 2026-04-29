# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportArgumentType=false
import asyncio
from uuid import UUID
from datetime import UTC, datetime

from bullmq import Job, Worker  # type: ignore
from tortoise import transactions

from app.env import settings
from app.lib.events import APP_EVENTS
from app.orm.models import Chunk, Document
from app.lib.chunker import chunk_document
from app.lib.logging import logger
from app.lib.metrics import ingestion_duration, chunks_per_document
from app.queues.jobs import dead_letter_queue
from app.services.embedding import (
    store_chunk_embeddings_batch,
    generate_embeddings_batch_cached,
)
from app.lib.document_extractor import extract_text, detect_format

worker: Worker | None = None


async def worker_function(job: Job, token: str) -> dict[str, object]:
    """Worker function to process document-processing tasks."""
    document_id = job.data.get("document_id")
    user_id = job.data.get("user_id")
    correlation_id = job.data.get("correlation_id")
    start_time = datetime.now(UTC)

    logger.info(
        "Document processing started",
        document_id=document_id,
        user_id=user_id,
        correlation_id=correlation_id,
    )

    document = None
    try:
        # Step 1: Fetch document
        document = await Document.get(id=UUID(document_id))
        document.status = "processing"
        await document.save()

        await job.updateProgress(5)

        # Step 2: Extract text
        format = detect_format(document.filename)
        extracted_details = await extract_text(document.content, format)
        await job.updateProgress(15)

        logger.info(
            "Text extracted",
            document_id=document_id,
            user_id=user_id,
            correlation_id=correlation_id,
            format=format,
            text_length=len(extracted_details["text"]),
            page_count=extracted_details.get("page_count", 1),
        )

        # Step 3: Chunk the text

        chunks = chunk_document(
            extracted_details["text"],
            max_tokens=500,
            overlap_tokens=50,
            min_chunk_tokens=50,
        )
        await job.updateProgress(30)

        logger.info(
            "Document chunked",
            document_id=document_id,
            user_id=user_id,
            correlation_id=correlation_id,
            chunk_count=len(chunks),
            average_tokens=round(sum(c["token_estimate"] for c in chunks)),
        )

        # Step 4: Store chunks in database
        async with transactions.in_transaction():
            await Chunk.filter(
                document_id=document.id
            ).delete()  # Clear existing chunks if re-processing
            await Chunk.bulk_create(
                [
                    Chunk(
                        document_id=document.id,
                        index=chunk["index"],
                        content=chunk["text"],
                        token_count=chunk["token_estimate"],
                    )
                    for chunk in chunks
                ]
            )

        await job.updateProgress(50)

        # Step 5: Generate embeddings (the expensive step)
        chunk_texts = [chunk["text"] for chunk in chunks]
        embeddings = await generate_embeddings_batch_cached(chunk_texts)
        await job.updateProgress(85)

        # Step 6: Store embeddings
        stored_chunks = (
            await Chunk.filter(document_id=document.id).order_by("index").only("id")
        )
        await store_chunk_embeddings_batch(
            [
                {"chunk_id": c.id, "embedding": embeddings[i]}
                for i, c in enumerate(stored_chunks)
            ]
        )
        await job.updateProgress(95)

        # Step 7: Mark complete
        document.status = "ready"
        document.chunk_count = len(chunks)
        await document.save()
        await job.updateProgress(100)

        duration = (datetime.now(UTC) - start_time).total_seconds()

        ingestion_duration.labels(format=format).observe(duration)
        chunks_per_document.observe(len(chunks))

        # Emit completion event with metrics
        APP_EVENTS.emit(
            "doc:processed",
            {
                "document_id": document_id,
                "user_id": user_id,
                "correlation_id": correlation_id,
                "chunk_count": len(chunks),
                "duration_seconds": duration,
                "format": format,
                "page_count": extracted_details.get("page_count", 1),
            },
        )

        logger.info(
            "Document processing complete",
            correlation_id=correlation_id,
            document_id=document_id,
            user_id=user_id,
            chunk_count=len(chunks),
            duration_seconds=duration,
        )

        return {"success": True, "chunks": len(chunks), "duration_seconds": duration}

    except Exception as e:
        if (job.attemptsMade >= (job.opts.get("attempts", 3) - 1)) and document:
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
