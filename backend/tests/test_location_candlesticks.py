import pytest
import pandas as pd
from app.patterns import evaluate_candlestick_patterns


def test_hammer_anchored_at_vwap():
    """Verifies that a Bullish Hammer forming at VWAP is confirmed as location-valid with full score boost."""
    df = pd.DataFrame({
        "Open":   [100.0, 100.2, 100.1, 100.0, 99.8, 99.0],
        "High":   [100.5, 100.4, 100.3, 100.2, 100.0, 99.2],
        "Low":    [99.8,  99.9,  99.8,  99.6,  99.4, 96.0], # Long tail down to 96.0
        "Close":  [100.2, 100.1, 100.0, 99.8,  99.5, 99.1], # Closes near high
        "Volume": [1000,  1200,  1100,  1050,  1300, 3500]
    })

    # VWAP is at 96.2, very close to low of 96.0 (diff ~0.2%)
    anchors = {
        "vwap": 96.2,
        "l3": 95.0,
        "l4": 94.0
    }

    res = evaluate_candlestick_patterns(df, timeframe="15m", anchor_levels=anchors)
    assert "BULLISH_HAMMER_PINBAR" in res["detected_patterns"]
    assert res["is_location_valid"] is True
    assert res["is_unanchored_churn"] is False
    assert res["anchored_level"] is not None
    assert "VWAP" in res["anchored_level"]
    assert res["pattern_score_boost"] > 0


def test_hammer_floating_unanchored_churn():
    """Verifies that a Hammer forming in the middle of nowhere without demand anchoring is neutralized."""
    df = pd.DataFrame({
        "Open":   [100.0, 100.2, 100.1, 100.0, 99.8, 99.0],
        "High":   [100.5, 100.4, 100.3, 100.2, 100.0, 99.2],
        "Low":    [99.8,  99.9,  99.8,  99.6,  99.4, 96.0],
        "Close":  [100.2, 100.1, 100.0, 99.8,  99.5, 99.1],
        "Volume": [1000,  1200,  1100,  1050,  1300, 3500]
    })

    # Anchors are far away at 90.0
    anchors = {
        "vwap": 90.0,
        "l3": 88.0,
        "l4": 86.0
    }

    res = evaluate_candlestick_patterns(df, timeframe="15m", anchor_levels=anchors)
    assert "BULLISH_HAMMER_PINBAR" in res["detected_patterns"]
    assert res["is_location_valid"] is False
    assert res["is_unanchored_churn"] is True
    assert res["pattern_score_boost"] == 0 # Score boost neutralized
