from uuid import UUID
from datetime import UTC, datetime

from tortoise.expressions import F
from tortoise_vector.expression import CosineSimilarity

from app.orm.models import Chunk
from app.lib.logging import logger

from .embedding import EMBEDDING_DIMENSIONS, generate_embedding_cached


async def semantic_search(
    query: str,
    user_id: UUID,
    document_id: UUID | None = None,
    top_k: int = 10,
    min_score: float = 0.3,
    correlation_id: str | None = None,
) -> list[Chunk]:
    """Perform semantic search for the given query and return relevant document chunks."""
    start_time = datetime.now(UTC)

    # Step 1: Embed the query
    query_embedding = await generate_embedding_cached(query)

    # Step 2: Search pgvector with ownership filter
    orm_query = Chunk.filter(document_id=document_id) if document_id else Chunk.filter()
    results = (
        await orm_query.filter(
            document__user_id=user_id,
            document__deleted_at__isnull=True,
            document__status="ready",
            embedding__isnull=False,
        )
        .annotate(
            similarity=CosineSimilarity(
                "embedding", query_embedding, EMBEDDING_DIMENSIONS
            ),
            score=1 - F("similarity"),
        )
        .order_by("similarity")
        .limit(top_k)
        .prefetch_related("document")
        .all()
    )

    filtered = [chunk for chunk in results if chunk.score >= min_score]

    duration = (datetime.now(UTC) - start_time).total_seconds()

    logger.info(
        "Semantic search completed",
        query=query[:100],
        total_results=len(results),
        filtered_results=len(filtered),
        top_score=round(filtered[0].score, 4) if filtered else None,
        duration_secs=duration,
        correlation_id=correlation_id,
    )

    return filtered
