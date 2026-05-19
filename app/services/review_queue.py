import json
from uuid import UUID
from typing import Any, Literal, TypedDict, NotRequired
from datetime import UTC, datetime, timedelta

from app.env import settings
from app.orm import transaction
from app.orm.models import AITrace, Message, ReviewQueue
from app.orm.enums.review_queue import ReviewStatus, ReviewPriority


class ReviewQueueService:
    """Service for managing the review queue."""

    @classmethod
    async def enqueue(
        cls,
        message_id: UUID,
        document_id: UUID,
        question: str,
        generated_answer: str,
        confidence: float,
        sources: list[Any],
        reason: str | None = None,
    ) -> ReviewQueue:
        """Add a new item to the review queue."""
        priority = cls.compute_priority(confidence)

        sla_deadline = datetime.now(UTC) + timedelta(minutes=settings.HITL_SLA_MINUTES)

        return await ReviewQueue.create(
            message_id=message_id,
            document_id=document_id,
            question=question,
            generated_answer=generated_answer,
            confidence=confidence,
            sources=sources,
            reason=reason,
            priority=priority,
            sla_deadline=sla_deadline,
        )

    @classmethod
    async def claim_next(cls, reviewer_id: UUID) -> ReviewQueue | None:
        """Claim the next pending review item for a reviewer."""
        # Use a transaction to prevent two reviewers from claiming the same item

        async with transaction.atomic_transaction():  # type: ignore
            item = (
                await ReviewQueue.filter(status=ReviewStatus.PENDING)
                .order_by("-priority", "created_at")
                .first()
            )
            if not item:
                return None

            item.status = ReviewStatus.IN_REVIEW
            item.reviewed_by = reviewer_id
            await item.save()
            return item

    class _Decision(TypedDict):
        action: Literal["approve", "reject"]
        edited_answer: NotRequired[str]
        reviewer_notes: NotRequired[str]

    @classmethod
    async def process_decision(
        cls, review_id: UUID, reviewer_id: UUID, decision: _Decision
    ) -> ReviewQueue:
        """Process a review decision (approve/reject)."""
        review = await ReviewQueue.get(id=review_id)
        review.update_from_dict(  # type: ignore
            dict(
                status="APPROVED" if decision["action"] == "approve" else "REJECTED",
                reviewed_by=reviewer_id,
                edited_answer=decision.get("edited_answer"),
                reviewer_notes=decision.get("reviewer_notes"),
                reviewed_at=datetime.now(UTC),
            )
        )
        await review.save()

        # Update the original message with the final answer
        if decision["action"] == "approve":
            final_answer = decision.get("edited_answer") or review.generated_answer

            await Message.filter(id=review.message_id).update(
                content=final_answer,
                # Mark it as human-reviewed so we know
                # this answer was validated
                # metadata={ humanReviewed: true, reviewId },
            )

        # Store the feedback for future improvement
        await cls.store_feedback(review, decision)
        return review

    @classmethod
    def compute_priority(cls, confidence: float) -> ReviewPriority:
        """Compute the priority of a review item based on confidence."""
        if confidence < 0.2:
            return ReviewPriority.URGENT
        if confidence < 0.4:
            return ReviewPriority.HIGH
        if confidence < 0.6:
            return ReviewPriority.NORMAL
        return ReviewPriority.LOW

    @classmethod
    async def store_feedback(cls, review: ReviewQueue, decision: _Decision) -> None:
        """Store feedback from the review decision for future analysis."""
        # This is the feedback loop. Every human decision becomes a data point you can use to improve the system.
        await AITrace.create(
            trace_id=f"review_{review.id}",
            user_id=review.reviewed_by,
            operation="hitl_review",
            data=json.dumps(
                {
                    "review_id": review.id,
                    "original_answer": review.generated_answer,
                    "edited_answer": decision.get("edited_answer"),
                    "was_edited": bool(decision.get("edited_answer")),
                    "action": decision["action"],
                    "confidence": review.confidence,
                    "question": review.question,
                    "reviewer_notes": decision.get("reviewer_notes"),
                }
            ),
        )
