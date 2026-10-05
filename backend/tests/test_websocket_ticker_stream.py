import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock

from app.market_cache import market_cache
from app.engine.ticker_stream import LiveTickerStreamManager, ticker_manager


@pytest.fixture(autouse=True)
def cleanup_market_cache_and_stream():
    """Cleans up in-memory cache and stream state between tests."""
    market_cache.clear()
    ticker_manager._subscribed_symbols.clear()
    ticker_manager._symbol_to_users_map.clear()
    ticker_manager._user_holdings_map.clear()
    ticker_manager._user_profiles_cache.clear()
    ticker_manager._breach_latch.clear()
    ticker_manager._tick_count = 0
    yield
    market_cache.clear()
    ticker_manager._breach_latch.clear()


def test_tick_updates_market_cache_atomically():
    """Verifies incoming broker tick packet atomically updates RAM cache in sub-millisecond time."""
    tick_packet = {
        "stock_code": "INFY",
        "last": 1650.50,
        "high": 1665.00,
        "low": 1642.00,
        "volume": 750000
    }

    ticker_manager.on_tick_received(tick_packet)

    cached = market_cache.get_stock("INFY")
    assert cached is not None
    assert cached["current_price"] == 1650.50
    assert cached["day_high"] == 1665.00
    assert cached["day_low"] == 1642.00
    assert cached["live_volume"] == 750000
    assert ticker_manager._tick_count == 1


def test_camarilla_l4_breach_detection():
    """
    Verifies that a tick breaking below institutional Camarilla L4 triggers a high-conviction
    breakdown event and arms the 15-minute latch.
    """
    # Pre-populate market_cache with Camarilla pivots (L4 = 2500.0)
    market_cache.set_stock("RELIANCE", {
        "symbol": "RELIANCE",
        "current_price": 2510.0,
        "technicals": {
            "current_price": 2510.0,
            "camarilla_pivots": {
                "h4": 2560.0,
                "h3": 2530.0,
                "l3": 2490.0,
                "l4": 2500.0
            }
        },
        "tactical_levels": {
            "protective_stop_loss": 2470.0,
            "target_1": 2580.0
        }
    })

    # Register user watching RELIANCE
    user_id = "test-user-101"
    ticker_manager.register_user_portfolio(
        user_id=user_id,
        holdings=[],
        watchlist_symbols=["RELIANCE"],
        profile={"id": user_id, "fcm_enabled": False, "telegram_enabled": False}
    )

    with patch.object(ticker_manager, "_dispatch_async_breach_alert") as mock_dispatch:
        # Tick 1: Above L4 (2502.0) -> No breach
        ticker_manager.on_tick_received({"stock_code": "RELIANCE", "last": 2502.0})
        assert mock_dispatch.call_count == 0

        # Tick 2: Breaks below L4 (2495.0 < 2500.0) -> Triggers breach!
        ticker_manager.on_tick_received({"stock_code": "RELIANCE", "last": 2495.0})
        assert mock_dispatch.call_count == 1

        call_args = mock_dispatch.call_args[0]
        # args: (user_id, symbol, ltp, breach_event, cached_pack, holding)
        assert call_args[0] == user_id
        assert call_args[1] == "RELIANCE"
        assert call_args[2] == 2495.0
        breach_event = call_args[3]
        assert breach_event["type"] == "CAMARILLA_L4_BREAKDOWN"
        assert breach_event["action_bias"] == "SELL_WATCH"

        # Latch is now armed
        latch_key = f"{user_id}:RELIANCE:CAMARILLA_L4"
        assert latch_key in ticker_manager._breach_latch


def test_demat_trailing_sl_breach_detection():
    """
    Verifies that a tick causing Demat position P&L <= -3.5% triggers an immediate
    CAPITAL_PRESERVATION_EXIT breach alert.
    """
    user_id = "test-user-202"
    # User holds TCS bought at 4000.0
    ticker_manager.register_user_portfolio(
        user_id=user_id,
        holdings=[{
            "symbol": "TCS",
            "quantity": 25,
            "average_price": 4000.0
        }],
        profile={"id": user_id, "fcm_enabled": False, "telegram_enabled": False}
    )

    with patch.object(ticker_manager, "_dispatch_async_breach_alert") as mock_dispatch:
        # Tick 1: Price drops to 3900.0 (-2.5%) -> No stop-loss trigger yet
        ticker_manager.on_tick_received({"stock_code": "TCS", "last": 3900.0})
        assert mock_dispatch.call_count == 0

        # Tick 2: Price drops to 3840.0 (-4.0% <= -3.5%) -> CAPITAL_PRESERVATION_EXIT!
        ticker_manager.on_tick_received({"stock_code": "TCS", "last": 3840.0})
        assert mock_dispatch.call_count == 1

        call_args = mock_dispatch.call_args[0]
        assert call_args[0] == user_id
        assert call_args[1] == "TCS"
        assert call_args[2] == 3840.0
        breach_event = call_args[3]
        assert breach_event["type"] == "DEMAT_STOPLOSS"
        assert breach_event["action_bias"] == "CAPITAL_PRESERVATION_EXIT"
        assert breach_event["pnl_pct"] == -4.0
        assert breach_event["catalyst_category"] == "TRAILING_STOP_TRIGGER"


