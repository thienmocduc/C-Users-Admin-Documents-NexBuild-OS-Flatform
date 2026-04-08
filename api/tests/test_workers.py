"""Worker endpoint tests."""
import pytest
from httpx import AsyncClient


async def _create_worker_user(db_session):
    from api.models.user import User, UserPreference
    from api.models.finance import Wallet
    from api.core.security import hash_password, create_access_token

    user = User(
        email="testworker@test.com",
        password_hash=hash_password("Worker1234"),
        full_name="Worker Test", role="worker", status="active",
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserPreference(user_id=user.id))
    db_session.add(Wallet(user_id=user.id))
    await db_session.commit()
    await db_session.refresh(user)
    return user, create_access_token(str(user.id), user.role)


@pytest.mark.asyncio
async def test_list_workers_empty(client: AsyncClient):
    resp = await client.get("/api/v1/workers")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_create_worker_profile(client: AsyncClient, db_session):
    user, token = await _create_worker_user(db_session)
    resp = await client.post("/api/v1/workers/profile", json={
        "trade": "tho_ho",
        "experience_years": 5,
        "daily_rate": 450000,
        "work_area": "Ha Noi",
        "bio": "15 nam kinh nghiem xay dung",
        "skills": ["to_trat", "op_lat", "do_be_tong"],
        "accept_escrow": True,
        "allow_gps": True,
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["trade"] == "tho_ho"
    assert data["daily_rate"] == 450000


@pytest.mark.asyncio
async def test_create_duplicate_profile(client: AsyncClient, db_session):
    user, token = await _create_worker_user(db_session)
    await client.post("/api/v1/workers/profile", json={
        "trade": "tho_ho", "daily_rate": 400000,
    }, headers={"Authorization": f"Bearer {token}"})

    resp = await client.post("/api/v1/workers/profile", json={
        "trade": "tho_dien", "daily_rate": 500000,
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_update_worker_profile(client: AsyncClient, db_session):
    user, token = await _create_worker_user(db_session)
    await client.post("/api/v1/workers/profile", json={
        "trade": "tho_ho", "daily_rate": 400000,
    }, headers={"Authorization": f"Bearer {token}"})

    resp = await client.put("/api/v1/workers/profile", json={
        "daily_rate": 500000,
        "bio": "Updated bio",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["daily_rate"] == 500000


@pytest.mark.asyncio
async def test_get_worker_detail(client: AsyncClient, db_session):
    from api.models.worker import WorkerProfile
    user, token = await _create_worker_user(db_session)

    profile = WorkerProfile(
        user_id=user.id, trade="tho_dien", daily_rate=550000,
        status="verified", experience_years=8,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    resp = await client.get(f"/api/v1/workers/{profile.id}")
    assert resp.status_code == 200
    assert resp.json()["trade"] == "tho_dien"


@pytest.mark.asyncio
async def test_worker_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/workers/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_verify_worker(client: AsyncClient, admin_user, db_session):
    from api.models.worker import WorkerProfile
    from api.models.user import User
    from api.core.security import hash_password

    worker_user = User(email="verify_worker@test.com", password_hash=hash_password("Test1234"),
                       full_name="Verify Worker", role="worker", status="active")
    db_session.add(worker_user)
    await db_session.flush()

    profile = WorkerProfile(user_id=worker_user.id, trade="tho_son", status="pending")
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    _, admin_token = admin_user
    resp = await client.patch(f"/api/v1/workers/{profile.id}/status",
                              json={"status": "verified"},
                              headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_portfolio_empty(client: AsyncClient, db_session):
    from api.models.worker import WorkerProfile
    user, _ = await _create_worker_user(db_session)
    profile = WorkerProfile(user_id=user.id, trade="tho_moc", status="verified")
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    resp = await client.get(f"/api/v1/workers/{profile.id}/portfolio")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_worker_reviews_empty(client: AsyncClient, db_session):
    from api.models.worker import WorkerProfile
    user, _ = await _create_worker_user(db_session)
    profile = WorkerProfile(user_id=user.id, trade="tho_nuoc", status="verified")
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    resp = await client.get(f"/api/v1/workers/{profile.id}/reviews")
    assert resp.status_code == 200
    assert resp.json() == []
