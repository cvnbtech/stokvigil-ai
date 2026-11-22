import pytest
from app.macro_filter import check_sector_alignment_gatekeeper, register_symbol_sector
from app.engine.deterministic import compute_deterministic_confluence


def setup_function():
    register_symbol_sector("TCS.NS", "NIFTY IT")
    register_symbol_sector("TATAMOTORS.NS", "NIFTY AUTO")


def test_sector_drag_vetoes_breakout():
    """Verifies that an individual stock breakout is vetoed when its parent sector is heavily underperforming."""
    macro_data = {
        "nifty_change_pct": 0.20,
        "allow_breakout_trades": True,
        "lagging_sectors": [
            {"name": "NIFTY IT", "price": 35000.0, "change_pct": -1.80}
        ],
        "leading_sectors": []
    }

    # Evaluate TCS which belongs to NIFTY IT
    gate = check_sector_alignment_gatekeeper("TCS.NS", macro_data)
    assert gate["is_aligned"] is False
    assert gate["has_drag"] is True
    assert gate["score_adjustment"] == -15
    assert "Sector Drag Veto" in gate["driver"]


def test_sector_leadership_tailwinds():
    """Verifies that a stock whose parent sector is a leading market driver receives tailwind bonuses."""
    macro_data = {
        "nifty_change_pct": 0.40,
        "allow_breakout_trades": True,
        "leading_sectors": [
            {"name": "NIFTY AUTO", "price": 22000.0, "change_pct": 1.90}
        ],
        "lagging_sectors": []
    }

    gate = check_sector_alignment_gatekeeper("TATAMOTORS.NS", macro_data)
    assert gate["is_aligned"] is True
    assert gate["has_tailwinds"] is True
    assert gate["score_adjustment"] == 8
    assert "Sector Leadership Tailwind" in gate["driver"]


def test_sector_gatekeeper_deterministic_veto():
    """Verifies that deterministic engine downgrades BUY_WATCH to HOLD_NEUTRAL on severe sector drag."""
    technicals = {
        "current_price": 3800.0,
        "change_pct": 2.5,
        "technical_score": 85,
        "volume_multiple": 2.2,
        "is_volume_surge": True,
        "close_location_pct": 0.90,
        "candle_5m_change_pct": 0.5,
        "price_vs_vwap_pct": 1.2,
        "atr_14": 45.0,
        "ema_200": 3500.0,
        "camarilla_pivots": {"h4": 3780.0, "h3": 3750.0, "l3": 3650.0, "l4": 3600.0}
    }
    financials = {"overall_score": 80, "beta_volatility": 1.0}
    flow_data = {"flow_score": 80}
    news_items = []
    forensics = {"forensic_score": 80}

    macro_data = {
        "nifty_change_pct": 0.10,
        "allow_breakout_trades": True,
        "lagging_sectors": [
            {"name": "NIFTY IT", "price": 35000.0, "change_pct": -2.20}
        ],
        "leading_sectors": []
    }

    res = compute_deterministic_confluence(
        symbol="TCS.NS",
        technicals=technicals,
        flow_data=flow_data,
        macro_data=macro_data,
        forensics=forensics,
        financials=financials,
        news_items=news_items,
        holding_info=None
    )

    # Long entry must be vetoed because NIFTY IT is dragging down -2.20%
    assert res["action_bias"] == "HOLD_NEUTRAL"
    assert any("Sector Gatekeeper Veto" in d for d in res["confluence_drivers"])
