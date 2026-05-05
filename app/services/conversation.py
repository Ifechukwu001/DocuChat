import asyncio
from uuid import UUID
from typing import Any

from tortoise import transactions
from tortoise.functions import Count

from app.orm.models import Message, Document, UsageLog, Conversation
from app.lib.response_formatter import (
    error_response,
    success_response,
    paginated_success_response,
)

from .rag import assemble_context, generate_rag_response
from .search import semantic_search


async def list_conversations(user_id: UUID, page: int, limit: int) -> dict[str, Any]:
    """List conversations for a user."""
    conversations, total = await asyncio.gather(
        Conversation.filter(user_id=user_id)
        .order_by("-updated_at")
        .offset((page - 1) * limit)
        .limit(limit)
        .prefetch_related("latest_message")
        .annotate(
            message_count=Count("messages"),
        ),
        Conversation.filter(user_id=user_id).count(),
    )

    return paginated_success_response(
        message="Conversations retrieved successfully",
        metadata={
            "page": page,
            "limit": limit,
            "total": total,
        },
        data=[
            {
                "id": conv.id,
                "title": conv.title,
                "updated_at": conv.updated_at,
                "message_count": conv.message_count,
                "latest_message": {
                    "id": conv.latest_message.id,
                    "role": conv.latest_message.role,
                    "content": conv.latest_message.content,
                    "created_at": conv.latest_message.created_at,
                }
                if conv.latest_message
                else None,
            }
            for conv in conversations
        ],
    )


async def create_conversation(user_id: UUID, title: str) -> dict[str, Any]:
    """Create a new conversation."""
    conversation = await Conversation.create(user_id=user_id, title=title)
    return success_response(
        message="Conversation created successfully",
        data={
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at,
        },
    )


async def get_conversation_messages(
    user_id: UUID, conversation_id: UUID
) -> dict[str, Any]:
    """Get messages for a conversation."""
    messages = (
        await Message.filter(
            conversation_id=conversation_id, conversation__user__id=user_id
        )
        .order_by("created_at")
        .all()
    )

    return success_response(
        message="Messages retrieved successfully",
        data=[
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at,
            }
            for msg in messages
        ],
    )


async def send_message(
    conversation_id: UUID,
    user_id: UUID,
    content: str,
    document_id: UUID | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Send a message in a conversation."""
    if document_id and not await Document.exists(id=document_id, deleted_at=None):
        return error_response(404, "Document not found")

    async with transactions.in_transaction():  # type: ignore
        #  1. Verify conversation ownership (same as before)
        conversation = await Conversation.get_or_none(
            id=conversation_id, user_id=user_id
        )

        if not conversation:
            return error_response(404, "Conversation not found")

        # 2. Save user message
        user_message = await Message.create(
            conversation_id=conversation.id,
            document_id=document_id,
            role="user",
            content=content,
        )

        conversation.latest_message = user_message
        await conversation.save()

        #  3. Load recent conversation history
        history = (
            await Message.filter(conversation_id=conversation.id)
            .order_by("-created_at")
            .limit(10)
            .only("role", "content")
            .all()
        )
        conversation_history = reversed(history)

        # 4. RAG: Retrieve
        search_results = await semantic_search(
            query=content, user_id=user_id, document_id=document_id
        )

        # 5. RAG: Augment
        context = assemble_context(search_results)

        # 6. RAG: Generate
        rag_response = await generate_rag_response(
            question=content,
            context=context,
            conversation_history=[
                {"role": msg.role, "content": msg.content}
                for msg in conversation_history
            ],
            user_id=user_id,
            conversation_id=conversation.id,
            correlation_id=correlation_id,
        )

        # 7. Save assistant message with metadata
        assistant_message = await Message.create(
            conversation_id=conversation.id,
            document_id=document_id,
            role="assistant",
            content=rag_response["answer"],
            prompt_tokens=rag_response["tokens_used"]["prompt"],
            completion_tokens=rag_response["tokens_used"]["completion"],
            cost_usd=rag_response["cost_usd"],
        )

        # 8. Touch conversation updatedAt
        conversation.latest_message = assistant_message
        await conversation.save()

        await UsageLog.create(
            user_id=user_id,
            action="chat",
            tokens=rag_response["tokens_used"]["total"],
            cost_usd=rag_response["cost_usd"],
        )

        return success_response(
            message="Message sent successfully",
            data={
                "conversation_id": conversation.id,
                "user_message": {
                    "id": user_message.id,
                    "content": user_message.content,
                    "created_at": user_message.created_at,
                },
                "assistant_message": {
                    "id": assistant_message.id,
                    "content": assistant_message.content,
                    "citations": rag_response["citations"],
                    "created_at": assistant_message.created_at,
                },
            },
        )
