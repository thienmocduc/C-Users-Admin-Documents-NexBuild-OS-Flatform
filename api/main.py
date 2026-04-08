"""NexBuild API — FastAPI entry point.

Run: uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
Docs: http://localhost:8000/docs (Swagger) | http://localhost:8000/redoc (ReDoc)
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.core.config import get_settings
from api.core.database import engine, Base

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables (dev only). Shutdown: dispose engine."""
    # DEV: auto-create tables. Production uses Alembic migrations.
    async with engine.begin() as conn:
        # Import all models so they register with Base
        import api.models.user  # noqa
        import api.models.module  # noqa
        import api.models.product  # noqa
        import api.models.worker  # noqa
        import api.models.marketplace  # noqa
        import api.models.order  # noqa
        import api.models.finance  # noqa
        import api.models.community  # noqa
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "NexBuild Holdings Platform API — Hệ sinh thái xây dựng thông minh.\n\n"
        "**Modules:** Hub (12 ecosystem) · Marketplace (B2B/B2C/D2C) · Dashboard (5 roles)\n\n"
        "**Auth:** JWT RS256 · HttpOnly refresh cookie · Rate limiting\n\n"
        "**Security:** OWASP Top 10 · IDOR prevention · Input sanitization"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


# ─── Security Headers Middleware ──────────────────────────
@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    if not settings.DEBUG:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'"
    return response


# ─── Register Routers ────────────────────────────────────
from api.routers.auth import router as auth_router
from api.routers.modules import router as modules_router
from api.routers.products import router as products_router, cat_router as categories_router
from api.routers.workers import router as workers_router
from api.routers.bookings import router as bookings_router
from api.routers.projects import router as projects_router
from api.routers.orders import cart_router, order_router
from api.routers.wallet import router as wallet_router
from api.routers.stats import stats_router, admin_router
from api.routers.forum import forum_router, review_router, notif_router

API = settings.API_PREFIX

app.include_router(auth_router, prefix=API)
app.include_router(modules_router, prefix=API)
app.include_router(products_router, prefix=API)
app.include_router(categories_router, prefix=API)
app.include_router(workers_router, prefix=API)
app.include_router(bookings_router, prefix=API)
app.include_router(projects_router, prefix=API)
app.include_router(cart_router, prefix=API)
app.include_router(order_router, prefix=API)
app.include_router(wallet_router, prefix=API)
app.include_router(stats_router, prefix=API)
app.include_router(admin_router, prefix=API)
app.include_router(forum_router, prefix=API)
app.include_router(review_router, prefix=API)
app.include_router(notif_router, prefix=API)


# ─── Health Check ─────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }
