"""Extended auth tests to boost coverage on auth router."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_creates_wallet_and_prefs(client: AsyncClient):
    """Register should create user + preferences + wallet."""
    resp = await client.post("/api/v1/auth/register", json={
        "full_name": "Wallet User",
        "email": "wallet@test.com",
        "password": "Test12345",
        "role": "buyer",
    })
    assert resp.status_code == 201

    # Login to verify
    login = await client.post("/api/v1/auth/login", json={
        "email_or_phone": "wallet@test.com",
        "password": "Test12345",
    })
    assert login.status_code == 200
    token = login.json()["access_token"]

    # Check wallet exists
    wallet = await client.get("/api/v1/wallet", headers={"Authorization": f"Bearer {token}"})
    assert wallet.status_code == 200
    assert wallet.json()["available_balance"] == 0

    # Check preferences
    prefs = await client.get("/api/v1/auth/me/preferences", headers={"Authorization": f"Bearer {token}"})
    assert prefs.status_code == 200
    assert prefs.json()["lang"] == "VI"
    assert prefs.json()["theme"] == "dark"


@pytest.mark.asyncio
async def test_register_with_phone(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "full_name": "Phone User",
        "email": "phone@test.com",
        "phone": "0911222333",
        "password": "Test12345",
        "role": "worker",
    })
    assert resp.status_code == 201

    # Login with phone
    login = await client.post("/api/v1/auth/login", json={
        "email_or_phone": "0911222333",
        "password": "Test12345",
    })
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "worker"


@pytest.mark.asyncio
async def test_register_duplicate_phone(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "full_name": "User A",
        "email": "a_dup_phone@test.com",
        "phone": "0999888777",
        "password": "Test12345",
        "role": "buyer",
    })
    resp = await client.post("/api/v1/auth/register", json={
        "full_name": "User B",
        "email": "b_dup_phone@test.com",
        "phone": "0999888777",
        "password": "Test12345",
        "role": "buyer",
    })
    assert resp.status_code == 400
    assert "điện thoại" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_login_sets_refresh_cookie(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "full_name": "Cookie User",
        "email": "cookie@test.com",
        "password": "Test12345",
        "role": "buyer",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email_or_phone": "cookie@test.com",
        "password": "Test12345",
    })
    assert resp.status_code == 200
    # Check refresh cookie is set
    assert "refresh_token" in resp.headers.get("set-cookie", "")


@pytest.mark.asyncio
async def test_update_me(client: AsyncClient, test_user):
    _, token = test_user
    resp = await client.patch("/api/v1/auth/me", json={
        "full_name": "Updated Name",
        "avatar_url": "https://example.com/avatar.png",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_forgot_password(client: AsyncClient):
    resp = await client.post("/api/v1/auth/forgot-password", json={
        "email": "anyone@test.com",
    })
    assert resp.status_code == 200
    assert "link" in resp.json()["message"].lower() or "email" in resp.json()["message"].lower()


@pytest.mark.asyncio
async def test_verify_otp(client: AsyncClient):
    resp = await client.post("/api/v1/auth/verify-otp", json={
        "phone": "0901234567",
        "otp": "123456",
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_suspended_user_cannot_login(client: AsyncClient, admin_user, test_user):
    user, user_token = test_user
    _, admin_token = admin_user

    # Suspend user
    await client.patch(f"/api/v1/admin/users/{user.id}",
                       json={"status": "suspended"},
                       headers={"Authorization": f"Bearer {admin_token}"})

    # Try login
    resp = await client.post("/api/v1/auth/login", json={
        "email_or_phone": "test@nexbuild.vn",
        "password": "Test1234",
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_me_with_supplier_fields(client: AsyncClient, supplier_user):
    _, token = supplier_user
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "supplier"
    assert resp.json()["store_name"] == "Test Store"
