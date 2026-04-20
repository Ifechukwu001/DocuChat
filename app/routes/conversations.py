from uuid import UUID
from typing import Annotated

from fastapi import Depends, APIRouter

from app.middleware.auth import authenticate
from app.services import conversation as conversation_service
from app.validators.conversation import SendMessageSchema, CreateConversationSchema

router = APIRouter(dependencies=[Depends(authenticate)])


@router.get("")
async def list_conversations(
    user_id: Annotated[UUID, Depends(authenticate)], page: int = 1, limit: int = 10
) -> dict[str, object]:
    """List conversations."""
    return await conversation_service.list_conversations(user_id, page, limit)


@router.post("")
async def create_conversation(details: CreateConversationSchema) -> dict[str, object]:
    """Create a new conversation."""
    return {}


@router.get("/{id}/messages")
async def get_conversation_messages(id: UUID) -> dict[str, object]:
    """Get conversation messages."""
    return {}


@router.post("/{id}/messages")
async def create_conversation_message(
    id: UUID,
    user_id: Annotated[UUID, Depends(authenticate)],
    details: SendMessageSchema,
) -> dict[str, object]:
    """Create a new message in a conversation."""
    return await conversation_service.send_message(
        conversation_id=id,
        user_id=user_id,
        content=details.content,
        document_id=details.document_id,
    )
