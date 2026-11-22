import pytest
from datetime import datetime, timezone, timedelta
from app.engine.deterministic import compute_deterministic_confluence

IST = timezone(timedelta(hours=5, minutes=30))


def test_regime_switcher_l3_bounce_mean_reversion():
    """Verifies that in a range-bound market, a stock bouncing from Camarilla L3 triggers a mean-reversion BUY_WATCH."""
    technicals = {
        "current_price": 1002.0,
        "change_pct": 0.2,
        "technical_score": 65,
        "volume_multiple": 1.1,
        "is_volume_surge": False,
        "close_location_pct": 0.70,
        "candle_5m_change_pct": 0.25,
        "price_vs_vwap_pct": 0.1,
        "atr_14": 15.0,
        "adx_14": 16.0, # Low ADX = Range-Bound Market Regime
        "ema_200": 950.0,
        "camarilla_open_type": "OPEN_INSIDE_VALUE",
        "camarilla_pivots": {
            "h5": 1040.0,
            "h4": 1025.0,
            "h3": 1015.0,
            "l3": 1000.0, # L3 floor is at 1000.0, price is at 1002.0
            "l4": 985.0,
            "l5": 970.0
        }
    }
    financials = {"overall_score": 75, "beta_volatility": 0.9}
    flow_data = {"flow_score": 60}
    forensics = {"forensic_score": 75}
    news_items = []
    morning_time = datetime(2026, 11, 22, 10, 15, tzinfo=IST) # 10:15 AM IST (morning active session)
    macro_data = {
        "allow_breakout_trades": True,
        "nifty_change_pct": 0.05,
        "india_vix": 12.8, # Low VIX = Choppy / Mean-Reverting
        "current_time_ist": morning_time
    }

    res = compute_deterministic_confluence(
        symbol="HDFCBANK.NS",
        technicals=technicals,
        flow_data=flow_data,
        macro_data=macro_data,
        forensics=forensics,
        financials=financials,
        news_items=news_items,
        holding_info=None,
        current_time_ist=morning_time
    )

    assert res["action_bias"] == "BUY_WATCH"
    assert res["catalyst_category"] == "CAMARILLA_L3_BOUNCE"
    assert "Camarilla L3 Support Floor Bounce" in res["alert_title"]
    assert any("Mean-Reversion Setup" in d for d in res["confluence_drivers"])
    # Targets should aim for H3 or H4/H5
    assert res["tactical_levels"]["target_1"] is not None


def test_regime_switcher_vetoes_breakout_in_range_market():
    """Verifies that in a range-bound market without volume surge, breakouts are vetoed in favor of mean reversion."""
    morning_time = datetime(2026, 11, 22, 10, 15, tzinfo=IST)
    technicals = {
        "current_price": 1030.0,
        "change_pct": 1.2,
        "technical_score": 78,
        "volume_multiple": 1.3, # Low volume breakout in range market
        "is_volume_surge": False,
        "close_location_pct": 0.85,
        "candle_5m_change_pct": 0.4,
        "price_vs_vwap_pct": 0.8,
        "atr_14": 15.0,
        "adx_14": 15.5, # Very low ADX
        "ema_200": 950.0,
        "camarilla_pivots": {
            "h5": 1045.0,
            "h4": 1025.0, # Crossed H4
            "h3": 1015.0,
            "l3": 1000.0,
            "l4": 985.0
        }
    }
    financials = {"overall_score": 75, "beta_volatility": 0.9}
    flow_data = {"flow_score": 60}
    forensics = {"forensic_score": 75}
    news_items = []
    macro_data = {
        "allow_breakout_trades": True,
        "nifty_change_pct": 0.05,
        "india_vix": 12.5, # Low VIX
        "current_time_ist": morning_time
    }

    res = compute_deterministic_confluence(
        symbol="HDFCBANK.NS",
        technicals=technicals,
        flow_data=flow_data,
        macro_data=macro_data,
        forensics=forensics,
        financials=financials,
        news_items=news_items,
        holding_info=None,
        current_time_ist=morning_time
    )

    # In low ADX / low VIX regime without strong volume surge, breakout must be vetoed
    assert res["action_bias"] == "HOLD_NEUTRAL"
    assert any("Market Regime Veto" in d for d in res["confluence_drivers"])
