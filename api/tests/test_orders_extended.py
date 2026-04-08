"""Extended orders + cart tests for coverage."""
import pytest
from httpx import AsyncClient


async def _make_product(client, supplier_token, admin_token) -> str:
    resp = await client.post("/api/v1/products", json={
        "name": "Test Product", "price": 200000, "unit": "kg", "stock": 500,
    }, headers={"Authorization": f"Bearer {supplier_token}"})
    pid = resp.json()["id"]
    await client.patch(f"/api/v1/products/{pid}/status", json={"status": "published"},
                       headers={"Authorization": f"Bearer {admin_token}"})
    return pid


@pytest.mark.asyncio
async def test_remove_cart_item(client: AsyncClient, test_user, supplier_user, admin_user):
    _, token = test_user
    _, sup_t = supplier_user
    _, adm_t = admin_user
    pid = await _make_product(client, sup_t, adm_t)

    # Add
    await client.post("/api/v1/cart/items", json={"product_id": pid, "quantity": 5},
                      headers={"Authorization": f"Bearer {token}"})

    # Get cart to find item id
    cart = await client.get("/api/v1/cart", headers={"Authorization": f"Bearer {token}"})
    item_id = cart.json()["items"][0]["id"]

    # Remove
    resp = await client.delete(f"/api/v1/cart/items/{item_id}",
                               headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    # Verify empty
    cart2 = await client.get("/api/v1/cart", headers={"Authorization": f"Bearer {token}"})
    assert cart2.json()["count"] == 0


@pytest.mark.asyncio
async def test_update_cart_quantity(client: AsyncClient, test_user, supplier_user, admin_user):
    _, token = test_user
    _, sup_t = supplier_user
    _, adm_t = admin_user
    pid = await _make_product(client, sup_t, adm_t)

    await client.post("/api/v1/cart/items", json={"product_id": pid, "quantity": 3},
                      headers={"Authorization": f"Bearer {token}"})

    cart = await client.get("/api/v1/cart", headers={"Authorization": f"Bearer {token}"})
    item_id = cart.json()["items"][0]["id"]

    # Update to 10
    resp = await client.put(f"/api/v1/cart/items/{item_id}", json={"quantity": 10},
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    cart2 = await client.get("/api/v1/cart", headers={"Authorization": f"Bearer {token}"})
    assert cart2.json()["items"][0]["quantity"] == 10


@pytest.mark.asyncio
async def test_update_cart_zero_removes(client: AsyncClient, test_user, supplier_user, admin_user):
    _, token = test_user
    _, sup_t = supplier_user
    _, adm_t = admin_user
    pid = await _make_product(client, sup_t, adm_t)

    await client.post("/api/v1/cart/items", json={"product_id": pid, "quantity": 1},
                      headers={"Authorization": f"Bearer {token}"})

    cart = await client.get("/api/v1/cart", headers={"Authorization": f"Bearer {token}"})
    item_id = cart.json()["items"][0]["id"]

    # Set to 0 = remove
    await client.put(f"/api/v1/cart/items/{item_id}", json={"quantity": 0},
                     headers={"Authorization": f"Bearer {token}"})

    cart2 = await client.get("/api/v1/cart", headers={"Authorization": f"Bearer {token}"})
    assert cart2.json()["count"] == 0


@pytest.mark.asyncio
async def test_add_nonexistent_product_to_cart(client: AsyncClient, test_user):
    _, token = test_user
    resp = await client.post("/api/v1/cart/items", json={
        "product_id": "00000000-0000-0000-0000-000000000000", "quantity": 1,
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_orders_with_filter(client: AsyncClient, test_user, supplier_user, admin_user):
    _, token = test_user
    _, sup_t = supplier_user
    _, adm_t = admin_user
    pid = await _make_product(client, sup_t, adm_t)

    # Create order
    await client.post("/api/v1/cart/items", json={"product_id": pid, "quantity": 2},
                      headers={"Authorization": f"Bearer {token}"})
    await client.post("/api/v1/orders/checkout", json={
        "shipping_address": "test", "payment_method": "vnpay",
    }, headers={"Authorization": f"Bearer {token}"})

    # List with filter
    resp = await client.get("/api/v1/orders?status=processing",
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()["items"]) >= 1


@pytest.mark.asyncio
async def test_get_order_detail_success(client: AsyncClient, test_user, supplier_user, admin_user):
    _, token = test_user
    _, sup_t = supplier_user
    _, adm_t = admin_user
    pid = await _make_product(client, sup_t, adm_t)

    await client.post("/api/v1/cart/items", json={"product_id": pid, "quantity": 1},
                      headers={"Authorization": f"Bearer {token}"})
    checkout = await client.post("/api/v1/orders/checkout", json={
        "shipping_address": "456 Le Loi", "receiver_name": "Tran B",
        "receiver_phone": "0912345678", "notes": "Giao sang",
        "payment_method": "bank_transfer",
    }, headers={"Authorization": f"Bearer {token}"})
    oid = checkout.json()["order_id"]

    resp = await client.get(f"/api/v1/orders/{oid}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["shipping_address"] == "456 Le Loi"
    assert data["receiver_name"] == "Tran B"
    assert data["payment_method"] == "bank_transfer"
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_reorder(client: AsyncClient, test_user, supplier_user, admin_user):
    _, token = test_user
    _, sup_t = supplier_user
    _, adm_t = admin_user
    pid = await _make_product(client, sup_t, adm_t)

    await client.post("/api/v1/cart/items", json={"product_id": pid, "quantity": 3},
                      headers={"Authorization": f"Bearer {token}"})
    checkout = await client.post("/api/v1/orders/checkout", json={
        "shipping_address": "test", "payment_method": "vnpay",
    }, headers={"Authorization": f"Bearer {token}"})
    oid = checkout.json()["order_id"]

    # Reorder
    resp = await client.post(f"/api/v1/orders/{oid}/reorder",
                             headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "1" in resp.json()["message"]

    # Cart should have items again
    cart = await client.get("/api/v1/cart", headers={"Authorization": f"Bearer {token}"})
    assert cart.json()["count"] == 1


@pytest.mark.asyncio
async def test_confirm_serious_quality_suggests_dispute(client: AsyncClient, test_user, supplier_user, admin_user):
    _, token = test_user
    _, sup_t = supplier_user
    _, adm_t = admin_user
    pid = await _make_product(client, sup_t, adm_t)

    await client.post("/api/v1/cart/items", json={"product_id": pid, "quantity": 1},
                      headers={"Authorization": f"Bearer {token}"})
    checkout = await client.post("/api/v1/orders/checkout", json={
        "shipping_address": "test", "payment_method": "vnpay",
    }, headers={"Authorization": f"Bearer {token}"})
    oid = checkout.json()["order_id"]

    resp = await client.patch(f"/api/v1/orders/{oid}/confirm",
                              json={"quality": "serious"},
                              headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["action"] == "dispute"
