from uuid import UUID
from typing import TypedDict
from datetime import UTC, datetime

from tortoise import transactions

from app.lib.cache import CACHE_TTL, hash_key, cache_get, cache_set
from app.orm.models import Chunk
from app.lib.logging import logger
from app.lib.metrics import embedding_cache_hit_rate
from app.lib.http.openai_breaker import call_openai

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


async def generate_embedding(text: str) -> list[float]:
    """Generate an embedding for the given text using OpenAI API."""
    start_time = datetime.now(UTC)

    response = await call_openai(
        "/embeddings",
        model=EMBEDDING_MODEL,
        input=text,
    )

    data = response.json()

    embedding = data["data"][0]["embedding"]
    duration = (datetime.now(UTC) - start_time).total_seconds()

    logger.info(
        "Embedding generated",
        model=EMBEDDING_MODEL,
        input_length=len(text),
        dimensions=len(embedding),
        duration_secs=duration,
        tokens_used=data.get("usage", {}).get("total_tokens"),
    )

    return embedding


async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts using OpenAI API."""
    if not texts:
        return []

    # OpenAI supports up to 2048 inputs per request
    BATCH_SIZE = 100  # Stay well under the limit
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]

        response = await call_openai(
            "/embeddings",
            model=EMBEDDING_MODEL,
            input=batch,
        )

        data = response.json()

        sorted_data = sorted(data["data"], key=lambda x: x["index"])

        for item in sorted_data:
            embedding = item["embedding"]
            all_embeddings.append(embedding)

        logger.info(
            "Embeddings batch processed",
            batch_index=i // BATCH_SIZE,
            batch_size=len(batch),
            total_texts=len(texts),
            tokens_used=data.get("usage", {}).get("total_tokens"),
        )

    return all_embeddings


async def store_chunk_embedding(chunk_id: UUID, embedding: list[float]) -> None:
    """Store the embedding for a document chunk in the database."""
    chunk = await Chunk.get(id=chunk_id)
    chunk.embedding = embedding
    await chunk.save()


class _ChunkEmbedding(TypedDict):
    chunk_id: UUID
    embedding: list[float]


async def store_chunk_embeddings_batch(chunks: list[_ChunkEmbedding]) -> None:
    """Store embeddings for a batch of document chunks in the database."""
    async with transactions.in_transaction():  # type: ignore
        for item in chunks:
            chunk = await Chunk.get(id=item["chunk_id"])
            chunk.embedding = item["embedding"]
            await chunk.save()


async def generate_embedding_cached(text: str) -> list[float]:
    """Generate an embedding for the given text using OpenAI API with caching."""
    hash = hash_key(text)
    cache_key = f"embed:{hash}"

    # Check cache first
    cached = await cache_get(cache_key, list[float])
    if cached:
        embedding_cache_hit_rate.inc()
        logger.debug("Embedding cache hit", hash=hash[:12])
        return cached

    # Cache miss, generate embedding
    embedding = await generate_embedding(text)

    # Emit an event #TODO

    await cache_set(cache_key, embedding, CACHE_TTL.EMBEDDING.value)
    logger.debug("Embedding cached", hash=hash[:12], ttl=CACHE_TTL.EMBEDDING.value)

    return embedding


class _UncachedEmbedding(TypedDict):
    index: int
    text: str


async def generate_embeddings_batch_cached(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts using OpenAI API with caching."""
    results: list[list[float]] = [[0]] * len(texts)
    uncached: list[_UncachedEmbedding] = []

    for i, text in enumerate(texts):
        hash = hash_key(text)

        cached = await cache_get(f"embed:{hash}", list[float])
        if cached:
            embedding_cache_hit_rate.inc()
            logger.debug("Embedding batch cache hit", index=i, hash=hash[:12])
            results[i] = cached
        else:
            uncached.append({"index": i, "text": text})

    logger.info(
        "Embedding batch cache check",
        total=len(texts),
        cache_hits=len(texts) - len(uncached),
        cache_misses=len(uncached),
    )

    if uncached:
        new_embeddings = await generate_embeddings([item["text"] for item in uncached])

        # Emit new generations #TODO

        for i in range(len(uncached)):
            hash = hash_key(uncached[i]["text"])
            await cache_set(
                f"embed:{hash}", new_embeddings[i], CACHE_TTL.EMBEDDING.value
            )
            results[uncached[i]["index"]] = new_embeddings[i]

    return results
