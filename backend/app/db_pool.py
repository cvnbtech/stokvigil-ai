"""
StokVigil AI — Database Connection Pool Manager (Supabase PgBouncer / Port 6543)
Handles high-throughput, non-blocking asynchronous PostgreSQL connections via Supavisor / PgBouncer.
Multiplexes thousands of client queries over a resilient pool of physical connections.
"""

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional, AsyncGenerator, Any
from urllib.parse import urlparse

import asyncpg
from app.config import settings

logger = logging.getLogger("stokvigil.db_pool")

# Thread-safe global pool singleton
_db_pool: Optional[asyncpg.Pool] = None
_pool_lock = asyncio.Lock()


def _mask_db_url(url: str) -> str:
    """Masks database password in connection string for safe log output."""
    if not url:
        return "Not Configured"
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc
        if "@" in netloc:
            creds, host_port = netloc.split("@", 1)
            if ":" in creds:
                user = creds.split(":", 1)[0]
                masked_netloc = f"{user}:***@{host_port}"
            else:
                masked_netloc = f"***@{host_port}"
        else:
            masked_netloc = netloc
        return f"{parsed.scheme}://{masked_netloc}{parsed.path}"
    except Exception:
        return "postgresql://***@pooler.supabase.com:6543/postgres"


async def init_db_pool() -> Optional[asyncpg.Pool]:
    """
    Initializes the asyncpg connection pool pointing to Supabase PgBouncer (Port 6543).
    Enforces statement_cache_size=0 as required by PgBouncer transaction pooling mode.
    """
    global _db_pool
    async with _pool_lock:
        if _db_pool is not None:
            return _db_pool

        raw_url = str(settings.DATABASE_URL or "").strip().strip('"').strip("'")
        if not raw_url:
            logger.info("DATABASE_URL not configured. Operating in standard REST mode.")
            return None

        # Normalize postgres:// -> postgresql:// for asyncpg parser
        if raw_url.startswith("postgres://"):
            raw_url = "postgresql://" + raw_url[len("postgres://"):]

        masked = _mask_db_url(raw_url)
        logger.info(f"Initializing Supabase PgBouncer Connection Pool on Port 6543: {masked}")

        try:
            # CRITICAL: statement_cache_size=0 is strictly required for PgBouncer Port 6543
            # Transaction mode does not support prepared statements across pooled connections
            _db_pool = await asyncpg.create_pool(
                raw_url,
                min_size=2,
                max_size=10,
                command_timeout=15.0,
                statement_cache_size=0,
                max_inactive_connection_lifetime=300.0
            )
            logger.info("✅ Supabase PgBouncer Connection Pool (Port 6543) initialized successfully.")
            return _db_pool
        except Exception as e:
            logger.warning(
                f"Note: Could not establish asyncpg connection pool to {masked}: {e}. "
                "Backend will continue safely using Supabase REST API."
            )
            _db_pool = None
            return None


async def close_db_pool():
    """Gracefully closes all connections in the pool on server shutdown."""
    global _db_pool
    async with _pool_lock:
        if _db_pool is not None:
            try:
                await _db_pool.close()
                logger.info("Supabase PgBouncer Connection Pool closed cleanly.")
            except Exception as e:
                logger.warning(f"Error closing PgBouncer pool: {e}")
            finally:
                _db_pool = None


async def get_db_pool() -> Optional[asyncpg.Pool]:
    """Returns the active asyncpg connection pool, or None if unconfigured."""
    if _db_pool is None:
        return await init_db_pool()
    return _db_pool


def is_pool_ready() -> bool:
    """Returns True if the connection pool is initialized and open."""
    return _db_pool is not None and not _db_pool._closed


@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[Optional[asyncpg.Connection], None]:
    """
    Async context manager to safely acquire a connection from the pool and return it.
    Example:
        async with get_db_connection() as conn:
            if conn:
                row = await conn.fetchrow("SELECT * FROM profiles WHERE id = $1", uid)
    """
    pool = await get_db_pool()
    if pool is None:
        yield None
        return

    conn = await pool.acquire()
    try:
        yield conn
    finally:
        await pool.release(conn)


def _normalize_param(arg: Any) -> Any:
    """
    Normalizes query arguments for asyncpg.
    Converts valid UUID strings to uuid.UUID objects so PostgreSQL can match
    UUID column types natively without type mismatch errors.
    """
    if isinstance(arg, str):
        try:
            return uuid.UUID(arg)
        except (ValueError, AttributeError):
            return arg
    return arg


def _normalize_value(v: Any) -> Any:
    """
    Normalizes PostgreSQL values returned by asyncpg to match the Supabase REST API schema:
    - uuid.UUID -> str (e.g. 'c44c502b-a010-449e-b9ff-fdbca2bbd3a7')
    - datetime / date / time -> ISO-8601 str
    - Decimal -> float
    - JSON string -> parsed dict or list
    """
    if isinstance(v, uuid.UUID):
        return str(v)
    elif isinstance(v, (datetime, date, time)):
        return v.isoformat()
    elif isinstance(v, Decimal):
        return float(v)
    elif isinstance(v, str) and len(v) >= 2 and ((v.startswith("{") and v.endswith("}")) or (v.startswith("[") and v.endswith("]"))):
        try:
            return json.loads(v)
        except Exception:
            return v
    return v


def _normalize_row(record: Any) -> dict:
    """Converts an asyncpg Record into a standard dictionary with REST-compatible types."""
    d = dict(record)
    for k, v in d.items():
        d[k] = _normalize_value(v)
    return d


async def fetch_all(query: str, *args) -> Optional[list]:
    """
    Executes a read query via the PgBouncer pool and returns rows as standard dictionaries.
    Guarantees that column types (UUIDs as str, timestamps as ISO-8601, JSONB as dict)
    strictly match the Supabase REST API format for 100% contract parity.
    Returns None if pool is unconfigured or on query error (signaling callers to use REST fallback).
    """
    pool = await get_db_pool()
    if pool is None:
        return None
    try:
        norm_args = [_normalize_param(a) for a in args]
        async with pool.acquire() as conn:
            records = await conn.fetch(query, *norm_args)
            return [_normalize_row(r) for r in records]
    except Exception as e:
        logger.warning(f"PgBouncer fetch_all query failed ({e}). Falling back to REST.")
        return None


async def fetch_one(query: str, *args) -> Optional[dict]:
    """
    Executes a single-row query via the PgBouncer pool.
    Guarantees that column types strictly match the Supabase REST API format.
    Returns:
        - dict: if a matching record was found
        - {}: if query succeeded but no record matched (0 rows)
        - None: if pool is unconfigured or on error (signaling caller to use REST fallback)
    """
    pool = await get_db_pool()
    if pool is None:
        return None
    try:
        norm_args = [_normalize_param(a) for a in args]
        async with pool.acquire() as conn:
            record = await conn.fetchrow(query, *norm_args)
            if not record:
                return {}
            return _normalize_row(record)
    except Exception as e:
        logger.warning(f"PgBouncer fetch_one query failed ({e}). Falling back to REST.")
        return None

