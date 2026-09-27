import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db_pool import init_db_pool, close_db_pool, get_db_pool
from app.notifications import (
    start_telegram_worker,
    stop_telegram_worker,
    close_telegram_client,
)
from app.core.dependencies import get_supabase
from app.routers import (
    orders as orders_router,
    stocks as stocks_router,
    market as market_router,
    auth as auth_router,
    cron as cron_router,
)

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("APILogger").setLevel(logging.WARNING)
logger = logging.getLogger("stokvigil.main")

# ==========================================
# FASTAPI APPLICATION ORCHESTRATOR
# ==========================================

app = FastAPI(
    title="StokVigil AI Engine API",
    description="Multi-Tenant Market Intelligence & Factual Alert Platform",
    version="1.0.0",
)

# Defensive HTTP Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if getattr(settings, "ENVIRONMENT", "") == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# CORS Setup - Whitelisted Origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Register Modular Routers
app.include_router(auth_router.router)
app.include_router(orders_router.router)
app.include_router(stocks_router.router)
app.include_router(market_router.router)
app.include_router(cron_router.router)


@app.on_event("startup")
async def startup_event():
    """Initializes Supabase PgBouncer Connection Pool on Port 6543 and Telegram queue worker."""
    await init_db_pool()
    start_telegram_worker()


@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully closes all connections in the database pool, HTTP clients, and background workers on shutdown."""
    await stop_telegram_worker()
    await close_db_pool()
    await close_telegram_client()


# ==========================================
# HEALTH & TELEMETRY ENDPOINTS
# ==========================================

@app.get("/")
def health_check():
    """Root heartbeat check returning platform operational status."""
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "package_id": settings.PACKAGE_ID,
        "mode": "Pure Intelligence & Factual Alerts (Non-Advisory)",
        "security": "JWT_Shielded_v1",
    }


@app.get("/api/health/db")
async def get_db_health():
    """
    Health check verifying the status of the Supabase Connection Pool (PgBouncer Port 6543)
    and underlying database connectivity.
    """
    try:
        pool = await get_db_pool()
        if pool is None:
            return {
                "status": "ready",
                "pooler_active": False,
                "driver": "supabase-rest",
                "message": "Operating via Supabase REST API (DATABASE_URL unconfigured or using fallback).",
            }
        async with pool.acquire() as conn:
            val = await conn.fetchval("SELECT 1")
        return {
            "status": "healthy",
            "pooler_active": True,
            "pooler": "pgbouncer-6543",
            "test_query": val,
            "max_size": pool.get_max_size(),
            "min_size": pool.get_min_size(),
            "idle_size": pool.get_idle_size(),
        }
    except Exception as e:
        logger.warning(f"Database health check query failed: {e}")
        return {
            "status": "degraded",
            "pooler_active": False,
            "error": "Database connectivity degraded." if settings.ENVIRONMENT == "production" else str(e),
            "fallback": "supabase-rest",
        }
