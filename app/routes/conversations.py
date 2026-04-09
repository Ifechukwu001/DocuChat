from uuid import UUID

from fastapi import Depends, APIRouter

from app.middleware.auth import authenticate
from app.validators.conversation import SendMessageSchema, CreateConversationSchema

router = APIRouter(dependencies=[Depends(authenticate)])


@router.get("")
async def list_conversations() -> dict[str, object]:
    """List conversations."""
    return {}


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
    id: UUID, details: SendMessageSchema
) -> dict[str, object]:
    """Create a new message in a conversation."""
    return {}
