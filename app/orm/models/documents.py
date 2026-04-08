# pyright: reportAssignmentType=false, reportUnknownVariableType=false

from uuid import UUID
from datetime import datetime

from tortoise import fields, models

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
    created_at: datetime = fields.DatetimeField(auto_now_add=True)

    class Meta(models.Model.Meta):
        """Chunk Meta."""

        unique_together = ("document", "index")
