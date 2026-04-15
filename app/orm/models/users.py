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


class Role(models.Model):
    """Role Model."""

    id: UUID = fields.UUIDField(primary_key=True)
    name: str = fields.CharField(max_length=50, unique=True)
    description: str = fields.CharField(max_length=255, null=True)
    is_default: bool = fields.BooleanField(default=False)
    created_at: datetime = fields.DatetimeField(auto_now_add=True)
    updated_at: datetime = fields.DatetimeField(auto_now=True)

    users: fields.ReverseRelation["UserRole"]
    permissions: fields.ReverseRelation["RolePermission"]


class Permission(models.Model):
    """Permission Model."""

    id: UUID = fields.UUIDField(primary_key=True)
    name: str = fields.CharField(max_length=50, unique=True)  # 'documents:create'
    description: str = fields.CharField(max_length=255, null=True)
    resource: str = fields.CharField(max_length=255, null=True)  # 'documents'
    action: str = fields.CharField(max_length=50, null=True)  # 'create'
    created_at: datetime = fields.DatetimeField(auto_now_add=True)

    class Meta(models.Model.Meta):
        """Permission Meta."""

        unique_together = (("resource", "action"),)


class UserRole(models.Model):
    """User Role Model."""

    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "main.User", related_name="roles", on_delete=fields.CASCADE
    )
    role: fields.ForeignKeyRelation[Role] = fields.ForeignKeyField(
        "main.Role", related_name="users", on_delete=fields.CASCADE
    )
    assigned_at: datetime = fields.DatetimeField(auto_now_add=True)
    assigned_by: UUID = fields.UUIDField(
        null=True
    )  # Who assigned this role (for audit)

    class Meta(models.Model.Meta):
        """User Role Meta."""

        unique_together = (("user", "role"),)


class RolePermission(models.Model):
    """Role Permission Model."""

    role: fields.ForeignKeyRelation[Role] = fields.ForeignKeyField(
        "main.Role", related_name="permissions", on_delete=fields.CASCADE
    )
    permission: fields.ForeignKeyRelation[Permission] = fields.ForeignKeyField(
        "main.Permission", related_name="roles", on_delete=fields.CASCADE
    )

    class Meta(models.Model.Meta):
        """Role Permission Meta."""

        unique_together = (("role", "permission"),)
