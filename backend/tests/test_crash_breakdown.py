import pytest
import asyncio
import os
import sys
from datetime import date
from unittest.mock import MagicMock

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ["ENVIRONMENT"] = "test"
os.environ["ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="

from app.engine.deterministic import compute_deterministic_confluence
from app.agent_runner import (
    evaluate_and_dispatch_macro_risk_alert,
    _MACRO_CRASH_DISPATCHED_DATE,
    _MACRO_LAST_DISPATCHED_VIX,
)
import app.agent_runner as ar
from app.routers.auth import _async_sync_demat_to_watchlists


def test_supply_shock_overrides_200_ema_demat():
    """
    Test that a severe breakdown on a stock trading above its 200 EMA
    triggers CAPITAL_PRESERVATION_EXIT when held in Demat, overriding the 200 EMA uptrend veto.
    """
    technicals = {
        "current_price": 2450.0,
        "ema_200": 2300.0,  # Macro uptrend active (price > 200 EMA)
        "change_pct": -4.2,  # Severe price drop!
        "price_vs_vwap_pct": -2.5,
        "is_volume_surge": True,
        "volume_multiple": 2.8,
        "rsi_15m": 32.0,
        "camarilla_pivots": {"l4": 2480.0, "h4": 2560.0}
    }
    demat_holding = {
        "symbol": "TATASTEEL",
        "average_price": 2550.0,
        "quantity": 100,
        "current_market_price": 2450.0
    }
    macro_data = {"india_vix": 17.5, "adr_ratio": 0.45, "allow_breakout_trades": True}

    res = compute_deterministic_confluence(
        symbol="TATASTEEL",
        technicals=technicals,
        macro_data=macro_data,
        flow_data={"delivery_pct": 30.0},
        forensics={"debt_to_equity": 0.5},
        financials={"price": 2450.0},
        holding_info=demat_holding
    )

    assert res["has_actionable_signal"] is True
    assert res["action_bias"] == "CAPITAL_PRESERVATION_EXIT"
    assert any("Supply Shock Override" in d for d in res["confluence_drivers"])
    assert "Capital Preservation" in res["alert_title"] or "Emergency Portfolio Defense" in res["alert_title"]


def test_supply_shock_overrides_200_ema_unheld():
    """
    Test that a severe breakdown on a stock trading above its 200 EMA
    triggers INTRADAY_MIS_SHORT when NOT held in Demat, with statutory 3:15 PM MIS warning.
    """
    technicals = {
        "current_price": 1400.0,
        "ema_200": 1300.0,  # Price > 200 EMA
        "change_pct": -3.8,  # Severe price drop
        "price_vs_vwap_pct": -2.1,
        "is_volume_surge": True,
        "volume_multiple": 2.2,
        "rsi_15m": 35.0,
        "camarilla_pivots": {"l4": 1420.0, "h4": 1460.0}
    }
    macro_data = {"india_vix": 16.0, "adr_ratio": 0.50, "allow_breakout_trades": True}

    res = compute_deterministic_confluence(
        symbol="INFY",
        technicals=technicals,
        macro_data=macro_data,
        flow_data={"delivery_pct": 25.0},
        forensics={"debt_to_equity": 0.1},
        financials={"price": 1400.0},
        holding_info=None  # Not held in Demat
    )

    assert res["has_actionable_signal"] is True
    assert res["action_bias"] == "INTRADAY_MIS_SHORT"
    assert any("Supply Shock Override" in d for d in res["confluence_drivers"])
    assert "Intraday MIS Short" in res["alert_title"]


def test_normal_sell_vetoed_by_200_ema():
    """
    Test that a standard weak setup above 200 EMA without severe breakdown
    is still properly vetoed to HOLD_NEUTRAL to avoid shorting strong primary bull trends.
    """
    technicals = {
        "current_price": 2500.0,
        "ema_200": 2400.0,  # Price > 200 EMA
        "change_pct": -0.4,  # Normal mild fluctuation, NOT a severe breakdown
        "price_vs_vwap_pct": -0.2,
        "is_volume_surge": False,
        "rsi_15m": 48.0,
        "camarilla_pivots": {"l4": 2470.0, "h4": 2530.0}
    }
    macro_data = {"india_vix": 13.5, "adr_ratio": 1.1, "allow_breakout_trades": True}

    res = compute_deterministic_confluence(
        symbol="RELIANCE",
        technicals=technicals,
        macro_data=macro_data,
        flow_data={"delivery_pct": 50.0},
        forensics={"debt_to_equity": 0.4},
        financials={"price": 2500.0},
        holding_info=None
    )

    # Low score or normal sell must be vetoed to HOLD_NEUTRAL because price > 200 EMA
    assert res["action_bias"] == "HOLD_NEUTRAL"
    assert res["has_actionable_signal"] is False


@pytest.mark.asyncio
async def test_macro_crash_state_latch_and_hysteresis():
    """
    Tests that:
    1. First crash trigger broadcasts successfully.
    2. Second trigger on the same day with flat VIX is suppressed by the state latch.
    3. Third trigger with VIX surging >= 15% triggers an escalation broadcast.
    """
    mock_supabase = MagicMock()
    mock_supabase.table().select().execute.return_value = MagicMock(data=[])

    # Reset module state
    ar._MACRO_CRASH_DISPATCHED_DATE = None
    ar._MACRO_LAST_DISPATCHED_VIX = 0.0

    crash_macro_1 = {
        "nifty_change_pct": -1.65,
        "india_vix": 17.0,
        "adr_ratio": 0.40
    }

    # 1. First trigger -> should dispatch
    first_result = await evaluate_and_dispatch_macro_risk_alert(crash_macro_1, mock_supabase)
    assert first_result is True
    assert ar._MACRO_CRASH_DISPATCHED_DATE == str(date.today())
    assert ar._MACRO_LAST_DISPATCHED_VIX == 17.0

    # 2. Second trigger with identical/slightly higher VIX (17.5, < 15% gain) -> should be suppressed
    crash_macro_2 = {
        "nifty_change_pct": -1.70,
        "india_vix": 17.5,
        "adr_ratio": 0.38
    }
    second_result = await evaluate_and_dispatch_macro_risk_alert(crash_macro_2, mock_supabase)
    assert second_result is False

    # 3. Third trigger with VIX surging to 20.0 (+17.6% above 17.0) -> should trigger escalation
    crash_macro_3 = {
        "nifty_change_pct": -2.10,
        "india_vix": 20.0,
        "adr_ratio": 0.30
    }
    third_result = await evaluate_and_dispatch_macro_risk_alert(crash_macro_3, mock_supabase)
    assert third_result is True
    assert ar._MACRO_LAST_DISPATCHED_VIX == 20.0


def test_async_sync_demat_to_watchlists_cost_basis():
    """
    Tests that _async_sync_demat_to_watchlists saves average_buy_price and quantity
    into the database upsert payload.
    """
    mock_db = MagicMock()
    upsert_mock = MagicMock()
    mock_db.table().upsert.return_value = upsert_mock

    holdings = [
        {"symbol": "TATASTEEL.NS", "average_price": 145.5, "quantity": 250},
        {"symbol": "HDFCBANK", "average_price": 1620.0, "quantity": 50},
    ]

    _async_sync_demat_to_watchlists(mock_db, "user-uuid-123", holdings)

    mock_db.table.assert_called_with("user_watchlists")
    call_args = mock_db.table().upsert.call_args[0][0]
    assert len(call_args) == 2
    assert call_args[0]["symbol"] == "TATASTEEL"
    assert call_args[0]["average_buy_price"] == 145.5
    assert call_args[0]["quantity"] == 250
    assert call_args[0]["is_auto_synced"] is True

    assert call_args[1]["symbol"] == "HDFCBANK"
    assert call_args[1]["average_buy_price"] == 1620.0
    assert call_args[1]["quantity"] == 50
