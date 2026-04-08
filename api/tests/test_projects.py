"""Projects + Bids tests."""
import pytest
from httpx import AsyncClient


async def _create_contractor(client: AsyncClient, db_session):
    """Create contractor user."""
    from api.models.user import User
    from api.core.security import hash_password, create_access_token

    user = User(
        email="contractor@test.com",
        password_hash=hash_password("Cont1234"),
        full_name="Nha Thau Test", role="contractor", status="active",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user, create_access_token(str(user.id), user.role)


@pytest.mark.asyncio
async def test_list_projects_empty(client: AsyncClient):
    resp = await client.get("/api/v1/projects")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, test_user):
    _, token = test_user
    resp = await client.post("/api/v1/projects", json={
        "title": "Xay nha pho 3 tang",
        "type": "nha_o",
        "budget_min": 280000000,
        "budget_max": 350000000,
        "duration_days": 45,
        "address": "Dong Da, Ha Noi",
        "floor_area_m2": 80,
        "requirements": "Xay tho + hoan thien",
        "work_categories": ["xay_tho", "hoan_thien", "dien_nuoc"],
        "payment_method": "escrow",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_get_project_detail(client: AsyncClient, test_user):
    _, token = test_user
    create_resp = await client.post("/api/v1/projects", json={
        "title": "Van phong 5 tang",
        "type": "van_phong",
        "budget_min": 2000000000,
        "budget_max": 5000000000,
    }, headers={"Authorization": f"Bearer {token}"})
    pid = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/projects/{pid}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Van phong 5 tang"
    assert resp.json()["view_count"] == 1  # incremented


@pytest.mark.asyncio
async def test_update_project(client: AsyncClient, test_user):
    _, token = test_user
    create_resp = await client.post("/api/v1/projects", json={
        "title": "Test project",
        "type": "nha_o",
    }, headers={"Authorization": f"Bearer {token}"})
    pid = create_resp.json()["id"]

    resp = await client.put(f"/api/v1/projects/{pid}", json={
        "title": "Updated project",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_submit_bid(client: AsyncClient, test_user, db_session):
    _, buyer_token = test_user
    contractor, cont_token = await _create_contractor(client, db_session)

    # Buyer creates project
    create_resp = await client.post("/api/v1/projects", json={
        "title": "Test bid project",
        "type": "nha_o",
        "budget_min": 300000000,
        "budget_max": 400000000,
    }, headers={"Authorization": f"Bearer {buyer_token}"})
    pid = create_resp.json()["id"]

    # Contractor submits bid
    resp = await client.post(f"/api/v1/projects/{pid}/bids", json={
        "bid_price": 350000000,
        "price_unit": "dong",
        "duration_value": 60,
        "duration_unit": "ngay",
        "capability": "15 nam kinh nghiem xay nha pho",
        "construction_plan": "Thi cong 3 giai doan",
    }, headers={"Authorization": f"Bearer {cont_token}"})
    assert resp.status_code == 201
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_list_bids(client: AsyncClient, test_user, db_session):
    _, buyer_token = test_user
    _, cont_token = await _create_contractor(client, db_session)

    create_resp = await client.post("/api/v1/projects", json={
        "title": "Bid list test",
        "type": "nha_o",
    }, headers={"Authorization": f"Bearer {buyer_token}"})
    pid = create_resp.json()["id"]

    await client.post(f"/api/v1/projects/{pid}/bids", json={
        "bid_price": 300000000,
    }, headers={"Authorization": f"Bearer {cont_token}"})

    resp = await client.get(f"/api/v1/projects/{pid}/bids",
                            headers={"Authorization": f"Bearer {buyer_token}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_update_bid_status(client: AsyncClient, test_user, db_session):
    _, buyer_token = test_user
    _, cont_token = await _create_contractor(client, db_session)

    create_resp = await client.post("/api/v1/projects", json={
        "title": "Status test",
        "type": "nha_o",
    }, headers={"Authorization": f"Bearer {buyer_token}"})
    pid = create_resp.json()["id"]

    bid_resp = await client.post(f"/api/v1/projects/{pid}/bids", json={
        "bid_price": 300000000,
    }, headers={"Authorization": f"Bearer {cont_token}"})
    bid_id = bid_resp.json()["bid_id"]

    resp = await client.patch(f"/api/v1/projects/{pid}/bids/{bid_id}",
                              json={"status": "shortlisted"},
                              headers={"Authorization": f"Bearer {buyer_token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_bid_unauthorized_non_contractor(client: AsyncClient, test_user):
    """Buyer cannot submit bid."""
    _, token = test_user  # buyer role
    create_resp = await client.post("/api/v1/projects", json={
        "title": "Auth test",
        "type": "nha_o",
    }, headers={"Authorization": f"Bearer {token}"})
    pid = create_resp.json()["id"]

    resp = await client.post(f"/api/v1/projects/{pid}/bids", json={
        "bid_price": 100000000,
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
