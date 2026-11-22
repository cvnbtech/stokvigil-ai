"""
Unit Tests for Vectorized Candlestick & Morphological Pattern Recognition Engine
Dual-Exchange (NSE & BSE) Compliant with Zero-Default Policy.
"""
import unittest
import pandas as pd
import numpy as np

from app.patterns import evaluate_candlestick_patterns
from app.engine.deterministic import compute_deterministic_confluence


class TestCandlestickPatterns(unittest.TestCase):

    def test_zero_default_on_empty_or_corrupt_data(self):
        """Zero-Default Policy: Returns unpopulated payload when data is empty or < 5 bars."""
        empty_res = evaluate_candlestick_patterns(pd.DataFrame())
        self.assertEqual(empty_res["primary_pattern"], "NONE")
        self.assertEqual(empty_res["pattern_bias"], "NEUTRAL")
        self.assertIsNone(empty_res["upper_wick_ratio"])
        self.assertFalse(empty_res["is_upper_wick_rejection"])

        # Corrupt / non-numeric
        corrupt_df = pd.DataFrame({"Open": ["abc"], "High": ["xyz"], "Low": [1], "Close": [2], "Volume": [10]})
        c_res = evaluate_candlestick_patterns(corrupt_df)
        self.assertEqual(c_res["primary_pattern"], "NONE")

    def test_bullish_hammer_pinbar_detection(self):
        """Tests Bullish Hammer / Pinbar demand absorption pattern."""
        # 6 bars: last bar has lower wick 3x body, tiny upper wick, closes near high
        opens = [100, 101, 102, 101, 100, 98.0]
        highs = [102, 103, 103, 102, 101, 99.0]
        lows = [99, 100, 100, 99, 98, 90.0]     # Long lower shadow down to 90
        closes = [101, 102, 101, 100, 98, 98.8] # Closes at 98.8 (top of candle)
        volumes = [1000] * 6

        df = pd.DataFrame({"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": volumes})
        res = evaluate_candlestick_patterns(df, timeframe="15m")

        self.assertIn("BULLISH_HAMMER_PINBAR", res["detected_patterns"])
        self.assertEqual(res["pattern_bias"], "BULLISH")
        self.assertGreater(res["lower_wick_ratio"], 0.50)
        self.assertGreaterEqual(res["close_location_quotient"], 0.65)
        self.assertGreater(res["pattern_score_boost"], 0)

    def test_bearish_shooting_star_rejection_detection(self):
        """Tests Bearish Shooting Star / Upper Wick Rejection pattern."""
        # Last bar spikes to 110 but dumps down to close at 100.5
        opens = [100, 101, 102, 101, 100, 101.0]
        highs = [102, 103, 103, 102, 101, 110.0] # Spike to 110
        lows = [99, 100, 100, 99, 98, 100.0]
        closes = [101, 102, 101, 100, 101, 100.5] # Closes in lower 30% of range
        volumes = [1000] * 6

        df = pd.DataFrame({"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": volumes})
        res = evaluate_candlestick_patterns(df, timeframe="15m")

        self.assertIn("BEARISH_SHOOTING_STAR", res["detected_patterns"])
        self.assertEqual(res["pattern_bias"], "BEARISH")
        self.assertTrue(res["is_upper_wick_rejection"])
        self.assertGreater(res["upper_wick_ratio"], 0.50)
        self.assertLessEqual(res["close_location_quotient"], 0.35)

    def test_bullish_engulfing_detection(self):
        """Tests Bullish Engulfing pattern."""
        # Prior candle red (102 -> 99), current candle green (98 -> 104) completely engulfing
        opens = [100, 101, 102, 103, 102.0, 98.0]
        highs = [101, 102, 103, 104, 102.5, 104.5]
        lows = [99, 100, 101, 101, 98.5, 97.5]
        closes = [100, 102, 102, 102, 99.0, 104.0] # Green swallows red
        volumes = [1000, 1000, 1000, 1000, 1000, 2500]

        df = pd.DataFrame({"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": volumes})
        res = evaluate_candlestick_patterns(df, timeframe="15m")

        self.assertIn("BULLISH_ENGULFING", res["detected_patterns"])
        self.assertEqual(res["pattern_bias"], "BULLISH")
        self.assertGreater(res["pattern_score_boost"], 0)

    def test_inside_bar_and_nr7_detection(self):
        """Tests Inside Bar and NR7 volatility compression."""
        opens = [100, 101, 102, 103, 102, 101, 100, 100.2]
        highs = [105, 106, 107, 108, 107, 106, 105, 101.0] # High inside prior 105
        lows = [95, 96, 97, 98, 97, 96, 95, 99.5]         # Low inside prior 95
        closes = [101, 102, 103, 104, 103, 102, 100, 100.8]
        volumes = [1000] * 8

        df = pd.DataFrame({"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": volumes})
        res = evaluate_candlestick_patterns(df, timeframe="15m")

        self.assertTrue(res["is_inside_bar"])
        self.assertTrue(res["is_nr7"])
        self.assertIn("INSIDE_BAR", res["detected_patterns"])
        self.assertIn("NR7_COMPRESSION", res["detected_patterns"])

    def test_shooting_star_vetoes_breakout_in_deterministic_engine(self):
        """Verifies that Shooting Star / Upper Wick Rejection vetoes BUY_WATCH to HOLD_NEUTRAL."""
        technicals = {
            "current_price": 1050.0,
            "technical_score": 75,
            "rsi_15m": 62.0,
            "rsi_daily": 58.0,
            "ema_50": 980.0,
            "ema_200": 950.0,
            "vwap": 1040.0,
            "atr_14": 15.0,
            "camarilla_pivots": {"h4": 1045.0, "h3": 1030.0, "l3": 1010.0, "l4": 1000.0},
            "upper_wick_ratio": 0.48, # 48% upper wick rejection
            "close_location_pct": 0.30,
            "is_upper_wick_rejection": True,
            "candlestick_patterns": {
                "detected_patterns": ["BEARISH_SHOOTING_STAR"],
                "is_upper_wick_rejection": True,
                "upper_wick_ratio": 0.48
            }
        }
        res = compute_deterministic_confluence(
            symbol="500325.BO", # BSE test symbol
            technicals=technicals,
            flow_data={"delivery_pct": 55.0},
            macro_data={"allow_breakout_trades": True},
            forensics={"forensic_score": 80},
            financials={},
            news_items=[],
            holding_info=None
        )

        # Upper wick rejection MUST veto BUY_WATCH to HOLD_NEUTRAL
        self.assertEqual(res["action_bias"], "HOLD_NEUTRAL")
        self.assertFalse(res["has_actionable_signal"])
        self.assertTrue(any("Wick Rejection Veto" in d for d in res["confluence_drivers"]))


if __name__ == "__main__":
    unittest.main()
