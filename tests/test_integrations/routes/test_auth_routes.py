import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_auth_register_login_refresh_logout_flow(
    async_client: AsyncClient,
) -> None:
    register_payload = {
        "email": "routeuser@example.com",
        "password": "StrongPass1",
    }

    register_response = await async_client.post(
        "/api/v1/auth/register",
        json=register_payload,
    )
    assert register_response.status_code == 201
    register_data = register_response.json()
    assert register_data["success"] is True
    assert register_data["data"]["email"] == "routeuser@example.com"

    duplicate_response = await async_client.post(
        "/api/v1/auth/register",
        json=register_payload,
    )
    assert duplicate_response.status_code == 400
    assert duplicate_response.json()["message"] == "Email already registered"

    invalid_login_response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "routeuser@example.com", "password": "wrong"},
    )
    assert invalid_login_response.status_code == 400
    assert invalid_login_response.json()["message"] == "Invalid credentials"

    login_response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "routeuser@example.com", "password": "StrongPass1"},
        headers={"User-Agent": "pytest"},
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    refresh_token = login_data["data"]["refresh_token"]
    assert login_data["data"]["access_token"]
    assert refresh_token

    refresh_response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 200
    refreshed = refresh_response.json()["data"]
    assert refreshed["access_token"]
    assert refreshed["refresh_token"]

    logout_response = await async_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refreshed["refresh_token"]},
    )
    assert logout_response.status_code == 200
    assert logout_response.json()["message"] == "Logged out"


@pytest.mark.anyio
async def test_auth_register_validation_error(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "invalid-email", "password": "weak"},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["success"] is False
    assert payload["message"] == "Validation Errors"
    assert payload["errors"]
