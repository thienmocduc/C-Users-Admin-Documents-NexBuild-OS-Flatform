"""JWT RS256 auth + password hashing + rate limiting."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import bcrypt as _bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import get_settings
from api.core.database import get_db
from api.core.redis import get_redis

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)


# ─── Password ────────────────────────────────────────────
def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = _bcrypt.gensalt(rounds=12)
    return _bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


# ─── JWT Keys ────────────────────────────────────────────
def _load_key(path: str) -> Optional[str]:
    p = Path(path)
    if p.exists():
        return p.read_text()
    return None


_private_key = _load_key(settings.JWT_PRIVATE_KEY_PATH)
_public_key = _load_key(settings.JWT_PUBLIC_KEY_PATH)

# Fallback to HS256 if RSA keys not available (dev/test)
_algorithm = "RS256" if _private_key else "HS256"
_sign_key = _private_key or settings.JWT_SECRET_KEY
_verify_key = _public_key or settings.JWT_SECRET_KEY


# ─── Token Creation ──────────────────────────────────────
def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, _sign_key, algorithm=_algorithm)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, _sign_key, algorithm=_algorithm)


def decode_token(token: str) -> dict:
    """Decode and verify JWT. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, _verify_key, algorithms=[_algorithm])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ─── Current User Dependency ─────────────────────────────
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Extract and validate current user from Bearer token."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập")

    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Token không hợp lệ")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")

    # Import here to avoid circular
    from api.models.user import User
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User không tồn tại")
    if user.status == "suspended":
        raise HTTPException(status_code=403, detail="Tài khoản đã bị khóa")

    return user


def require_role(*roles: str):
    """Dependency factory — restrict endpoint to specific roles."""
    async def checker(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Không có quyền truy cập")
        return current_user
    return checker


# ─── Rate Limiting ────────────────────────────────────────
def _client_ip(request: Request) -> str:
    """Extract real client IP behind proxy chain (Railway GCP LB / Vercel / Cloudflare).

    Priority: X-Forwarded-For (first hop) > X-Real-IP > request.client.host.
    Railway's GCP LB rotates 100.64.0.x internal IPs, so we MUST trust X-Forwarded-For.
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


async def check_login_rate_limit(request: Request, redis_conn=Depends(get_redis)):
    """Block IP after 5 failed login attempts in 15 minutes."""
    ip = _client_ip(request)
    key = f"login_attempts:{ip}"

    attempts = await redis_conn.get(key)
    if attempts and int(attempts) >= settings.LOGIN_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Quá nhiều lần đăng nhập thất bại. Thử lại sau {settings.LOGIN_LOCKOUT_MINUTES} phút.",
        )


async def record_login_attempt(ip: str, success: bool, redis_conn):
    """Track login attempts in Redis."""
    if success:
        await redis_conn.delete(f"login_attempts:{ip}")
        return

    key = f"login_attempts:{ip}"
    pipe = redis_conn.pipeline()
    pipe.incr(key)
    pipe.expire(key, settings.LOGIN_LOCKOUT_MINUTES * 60)
    await pipe.execute()


async def check_api_rate_limit(request: Request, redis_conn=Depends(get_redis)):
    """100 req/min per IP."""
    ip = _client_ip(request)
    key = f"api_rate:{ip}"

    current = await redis_conn.incr(key)
    if current == 1:
        await redis_conn.expire(key, 60)

    if current > settings.API_RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Thử lại sau 1 phút.")
