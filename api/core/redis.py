"""Redis connection for cache, rate limiting, session store."""
import redis.asyncio as redis
from api.core.config import get_settings

settings = get_settings()

redis_client = redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
)


async def get_redis() -> redis.Redis:
    """FastAPI dependency."""
    return redis_client
