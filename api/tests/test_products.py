"""Product endpoint tests."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_products_empty(client: AsyncClient):
    resp = await client.get("/api/v1/products")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_create_product_unauthorized(client: AsyncClient, test_user):
    _, token = test_user  # buyer, not supplier
    resp = await client.post("/api/v1/products", json={
        "name": "Xi mang",
        "price": 128000,
        "unit": "bao",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403  # Not supplier


@pytest.mark.asyncio
async def test_create_product_success(client: AsyncClient, supplier_user):
    _, token = supplier_user
    resp = await client.post("/api/v1/products", json={
        "name": "Xi mang Vicem PCB40",
        "price": 128000,
        "unit": "bao",
        "stock": 5000,
        "min_order": 100,
        "delivery_time": "24h",
        "is_d2c": True,
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Xi mang Vicem PCB40"
    assert data["price"] == 128000
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_create_product_invalid_unit(client: AsyncClient, supplier_user):
    _, token = supplier_user
    resp = await client.post("/api/v1/products", json={
        "name": "Test",
        "price": 100,
        "unit": "invalid_unit",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_product_negative_price(client: AsyncClient, supplier_user):
    _, token = supplier_user
    resp = await client.post("/api/v1/products", json={
        "name": "Test",
        "price": -100,
        "unit": "kg",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_admin_approve_product(client: AsyncClient, supplier_user, admin_user):
    _, sup_token = supplier_user
    _, admin_token = admin_user

    # Create product
    create_resp = await client.post("/api/v1/products", json={
        "name": "Thep Hoa Phat",
        "price": 18500,
        "unit": "kg",
    }, headers={"Authorization": f"Bearer {sup_token}"})
    product_id = create_resp.json()["id"]

    # Approve
    resp = await client.patch(
        f"/api/v1/products/{product_id}/status",
        json={"status": "published"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    # Now visible in public list
    list_resp = await client.get("/api/v1/products")
    assert list_resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_product_idor_prevention(client: AsyncClient, supplier_user):
    """Supplier A cannot edit Supplier B's product."""
    _, token_a = supplier_user

    # Create another supplier
    await client.post("/api/v1/auth/register", json={
        "full_name": "Supplier B",
        "email": "supplierb@test.com",
        "password": "Test12345",
        "role": "supplier",
    })
    login_resp = await client.post("/api/v1/auth/login", json={
        "email_or_phone": "supplierb@test.com",
        "password": "Test12345",
    })
    token_b = login_resp.json()["access_token"]

    # B creates product
    create_resp = await client.post("/api/v1/products", json={
        "name": "Product B",
        "price": 50000,
        "unit": "cai",
    }, headers={"Authorization": f"Bearer {token_b}"})
    product_id = create_resp.json()["id"]

    # A tries to edit B's product
    resp = await client.put(
        f"/api/v1/products/{product_id}",
        json={"name": "Hacked"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 403
