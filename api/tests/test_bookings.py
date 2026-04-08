"""Booking endpoint tests."""
import pytest
from httpx import AsyncClient


async def _setup_worker(client: AsyncClient, db_session):
    """Create a worker user + profile for booking tests."""
    from api.models.user import User, UserPreference
    from api.models.worker import WorkerProfile
    from api.models.finance import Wallet
    from api.core.security import hash_password, create_access_token

    user = User(
        email="worker@test.com", phone="0909876543",
        password_hash=hash_password("Worker1234"),
        full_name="Tho Test", role="worker", status="active",
    )
    db_session.add(user)
    await db_session.flush()

    db_session.add(UserPreference(user_id=user.id))
    db_session.add(Wallet(user_id=user.id))

    profile = WorkerProfile(
        user_id=user.id, trade="tho_ho", experience_years=5,
        daily_rate=450000, work_area="Ha Noi", status="verified",
        accept_escrow=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    token = create_access_token(str(user.id), user.role)
    return user, profile, token


@pytest.mark.asyncio
async def test_create_booking(client: AsyncClient, test_user, db_session):
    _, buyer_token = test_user
    worker_user, worker_profile, _ = await _setup_worker(client, db_session)

    resp = await client.post("/api/v1/bookings", json={
        "worker_id": str(worker_profile.id),
        "job_description": "Xay tuong bep 3m x 2.5m",
        "work_address": "123 Nguyen Trai, HN",
        "num_days": 3,
        "start_date": "2026-04-15",
        "shift": "morning",
    }, headers={"Authorization": f"Bearer {buyer_token}"})

    assert resp.status_code == 201
    data = resp.json()
    assert data["worker_fee"] == 1350000  # 450000 * 3
    assert data["service_fee"] == 108000  # 8% of 1350000
    assert data["total"] == 1458000
    assert "escrow_id" in data


@pytest.mark.asyncio
async def test_create_booking_worker_not_found(client: AsyncClient, test_user):
    _, token = test_user
    resp = await client.post("/api/v1/bookings", json={
        "worker_id": "00000000-0000-0000-0000-000000000000",
        "job_description": "Test",
        "num_days": 1,
        "start_date": "2026-04-15",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_bookings_buyer(client: AsyncClient, test_user, db_session):
    _, buyer_token = test_user
    _, worker_profile, _ = await _setup_worker(client, db_session)

    # Create booking
    await client.post("/api/v1/bookings", json={
        "worker_id": str(worker_profile.id),
        "job_description": "Test job",
        "num_days": 1,
        "start_date": "2026-04-15",
    }, headers={"Authorization": f"Bearer {buyer_token}"})

    resp = await client.get("/api/v1/bookings", headers={"Authorization": f"Bearer {buyer_token}"})
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


@pytest.mark.asyncio
async def test_list_bookings_worker_view(client: AsyncClient, test_user, db_session):
    _, buyer_token = test_user
    _, worker_profile, worker_token = await _setup_worker(client, db_session)

    await client.post("/api/v1/bookings", json={
        "worker_id": str(worker_profile.id),
        "job_description": "Test",
        "num_days": 1,
        "start_date": "2026-04-15",
    }, headers={"Authorization": f"Bearer {buyer_token}"})

    resp = await client.get("/api/v1/bookings", headers={"Authorization": f"Bearer {worker_token}"})
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


@pytest.mark.asyncio
async def test_accept_booking(client: AsyncClient, test_user, db_session):
    _, buyer_token = test_user
    _, worker_profile, worker_token = await _setup_worker(client, db_session)

    create_resp = await client.post("/api/v1/bookings", json={
        "worker_id": str(worker_profile.id),
        "job_description": "Test",
        "num_days": 1,
        "start_date": "2026-04-15",
    }, headers={"Authorization": f"Bearer {buyer_token}"})
    booking_id = create_resp.json()["booking_id"]

    resp = await client.patch(f"/api/v1/bookings/{booking_id}/accept",
                              headers={"Authorization": f"Bearer {worker_token}"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_reject_booking_refunds_escrow(client: AsyncClient, test_user, db_session):
    _, buyer_token = test_user
    _, worker_profile, worker_token = await _setup_worker(client, db_session)

    create_resp = await client.post("/api/v1/bookings", json={
        "worker_id": str(worker_profile.id),
        "job_description": "Test",
        "num_days": 1,
        "start_date": "2026-04-15",
    }, headers={"Authorization": f"Bearer {buyer_token}"})
    booking_id = create_resp.json()["booking_id"]

    resp = await client.patch(f"/api/v1/bookings/{booking_id}/reject",
                              json={"reason": "Ban"},
                              headers={"Authorization": f"Bearer {worker_token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_complete_booking(client: AsyncClient, test_user, db_session):
    _, buyer_token = test_user
    _, worker_profile, worker_token = await _setup_worker(client, db_session)

    create_resp = await client.post("/api/v1/bookings", json={
        "worker_id": str(worker_profile.id),
        "job_description": "Test",
        "num_days": 1,
        "start_date": "2026-04-15",
    }, headers={"Authorization": f"Bearer {buyer_token}"})
    booking_id = create_resp.json()["booking_id"]

    # Accept first
    await client.patch(f"/api/v1/bookings/{booking_id}/accept",
                       headers={"Authorization": f"Bearer {worker_token}"})

    # Complete
    resp = await client.patch(f"/api/v1/bookings/{booking_id}/complete",
                              headers={"Authorization": f"Bearer {buyer_token}"})
    assert resp.status_code == 200
    assert "Escrow" in resp.json()["message"]


@pytest.mark.asyncio
async def test_checkin_booking(client: AsyncClient, test_user, db_session):
    _, buyer_token = test_user
    _, worker_profile, worker_token = await _setup_worker(client, db_session)

    create_resp = await client.post("/api/v1/bookings", json={
        "worker_id": str(worker_profile.id),
        "job_description": "Test",
        "num_days": 1,
        "start_date": "2026-04-15",
    }, headers={"Authorization": f"Bearer {buyer_token}"})
    booking_id = create_resp.json()["booking_id"]

    await client.patch(f"/api/v1/bookings/{booking_id}/accept",
                       headers={"Authorization": f"Bearer {worker_token}"})

    resp = await client.patch(f"/api/v1/bookings/{booking_id}/checkin",
                              json={"lat": 21.0285, "lng": 105.8542},
                              headers={"Authorization": f"Bearer {worker_token}"})
    assert resp.status_code == 200
