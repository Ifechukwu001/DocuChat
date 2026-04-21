from uuid import UUID

from app.orm.models import UserRole


async def get_user_permissions(user_id: UUID) -> set[str]:
    """Get user permissions based on their role."""

    user_roles = (
        await UserRole.filter(user_id=user_id)
        .prefetch_related("role__permissions__permission")
        .all()
    )
    permissions: set[str] = set()
    for user_role in user_roles:
        for role_permission in user_role.role.permissions:
            permissions.add(role_permission.permission.name)

    return permissions
