"""
StokVigil AI — Test Suite for Zero-Cost Hybrid Market Cache (Phase 1)
Tests dual-tier storage: Tier-1 (Local RAM) and Tier-2 (Supabase UNLOGGED Table fallback).
"""

import time
import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from app.market_cache import MarketCacheManager, market_cache


@pytest.fixture(autouse=True)
def reset_cache():
    market_cache.clear()
    yield
    market_cache.clear()


def test_market_cache_tier1_ram_hit_and_miss():
    """Validates sub-millisecond Tier-1 RAM cache reads and writes."""
    test_data = {
        "symbol": "RELIANCE",
        "current_price": 2950.50,
        "confluence_score": 82,
        "action_bias": "STRONG_BUY"
    }
    
    # Cache miss
    assert market_cache.get_stock("RELIANCE") is None
    assert market_cache.is_fresh("RELIANCE") is False

    # Cache write
    market_cache.set_stock("RELIANCE", test_data, ttl_seconds=60)
    
    # Cache hit
    cached = market_cache.get_stock("RELIANCE")
    assert cached is not None
    assert cached["current_price"] == 2950.50
    assert cached["confluence_score"] == 82
    assert market_cache.is_fresh("RELIANCE") is True

    # Suffix normalization check (RELIANCE.NS matches RELIANCE)
    cached_ns = market_cache.get_stock("RELIANCE.NS")
    assert cached_ns is not None
    assert cached_ns["current_price"] == 2950.50


def test_market_cache_expiration():
    """Validates TTL expiry behavior in RAM cache."""
    test_data = {"symbol": "INFY", "current_price": 1850.00}
    market_cache.set_stock("INFY", test_data, ttl_seconds=1)
    
    # Fresh immediately
    assert market_cache.get_stock("INFY") is not None
    
    # Fast-forward time to simulate expiry
    time.sleep(1.1)
    assert market_cache.get_stock("INFY") is None


def test_market_cache_live_tick_update():
    """Validates atomic live tick updating (LTP, VWAP deviation, high, low)."""
    # Seed data with VWAP
    market_cache.set_stock("TCS", {
        "symbol": "TCS",
        "current_price": 4000.0,
        "vwap": 4000.0,
        "day_high": 4020.0,
        "day_low": 3980.0
    }, ttl_seconds=300)

    # Ingest tick: LTP rises to 4040.0
    market_cache.update_live_tick("TCS", ltp=4040.0, volume=150000, high=4050.0)
    
    updated = market_cache.get_stock("TCS")
    assert updated is not None
    assert updated["current_price"] == 4040.0
    assert updated["price_vs_vwap_pct"] == 1.0  # (4040 - 4000) / 4000 * 100
    assert updated["day_high"] == 4050.0
    assert updated["live_volume"] == 150000


@pytest.mark.asyncio
async def test_market_cache_tier2_db_fallback():
    """Validates asynchronous cold-start fallback to Supabase UNLOGGED table."""
    db_mock_row = {
        "key": "HDFCBANK",
        "value": {
            "symbol": "HDFCBANK",
            "current_price": 1680.0,
            "confluence_score": 75
        },
        "updated_at": "2026-11-07T10:00:00+00:00"
    }

    with patch("app.db_pool.fetch_one", new_callable=AsyncMock) as mock_fetch_one:
        mock_fetch_one.return_value = db_mock_row
        
        # RAM is empty
        assert market_cache.get_stock("HDFCBANK") is None
        
        # Async get fetches from Tier-2 DB table and hydrates Tier-1 RAM
        res = await market_cache.async_get_stock("HDFCBANK", max_age_seconds=999999)
        assert res is not None
        assert res["current_price"] == 1680.0
        
        # Now Tier-1 RAM should be hydrated
        cached_in_ram = market_cache.get_stock("HDFCBANK")
        assert cached_in_ram is not None
        assert cached_in_ram["current_price"] == 1680.0


@pytest.mark.asyncio
async def test_market_cache_bulk_hydration_and_flush():
    """Validates bulk cold-start preloading and batch RAM flush."""
    # 1. Bulk Hydration from DB
    mock_rows = [
        {"key": "SBIN", "value": {"symbol": "SBIN", "current_price": 820.0}, "updated_at": "2026-11-07T10:00:00+00:00"},
        {"key": "ITC", "value": {"symbol": "ITC", "current_price": 490.0}, "updated_at": "2026-11-07T10:00:00+00:00"}
    ]

    with patch("app.db_pool.fetch_all", new_callable=AsyncMock) as mock_fetch_all:
        mock_fetch_all.return_value = mock_rows
        count = await market_cache.async_hydrate_all_from_db(max_age_seconds=999999)
        assert count == 2
        assert market_cache.get_stock("SBIN")["current_price"] == 820.0
        assert market_cache.get_stock("ITC")["current_price"] == 490.0

    # 2. Batch Flush to DB
    with patch("app.db_pool.executemany", new_callable=AsyncMock) as mock_executemany:
        mock_executemany.return_value = True
        flushed_count = await market_cache.async_flush_ram_to_db()
        assert flushed_count == 2
        assert mock_executemany.called
