from typing import Annotated
from collections.abc import Callable, Awaitable

from fastapi import Depends, status
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
)

from app.services.rbac import get_user_permissions
from app.lib.exceptions import ErrorResponse
from app.middleware.auth import UserInfo, authenticate

Authorization = Annotated[
    HTTPAuthorizationCredentials, Depends(HTTPBearer(auto_error=False))
]


def require_permission(
    *args: str,
) -> Callable[[UserInfo], Awaitable[None]]:
    """Authorize request."""

    async def _(user: Annotated[UserInfo, Depends(authenticate)]) -> None:

        user_permissions = await get_user_permissions(user.get("id"))

        if not all(permission in user_permissions for permission in args):
            raise ErrorResponse(
                status.HTTP_403_FORBIDDEN, "You do not have the required permission"
            )

    return _
