from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.lib.tokens import generate_access_token, generate_refresh_token


@pytest.mark.anyio
async def test_documents_routes_require_auth(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/documents")
    assert response.status_code == 401
    assert response.json()["message"] == "No token provided"

    invalid_token_response = await async_client.get(
        "/api/v1/documents",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert invalid_token_response.status_code == 401
    assert invalid_token_response.json()["message"] == "Invalid token"


@pytest.mark.anyio
async def test_documents_routes_accept_valid_access_token(
    async_client: AsyncClient,
) -> None:
    token = generate_access_token(str(uuid4()), "free")

    response = await async_client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == {}


@pytest.mark.anyio
async def test_documents_routes_reject_refresh_token(async_client: AsyncClient) -> None:
    token = generate_refresh_token(str(uuid4()), "free")

    response = await async_client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert response.json()["message"] == "Invalid token"


@pytest.mark.anyio
async def test_conversations_routes_accept_valid_access_token(
    async_client: AsyncClient,
) -> None:
    token = generate_access_token(str(uuid4()), "free")

    response = await async_client.get(
        "/api/v1/conversations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == {}
