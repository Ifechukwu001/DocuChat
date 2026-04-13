"""Pytest global fixtures for unit and integration tests."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise

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
