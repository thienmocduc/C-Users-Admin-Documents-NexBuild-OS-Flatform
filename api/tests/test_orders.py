"""Orders + Cart + Escrow tests."""
import pytest
from httpx import AsyncClient


async def _create_published_product(client, supplier_token, admin_token) -> str:
    """Helper: create and approve a product."""
    resp = await client.post("/api/v1/products", json={
        "name": "Xi mang test",
        "price": 100000,
        "unit": "bao",
        "stock": 1000,
    }, headers={"Authorization": f"Bearer {supplier_token}"})
    pid = resp.json()["id"]

    await client.patch(
        f"/api/v1/products/{pid}/status",
        json={"status": "published"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    return pid


@pytest.mark.asyncio
async def test_cart_flow(client: AsyncClient, test_user, supplier_user, admin_user):
    user, token = test_user
    _, sup_token = supplier_user
    _, admin_token = admin_user

    product_id = await _create_published_product(client, sup_token, admin_token)

    # Add to cart
    resp = await client.post("/api/v1/cart/items", json={
        "product_id": product_id,
        "quantity": 10,
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201

    # Get cart
    cart = await client.get("/api/v1/cart", headers={"Authorization": f"Bearer {token}"})
    assert cart.status_code == 200
    data = cart.json()
    assert data["count"] == 1
    assert data["subtotal"] == 1000000  # 100000 * 10
    assert data["vat"] == 100000  # 10%

    # Add same product again (should increment)
    await client.post("/api/v1/cart/items", json={
        "product_id": product_id,
        "quantity": 5,
    }, headers={"Authorization": f"Bearer {token}"})

    cart2 = await client.get("/api/v1/cart", headers={"Authorization": f"Bearer {token}"})
    assert cart2.json()["items"][0]["quantity"] == 15


@pytest.mark.asyncio
async def test_checkout_creates_escrow(client: AsyncClient, test_user, supplier_user, admin_user):
    user, token = test_user
    _, sup_token = supplier_user
    _, admin_token = admin_user

    product_id = await _create_published_product(client, sup_token, admin_token)

    # Add to cart
    await client.post("/api/v1/cart/items", json={
        "product_id": product_id,
        "quantity": 5,
    }, headers={"Authorization": f"Bearer {token}"})

    # Checkout
    resp = await client.post("/api/v1/orders/checkout", json={
        "shipping_address": "123 Nguyen Trai, HN",
        "receiver_name": "Nguyen Van A",
        "receiver_phone": "0901234567",
        "payment_method": "vnpay",
    }, headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 201
    data = resp.json()
    assert "order_id" in data
    assert "escrow_id" in data
    assert data["requires_otp"] is True
    assert data["total"] == 550000  # 500000 + 50000 VAT

    # Cart should be empty now
    cart = await client.get("/api/v1/cart", headers={"Authorization": f"Bearer {token}"})
    assert cart.json()["count"] == 0


@pytest.mark.asyncio
async def test_checkout_empty_cart(client: AsyncClient, test_user):
    _, token = test_user
    resp = await client.post("/api/v1/orders/checkout", json={
        "shipping_address": "test",
        "payment_method": "vnpay",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_order_idor_prevention(client: AsyncClient, test_user, supplier_user, admin_user):
    """User A cannot view User B's orders."""
    user_a, token_a = test_user
    _, sup_token = supplier_user
    _, admin_token = admin_user

    # Create order for user A
    product_id = await _create_published_product(client, sup_token, admin_token)
    await client.post("/api/v1/cart/items", json={"product_id": product_id, "quantity": 1},
                      headers={"Authorization": f"Bearer {token_a}"})
    checkout_resp = await client.post("/api/v1/orders/checkout", json={
        "shipping_address": "test", "payment_method": "vnpay",
    }, headers={"Authorization": f"Bearer {token_a}"})
    order_id = checkout_resp.json()["order_id"]

    # Create user B
    await client.post("/api/v1/auth/register", json={
        "full_name": "User B", "email": "userb@test.com",
        "password": "Test12345", "role": "buyer",
    })
    login_b = await client.post("/api/v1/auth/login", json={
        "email_or_phone": "userb@test.com", "password": "Test12345",
    })
    token_b = login_b.json()["access_token"]

    # User B tries to view User A's order
    resp = await client.get(f"/api/v1/orders/{order_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_confirm_order_releases_escrow(client: AsyncClient, test_user, supplier_user, admin_user):
    _, token = test_user
    _, sup_token = supplier_user
    _, admin_token = admin_user

    product_id = await _create_published_product(client, sup_token, admin_token)
    await client.post("/api/v1/cart/items", json={"product_id": product_id, "quantity": 1},
                      headers={"Authorization": f"Bearer {token}"})
    checkout = await client.post("/api/v1/orders/checkout", json={
        "shipping_address": "test", "payment_method": "vnpay",
    }, headers={"Authorization": f"Bearer {token}"})
    order_id = checkout.json()["order_id"]

    # Confirm receipt
    resp = await client.patch(f"/api/v1/orders/{order_id}/confirm", json={
        "quality": "correct",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "Escrow đã được giải phóng" in resp.json()["message"]
