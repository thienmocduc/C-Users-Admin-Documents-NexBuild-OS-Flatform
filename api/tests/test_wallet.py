"""Wallet + Transaction tests."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_wallet(client: AsyncClient, test_user):
    _, token = test_user
    resp = await client.get("/api/v1/wallet", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["available_balance"] == 100_000_000  # from fixture
    assert data["escrow_held"] == 0
    assert data["nxt_balance"] == 0


@pytest.mark.asyncio
async def test_topup(client: AsyncClient, test_user):
    _, token = test_user
    resp = await client.post("/api/v1/wallet/topup", json={
        "amount": 5000000,
        "payment_method": "vnpay",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["balance"] == 105_000_000


@pytest.mark.asyncio
async def test_topup_zero_amount(client: AsyncClient, test_user):
    _, token = test_user
    resp = await client.post("/api/v1/wallet/topup", json={
        "amount": 0,
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_withdraw(client: AsyncClient, test_user):
    _, token = test_user
    resp = await client.post("/api/v1/wallet/withdraw", json={
        "amount": 10_000_000,
        "bank_account_id": "test",
        "note": "Rut tien test",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["balance"] == 90_000_000


@pytest.mark.asyncio
async def test_withdraw_insufficient(client: AsyncClient, test_user):
    _, token = test_user
    resp = await client.post("/api/v1/wallet/withdraw", json={
        "amount": 999_999_999_999,
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_transaction_history(client: AsyncClient, test_user):
    _, token = test_user
    # Do a topup first
    await client.post("/api/v1/wallet/topup", json={"amount": 1000000},
                      headers={"Authorization": f"Bearer {token}"})

    resp = await client.get("/api/v1/wallet/transactions",
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
    assert resp.json()[0]["type"] == "topup"


@pytest.mark.asyncio
async def test_bank_accounts(client: AsyncClient, test_user):
    _, token = test_user

    # Add bank account
    resp = await client.post("/api/v1/wallet/bank-accounts", json={
        "bank_name": "Vietcombank",
        "account_number": "0123456789",
        "account_holder": "NGUYEN VAN A",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201

    # List
    list_resp = await client.get("/api/v1/wallet/bank-accounts",
                                 headers={"Authorization": f"Bearer {token}"})
    assert len(list_resp.json()) == 1
    assert list_resp.json()[0]["bank_name"] == "Vietcombank"
