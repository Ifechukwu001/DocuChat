from uuid import UUID
from typing import Annotated

from fastapi import Body, Depends, APIRouter
from tortoise.functions import Count

from app.lib.events import APP_EVENTS
from app.lib.response_formatter import error_response, success_response
from app.middleware.auth import authenticate
from app.middleware.authorize import require_permission
from app.orm.models import Role, User, UserRole

router = APIRouter(dependencies=[Depends(require_permission("roles:manage"))])


@router.get("/roles")
async def list_roles() -> dict[str, object]:
    """List roles."""

    roles = (
        await Role.annotate(users_count=Count("users"))
        .prefetch_related("permissions__permission")
        .all()
    )

    return success_response(
        "Roles retrieved successfully",
        data=[
            {
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "is_default": role.is_default,
                "users_count": role.users_count,  # type: ignore
                "permissions": [rp.permission.name for rp in role.permissions],
            }
            for role in roles
        ],
    )


@router.post("/users/{user_id}}/roles")
async def assign_user_roles(
    user_id: UUID,
    role_name: Annotated[str, Body(embed=True)],
    admin_id: Annotated[UUID, Depends(authenticate)],
) -> dict[str, object]:
    """Assign a role to a user."""

    user = await User.get_or_none(id=user_id)
    if not user:
        return error_response(404, "User not found")

    role = await Role.get_or_none(name=role_name)
    if not role:
        return error_response(404, f"Role {role_name} not found")

    await UserRole.get_or_create(  # type: ignore
        user=user, role=role, defaults={"assigned_by": admin_id}
    )

    APP_EVENTS.emit(
        "admin:role_assigned",
        {"assigned_by": admin_id, "target_user_id": user_id, "role_name": role_name},
    )

    return success_response(f"Role {role_name} assigned to user")


@router.delete("/users/{user_id}}/roles/{role_name}")
async def remove_user_role(
    user_id: UUID,
    role_name: str,
    admin_id: Annotated[UUID, Depends(authenticate)],
) -> dict[str, object]:
    """Remove a role from a user."""
    role = await Role.get_or_none(name=role_name)
    if not role:
        return error_response(404, f"Role {role_name} not found")

    await UserRole.filter(user_id=user_id, role_id=role.id).delete()

    APP_EVENTS.emit(
        "admin:role_revoked",
        {"revoked_by": admin_id, "target_user_id": user_id, "role_name": role_name},
    )

    return success_response(f"Role {role_name} revoked")
