# pyright: reportAssignmentType=false, reportUnknownVariableType=false

from uuid import UUID
from datetime import datetime

from tortoise import fields, models

from .users import User
from .documents import Document


class Conversation(models.Model):
    """Conversation Model."""

    id: UUID = fields.UUIDField(primary_key=True)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "main.User", related_name="conversations", on_delete=fields.CASCADE
    )
    title: str = fields.CharField(max_length=255, null=True)
    created_at: datetime = fields.DatetimeField(auto_now_add=True)
    updated_at: datetime = fields.DatetimeField(auto_now=True)

    latest_message: fields.ForeignKeyNullableRelation["Message"] = (
        fields.ForeignKeyField("main.Message", on_delete=fields.SET_NULL, null=True)
    )


class Message(models.Model):
    """Message Model."""

    id: UUID = fields.UUIDField(primary_key=True)
    conversation: fields.ForeignKeyRelation[Conversation] = fields.ForeignKeyField(
        "main.Conversation", related_name="messages", on_delete=fields.CASCADE
    )
    document: fields.ForeignKeyNullableRelation[Document] = fields.ForeignKeyField(
        "main.Document", related_name="messages", on_delete=fields.SET_NULL, null=True
    )
    role: str = fields.CharField(max_length=50)  # "user" or "assistant"
    content: str = fields.TextField()
    sources: str = fields.TextField(null=True)  # JSON: chunk IDs used as context
    confidence: str = fields.CharField(
        max_length=50, null=True
    )  # "high", "medium", "low"
    prompt_tokens: int = fields.IntField(null=True)
    completion_tokens: int = fields.IntField(null=True)
    cost_usd: float = fields.FloatField(null=True)
    latency_ms: int = fields.IntField(null=True)
    created_at: datetime = fields.DatetimeField(auto_now_add=True)
