from http import HTTPStatus
from uuid import uuid4
from types import SimpleNamespace
from datetime import UTC, datetime, timedelta

import pytest

from app.services import auth
from app.lib.exceptions import ErrorResponse


@pytest.mark.anyio
async def test_register_success(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = uuid4()
    captured: dict[str, object] = {}
    emitted: list[tuple[str, object]] = []

    async def fake_exists(**kwargs: str) -> bool:
        captured["exists_kwargs"] = kwargs
        return False

    async def fake_create(email: str, password_hash: str) -> SimpleNamespace:
        captured["created_email"] = email
        captured["created_password_hash"] = password_hash
        return SimpleNamespace(id=user_id, email=email, tier="free")

    def fake_password_hash(password: str) -> str:
        return "hashed-secret"

    def fake_emit(event: str, payload: object) -> None:
        emitted.append((event, payload))

    async def fake_first() -> SimpleNamespace:
        return SimpleNamespace(id=uuid4())

    class FakeRoleQuery:
        async def first(self) -> SimpleNamespace:
            return await fake_first()

    def fake_role_filter(**_: object) -> FakeRoleQuery:
        return FakeRoleQuery()

    async def fake_user_role_create(**kwargs: object) -> None:
        captured["user_role_create"] = kwargs

    monkeypatch.setattr(auth.User, "exists", fake_exists)
    monkeypatch.setattr(auth, "hash_password", fake_password_hash)
    monkeypatch.setattr(auth.User, "create", fake_create)
    monkeypatch.setattr(auth.Role, "filter", fake_role_filter)
    monkeypatch.setattr(auth.UserRole, "create", fake_user_role_create)
    monkeypatch.setattr(auth.APP_EVENTS, "emit", fake_emit)

    response = await auth.register("USER@Example.COM", "StrongPass1")

    assert response["success"] is True
    assert response["message"] == "User registered successfully"
    assert response["data"] == {
        "id": user_id,
        "email": "user@example.com",
        "tier": "free",
    }
    assert captured["exists_kwargs"] == {"email__iexact": "USER@Example.COM"}
    assert captured["created_email"] == "user@example.com"
    assert captured["created_password_hash"] == "hashed-secret"
    assert isinstance(captured["user_role_create"], dict)
    assert len(emitted) == 1


@pytest.mark.anyio
async def test_register_rejects_existing_email(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_exists(**_: str) -> bool:
        return True

    monkeypatch.setattr(auth.User, "exists", fake_exists)

    with pytest.raises(ErrorResponse) as exc:
        await auth.register("user@example.com", "StrongPass1")

    assert exc.value.status == HTTPStatus.BAD_REQUEST
    assert exc.value.message == "Email already registered"


@pytest.mark.anyio
async def test_login_rejects_missing_or_inactive_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    emitted: list[tuple[str, object]] = []

    async def fake_get_or_none(**_: str) -> None:
        return None

    def fake_emit(event: str, payload: object) -> None:
        emitted.append((event, payload))

    monkeypatch.setattr(auth.User, "get_or_none", fake_get_or_none)
    monkeypatch.setattr(auth.APP_EVENTS, "emit", fake_emit)

    with pytest.raises(ErrorResponse) as exc:
        await auth.login("user@example.com", "StrongPass1", "pytest-agent")

    assert exc.value.status == HTTPStatus.BAD_REQUEST
    assert exc.value.message == "Invalid credentials"
    assert emitted and emitted[0][0]


@pytest.mark.anyio
async def test_login_rejects_invalid_password(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(
        id=uuid4(),
        email="user@example.com",
        tier="free",
        password_hash="stored-hash",
        is_active=True,
    )

    async def fake_get_or_none(**_: str) -> SimpleNamespace:
        return user

    def fake_verify_password(*_: str) -> bool:
        return False

    monkeypatch.setattr(auth.User, "get_or_none", fake_get_or_none)
    monkeypatch.setattr(auth, "verify_password", fake_verify_password)

    with pytest.raises(ErrorResponse) as exc:
        await auth.login("user@example.com", "wrong-password")

    assert exc.value.status == HTTPStatus.BAD_REQUEST
    assert exc.value.message == "Invalid credentials"


@pytest.mark.anyio
async def test_login_success(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(
        id=uuid4(),
        email="user@example.com",
        tier="pro",
        password_hash="stored-hash",
        is_active=True,
    )
    captured: dict[str, object] = {}

    async def fake_get_or_none(**_: str) -> SimpleNamespace:
        return user

    def fake_verify_password(*_: str) -> bool:
        return True

    def fake_generate_access_token(*_: str) -> str:
        return "access-token"

    def fake_generate_refresh_token(*_: str) -> str:
        return "refresh-token"

    async def fake_create(**kwargs: object) -> None:
        captured["refresh_create"] = kwargs

    def fake_emit(*_: object) -> None:
        pass

    monkeypatch.setattr(auth.User, "get_or_none", fake_get_or_none)
    monkeypatch.setattr(auth, "verify_password", fake_verify_password)
    monkeypatch.setattr(auth, "generate_access_token", fake_generate_access_token)
    monkeypatch.setattr(auth, "generate_refresh_token", fake_generate_refresh_token)
    monkeypatch.setattr(auth.RefreshToken, "create", fake_create)
    monkeypatch.setattr(auth.APP_EVENTS, "emit", fake_emit)

    response = await auth.login("user@example.com", "StrongPass1")

    assert response["success"] is True
    assert response["data"]["access_token"] == "access-token"
    assert response["data"]["refresh_token"] == "refresh-token"
    assert response["data"]["user"]["id"] == user.id
    assert response["data"]["user"]["tier"] == "pro"
    refresh_create = captured["refresh_create"]
    assert isinstance(refresh_create, dict)
    assert refresh_create["user_id"] == user.id


@pytest.mark.anyio
async def test_refresh_rejects_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:

    def fake_verify_refresh_token(_: str) -> dict[str, str]:
        raise ValueError("bad token")

    monkeypatch.setattr(auth, "verify_refresh_token", fake_verify_refresh_token)

    with pytest.raises(ErrorResponse) as exc:
        await auth.refresh("invalid-token")

    assert exc.value.status == HTTPStatus.BAD_REQUEST
    assert exc.value.message == "Invalid refresh token"


@pytest.mark.anyio
async def test_refresh_rejects_non_refresh_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_verify_refresh_token(_: str) -> dict[str, str]:
        return {"sub": str(uuid4()), "type": "access", "role": "free"}

    monkeypatch.setattr(auth, "verify_refresh_token", fake_verify_refresh_token)

    with pytest.raises(ErrorResponse) as exc:
        await auth.refresh("token")

    assert exc.value.status == HTTPStatus.BAD_REQUEST
    assert exc.value.message == "Invalid token type"


@pytest.mark.anyio
async def test_refresh_rejects_expired_or_revoked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_verify_refresh_token(_: str) -> dict[str, str]:
        return {"sub": str(uuid4()), "type": "refresh", "role": "free"}

    monkeypatch.setattr(auth, "verify_refresh_token", fake_verify_refresh_token)

    async def fake_get_or_none(**_: str) -> None:
        return None

    monkeypatch.setattr(auth.RefreshToken, "get_or_none", fake_get_or_none)

    with pytest.raises(ErrorResponse) as exc:
        await auth.refresh("token")

    assert exc.value.status == HTTPStatus.BAD_REQUEST
    assert exc.value.message == "Refresh token expired or revoked"


@pytest.mark.anyio
async def test_refresh_success(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = uuid4()
    captured: dict[str, object] = {}

    class StoredToken:
        expires_at = datetime.now(UTC) + timedelta(days=1)

        async def delete(self) -> None:
            captured["deleted"] = True

    user = SimpleNamespace(
        id=user_id, email="user@example.com", tier="free", is_active=True
    )

    def fake_verify_refresh_token(_: str) -> dict[str, str]:
        return {"sub": str(user_id), "type": "refresh", "role": "free"}

    monkeypatch.setattr(auth, "verify_refresh_token", fake_verify_refresh_token)

    async def fake_get_token(**_: str) -> StoredToken:
        return StoredToken()

    async def fake_get_user(**_: object) -> SimpleNamespace:
        return user

    def fake_generate_access_token(*_: str) -> str:
        return "new-access"

    def fake_generate_refresh_token(*_: str) -> str:
        return "new-refresh"

    async def fake_create(**kwargs: object) -> None:
        captured["created"] = kwargs

    monkeypatch.setattr(auth.RefreshToken, "get_or_none", fake_get_token)
    monkeypatch.setattr(auth.User, "get_or_none", fake_get_user)
    monkeypatch.setattr(auth, "generate_access_token", fake_generate_access_token)
    monkeypatch.setattr(auth, "generate_refresh_token", fake_generate_refresh_token)
    monkeypatch.setattr(auth.RefreshToken, "create", fake_create)

    response = await auth.refresh("old-refresh")

    assert response["success"] is True
    assert response["data"] == {
        "access_token": "new-access",
        "refresh_token": "new-refresh",
    }
    assert captured["deleted"] is True
    assert isinstance(captured["created"], dict)


@pytest.mark.anyio
async def test_logout_revokes_hashed_token(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class DeleteQuery:
        async def delete(self) -> None:
            captured["deleted"] = True

    def fake_filter(**kwargs: str) -> DeleteQuery:
        captured["filter_kwargs"] = kwargs
        return DeleteQuery()

    monkeypatch.setattr(auth.RefreshToken, "filter", fake_filter)

    response = await auth.logout("refresh-token")

    assert response == {
        "success": True,
        "message": "Logged out",
        "data": None,
    }
    assert captured["deleted"] is True
    assert isinstance(captured["filter_kwargs"], dict)
