# pyright: reportAssignmentType=false, reportUnknownVariableType=false

from uuid import UUID
from datetime import datetime

from tortoise import fields, models


class User(models.Model):
    """User Model."""

    id: UUID = fields.UUIDField(primary_key=True)
    email: str = fields.CharField(max_length=255, unique=True)
    password_hash: str = fields.CharField(max_length=255)
    tier: str = fields.CharField(max_length=50, default="free")
    tokens_used: int = fields.IntField(default=0)
    token_limit: int = fields.IntField(default=10000)
    is_active: bool = fields.BooleanField(default=True)
    created_at: datetime = fields.DatetimeField(auto_now_add=True)
    updated_at: datetime = fields.DatetimeField(auto_now=True)


class RefreshToken(models.Model):
    """Refresh Token Model."""

    id: UUID = fields.UUIDField(primary_key=True)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "main.User", related_name="refresh_tokens", on_delete=fields.CASCADE
    )
    token: str = fields.CharField(  # SHA-256 hash of the actual token
        max_length=255, unique=True
    )
    expires_at: datetime = fields.DatetimeField()
    created_at: datetime = fields.DatetimeField(auto_now_add=True)

    class Meta(models.Model.Meta):
        """Refresh Token Meta."""

        indexes = ("expires_at",)
