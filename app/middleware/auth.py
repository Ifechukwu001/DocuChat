from typing import Annotated
from uuid import UUID

from jwt import ExpiredSignatureError
from fastapi import Depends, status
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
)

from app.lib.tokens import verify_access_token
from app.lib.exceptions import ErrorResponse

Authorization = Annotated[
    HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=False))
]


async def authenticate(auth: Authorization) -> UUID:
    """Authenticate request."""
    if not auth:
        raise ErrorResponse(status.HTTP_401_UNAUTHORIZED, "No token provided")

    try:
        payload = verify_access_token(auth.credentials)
        if payload.get("type") != "access":
            raise ErrorResponse(status.HTTP_401_UNAUTHORIZED, "Invalid token type")

        return UUID(str(payload.get("sub")))

    except ErrorResponse:
        raise
    except ExpiredSignatureError:
        raise ErrorResponse(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except Exception:
        raise ErrorResponse(status.HTTP_401_UNAUTHORIZED, "Invalid token")
