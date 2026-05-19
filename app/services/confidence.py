from typing import Literal, TypedDict, NotRequired

from app.orm.models import Chunk

ConfidenceLevel = Literal["high", "medium", "low", "none"]


class ConfidenceResult(TypedDict):
    """Represents the overall confidence result for a query."""

    score: float  # 0 to 1
    level: ConfidenceLevel
    should_escalate: bool
    reason: NotRequired[str]


def compute_confidence(chunks: list[Chunk], threshold: float = 0.6) -> ConfidenceResult:
    """Computes the overall confidence score and level based on the provided chunks."""
    # No chunks retrieved at all — the document probably
    # does not contain information relevant to this question
    if not chunks:
        return ConfidenceResult(
            score=0.0,
            level="none",
            should_escalate=True,
            reason="No relevant chunks found in document",
        )

    #  Weighted average: rank 1 gets weight 5, rank 2 gets 4, etc.
    weights = [len(chunks) - i for i in range(len(chunks))]
    total_weight = sum(weights)
    weighted_score = (
        sum(chunk.score * weights[i] for i, chunk in enumerate(chunks)) / total_weight
    )

    # Classify the confidence level
    level: ConfidenceLevel
    reason: str | None = None

    if weighted_score >= 0.85:
        level = "high"
    elif weighted_score >= threshold:
        level = "medium"
    elif weighted_score > 0.3:
        level = "low"
        reason = (
            f"Retrieval confidence {round(weighted_score * 100)}% "
            f"below threshold {round(threshold * 100)}%"
        )
    else:
        level = "none"
        reason = "Retrieved chunks are not relevant to the question"

    return ConfidenceResult(
        score=weighted_score,
        level=level,
        should_escalate=level in ("low", "none"),
        **({"reason": reason} if reason else {}),
    )
