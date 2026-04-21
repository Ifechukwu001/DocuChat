"""Pytest global fixtures for unit and integration tests."""

from collections.abc import AsyncGenerator

import pytest
from httpx import AsyncClient, ASGITransport
from tortoise import Tortoise

from app.env import settings
from app.main import application


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Use asyncio for async tests."""
    return "asyncio"


@pytest.fixture
async def db_connection() -> AsyncGenerator[None]:
    """Create an isolated in-memory DB for each test."""
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"main": ["app.orm.models"]},
    )
    await Tortoise.generate_schemas(safe=False)
    yield
    await Tortoise.close_connections()


@pytest.fixture
async def async_client(db_connection: None) -> AsyncGenerator[AsyncClient]:
    """Create an HTTP client for testing the ASGI app."""
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://testserver",
    ) as client:
        yield client


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture to mock settings for tests."""
    monkeypatch.setattr(
        settings,
        "JWT_ACCESS_SECRET",
        "random-access-secret-that-is-long-enough",
    )

    monkeypatch.setattr(
        settings,
        "JWT_REFRESH_SECRET",
        "random-refresh-secret-that-is-long-enough",
    )
