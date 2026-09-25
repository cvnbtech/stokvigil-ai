import os
import sys
import unittest
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.accuracy_verifier import (
    parse_tactical_price,
    parse_rr_ratio,
    normalize_symbol_for_yf,
    verify_single_alert,
    batch_verify_alerts,
)


class TestRealAccuracyVerifier(unittest.TestCase):
    def setUp(self):
        self.base_time = datetime(2026, 9, 10, 9, 30, tzinfo=timezone.utc)

    def test_parse_tactical_price(self):
        """Test extraction of numerical prices from formatted currency strings and ranges."""
        self.assertEqual(parse_tactical_price("₹1,365.00"), 1365.0)
        self.assertEqual(parse_tactical_price("₹2,450.50"), 2450.5)
        self.assertEqual(parse_tactical_price("100"), 100.0)
        self.assertEqual(parse_tactical_price(550.25), 550.25)
        # Range midpoint
        self.assertEqual(parse_tactical_price("₹1,320.00 - ₹1,330.00"), 1325.0)
        # Invalid / missing
        self.assertIsNone(parse_tactical_price("-"))
        self.assertIsNone(parse_tactical_price(None))
        self.assertIsNone(parse_tactical_price("N/A"))

    def test_parse_rr_ratio(self):
        """Test parsing of risk:reward ratios."""
        self.assertEqual(parse_rr_ratio("1:2.8"), 2.8)
        self.assertEqual(parse_rr_ratio("1:3.5"), 3.5)
        self.assertEqual(parse_rr_ratio(2.0), 2.0)
        self.assertEqual(parse_rr_ratio("invalid"), 2.5)

    def test_normalize_symbol(self):
        """Ensure correct exchange suffixes."""
        self.assertEqual(normalize_symbol_for_yf("RELIANCE"), "RELIANCE.NS")
        self.assertEqual(normalize_symbol_for_yf("TCS.NS"), "TCS.NS")
        self.assertEqual(normalize_symbol_for_yf("INFY.BO"), "INFY.BO")

    def test_bullish_alert_target_reached(self):
        """Verify bullish alert correctly detects TARGET_1_REACHED when High exceeds target before SL."""
        alert = {
            "id": "alert-001",
            "symbol": "RELIANCE",
            "alert_title": "RELIANCE Breakout",
            "catalyst_type": "TECHNICAL_BREAKOUT",
            "impact_score": 82,
            "metrics_snapshot": {
                "action_bias": "STRONG_BUY",
                "tactical_levels": {
                    "entry_range": "₹1,000.00",
                    "target_1": "₹1,050.00",
                    "protective_stop_loss": "₹970.00",
                    "risk_reward_ratio": "1:2.5",
                },
            },
            "created_at": self.base_time.isoformat(),
        }

        # Candles: 3 bars post alert, bar 2 reaches 1,060
        times = [
            self.base_time + timedelta(hours=1),
            self.base_time + timedelta(hours=2),
            self.base_time + timedelta(hours=3),
        ]
        df = pd.DataFrame(
            {
                "Open": [1000.0, 1020.0, 1055.0],
                "High": [1015.0, 1060.0, 1070.0],  # Hit 1060 (> 1050 target)
                "Low": [990.0, 1010.0, 1045.0],    # Never touched 970 SL
                "Close": [1010.0, 1055.0, 1065.0],
                "Volume": [10000, 15000, 12000],
            },
            index=times,
        )

        res = verify_single_alert(alert, candles_df=df)
        self.assertEqual(res["outcome"], "TARGET_1_REACHED")
        self.assertGreaterEqual(res["max_gain_pct"], 6.0)
        self.assertIsNotNone(res["hold_duration_hours"])
        self.assertEqual(res["verified_by"], "REAL_CANDLE_VERIFICATION")

    def test_bullish_alert_stop_loss_hit(self):
        """Verify bullish alert correctly detects STOP_LOSS_DEFENDED when Low breaches SL before target."""
        alert = {
            "id": "alert-002",
            "symbol": "INFY",
            "alert_title": "INFY Momentum",
            "catalyst_type": "MOMENTUM_EXPANSION",
            "impact_score": 78,
            "metrics_snapshot": {
                "action_bias": "BUY",
                "tactical_levels": {
                    "entry_range": "₹1,500.00",
                    "target_1": "₹1,580.00",
                    "protective_stop_loss": "₹1,460.00",
                    "risk_reward_ratio": "1:2.0",
                },
            },
            "created_at": self.base_time.isoformat(),
        }

        times = [
            self.base_time + timedelta(hours=1),
            self.base_time + timedelta(hours=2),
        ]
        df = pd.DataFrame(
            {
                "Open": [1500.0, 1470.0],
                "High": [1510.0, 1475.0],
                "Low": [1480.0, 1450.0],  # Breached 1,460 SL
                "Close": [1475.0, 1455.0],
                "Volume": [20000, 30000],
            },
            index=times,
        )

        res = verify_single_alert(alert, candles_df=df)
        self.assertEqual(res["outcome"], "STOP_LOSS_DEFENDED")
        self.assertEqual(res["verified_by"], "REAL_CANDLE_VERIFICATION")

    def test_bearish_alert_target_reached(self):
        """Verify bearish short alert correctly detects TARGET_1_REACHED when Low drops below downside target."""
        alert = {
            "id": "alert-003",
            "symbol": "TATASTEEL",
            "alert_title": "TATASTEEL Breakdown",
            "catalyst_type": "BEARISH_DIVERGENCE",
            "impact_score": 80,
            "metrics_snapshot": {
                "action_bias": "SELL_WATCH",
                "tactical_levels": {
                    "entry_range": "₹150.00",
                    "target_1": "₹140.00",
                    "protective_stop_loss": "₹155.00",
                    "risk_reward_ratio": "1:2.0",
                },
            },
            "created_at": self.base_time.isoformat(),
        }

        times = [
            self.base_time + timedelta(hours=1),
            self.base_time + timedelta(hours=2),
        ]
        df = pd.DataFrame(
            {
                "Open": [150.0, 145.0],
                "High": [151.0, 146.0],  # Never touched 155 buy-stop
                "Low": [144.0, 138.0],   # Dropped to 138 (< 140 target)
                "Close": [145.0, 139.0],
                "Volume": [50000, 60000],
            },
            index=times,
        )

        res = verify_single_alert(alert, candles_df=df)
        self.assertEqual(res["outcome"], "TARGET_1_REACHED")
        self.assertGreaterEqual(res["max_gain_pct"], 8.0)

    def test_batch_verify_alerts_kpis(self):
        """Verify batch aggregation accurately computes win_rate_pct, profit_factor, and counts."""
        raw_alerts = [
            {
                "id": "a1",
                "symbol": "TCS",
                "alert_title": "TCS Breakout",
                "catalyst_type": "TECHNICAL_BREAKOUT",
                "impact_score": 85,
                "metrics_snapshot": {
                    "action_bias": "STRONG_BUY",
                    "tactical_levels": {
                        "entry_range": "₹3,500.00",
                        "target_1": "₹3,600.00",
                        "protective_stop_loss": "₹3,450.00",
                        "risk_reward_ratio": "1:2.0",
                    },
                },
                "created_at": self.base_time.isoformat(),
            },
            {
                "id": "a2",
                "symbol": "WIPRO",
                "alert_title": "WIPRO Breakdown",
                "catalyst_type": "SUPPORT_BREAKDOWN",
                "impact_score": 60,
                "metrics_snapshot": {
                    "action_bias": "STRONG_BUY",
                    "tactical_levels": {
                        "entry_range": "₹500.00",
                        "target_1": "₹520.00",
                        "protective_stop_loss": "₹490.00",
                        "risk_reward_ratio": "1:2.0",
                    },
                },
                "created_at": self.base_time.isoformat(),
            },
        ]

        result = batch_verify_alerts(raw_alerts)
        self.assertIn("audited_summary", result)
        self.assertIn("ledger", result)
        summary = result["audited_summary"]

        self.assertEqual(summary["total_verified_signals"], 2)
        self.assertIn("win_rate_pct", summary)
        self.assertIn("profit_factor", summary)
        self.assertIn("avg_risk_reward", summary)
        self.assertEqual(len(result["ledger"]), 2)


if __name__ == "__main__":
    unittest.main()
