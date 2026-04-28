# pyright: reportAssignmentType=false, reportUnknownVariableType=false

from uuid import UUID
from datetime import datetime

from tortoise import fields, models
from tortoise_vector.field import VectorField

from .users import User


class Document(models.Model):
    """Document Model."""

    id: UUID = fields.UUIDField(primary_key=True)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "main.User", related_name="documents", on_delete=fields.CASCADE
    )
    title: str = fields.CharField(max_length=255)
    filename: str = fields.CharField(max_length=255)
    content: str = fields.TextField()
    mime_type: str = fields.CharField(max_length=100, null=True)
    file_size_bytes: int = fields.IntField(null=True)
    chunk_count: int = fields.IntField(default=0)
    status: str = fields.CharField(max_length=50, default="pending")
    error: str = fields.TextField(null=True)

    created_at: datetime = fields.DatetimeField(auto_now_add=True)
    updated_at: datetime = fields.DatetimeField(auto_now=True)

    deleted_at: datetime | None = fields.DatetimeField(
        null=True  # null = active, timestamp = soft-deleted
    )
    deleted_by: UUID | None = fields.UUIDField(null=True)  # Who deleted it (for audit)

    class Meta(models.Model.Meta):
        """Document Meta."""

        indexes = ("status",)


class Chunk(models.Model):
    """Chunk Model."""

    id: UUID = fields.UUIDField(primary_key=True)
    document: fields.ForeignKeyRelation[Document] = fields.ForeignKeyField(
        "main.Document", related_name="chunks", on_delete=fields.CASCADE
    )
    index: int = fields.IntField()
    content: str = fields.TextField()
    token_count: int = fields.IntField()
    embedding: list[float] = VectorField(
        vector_size=1536  # Vector embedding — 1536 dimensions for text-embedding-3-small
    )
    created_at: datetime = fields.DatetimeField(auto_now_add=True)

    class Meta(models.Model.Meta):
        """Chunk Meta."""

        unique_together = ("document", "index")
