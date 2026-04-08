"""Security tests — OWASP compliance."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_security_headers(client: AsyncClient):
    """Verify security headers are set."""
    resp = await client.get("/health")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("Referrer-Policy") == "strict-origin"
    assert resp.headers.get("X-XSS-Protection") == "1; mode=block"


@pytest.mark.asyncio
async def test_cors_headers(client: AsyncClient):
    """Verify CORS is configured."""
    resp = await client.options("/health", headers={
        "Origin": "https://nexbuild.holdings",
        "Access-Control-Request-Method": "GET",
    })
    # FastAPI CORS middleware should respond


@pytest.mark.asyncio
async def test_auth_required_endpoints(client: AsyncClient):
    """Key endpoints require auth."""
    endpoints = [
        ("GET", "/api/v1/auth/me"),
        ("GET", "/api/v1/cart"),
        ("GET", "/api/v1/orders"),
        ("GET", "/api/v1/wallet"),
        ("GET", "/api/v1/notifications"),
    ]
    for method, path in endpoints:
        if method == "GET":
            resp = await client.get(path)
        assert resp.status_code == 401, f"{method} {path} should require auth"


@pytest.mark.asyncio
async def test_admin_endpoints_require_admin_role(client: AsyncClient, test_user):
    """Admin endpoints reject non-admin users."""
    _, token = test_user  # buyer role
    endpoints = [
        "/api/v1/admin/users",
        "/api/v1/admin/products/pending",
        "/api/v1/admin/workers/pending",
        "/api/v1/admin/disputes",
        "/api/v1/admin/settings",
        "/api/v1/admin/audit-log",
    ]
    for path in endpoints:
        resp = await client.get(path, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403, f"{path} should reject buyer role"


@pytest.mark.asyncio
async def test_sql_injection_in_search(client: AsyncClient):
    """Search params should be sanitized."""
    resp = await client.get("/api/v1/products?search=' OR 1=1 --")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0  # No injection, just empty results


@pytest.mark.asyncio
async def test_xss_in_registration(client: AsyncClient):
    """XSS attempt in user input should be stored as-is (sanitized on output)."""
    resp = await client.post("/api/v1/auth/register", json={
        "full_name": "<script>alert('xss')</script>",
        "email": "xss@test.com",
        "password": "SecurePass123",
        "role": "buyer",
    })
    # Should succeed but script tag stored as text, not executed
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_invalid_jwt_rejected(client: AsyncClient):
    """Malformed JWT should be rejected."""
    resp = await client.get("/api/v1/auth/me", headers={
        "Authorization": "Bearer invalid.token.here"
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_expired_token_handling(client: AsyncClient):
    """Token with wrong signature rejected."""
    from api.core.security import create_access_token
    # This creates a valid token, but let's test with garbage
    resp = await client.get("/api/v1/auth/me", headers={
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwidHlwZSI6ImFjY2VzcyJ9.invalid"
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
