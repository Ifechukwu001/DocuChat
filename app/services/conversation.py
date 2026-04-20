import asyncio
from typing import Any
from uuid import UUID

from tortoise import transactions
from tortoise.functions import Count

from app.lib.response_formatter import (
    error_response,
    paginated_success_response,
    success_response,
)
from app.orm.models import Conversation, Document, Message, UsageLog


async def list_conversations(user_id: UUID, page: int, limit: int) -> dict[str, Any]:
    """List conversations for a user."""

    conversations, total = asyncio.gather(
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
                "id": conv.id.hex,
                "title": conv.title,
                "updated_at": conv.updated_at,
                "message_count": conv.message_count,
                "latest_message": {
                    "id": conv.latest_message.id.hex,
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


async def send_message(
    conversation_id: UUID, user_id: UUID, content: str, document_id: UUID | None = None
) -> dict[str, Any]:
    """Send a message in a conversation."""
    if document_id and not await Document.exists(id=document_id, deleted_at=None):
        return error_response(404, "Document not found")

    async with transactions.in_transaction():  # type: ignore
        conversation = await Conversation.get_or_none(
            id=conversation_id, user_id=user_id
        )

        if not conversation:
            return error_response(404, "Conversation not found")

        user_message = await Message.create(
            conversation_id=conversation.id,
            document_id=document_id,
            role="user",
            content=content,
        )

        conversation.latest_message = user_message
        await conversation.save()

        assistant_message = await Message.create(
            conversation_id=conversation.id,
            document_id=document_id,
            role="assistant",
            content="AI response placeholder (Week 4)",
            prompt_tokens=0,
            completion_tokens=0,
            cost_usd=0,
        )

        await UsageLog.create(
            user_id=user_id,
            action="chat",
            tokens=0,  # Placehoder until week 4
            cost_usd=0,
        )

        return success_response(
            message="Message sent successfully",
            data={
                "conversation_id": conversation.id.hex,
                "user_message": {
                    "id": user_message.id.hex,
                    "content": user_message.content,
                    "created_at": user_message.created_at,
                },
                "assistant_message": {
                    "id": assistant_message.id.hex,
                    "content": assistant_message.content,
                    "created_at": assistant_message.created_at,
                },
            },
        )
