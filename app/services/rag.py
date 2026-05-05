from uuid import UUID
from typing import TypedDict
from datetime import UTC, datetime

from app.lib.events import APP_EVENTS
from app.orm.models import Chunk
from app.lib.logging import logger
from app.config.prompts import RAG_SYSTEM_PROMPT
from app.lib.http.openai_breaker import call_openai


class AssembledContext(TypedDict):
    """Assembled context for RAG."""

    chunks: list[Chunk]
    context_text: str
    total_tokens: int
    citations: list[Citation]


class Citation(TypedDict):
    """Citation for a chunk in RAG."""

    index: int  # [1], [2], etc.
    chunk_id: UUID
    document_id: UUID
    document_title: str
    chunk_index: int
    score: float


CONTEXT_TOKEN_BUDGET = 3500


def assemble_context(search_results: list[Chunk]) -> AssembledContext:
    """Assemble the context text and metadata for RAG based on search results."""
    selected: list[Chunk] = []
    total_tokens = 0

    def is_redundant(candidate: Chunk, selected: list[Chunk]) -> bool:
        return any(
            candidate.document.id == s.document.id
            and abs(candidate.index - s.index) <= 1
            for s in selected
        )

    # Results are already sorted by score (descending)
    for result in search_results:
        if is_redundant(result, selected):
            continue

        if (total_tokens + result.token_count) > CONTEXT_TOKEN_BUDGET:
            break
        selected.append(result)
        total_tokens += result.token_count

    # Build citations
    citations: list[Citation] = [
        {
            "index": i,
            "chunk_id": chunk.id,
            "document_id": chunk.document.id,
            "document_title": chunk.document.title,
            "chunk_index": chunk.index,
            "score": chunk.score,
        }
        for i, chunk in enumerate(selected, start=1)
    ]

    # Build context text block
    context_text = "\n\n---\n\n".join(
        f'[Source {i}: "{chunk.document.title}", Section {chunk.index + 1}]\n{chunk.content}'
        for i, chunk in enumerate(selected, start=1)
    )

    return {
        "chunks": selected,
        "context_text": context_text,
        "total_tokens": total_tokens,
        "citations": citations,
    }


class _TokensUsed(TypedDict):
    prompt: int
    completion: int
    total: int


class RAGResponse(TypedDict):
    """Response from RAG answer generation."""

    answer: str
    citations: list[Citation]
    tokens_used: _TokensUsed
    cost_usd: float
    model: str


class Conversation(TypedDict):
    """Conversation history for RAG."""

    role: str
    content: str


CHAT_MODEL = "phi4-mini"


async def generate_rag_response(
    question: str,
    context: AssembledContext,
    conversation_history: list[Conversation],
    user_id: UUID,
    conversation_id: UUID,
    correlation_id: str | None = None,
) -> RAGResponse:
    """Generate an answer using RAG based on the question, context, and conversation history."""
    # Build the messages array
    messages: list[Conversation] = [{"role": "system", "content": RAG_SYSTEM_PROMPT}]

    # Add recent conversation history (last 5 exchanges)
    if conversation_history and len(conversation_history) > 0:
        messages.extend(conversation_history[-10:])

    # Add the context and question
    if len(context["chunks"]) > 0:
        messages.append(
            {
                "role": "user",
                "content": "\n".join(
                    [
                        "Here is the relevant context from my documents:",
                        "",
                        context["context_text"],
                        "",
                        "---",
                        "",
                        f"My question: {question}",
                    ]
                ),
            }
        )
    else:
        messages.append(
            {
                "role": "user",
                "content": "\n".join(
                    [
                        "No relevant context was found in my documents for this question.",
                        "",
                        f"My question: {question}",
                    ]
                ),
            }
        )

    start_time = datetime.now(UTC)

    # Call the LLM through the circuit breaker
    response = await call_openai(
        "/chat",
        model=CHAT_MODEL,
        messages=messages,
        stream=False,
        options={
            "temperature": 0.1,  # Low temperature for factual answers
            "num_predict": 1500,  # Max tokens in the answer
        },
    )

    result = response.json()
    answer = result["message"]["content"]
    prompt_tokens = result["prompt_eval_count"]
    completion_tokens = result["eval_count"]
    duration = (datetime.now(UTC) - start_time).total_seconds()

    # Calculate Cost (assuming for phi4-mini)
    cost_usd = (
        (prompt_tokens / 1_000_000) * 2.50  # Input
        + (completion_tokens / 1_000_000) * 10.00  # Output
    )

    logger.info(
        "RAG response generated",
        correlation_id=correlation_id,
        conversation_id=conversation_id,
        model=CHAT_MODEL,
        context_chunks=len(context["chunks"]),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=round(cost_usd, 4),
        duration_secs=duration,
    )

    # Track usage
    APP_EVENTS.emit(
        "ai:chat-completed",
        user_id=user_id,
        conversation_id=conversation_id,
        correlation_id=correlation_id,
        model=CHAT_MODEL,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
    )

    return {
        "answer": answer,
        "citations": context["citations"],
        "tokens_used": {
            "prompt": prompt_tokens,
            "completion": completion_tokens,
            "total": prompt_tokens + completion_tokens,
        },
        "cost_usd": cost_usd,
        "model": CHAT_MODEL,
    }
