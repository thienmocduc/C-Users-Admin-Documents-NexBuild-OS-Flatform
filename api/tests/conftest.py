"""Test configuration — in-memory SQLite for fast tests."""
import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.core.database import Base, get_db
from api.core.security import create_access_token, hash_password
from api.main import app

# In-memory SQLite for testing (no PostgreSQL needed)
TEST_DB_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
test_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with test_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Mock Redis
class MockRedis:
    _store: dict = {}

    async def get(self, key):
        return self._store.get(key)

    async def set(self, key, value, ex=None):
        self._store[key] = value

    async def incr(self, key):
        self._store[key] = self._store.get(key, 0) + 1
        return self._store[key]

    async def expire(self, key, seconds):
        pass

    async def delete(self, key):
        self._store.pop(key, None)

    def pipeline(self):
        return MockPipeline(self)


class MockPipeline:
    def __init__(self, redis):
        self.redis = redis
        self.ops = []

    def incr(self, key):
        self.ops.append(("incr", key))
        return self

    def expire(self, key, seconds):
        self.ops.append(("expire", key, seconds))
        return self

    async def execute(self):
        for op in self.ops:
            if op[0] == "incr":
                await self.redis.incr(op[1])


mock_redis = MockRedis()


async def override_get_redis():
    return mock_redis


# Override dependencies
app.dependency_overrides[get_db] = override_get_db

from api.core.redis import get_redis
app.dependency_overrides[get_redis] = override_get_redis


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_session() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user and return (user, access_token)."""
    from api.models.user import User, UserPreference
    from api.models.finance import Wallet

    user = User(
        email="test@nexbuild.vn",
        phone="0901234567",
        password_hash=hash_password("Test1234"),
        full_name="Test User",
        role="buyer",
        status="active",
    )
    db_session.add(user)
    await db_session.flush()

    pref = UserPreference(user_id=user.id)
    db_session.add(pref)

    wallet = Wallet(user_id=user.id, available_balance=100_000_000)
    db_session.add(wallet)

    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(str(user.id), user.role)
    return user, token


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    """Create an admin user."""
    from api.models.user import User

    user = User(
        email="admin@nexbuild.vn",
        password_hash=hash_password("Admin1234"),
        full_name="Admin",
        role="admin",
        status="active",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(str(user.id), user.role)
    return user, token


@pytest_asyncio.fixture
async def supplier_user(db_session: AsyncSession):
    """Create a supplier user."""
    from api.models.user import User

    user = User(
        email="supplier@nexbuild.vn",
        password_hash=hash_password("Supp1234"),
        full_name="Supplier Test",
        role="supplier",
        status="active",
        store_name="Test Store",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(str(user.id), user.role)
    return user, token
