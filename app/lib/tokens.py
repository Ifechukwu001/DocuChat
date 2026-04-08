from datetime import UTC, datetime, timedelta

import jwt

from app.env import settings


def generate_access_token(user_id: str, user_tier: str) -> str:
    """Generate access token for a user."""
    return jwt.encode(  # type: ignore
        {
            "sub": user_id,
            "role": user_tier,
            "type": "access",
            "exp": datetime.now(UTC) + timedelta(minutes=15),
        },
        key=settings.JWT_ACCESS_SECRET,
        algorithm="HS256",
    )


def generate_refresh_token(user_id: str, user_tier: str) -> str:
    """Generate refresh token for a user."""
    return jwt.encode(  # type: ignore
        {
            "sub": user_id,
            "role": user_tier,
            "type": "refresh",
            "exp": datetime.now(UTC) + timedelta(days=7),
        },
        key=settings.JWT_REFRESH_SECRET,
        algorithm="HS256",
    )


def verify_access_token(token: str) -> dict[str, str | int]:
    """Verify access token and return payload."""
    payload = jwt.decode_complete(  # type: ignore
        token,
        settings.JWT_ACCESS_SECRET,
        algorithms=["HS256"],
        options={"require": ["sub", "role", "type", "exp"]},
    )["payload"]

    return {
        "sub": payload.get("sub"),
        "role": payload.get("role"),
        "type": payload.get("type"),
    }


def verify_refresh_token(token: str) -> dict[str, str | int]:
    """Verify refresh token and return payload."""
    payload = jwt.decode_complete(  # type: ignore
        token,
        settings.JWT_REFRESH_SECRET,
        algorithms=["HS256"],
        options={"require": ["sub", "role", "type", "exp"]},
    )["payload"]

    return {
        "sub": payload.get("sub"),
        "role": payload.get("role"),
        "type": payload.get("type"),
    }
