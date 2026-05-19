# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportArgumentType=false
import asyncio
from typing import Any
from datetime import UTC, datetime, timedelta

from bullmq import Job, Worker  # type: ignore

from app.env import settings
from app.lib.events import APP_EVENTS
from app.orm.models import Message, ReviewQueue
from app.lib.logging import logger
from app.queues.jobs import dead_letter_queue
from app.orm.enums.review_queue import ReviewStatus, ReviewPriority

worker: Worker | None = None


async def check_escallations(job: Job, token: str) -> None:
    """Worker function to check escalation tasks."""
    now = datetime.now(UTC)
    warning_window = now + timedelta(minutes=15)  # 15 minutes before SLA

    # Find items approaching SLA deadline
    at_risk = (
        ReviewQueue.filter(
            status__in={ReviewStatus.PENDING, ReviewStatus.IN_REVIEW},
            sla_deadline__lte=warning_window,
            escalated_at__isnull=True,
        )
        .order_by("sla_deadline")
        .all()
    )

    async for item in at_risk:
        if item.sla_deadline <= now:
            # SLA breached — deliver the answer with a disclaimer
            await handle_sla_breach(item)
        else:
            # Approaching SLA — escalate priority
            await escalate_item(item)


async def escalate_item(item: ReviewQueue) -> None:
    """Escalate a review item that is approaching its SLA deadline."""
    item.priority = ReviewPriority.URGENT
    item.escalated_at = datetime.now(UTC)
    await item.save()

    # Notify admins via the event system
    APP_EVENTS.emit(
        "review:escalated",
        review_id=item.id,
        question=item.question,
        confidence=item.confidence,
        sla_deadline=item.sla_deadline.isoformat(),
        wait_time_minutes=round(
            (datetime.now(UTC) - item.created_at).total_seconds() / 60
        ),
    )


async def handle_sla_breach(item: ReviewQueue) -> None:
    """Deliver the original answer with a low-confidence disclaimer."""
    await Message.filter(id=item.message_id).update(
        content=item.generated_answer,
        # FIXME: Not in model, should we add this?
        # metadata=json.dumps(
        #     {
        #         "humanReviewed": False,
        #         "disclaimer": (
        #             "This answer was generated with low confidence "
        #             "and could not be reviewed in time. "
        #             "Please verify the information independently."
        #         ),
        #         "slaBreach": True,
        #     }
        # ),
    )

    item.status = ReviewStatus.ESCALATED
    await item.save()

    APP_EVENTS.emit(
        "review:sla_breached",
        review_id=item.id,
        wait_time_minutes=round(
            (datetime.now(UTC) - item.created_at).total_seconds() / 60
        ),
    )


def completed_function(job: Job, *args: Any, **kwargs: Any) -> None:
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
        "escalation-checker",
        check_escallations,
        {"connection": settings.REDIS_URL},
    )

    worker.on("completed", completed_function)
    worker.on("failed", failed_function)
    worker.on("error", error_function)

    return worker
