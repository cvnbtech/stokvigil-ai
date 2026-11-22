import pytest
from app.derivatives_tracker import (
    register_scrip_oi,
    classify_oi_buildup,
    evaluate_derivatives_microstructure,
    clear_oi_cache
)
from app.engine.deterministic import compute_deterministic_confluence


def setup_function():
    clear_oi_cache()


def test_classify_oi_quadrants():
    """Verifies that all 4 institutional price-OI buildup/unwinding regimes are accurately classified."""
    # 1. Long Build-up (Price Up + OI Up)
    r1 = classify_oi_buildup(price_change_pct=1.2, oi_change_pct=4.5)
    assert r1["oi_regime"] == "LONG_BUILDUP"
    assert r1["conviction_score"] == 10

    # 2. Short Covering (Price Up + OI Down)
    r2 = classify_oi_buildup(price_change_pct=0.8, oi_change_pct=-3.2)
    assert r2["oi_regime"] == "SHORT_COVERING"
    assert r2["conviction_score"] == 3

    # 3. Short Build-up (Price Down + OI Up)
    r3 = classify_oi_buildup(price_change_pct=-1.5, oi_change_pct=5.0)
    assert r3["oi_regime"] == "SHORT_BUILDUP"
    assert r3["conviction_score"] == -12

    # 4. Long Unwinding (Price Down + OI Down)
    r4 = classify_oi_buildup(price_change_pct=-1.1, oi_change_pct=-4.0)
    assert r4["oi_regime"] == "LONG_UNWINDING"
    assert r4["conviction_score"] == -10


def test_derivatives_short_buildup_vetoes_buy_watch():
    """Verifies that institutional Short Buildup on futures vetoes cash equity BUY_WATCH breakouts."""
    # Register heavy institutional short buildup for RELIANCE
    register_scrip_oi(symbol="RELIANCE.NS", price_change_pct=-0.8, oi_change_pct=6.5)

    technicals = {
        "current_price": 2500.0,
        "change_pct": 1.5,
        "technical_score": 85,
        "volume_multiple": 2.5,
        "is_volume_surge": True,
        "close_location_pct": 0.85,
        "candle_5m_change_pct": 0.3,
        "price_vs_vwap_pct": 0.5,
        "atr_14": 30.0,
        "ema_200": 2400.0,
        "camarilla_pivots": {"h4": 2480.0, "h3": 2460.0, "l3": 2420.0, "l4": 2400.0}
    }
    financials = {"overall_score": 85, "beta_volatility": 1.0}
    flow_data = {"flow_score": 80}
    forensics = {"forensic_score": 85}
    news_items = []
    macro_data = {"allow_breakout_trades": True, "nifty_change_pct": 0.3}

    res = compute_deterministic_confluence(
        symbol="RELIANCE.NS",
        technicals=technicals,
        flow_data=flow_data,
        macro_data=macro_data,
        forensics=forensics,
        financials=financials,
        news_items=news_items,
        holding_info=None
    )

    # Must be vetoed to HOLD_NEUTRAL
    assert res["action_bias"] == "HOLD_NEUTRAL"
    assert any("Derivatives Microstructure Veto" in d for d in res["confluence_drivers"])


def test_derivatives_zero_default_for_cash_scrip():
    """Verifies that non-F&O cash equities or unpopulated scrips return None without penalty."""
    eval_res = evaluate_derivatives_microstructure("TATACHEM.NS")
    assert eval_res["is_fno_eligible"] is False
    assert eval_res["oi_regime"] is None
    assert eval_res["conviction_score"] == 0
