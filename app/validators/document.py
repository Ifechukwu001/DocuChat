from typing import Literal

from pydantic import Field, BaseModel

from ._commons import String


class CreateDocumentSchema(BaseModel):
    """Create Document Schema."""

    title: String = Field(..., min_length=1, max_length=255)
    content: String = Field(..., min_length=1)


class ListDocumentsSchema(BaseModel):
    """List Documents Schema."""

    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)
    status: Literal["pending", "processing", "ready", "failed"] | None = None
    search: String | None = None
    sort_by: Literal["created_at", "title", "chunk_count"] | None = None
    sort_order: Literal["asc", "desc"] = "desc"
