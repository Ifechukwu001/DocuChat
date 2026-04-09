from uuid import UUID

from pydantic import Field, BaseModel


class CreateConversationSchema(BaseModel):
    """Create Conversation Schema."""

    title: str | None = Field(None, max_length=200)
    document_id: UUID | None = None


class SendMessageSchema(BaseModel):
    """Send Message Schema."""

    content: str = Field(..., min_length=1, max_length=10_000)
    document_id: UUID | None = None
