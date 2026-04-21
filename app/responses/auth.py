from uuid import UUID

from pydantic import BaseModel


class UserResponse(BaseModel):
    """User Response."""

    id: UUID
    email: str
    tier: str


class LoginResponse(BaseModel):
    """Login Response."""

    access_token: str
    refresh_token: str
    user: UserResponse


class RefreshResponse(BaseModel):
    """Refresh Response."""

    access_token: str
    refresh_token: str
