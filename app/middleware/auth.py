from uuid import UUID
from typing import Annotated, TypedDict

from jwt import ExpiredSignatureError
from fastapi import Depends, Request, status
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
)

from app.lib.tokens import verify_access_token
from app.lib.exceptions import ErrorResponse

Authorization = Annotated[
    HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=False))
]


class UserInfo(TypedDict):
    """User Auth Info TypedDict."""

    id: UUID
    tier: str


async def authenticate(auth: Authorization, request: Request) -> UserInfo:
    """Authenticate request."""
    if not auth:
        raise ErrorResponse(status.HTTP_401_UNAUTHORIZED, "No token provided")

    try:
        payload = verify_access_token(auth.credentials)
        if payload.get("type") != "access":
            raise ErrorResponse(status.HTTP_401_UNAUTHORIZED, "Invalid token type")

        request.state.user_id = payload.get("sub")
        request.state.user_tier = payload.get("role")

        return {"id": UUID(str(payload.get("sub"))), "tier": str(payload.get("role"))}

    except ErrorResponse:
        raise
    except ExpiredSignatureError:
        raise ErrorResponse(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except Exception:
        raise ErrorResponse(status.HTTP_401_UNAUTHORIZED, "Invalid token")
