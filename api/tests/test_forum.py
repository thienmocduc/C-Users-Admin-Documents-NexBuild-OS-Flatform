"""Forum + Reviews + Notifications tests."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_posts_empty(client: AsyncClient):
    resp = await client.get("/api/v1/forum/posts")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_post(client: AsyncClient, test_user):
    _, token = test_user
    resp = await client.post("/api/v1/forum/posts", json={
        "title": "Kinh nghiem chong tham san thuong",
        "content": "Chia se cach chong tham hieu qua voi Sika...",
        "tags": ["ky_thuat", "chong_tham"],
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_get_post_detail(client: AsyncClient, test_user):
    _, token = test_user
    create_resp = await client.post("/api/v1/forum/posts", json={
        "title": "Test post detail",
        "content": "Full content here",
        "tags": ["test"],
    }, headers={"Authorization": f"Bearer {token}"})
    pid = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/forum/posts/{pid}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Test post detail"
    assert resp.json()["content"] == "Full content here"


@pytest.mark.asyncio
async def test_vote_post(client: AsyncClient, test_user):
    _, token = test_user
    create_resp = await client.post("/api/v1/forum/posts", json={
        "title": "Vote test",
        "content": "Content",
    }, headers={"Authorization": f"Bearer {token}"})
    pid = create_resp.json()["id"]

    # Upvote
    resp = await client.post(f"/api/v1/forum/posts/{pid}/vote",
                             json={"value": 1},
                             headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["votes"] == 1

    # Upvote again
    resp2 = await client.post(f"/api/v1/forum/posts/{pid}/vote",
                              json={"value": 1},
                              headers={"Authorization": f"Bearer {token}"})
    assert resp2.json()["votes"] == 2


@pytest.mark.asyncio
async def test_comments(client: AsyncClient, test_user):
    _, token = test_user
    create_resp = await client.post("/api/v1/forum/posts", json={
        "title": "Comment test",
        "content": "Content",
    }, headers={"Authorization": f"Bearer {token}"})
    pid = create_resp.json()["id"]

    # Add comment
    resp = await client.post(f"/api/v1/forum/posts/{pid}/comments",
                             json={"content": "Cam on chia se!"},
                             headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201

    # List comments
    list_resp = await client.get(f"/api/v1/forum/posts/{pid}/comments")
    assert len(list_resp.json()) == 1
    assert list_resp.json()[0]["content"] == "Cam on chia se!"


@pytest.mark.asyncio
async def test_post_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/forum/posts/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


# ─── Reviews ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_review(client: AsyncClient, test_user):
    _, token = test_user
    resp = await client.post("/api/v1/reviews", json={
        "target_type": "supplier",
        "target_id": "00000000-0000-0000-0000-000000000001",
        "stars": 5,
        "criteria": {"correct_description": True, "on_time": True},
        "comment": "Giao hang nhanh, chat luong tot",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_list_reviews(client: AsyncClient, test_user):
    _, token = test_user
    target_id = "00000000-0000-0000-0000-000000000002"

    await client.post("/api/v1/reviews", json={
        "target_type": "worker",
        "target_id": target_id,
        "stars": 4,
        "comment": "Lam viec tot",
    }, headers={"Authorization": f"Bearer {token}"})

    resp = await client.get(f"/api/v1/reviews?target_type=worker&target_id={target_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ─── Notifications ────────────────────────────────────

@pytest.mark.asyncio
async def test_list_notifications(client: AsyncClient, test_user):
    _, token = test_user
    resp = await client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_unread_count(client: AsyncClient, test_user):
    _, token = test_user
    resp = await client.get("/api/v1/notifications/unread-count",
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["unread"] == 0


@pytest.mark.asyncio
async def test_mark_all_read(client: AsyncClient, test_user):
    _, token = test_user
    resp = await client.patch("/api/v1/notifications/read-all",
                              headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
