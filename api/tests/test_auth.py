"""Auth endpoint tests."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "full_name": "Nguyen Van A",
        "email": "nguyenvana@test.com",
        "phone": "0912345678",
        "password": "SecurePass123",
        "role": "buyer",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["ok"] is True


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {
        "full_name": "User A",
        "email": "dup@test.com",
        "password": "SecurePass123",
        "role": "buyer",
    }
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 400
    assert "đã được sử dụng" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_register_invalid_role(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "full_name": "User",
        "email": "role@test.com",
        "password": "SecurePass123",
        "role": "hacker",
    })
    assert resp.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "full_name": "User",
        "email": "short@test.com",
        "password": "abc",
        "role": "buyer",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    # Register first
    await client.post("/api/v1/auth/register", json={
        "full_name": "Login User",
        "email": "login@test.com",
        "password": "SecurePass123",
        "role": "buyer",
    })

    resp = await client.post("/api/v1/auth/login", json={
        "email_or_phone": "login@test.com",
        "password": "SecurePass123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "login@test.com"
    assert data["user"]["role"] == "buyer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "full_name": "Wrong Pass",
        "email": "wrongpass@test.com",
        "password": "CorrectPass123",
        "role": "buyer",
    })

    resp = await client.post("/api/v1/auth/login", json={
        "email_or_phone": "wrongpass@test.com",
        "password": "WrongPass123",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={
        "email_or_phone": "nouser@test.com",
        "password": "Whatever123",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authorized(client: AsyncClient, test_user):
    user, token = test_user
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@nexbuild.vn"
    assert data["role"] == "buyer"


@pytest.mark.asyncio
async def test_update_preferences(client: AsyncClient, test_user):
    _, token = test_user
    resp = await client.patch(
        "/api/v1/auth/me/preferences",
        json={"lang": "EN", "theme": "light"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["lang"] == "EN"
    assert data["theme"] == "light"


@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
