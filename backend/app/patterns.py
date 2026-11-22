"""
StokVigil AI - Vectorized Candlestick & Price Action Pattern Engine
===================================================================
High-performance morphological candle anatomy and pattern recognition.
Dual-Exchange (NSE & BSE) compliant with ZERO-DEFAULT POLICY.

Patterns Detected:
1. Hammer / Bullish Pinbar (Demand absorption at key support)
2. Shooting Star / Bearish Pinbar (Supply rejection at resistance)
3. Bullish Engulfing (Buyers overwhelming sellers with body expansion)
4. Bearish Engulfing (Institutional distribution overpowering buyers)
5. Inside Bar / Narrow Range 7 (NR7) (Volatility compression before explosion)
6. Upper Wick Rejection Traps (Breakout failure defense)

Zero-Default Guarantee:
Returns clean None / empty structure if historical bars are insufficient.
Never manufactures placeholder patterns or dummy metrics.
"""

import logging
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger("stokvigil.patterns")


def evaluate_candlestick_patterns(
    df: pd.DataFrame, 
    timeframe: str = "15m",
    anchor_levels: Optional[Dict[str, Optional[float]]] = None
) -> Dict[str, Any]:
    """
    Evaluates morphological candlestick patterns on OHLCV bars with institutional location anchoring.
    
    Parameters:
    - df: DataFrame with ['Open', 'High', 'Low', 'Close', 'Volume']
    - timeframe: "15m" or "1d"
    - anchor_levels: Optional dict with institutional levels:
        {"vwap": float, "l3": float, "l4": float, "h3": float, "h4": float, "ema200": float, "ema50": float}
    
    Returns structured pattern payload with wick metrics, location validation, and conviction score.
    Zero-Default Guarantee: Never manufactures placeholder patterns.
    """
    default_res: Dict[str, Any] = {
        "timeframe": timeframe,
        "detected_patterns": [],
        "primary_pattern": "NONE",
        "pattern_bias": "NEUTRAL",
        "upper_wick_ratio": None,
        "lower_wick_ratio": None,
        "body_ratio": None,
        "close_location_quotient": None,
        "is_upper_wick_rejection": False,
        "is_lower_wick_rejection": False,
        "is_inside_bar": False,
        "is_nr7": False,
        "is_location_valid": True,
        "anchored_level": None,
        "is_unanchored_churn": False,
        "pattern_score_boost": 0
    }

    if df is None or df.empty or len(df) < 5:
        return default_res

    # Clean & ensure numeric price columns
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col not in df.columns:
            return default_res

    try:
        opens = df["Open"].astype(float).values
        highs = df["High"].astype(float).values
        lows = df["Low"].astype(float).values
        closes = df["Close"].astype(float).values
        volumes = df["Volume"].astype(float).values
    except (ValueError, TypeError) as e:
        logger.debug(f"Data type conversion error in pattern engine: {e}")
        return default_res

    n = len(closes)
    if n < 5:
        return default_res

    # Current bar (most recent completed or active bar)
    cur_open = float(opens[-1])
    cur_high = float(highs[-1])
    cur_low = float(lows[-1])
    cur_close = float(closes[-1])
    cur_vol = float(volumes[-1])

    cur_range = cur_high - cur_low
    if cur_range <= 0.0001:
        # Avoid division by zero on flat/circuit candles
        return default_res

    cur_body = abs(cur_close - cur_open)
    cur_upper_wick = cur_high - max(cur_open, cur_close)
    cur_lower_wick = min(cur_open, cur_close) - cur_low

    upper_wick_ratio = round(cur_upper_wick / cur_range, 3)
    lower_wick_ratio = round(cur_lower_wick / cur_range, 3)
    body_ratio = round(cur_body / cur_range, 3)
    clq = round((cur_close - cur_low) / cur_range, 3)

    is_green = cur_close >= cur_open
    is_red = cur_close < cur_open

    # Prior bar (-2)
    prev_open = float(opens[-2])
    prev_high = float(highs[-2])
    prev_low = float(lows[-2])
    prev_close = float(closes[-2])
    prev_range = prev_high - prev_low
    prev_body = abs(prev_close - prev_open)
    prev_green = prev_close >= prev_open
    prev_red = prev_close < prev_open

    detected: List[str] = []
    bias = "NEUTRAL"
    score_boost = 0

    # 1. Inside Bar
    is_inside = (cur_high <= prev_high) and (cur_low >= prev_low)
    if is_inside:
        detected.append("INSIDE_BAR")

    # 2. Narrow Range 7 (NR7) Volatility Compression
    is_nr7 = False
    if n >= 7:
        last_7_ranges = [highs[i] - lows[i] for i in range(n - 7, n - 1)]
        if last_7_ranges and cur_range < min(last_7_ranges):
            is_nr7 = True
            detected.append("NR7_COMPRESSION")

    # 3. Upper Wick Rejection (Breakout trap signal)
    is_upper_wick_rej = bool(upper_wick_ratio >= 0.40 and clq <= 0.50)

    # 4. Lower Wick Rejection (Bear trap signal)
    is_lower_wick_rej = bool(lower_wick_ratio >= 0.40 and clq >= 0.50)

    # 5. Hammer / Bullish Pinbar (Demand Absorption)
    # Lower shadow at least 2x body, tiny upper shadow, closes near high
    is_hammer = (
        (cur_lower_wick >= 2.0 * max(0.01, cur_body) or lower_wick_ratio >= 0.55) and
        upper_wick_ratio <= 0.25 and
        clq >= 0.65
    )
    if is_hammer:
        detected.append("BULLISH_HAMMER_PINBAR")
        bias = "BULLISH"
        score_boost = max(score_boost, 6)

    # 6. Shooting Star / Bearish Pinbar (Supply Rejection)
    # Upper shadow at least 2x body, tiny lower shadow, closes near low
    is_shooting_star = (
        (cur_upper_wick >= 2.0 * max(0.01, cur_body) or upper_wick_ratio >= 0.55) and
        lower_wick_ratio <= 0.25 and
        clq <= 0.35
    )
    if is_shooting_star:
        detected.append("BEARISH_SHOOTING_STAR")
        bias = "BEARISH"
        score_boost = min(score_boost, -6)

    # 7. Bullish Engulfing
    # Prior red candle swallowed completely by green candle with body expansion
    is_bullish_engulfing = (
        prev_red and is_green and
        cur_open <= prev_close and
        cur_close > prev_open and
        cur_body > prev_body
    )
    if is_bullish_engulfing:
        detected.append("BULLISH_ENGULFING")
        bias = "BULLISH"
        score_boost = max(score_boost, 7)

    # 8. Bearish Engulfing
    # Prior green candle swallowed completely by red candle with body expansion
    is_bearish_engulfing = (
        prev_green and is_red and
        cur_open >= prev_close and
        cur_close < prev_open and
        cur_body > prev_body
    )
    if is_bearish_engulfing:
        detected.append("BEARISH_ENGULFING")
        bias = "BEARISH"
        score_boost = min(score_boost, -7)

    # 9. Morning Star (3-Bar Bullish Reversal)
    if n >= 3:
        bar3_open = float(opens[-3])
        bar3_close = float(closes[-3])
        bar3_red = bar3_close < bar3_open
        star_body = prev_body
        is_morning_star = (
            bar3_red and
            star_body < (abs(bar3_close - bar3_open) * 0.5) and
            is_green and
            cur_close > (bar3_open + bar3_close) / 2.0
        )
        if is_morning_star:
            detected.append("BULLISH_MORNING_STAR")
            bias = "BULLISH"
            score_boost = max(score_boost, 8)

    # 10. Institutional Location Anchoring & Churn Filter
    is_location_valid = True
    anchored_level = None
    is_unanchored_churn = False

    if anchor_levels and isinstance(anchor_levels, dict) and detected:
        if bias == "BULLISH":
            # Bullish patterns (Hammer, Engulfing, Morning Star) must anchor to a demand floor
            demand_keys = ["vwap", "l3", "l4", "ema200", "ema50", "prior_low"]
            valid_anchors = {k: float(anchor_levels[k]) for k in demand_keys if anchor_levels.get(k) is not None and float(anchor_levels[k]) > 0}
            if valid_anchors:
                # Find closest demand anchor to candle low
                closest_anchor = min(valid_anchors.items(), key=lambda x: abs(cur_low - x[1]))
                distance_pct = abs(cur_low - closest_anchor[1]) / cur_close * 100.0
                if distance_pct <= 0.65:
                    is_location_valid = True
                    anchored_level = f"{closest_anchor[0].upper()} (dist: {distance_pct:.2f}%)"
                else:
                    # Floating in the middle of nowhere / unanchored churn
                    is_location_valid = False
                    is_unanchored_churn = True
                    score_boost = 0  # Neutralize boost for floating unanchored candle
        elif bias == "BEARISH":
            # Bearish patterns (Shooting Star, Bearish Engulfing) must anchor to a supply ceiling
            supply_keys = ["h3", "h4", "vwap", "ema200", "prior_high"]
            valid_anchors = {k: float(anchor_levels[k]) for k in supply_keys if anchor_levels.get(k) is not None and float(anchor_levels[k]) > 0}
            if valid_anchors:
                closest_anchor = min(valid_anchors.items(), key=lambda x: abs(cur_high - x[1]))
                distance_pct = abs(cur_high - closest_anchor[1]) / cur_close * 100.0
                if distance_pct <= 0.65:
                    is_location_valid = True
                    anchored_level = f"{closest_anchor[0].upper()} (dist: {distance_pct:.2f}%)"
                else:
                    is_location_valid = False
                    is_unanchored_churn = True
                    score_boost = 0

    primary_pattern = detected[0] if detected else "NONE"

    return {
        "timeframe": timeframe,
        "detected_patterns": detected,
        "primary_pattern": primary_pattern,
        "pattern_bias": bias,
        "upper_wick_ratio": upper_wick_ratio,
        "lower_wick_ratio": lower_wick_ratio,
        "body_ratio": body_ratio,
        "close_location_quotient": clq,
        "is_upper_wick_rejection": is_upper_wick_rej,
        "is_lower_wick_rejection": is_lower_wick_rej,
        "is_inside_bar": is_inside,
        "is_nr7": is_nr7,
        "is_location_valid": is_location_valid,
        "anchored_level": anchored_level,
        "is_unanchored_churn": is_unanchored_churn,
        "pattern_score_boost": score_boost
    }
