"""Extended product tests — search, sort, filter, delete."""
import pytest
from httpx import AsyncClient


async def _pub_product(client, sup_t, adm_t, name="Test", price=100000) -> str:
    r = await client.post("/api/v1/products", json={"name": name, "price": price, "unit": "kg"},
                          headers={"Authorization": f"Bearer {sup_t}"})
    pid = r.json()["id"]
    await client.patch(f"/api/v1/products/{pid}/status", json={"status": "published"},
                       headers={"Authorization": f"Bearer {adm_t}"})
    return pid


@pytest.mark.asyncio
async def test_search_products(client: AsyncClient, supplier_user, admin_user):
    _, sup_t = supplier_user
    _, adm_t = admin_user
    await _pub_product(client, sup_t, adm_t, "Xi mang Vicem")
    await _pub_product(client, sup_t, adm_t, "Thep Hoa Phat")

    resp = await client.get("/api/v1/products?search=Xi mang")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert "Xi mang" in resp.json()["items"][0]["name"]


@pytest.mark.asyncio
async def test_sort_products_price(client: AsyncClient, supplier_user, admin_user):
    _, sup_t = supplier_user
    _, adm_t = admin_user
    await _pub_product(client, sup_t, adm_t, "Cheap", 50000)
    await _pub_product(client, sup_t, adm_t, "Expensive", 900000)

    asc = await client.get("/api/v1/products?sort=price_asc")
    items = asc.json()["items"]
    assert items[0]["price"] <= items[-1]["price"]

    desc = await client.get("/api/v1/products?sort=price_desc")
    items2 = desc.json()["items"]
    assert items2[0]["price"] >= items2[-1]["price"]


@pytest.mark.asyncio
async def test_sort_products_rating(client: AsyncClient, supplier_user, admin_user):
    _, sup_t = supplier_user
    _, adm_t = admin_user
    await _pub_product(client, sup_t, adm_t, "Rated product")

    resp = await client.get("/api/v1/products?sort=rating")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_product_detail(client: AsyncClient, supplier_user, admin_user):
    _, sup_t = supplier_user
    _, adm_t = admin_user
    pid = await _pub_product(client, sup_t, adm_t, "Detail test", 250000)

    resp = await client.get(f"/api/v1/products/{pid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Detail test"
    assert resp.json()["price"] == 250000


@pytest.mark.asyncio
async def test_product_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/products/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_product(client: AsyncClient, supplier_user):
    _, token = supplier_user
    r = await client.post("/api/v1/products", json={"name": "Delete me", "price": 1000, "unit": "cai"},
                          headers={"Authorization": f"Bearer {token}"})
    pid = r.json()["id"]

    resp = await client.delete(f"/api/v1/products/{pid}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_reject_product(client: AsyncClient, supplier_user, admin_user):
    _, sup_t = supplier_user
    _, adm_t = admin_user
    r = await client.post("/api/v1/products", json={"name": "Reject me", "price": 1000, "unit": "bao"},
                          headers={"Authorization": f"Bearer {sup_t}"})
    pid = r.json()["id"]

    resp = await client.patch(f"/api/v1/products/{pid}/status", json={"status": "rejected"},
                              headers={"Authorization": f"Bearer {adm_t}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_categories_empty(client: AsyncClient):
    resp = await client.get("/api/v1/categories")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_category_products_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/categories/nonexistent/products")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_pagination(client: AsyncClient, supplier_user, admin_user):
    _, sup_t = supplier_user
    _, adm_t = admin_user
    for i in range(5):
        await _pub_product(client, sup_t, adm_t, f"Pag item {i}", 10000 * (i + 1))

    resp = await client.get("/api/v1/products?page=1&limit=2")
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["pages"] == 3

    resp2 = await client.get("/api/v1/products?page=3&limit=2")
    assert len(resp2.json()["items"]) == 1
