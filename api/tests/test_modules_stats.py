"""Modules + Stats + Admin tests."""
import pytest
from httpx import AsyncClient


# ─── Modules ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_modules_empty(client: AsyncClient):
    resp = await client.get("/api/v1/modules")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_module_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/modules/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_modules_with_data(client: AsyncClient, db_session):
    from api.models.module import Module
    m = Module(id="design", name="NexDesign AI", num="01", tag="AI Thiet ke",
               model="Subscription SaaS", hook="Thiet ke nha bang AI",
               color="#00C9A7", is_active=True, sort_order=1)
    db_session.add(m)
    await db_session.commit()

    resp = await client.get("/api/v1/modules")
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "NexDesign AI"


@pytest.mark.asyncio
async def test_get_module_detail(client: AsyncClient, db_session):
    from api.models.module import Module, ModulePain, ModuleResult
    m = Module(id="talent", name="NexTalent", num="02", tag="Lao dong",
               color="#0EA5E9", is_active=True, sort_order=2)
    db_session.add(m)
    await db_session.flush()

    db_session.add(ModulePain(module_id="talent", before_title="Tim tho kho",
                              after_title="1 click la co", sort_order=0))
    db_session.add(ModuleResult(module_id="talent", emoji="📈",
                                title="Booking tang 300%", kpi="+300%", sort_order=0))
    await db_session.commit()

    resp = await client.get("/api/v1/modules/talent")
    assert resp.status_code == 200
    data = resp.json()
    assert data["module"]["name"] == "NexTalent"
    assert len(data["pains"]) == 1
    assert len(data["results"]) == 1


# ─── Stats ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_platform_stats(client: AsyncClient):
    resp = await client.get("/api/v1/stats/platform")
    assert resp.status_code == 200
    data = resp.json()
    assert "workers" in data
    assert "suppliers" in data
    assert "projects" in data


@pytest.mark.asyncio
async def test_admin_stats_unauthorized(client: AsyncClient, test_user):
    _, token = test_user  # buyer
    resp = await client.get("/api/v1/stats/admin", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_stats(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.get("/api/v1/stats/admin", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_users" in data
    assert "gmv" in data


@pytest.mark.asyncio
async def test_admin_stats_detail(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.get("/api/v1/stats/admin?detail=true",
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "pending_products" in data
    assert "pending_workers" in data


# ─── Admin CRUD ───────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_list_users(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_admin_list_users_filter_role(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.get("/api/v1/admin/users?role=admin",
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_pending_products(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.get("/api/v1/admin/products/pending",
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_pending_workers(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.get("/api/v1/admin/workers/pending",
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_disputes(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.get("/api/v1/admin/disputes",
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_transactions(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.get("/api/v1/admin/transactions",
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_settings(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.get("/api/v1/admin/settings",
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_audit_log(client: AsyncClient, admin_user):
    _, token = admin_user
    resp = await client.get("/api/v1/admin/audit-log",
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_update_user_status(client: AsyncClient, admin_user, test_user):
    _, admin_token = admin_user
    user, _ = test_user

    resp = await client.patch(f"/api/v1/admin/users/{user.id}",
                              json={"status": "suspended"},
                              headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
