import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.technical_engine import (
    calculate_camarilla_pivots,
    calculate_weekly_camarilla_pivots,
    detect_camarilla_pivot_clustering,
    classify_camarilla_open
)


def test_camarilla_full_pivots_h1_to_h5():
    """Verifies that full H1-H5 and L1-L5 levels are calculated with mathematical precision."""
    # Create 2 days of closed daily bars:
    # High = 100, Low = 90, Close = 95 -> Range = 10
    dates = pd.date_range(end=datetime.now() - timedelta(days=2), periods=2, freq='D')
    df_daily = pd.DataFrame({
        "Open": [92.0, 93.0],
        "High": [98.0, 100.0],
        "Low": [88.0, 90.0],
        "Close": [94.0, 95.0],
        "Volume": [100000, 150000]
    }, index=dates)

    pivots = calculate_camarilla_pivots(df_daily)

    # Range = 10.0, Close = 95.0
    # H5 = Close + Range * 1.1 = 95 + 11.0 = 106.0
    # H4 = Close + Range * 1.1 / 2.0 = 95 + 5.5 = 100.5
    # H3 = Close + Range * 1.1 / 4.0 = 95 + 2.75 = 97.75
    # L3 = Close - Range * 1.1 / 4.0 = 95 - 2.75 = 92.25
    # L4 = Close - Range * 1.1 / 2.0 = 95 - 5.5 = 89.5
    # L5 = Close - Range * 1.1 = 95 - 11.0 = 84.0
    assert pivots["h5"] == 106.0
    assert pivots["h4"] == 100.5
    assert pivots["h3"] == 97.75
    assert pivots["l3"] == 92.25
    assert pivots["l4"] == 89.5
    assert pivots["l5"] == 84.0
    assert pivots["h1"] is not None
    assert pivots["l1"] is not None


def test_camarilla_zero_default_empty_data():
    """Verifies Zero-Default Policy: Returns clean dictionary of None values when bars are insufficient."""
    empty_df = pd.DataFrame()
    pivots = calculate_camarilla_pivots(empty_df)
    assert pivots["h4"] is None
    assert pivots["l4"] is None
    assert pivots["h5"] is None
    assert pivots["l5"] is None


def test_camarilla_open_classification():
    """Verifies that the 5 institutional market open states are correctly identified."""
    pivots = {"h5": 106.0, "h4": 100.5, "h3": 97.75, "l3": 92.25, "l4": 89.5, "l5": 84.0}

    # 1. Open Inside Value (Equilibrium)
    assert classify_camarilla_open(95.0, pivots) == "OPEN_INSIDE_VALUE"
    assert classify_camarilla_open(97.75, pivots) == "OPEN_INSIDE_VALUE"
    assert classify_camarilla_open(92.25, pivots) == "OPEN_INSIDE_VALUE"

    # 2. Open Above H4 (Gap-and-Go Breakout)
    assert classify_camarilla_open(101.5, pivots) == "OPEN_ABOVE_H4_BREAKOUT"

    # 3. Open Below L4 (Gap-Down Breakdown)
    assert classify_camarilla_open(88.0, pivots) == "OPEN_BELOW_L4_BREAKDOWN"

    # 4. Open in Upper Trap Zone
    assert classify_camarilla_open(99.0, pivots) == "OPEN_IN_UPPER_TRAP_ZONE"

    # 5. Open in Lower Trap Zone
    assert classify_camarilla_open(91.0, pivots) == "OPEN_IN_LOWER_TRAP_ZONE"

    # 6. Missing Open Price
    assert classify_camarilla_open(None, pivots) == "DATA_INSUFFICIENT"


def test_camarilla_pivot_clustering():
    """Verifies detection of Multi-Timeframe Daily and Weekly pivot clusters."""
    daily_pivots = {"h4": 100.5, "l4": 89.5}
    # Weekly H3 at 100.3 (within 0.35% of Daily H4 100.5)
    weekly_pivots = {"w_h4": 105.0, "w_h3": 100.3, "w_l3": 89.4, "w_l4": 85.0}

    cluster = detect_camarilla_pivot_clustering(daily_pivots, weekly_pivots, threshold_pct=0.35)
    assert cluster["is_pivot_cluster"] is True
    assert cluster["cluster_type"] == "BULLISH_MTF_CLUSTER"
    assert "Daily H4" in cluster["description"]
