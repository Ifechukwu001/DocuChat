from typing import Annotated
from collections.abc import Callable, Awaitable

from fastapi import Depends, status
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
)

from app.lib.exceptions import ErrorResponse
from app.middleware.auth import UserInfo, authenticate

Authorization = Annotated[
    HTTPAuthorizationCredentials, Depends(HTTPBearer(auto_error=False))
]


def authorize(
    *args: str,
) -> Callable[[UserInfo], Awaitable[None]]:
    """Authorize request."""

    async def _(user: Annotated[UserInfo, Depends(authenticate)]) -> None:
        if user["role"] not in args:
            raise ErrorResponse(status.HTTP_403_FORBIDDEN, "Insufficient permissions")

    return _
