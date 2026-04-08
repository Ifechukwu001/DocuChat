# pyright: reportAssignmentType=false, reportUnknownVariableType=false

from uuid import UUID
from datetime import datetime

from tortoise import fields, models

from .users import User


class UsageLog(models.Model):
    """Usage Log Model."""

    id: UUID = fields.UUIDField(primary_key=True)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "main.User", related_name="usage_logs", on_delete=fields.CASCADE
    )
    action: str = fields.CharField(max_length=50)  # "embed", "chat", "upload"
    tokens: int = fields.IntField()
    cost_usd: float = fields.FloatField()
    metadata: str = fields.TextField(null=True)  # JSON string
    created_at: datetime = fields.DatetimeField(auto_now_add=True)
    updated_at: datetime = fields.DatetimeField(auto_now=True)

    class Meta(models.Model.Meta):
        """Usage Log Meta."""

        indexes = ("action", "created_at")


class AITrace(models.Model):
    """AI Trace Model."""

    id: UUID = fields.UUIDField(primary_key=True)
    trace_id: str = fields.CharField(max_length=255, unique=True)
    user_id: UUID = fields.UUIDField(null=True)
    operation: str = fields.CharField(max_length=100)
    data: str = fields.TextField(null=True)  # JSON string
    created_at: datetime = fields.DatetimeField(auto_now_add=True)

    class Meta(models.Model.Meta):
        """AI Trace Meta."""

        indexes = ("user_id", "operation")
