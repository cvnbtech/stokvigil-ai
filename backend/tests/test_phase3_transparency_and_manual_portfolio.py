"""
StokVigil AI — Test Suite for Phase 3: Feed Transparency & Broker-Agnostic Portfolio Protection
Validates:
1. 'data_source_mode' metadata tagging ('REALTIME_BROKER_FEED' vs 'DELAYED_EOD_SCRAPE').
2. Activation of Demat Downside Shield (-3.5% Capital Preservation Exit) for manual Zerodha/Groww entries.
3. API response payload parity for latency mode indicators.
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from app.market_cache import market_cache
from app.agent_runner import evaluate_user_portfolio_and_watchlists
from app.routers.stocks import _fetch_single_stock_quote


@pytest.fixture(autouse=True)
def reset_cache():
    market_cache.clear()
    yield
    market_cache.clear()


def test_data_source_mode_tagging():
    """Validates that market cache correctly tags delayed vs real-time quotes."""
    # 1. Historical scrape / default cache entry
    market_cache.set_stock("RELIANCE", {
        "symbol": "RELIANCE",
        "current_price": 2900.0,
        "confluence_score": 70
    })
    cached = market_cache.get_stock("RELIANCE")
    assert cached["data_source_mode"] == "DELAYED_EOD_SCRAPE"
    assert cached["is_realtime"] is False

    # 2. Live tick feed update (e.g. from Breeze WebSocket or Broker Tick API)
    market_cache.update_live_tick("RELIANCE", ltp=2910.0, volume=50000)
    updated = market_cache.get_stock("RELIANCE")
    assert updated["data_source_mode"] == "REALTIME_BROKER_FEED"
    assert updated["is_realtime"] is True
    assert updated["current_price"] == 2910.0


def test_quote_endpoint_includes_latency_metadata():
    """Validates that single stock quotes return data_source_mode and is_realtime."""
    # Seed live tick
    market_cache.set_stock("TCS", {
        "symbol": "TCS",
        "current_price": 4100.0,
        "data_source_mode": "REALTIME_BROKER_FEED",
        "is_realtime": True,
        "technicals": {
            "change_pct": 1.25,
            "day_high": 4120.0,
            "day_low": 4080.0
        }
    })

    quote = _fetch_single_stock_quote("TCS")
    assert quote is not None
    assert "data_source_mode" in quote
    assert "is_realtime" in quote
    assert quote["data_source_mode"] == "REALTIME_BROKER_FEED"
    assert quote["is_realtime"] is True


@pytest.mark.asyncio
async def test_non_icici_manual_demat_downside_shield():
    """
    Validates that a non-ICICI user (Zerodha, Groww, Angel One) with manually entered
    average_buy_price gets active downside risk protection (-3.5% rule).
    """
    user_id = "11111111-2222-3333-4444-555555555555"

    user_profile = {
        "id": user_id,
        "alert_sensitivity": "HIGH",
        "fcm_enabled": False,
        "telegram_enabled": False
    }

    # Manual watchlist entry with cost basis (Zerodha trade: bought at ₹1,000, current price drops to ₹960 -> -4% loss)
    manual_watchlist_rows = [
        {
            "symbol": "INFY",
            "average_buy_price": 1000.0,
            "quantity": 50,
            "is_auto_synced": False  # Manually added, NOT auto-synced from ICICI
        }
    ]

    # Pre-cache INFY at ₹960 (-4% plunge)
    market_cache.set_stock("INFY", {
        "symbol": "INFY",
        "current_price": 960.0,
        "confluence_score": 60,
        "action_bias": "HOLD_NEUTRAL",
        "technicals": {
            "current_price": 960.0,
            "rsi_15m": 35.0
        }
    })

    user_ctx = {
        "profile": user_profile,
        "symbols": ["INFY"],
        "cached_demat_rows": manual_watchlist_rows,
        "cred": None
    }

    macro_data = {"nifty_change_pct": 0.05, "india_vix": 13.5}

    with patch("app.alert_limiter.should_dispatch_alert", return_value=(True, "OK")):
        supabase_mock = MagicMock()
        exec_res = MagicMock(data=[])
        supabase_mock.table.return_value.insert.return_value.execute.return_value = exec_res

        alerts = await evaluate_user_portfolio_and_watchlists(
            user_id=user_id,
            supabase_client=supabase_mock,
            macro_data=macro_data,
            preloaded_user_ctx=user_ctx
        )

        assert alerts is not None
        assert len(alerts) > 0
        alert = alerts[0]
        
        # Assert -3.5% Demat Downside Shield triggered CAPITAL_PRESERVATION_EXIT
        assert alert["symbol"] == "INFY"
        assert alert["metrics_snapshot"]["action_bias"] == "CAPITAL_PRESERVATION_EXIT"
        assert "Capital Preservation Exit Trigger" in alert["alert_title"]
        assert "-4.0%" in alert["alert_title"]
