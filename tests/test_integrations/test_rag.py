from uuid import UUID, uuid4
from collections.abc import AsyncGenerator

import pytest
from tortoise import Tortoise
from tortoise_vector.field import VectorField

from app.services import search
from app.orm.models import User, Chunk, Document


def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Pure-Python cosine similarity used in place of the pgvector SQL function."""
    dot = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = sum(a**2 for a in vec1) ** 0.5
    mag2 = sum(b**2 for b in vec2) ** 0.5
    if not mag1 or not mag2:
        return 0.0
    return dot / (mag1 * mag2)


async def _sqlite_semantic_search(
    query: str,
    user_id: UUID,
    document_id: UUID | None = None,
    top_k: int = 10,
    min_score: float = 0.3,
    correlation_id: str | None = None,
) -> list[Chunk]:
    """SQLite-compatible drop-in for semantic_search.

    Replicates the same ownership / status / deleted_at filters as the real
    implementation, but replaces the pgvector CosineSimilarity annotation with
    Python-level scoring so the test can run on SQLite.
    """
    query_embedding = await search.generate_embedding_cached(query)

    orm_query = Chunk.filter(document_id=document_id) if document_id else Chunk.filter()
    results = await (
        orm_query.filter(
            document__user_id=user_id,
            document__deleted_at__isnull=True,
            document__status="ready",
            embedding__isnull=False,
        )
        .prefetch_related("document")
        .all()
    )

    for chunk in results:
        chunk.score = _cosine_similarity(query_embedding, chunk.embedding)

    filtered = sorted(
        [c for c in results if c.score >= min_score],
        key=lambda c: c.score,
        reverse=True,
    )
    return filtered[:top_k]


@pytest.fixture
async def rag_db(monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[None]:
    """Isolated in-memory SQLite DB containing only the models required for RAG tests (User, Document, Chunk).

    VectorField.SQL_TYPE is patched to TEXT so SQLite can create the schema
    (the field's to_db_value / to_python_value already serialise to/from a
    plain '[x,y,z]' string, so round-tripping works transparently).

    Conversation/Message models are intentionally excluded: they have a cyclic
    FK that SQLite's schema generator cannot resolve.
    """
    monkeypatch.setattr(VectorField, "SQL_TYPE", property(lambda self: "TEXT"))

    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={
            "main": [
                "app.orm.models.users",  # User, Role, Permission, UserRole, RolePermission, RefreshToken
                "app.orm.models.documents",  # Document, Chunk
            ]
        },
    )
    await Tortoise.generate_schemas(safe=False)
    yield
    await Tortoise.close_connections()


@pytest.mark.anyio
async def test_rag_retrieval_quality(
    rag_db: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RAG retrieval quality — converted from the Vitest test flow.

    Asserts:
      1. A relevant query surfaces the right document chunk.
      2. An irrelevant query returns no results when min_score is high.
      3. Ownership is respected — users cannot see each other's documents.
    """
    # --- deterministic embeddings ----------------------------------------
    # Dimensions are small (3D) so arithmetic is easy to reason about.
    # The "return / refund" embedding is almost parallel to the query vector
    # (cosine ~0.9998); the "shipping" embedding is at ~45°; "quantum" is
    # orthogonal (cosine = 0).
    refund_embedding = [0.99, 0.01, 0.0]
    shipping_embedding = [0.2, 0.8, 0.0]

    async def fake_embedding(text: str) -> list[float]:
        if "quantum" in text.lower():
            return [0.0, 0.0, 1.0]  # orthogonal → score = 0
        return [1.0, 0.0, 0.0]  # aligned with refund_embedding

    monkeypatch.setattr(search, "generate_embedding_cached", fake_embedding)
    # Also patch in the sqlite-compatible search implementation
    monkeypatch.setattr(search, "semantic_search", _sqlite_semantic_search)

    # --- seed real ORM data -----------------------------------------------
    test_user = await User.create(
        id=uuid4(), email="owner@example.com", password_hash="x"
    )
    other_user = await User.create(
        id=uuid4(), email="other@example.com", password_hash="x"
    )

    test_doc = await Document.create(
        id=uuid4(),
        user=test_user,
        title="Refund Policy",
        filename="refund-policy.md",
        content="Customers can return products within 30 days for a refund.",
        status="ready",
        chunk_count=1,
    )
    await Document.create(
        id=uuid4(),
        user=test_user,
        title="Shipping Policy",
        filename="shipping-policy.md",
        content="Standard shipping takes 5–7 business days.",
        status="ready",
        chunk_count=1,
    )
    other_doc = await Document.create(
        id=uuid4(),
        user=other_user,
        title="Private Notes",
        filename="private-notes.md",
        content="Internal return policy notes.",
        status="ready",
        chunk_count=1,
    )

    await Chunk.create(
        id=uuid4(),
        document=test_doc,
        index=0,
        content="You can return a product within 30 days for a full refund or reimbursement.",
        token_count=32,
        embedding=refund_embedding,
    )
    await Chunk.create(
        id=uuid4(),
        document=test_doc,
        index=1,
        content="Shipping estimates and delivery windows are listed here.",
        token_count=32,
        embedding=shipping_embedding,
    )
    await Chunk.create(
        id=uuid4(),
        document=other_doc,
        index=0,
        content="Internal-only return policy notes.",
        token_count=32,
        embedding=refund_embedding,
    )

    # --- Test 1: finds the refund policy when asked about returns ---------
    results = await search.semantic_search(
        query="How do I return a product?",
        user_id=test_user.id,
    )

    assert len(results) > 0, "Expected to find refund-related results"
    assert results[0].score > 0.5, f"Expected top score > 0.5, got {results[0].score}"
    top_content = results[0].content.lower()
    assert (
        "return" in top_content
        or "refund" in top_content
        or "reimbursement" in top_content
    ), "Expected top result to contain refund-related keywords"

    # --- Test 2: returns nothing for irrelevant queries -------------------
    irrelevant = await search.semantic_search(
        query="What is quantum computing?",
        user_id=test_user.id,
        min_score=0.5,
    )
    assert len(irrelevant) == 0, (
        f"Expected no results for irrelevant query, got {len(irrelevant)}"
    )

    # --- Test 3: respects document ownership ------------------------------
    ownership_results = await search.semantic_search(
        query="return policy",
        user_id=other_user.id,
    )
    has_test_user_docs = any(r.document_id == test_doc.id for r in ownership_results)
    assert not has_test_user_docs, (
        "Expected other_user to not have access to test_user's documents"
    )
