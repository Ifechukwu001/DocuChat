from uuid import UUID

from app.lib.cache import CACHE_TTL, cache_get_or_set
from app.orm.models import UserRole


async def get_user_permissions(user_id: UUID) -> set[str]:
    """Get user permissions based on their role."""

    async def _fetch_permissions() -> list[str]:
        user_roles = (
            await UserRole.filter(user_id=user_id)
            .prefetch_related("role__permissions__permission")
            .all()
        )
        permissions: list[str] = []
        for user_role in user_roles:
            for role_permission in user_role.role.permissions:
                permissions.append(role_permission.permission.name)

        return permissions

    permissions = await cache_get_or_set(
        key=f"permissions:{user_id}",
        type=list[str],
        ttl_seconds=CACHE_TTL.PERMISSIONS.value,
        fetch_func=_fetch_permissions,
    )

    return set(permissions)
