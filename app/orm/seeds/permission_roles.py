from typing import Any

from tortoise import Tortoise, run_async  # type: ignore

from app.orm.config import TORTOISE_CONFIG
from app.orm.models import Role, Permission, RolePermission


async def main() -> None:
    """Script entrypoint."""
    await Tortoise.init(config=TORTOISE_CONFIG)

    permission_defs = [
        {
            "name": "documents:create",
            "resource": "documents",
            "action": "create",
            "description": "Upload documents",
        },
        {
            "name": "documents:read",
            "resource": "documents",
            "action": "read",
            "description": "View documents",
        },
        {
            "name": "documents:update",
            "resource": "documents",
            "action": "update",
            "description": "Edit document metadata",
        },
        {
            "name": "documents:delete",
            "resource": "documents",
            "action": "delete",
            "description": "Delete documents",
        },
        {
            "name": "conversations:create",
            "resource": "conversations",
            "action": "create",
            "description": "Start conversations",
        },
        {
            "name": "conversations:read",
            "resource": "conversations",
            "action": "read",
            "description": "View conversations",
        },
        {
            "name": "users:read",
            "resource": "users",
            "action": "read",
            "description": "View user list",
        },
        {
            "name": "users:manage",
            "resource": "users",
            "action": "manage",
            "description": "Manage user accounts",
        },
        {
            "name": "roles:manage",
            "resource": "roles",
            "action": "manage",
            "description": "Manage roles and permissions",
        },
    ]

    permissions: dict[str, Permission] = {}
    for perm_def in permission_defs:
        permissions[perm_def["name"]], _ = await Permission.get_or_create(  # type: ignore
            name=perm_def["name"],
            defaults={
                "resource": perm_def["resource"],
                "action": perm_def["action"],
                "description": perm_def["description"],
            },
        )

    role_defs: list[dict[str, Any]] = [
        {
            "name": "admin",
            "description": "Full system access",
            "permissions": permissions.keys(),  # All permissions
        },
        {
            "name": "member",
            "description": "Standard user",
            "is_default": True,
            "permissions": [
                "documents:create",
                "documents:read",
                "documents:update",
                "conversations:create",
                "conversations:read",
            ],
        },
        {
            "name": "viewer",
            "description": "Read-only access",
            "permissions": ["documents:read", "conversations:read"],
        },
    ]

    for role_def in role_defs:
        role, _ = await Role.get_or_create(  # type: ignore
            name=role_def["name"],
            defaults={
                "description": role_def["description"],
                "is_default": role_def.get("is_default", False),
            },
        )

        for perm_name in role_def["permissions"]:
            await RolePermission.get_or_create(  # type: ignore
                role=role, permission=permissions[perm_name]
            )

    print("RBAC seeded: 3 roles, 9 permissions")


if __name__ == "__main__":
    run_async(main())