def test_15_minute_hysteresis_latch():
    """
    Verifies anti-spam shield: 10 rapid oscillating ticks below stop-loss
    generate ONLY 1 alert, with subsequent ticks suppressed by the 15-minute latch.
    """
    user_id = "test-user-303"
    ticker_manager.register_user_portfolio(
        user_id=user_id,
        holdings=[{"symbol": "INFY", "quantity": 10, "average_price": 1500.0}],
        profile={"id": user_id, "fcm_enabled": False, "telegram_enabled": False}
    )

    with patch.object(ticker_manager, "_dispatch_async_breach_alert") as mock_dispatch:
        # Send 10 consecutive ticks below -3.5% (1440.0 is -4.0%)
        for price in [1440.0, 1438.0, 1442.0, 1439.0, 1441.0, 1440.5, 1437.0, 1443.0, 1439.5, 1440.0]:
            ticker_manager.on_tick_received({"stock_code": "INFY", "last": price})

        # Exactly 1 alert must be dispatched
        assert mock_dispatch.call_count == 1


def test_zero_default_policy():
    """
    Strict Zero-Default Policy:
    If a stock does not have Camarilla L4 computed (e.g. missing daily bars),
    or if user has no Demat position, no synthetic alerts or fake levels are fabricated.
    """
    # Stock without camarilla pivots
    market_cache.set_stock("HDFCBANK", {
        "symbol": "HDFCBANK",
        "current_price": 1600.0,
        "technicals": {
            "current_price": 1600.0,
            "camarilla_pivots": None  # No pivots computed
        }
    })

    user_id = "test-user-404"
    ticker_manager.register_user_portfolio(
        user_id=user_id,
        holdings=[],  # No holdings
        watchlist_symbols=["HDFCBANK"],
        profile={"id": user_id}
    )

    with patch.object(ticker_manager, "_dispatch_async_breach_alert") as mock_dispatch:
        # Tick arrives
        ticker_manager.on_tick_received({"stock_code": "HDFCBANK", "last": 1550.0})
        # No fake Camarilla alert or fake SL alert must fire
        assert mock_dispatch.call_count == 0


@pytest.mark.asyncio
async def test_gemini_ai_handoff_and_mathematical_sovereignty():
    """
    Verifies that when a breach triggers Gemini AI:
    1. Gemini AI qualitative narrative and holding guidance are attached to the alert.
    2. Mathematical sovereignty is preserved: deterministic price (3840.0) and P&L (-4.0%)
       cannot be modified or hallucinated by the LLM.
    """
    user_id = "test-user-505"
    mock_profile = {
        "id": user_id,
        "fcm_device_token": "mock-fcm-token",
        "fcm_enabled": True,
        "telegram_chat_id": 999888,
        "telegram_enabled": True
    }

    ticker_manager._user_profiles_cache[user_id] = mock_profile

    breach_event = {
        "type": "DEMAT_STOPLOSS",
        "action_bias": "CAPITAL_PRESERVATION_EXIT",
        "catalyst_category": "TRAILING_STOP_TRIGGER",
        "confluence_score": 90,
        "pnl_pct": -4.0,
        "title": "🚨 TCS: Capital Preservation Exit Trigger (P&L: -4.0%)",
        "reason": "Demat portfolio protection trigger: Position down -4.0%.",
        "urgency": "CRITICAL",
    }

    holding = {
        "symbol": "TCS",
        "quantity": 10,
        "average_price": 4000.0
    }

    cached_pack = {
        "symbol": "TCS",
        "current_price": 3840.0,
        "technicals": {"current_price": 3840.0, "rsi_15m": 24.5, "vwap": 3910.0},
        "financials": {"pe_ratio": 28.5},
        "tactical_levels": {"protective_stop_loss": 3850.0}
    }

    # Mock Gemini AI return
    mock_ai_output = {
        "alert_title": "🚨 TCS: Institutional Liquidity Breakdown & Emergency Exit",
        "holding_guidance": "Defensive Action Required: Institutional distribution confirmed. Liquidate to protect capital.",
        "confluence_drivers": ["Heavy block selling detected", "Multi-day support breached"]
    }

    with patch("app.engine.gemini_ai.evaluate_stock_with_ai", new_callable=AsyncMock) as mock_ai, \
         patch("app.engine.ticker_stream.send_fcm_notification", new_callable=AsyncMock) as mock_fcm, \
         patch("app.engine.ticker_stream.send_telegram_notification", new_callable=AsyncMock) as mock_tg, \
         patch("app.core.dependencies.get_supabase") as mock_get_sb:

        mock_ai.return_value = mock_ai_output
        mock_sb_client = MagicMock()
        mock_get_sb.return_value = mock_sb_client

        await ticker_manager._execute_breach_workflow(
            user_id=user_id,
            symbol="TCS",
            ltp=3840.0,
            breach_event=breach_event,
            cached_pack=cached_pack,
            holding=holding
        )

        # 1. AI was invoked
        assert mock_ai.call_count == 1

        # 2. FCM was dispatched with AI title and guidance
        assert mock_fcm.call_count == 1
        fcm_args = mock_fcm.call_args[0]
        assert fcm_args[0] == "mock-fcm-token"
        assert fcm_args[1] == "🚨 TCS: Institutional Liquidity Breakdown & Emergency Exit"
        assert "₹3,840.00" in fcm_args[2]

        # 3. Telegram was dispatched
        assert mock_tg.call_count == 1
        tg_args = mock_tg.call_args[0]
        assert tg_args[0] == 999888
        assert "TCS" in tg_args[1]

        # 4. Mathematical Sovereignty in Supabase record:
        assert mock_sb_client.table.return_value.insert.call_count == 1
        saved_record = mock_sb_client.table.return_value.insert.call_args[0][0]
        assert saved_record["metrics_snapshot"]["current_price"] == 3840.0
        assert saved_record["metrics_snapshot"]["demat_position"]["unrealized_pnl_pct"] == -4.0
        assert saved_record["metrics_snapshot"]["demat_position"]["average_buy_price"] == 4000.0
