import hashlib
from http import HTTPStatus
from uuid import UUID
from typing import Any
from datetime import UTC, datetime, timedelta

from app.lib.events import APP_EVENTS
from app.lib.tokens import (
    verify_refresh_token,
    generate_access_token,
    generate_refresh_token,
)
from app.orm.models import User, RefreshToken, Role, UserRole
from app.lib.password import hash_password, verify_password
from app.events.auth import AuthEvents
from app.lib.response_formatter import error_response, success_response


async def register(email: str, password: str) -> dict[str, Any]:
    """Register a new user."""
    existing = await User.exists(email__iexact=email)
    if existing:
        return error_response(HTTPStatus.BAD_REQUEST, "Email already registered")

    password_hash = hash_password(password)
    user = await User.create(email=email.lower(), password_hash=password_hash)

    # Assign default role to the new user
    default_role = await Role.filter(is_default=True).first()
    if default_role:
        await UserRole.create(user=user, role=default_role)

    APP_EVENTS.emit(AuthEvents.USER_REGISTERED, user)

    return success_response(
        "User registered successfully",
        {"id": user.id, "email": user.email, "tier": user.tier},
    )


async def login(
    email: str, password: str, device_info: str | None = None
) -> dict[str, Any]:
    """Login user and return tokens."""
    user = await User.get_or_none(email__iexact=email)
    if not user or not user.is_active:
        APP_EVENTS.emit(
            AuthEvents.LOGIN_FAILED, {"email": email, "device_info": device_info}
        )
        return error_response(HTTPStatus.BAD_REQUEST, "Invalid credentials")

    valid = verify_password(password, user.password_hash)
    if not valid:
        APP_EVENTS.emit(
            AuthEvents.LOGIN_FAILED, {"email": email, "device_info": device_info}
        )
        return error_response(HTTPStatus.BAD_REQUEST, "Invalid credentials")

    access_token = generate_access_token(user.id.hex, user.tier)
    refresh_token = generate_refresh_token(user.id.hex, user.tier)

    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

    await RefreshToken.create(
        user_id=user.id,
        token=token_hash,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )

    APP_EVENTS.emit(
        AuthEvents.USER_LOGGED_IN, {"user_id": user.id.hex, "device_info": device_info}
    )

    return success_response(
        "User logged in successfully",
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {"id": user.id, "email": user.email, "tier": user.tier},
        },
    )


async def refresh(raw_refresh_token: str) -> dict[str, Any]:
    """Refresh access token using refresh token."""
    try:
        payload = verify_refresh_token(raw_refresh_token)
    except Exception:
        return error_response(HTTPStatus.BAD_REQUEST, "Invalid refresh token")

    if payload.get("type") != "refresh":
        return error_response(HTTPStatus.BAD_REQUEST, "Invalid token type")

    token_hash = hashlib.sha256(raw_refresh_token.encode()).hexdigest()

    stored = await RefreshToken.get_or_none(token=token_hash)

    if not stored or stored.expires_at < datetime.now(UTC):
        return error_response(
            HTTPStatus.BAD_REQUEST, "Refresh token expired or revoked"
        )

    user = await User.get_or_none(id=UUID(str(payload.get("sub"))))

    if not user or not user.is_active:
        return error_response(HTTPStatus.BAD_REQUEST, "User not found or inactive")

    await stored.delete()

    new_access_token = generate_access_token(user.id.hex, user.tier)
    new_refresh_token = generate_refresh_token(user.id.hex, user.tier)
    new_hash = hashlib.sha256(new_refresh_token.encode()).hexdigest()

    await RefreshToken.create(
        user_id=user.id,
        token=new_hash,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )

    return success_response(
        "Access token refreshed successfully",
        {"access_token": new_access_token, "refresh_token": new_refresh_token},
    )


async def logout(raw_refresh_token: str) -> dict[str, Any]:
    """Logout user by revoking refresh token."""
    token_hash = hashlib.sha256(raw_refresh_token.encode()).hexdigest()
    await RefreshToken.filter(token=token_hash).delete()

    return success_response("Logged out")
