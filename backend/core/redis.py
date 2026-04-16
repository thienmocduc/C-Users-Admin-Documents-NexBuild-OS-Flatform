"""Redis connection for cache, rate limiting, session store.

Falls back gracefully when Redis is unavailable (dev mode).
"""
import redis.asyncio as aioredis
from api.core.config import get_settings

settings = get_settings()

redis_client = None
redis_pool = None

try:
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    redis_pool = settings.REDIS_URL
except Exception:
    pass


class FakeRedis:
    """Fallback when Redis is unavailable (dev/testing)."""
    _store = {}

    async def get(self, key):
        return self._store.get(key)

    async def set(self, key, value, ex=None):
        self._store[key] = value

    async def setex(self, key, ttl, value):
        self._store[key] = value

    async def delete(self, key):
        self._store.pop(key, None)

    async def incr(self, key):
        val = int(self._store.get(key, 0)) + 1
        self._store[key] = str(val)
        return val

    async def expire(self, key, ttl):
        pass

    def pipeline(self):
        return FakePipeline(self)


class FakePipeline:
    def __init__(self, fake_redis):
        self._redis = fake_redis
        self._ops = []

    def incr(self, key):
        self._ops.append(('incr', key))
        return self

    def expire(self, key, ttl):
        self._ops.append(('expire', key, ttl))
        return self

    async def execute(self):
        for op in self._ops:
            if op[0] == 'incr':
                await self._redis.incr(op[1])


_fake_redis = FakeRedis()


async def get_redis():
    """FastAPI dependency. Returns real Redis or FakeRedis fallback."""
    if redis_client:
        try:
            await redis_client.ping()
            return redis_client
        except Exception:
            pass
    return _fake_redis
