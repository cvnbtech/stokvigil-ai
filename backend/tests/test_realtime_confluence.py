import os
import sys
import unittest
from datetime import datetime, timezone
import pandas as pd
import numpy as np

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.engine.deterministic import (
    compute_deterministic_confluence,
    compute_tactical_levels,
)
from app.accuracy_verifier import verify_single_alert, batch_verify_alerts


class TestRealtimeConfluenceEngine(unittest.TestCase):
    def setUp(self):
        self.symbol = "TATAMOTORS"
        self.ltp = 950.0

    def test_dynamic_weight_renormalization_zero_phantom_points(self):
        """
        Verify that missing factors (flow, forensics, news) do NOT inject synthetic 50.0 neutral points.
        Active weights must be re-normalized dynamically over authentically available factors only.
        """
        # When technical_score is 70 and flow, forensics, news are all None
        result = compute_deterministic_confluence(
            symbol=self.symbol,
            technicals={
                "current_price": self.ltp,
                "technical_score": 70,
                "atr_14": 15.0,
                "change_pct": 0.5,
            },
            financials={"price": self.ltp},
            flow_data=None,
            forensics=None,
            news_items=None,
            macro_data={"india_vix": 14.0, "allow_breakout_trades": True},
        )

        score = result["confluence_score"]
        self.assertIsInstance(score, (int, float))
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)

        # When technical_score is 20 (weak) and other factors are missing:
        # Without dynamic re-normalization, 3 missing factors at 50.0 would have added 22.5 points,
        # elevating the score to ~45-50. With dynamic re-normalization, the weak score remains weak.
        res_weak = compute_deterministic_confluence(
            symbol=self.symbol,
            technicals={
                "current_price": self.ltp,
                "technical_score": 20,
                "atr_14": 15.0,
                "change_pct": -1.5,
            },
            financials={"price": self.ltp},
            flow_data=None,
            forensics=None,
            news_items=None,
            macro_data={"india_vix": 14.0, "allow_breakout_trades": True},
        )
        self.assertLess(res_weak["confluence_score"], 40)

    def test_zero_dummy_atr_and_missing_volatility(self):
        """
        Verify that if authentic ATR and daily range are missing, tactical_levels is None
        and no actionable signal is generated (never fallback to synthetic 2% or 1.5% ATR).
        """
        # compute_tactical_levels with atr_val=None and no high/low range
        tactical = compute_tactical_levels(
            current_price=self.ltp,
            atr_val=None,
            swing_high=None,
            demat_context=None,
            h3=None,
            h4=None,
            l3=None,
            l4=None,
            vwap_val=None,
            vwap_upper_1s=None,
            action_bias="BUY_WATCH",
        )
        self.assertIsNone(tactical, "compute_tactical_levels must return None when authentic volatility range is unavailable")

        # Confluence engine must refuse actionable signal when volatility is missing
        res = compute_deterministic_confluence(
            symbol=self.symbol,
            technicals={
                "current_price": self.ltp,
                "technical_score": 85,
                "atr_14": None,
                "day_high": None,
                "day_low": None,
                "orb_high_15m": None,
                "orb_low_15m": None,
                "change_pct": 2.0,
            },
            financials={"price": self.ltp},
            flow_data=None,
            forensics=None,
            news_items=None,
            macro_data={"india_vix": 14.0, "allow_breakout_trades": True},
        )
        self.assertIsNone(res["tactical_levels"])
        self.assertFalse(res["has_actionable_signal"])
        self.assertTrue(
            any("Authentic price volatility (ATR) unavailable" in d for d in res["confluence_drivers"]),
            "Must document why actionable signal was suspended"
        )

    def test_anchored_vwap_exhaustion_trap_detection(self):
        """
        Verify that when price is overextended > +2.0 sigma above VWAP and 15m RSI >= 76.0,
        a long breakout signal is blocked (BUY_WATCH downgraded to HOLD_NEUTRAL) and logged as an exhaustion trap.
        """
        res = compute_deterministic_confluence(
            symbol=self.symbol,
            technicals={
                "current_price": 965.0,
                "vwap": 920.0,
                "vwap_upper_2s": 945.0,  # Price 965 is well above VWAP +2s
                "rsi_15m": 79.5,         # RSI >= 76 (overbought exhaustion)
                "change_pct": 3.5,
                "atr_14": 14.0,
                "technical_score": 88,
                "macd_trend": "BULLISH_CROSSOVER",
                "is_volume_surge": True,
                "volume_multiple": 2.0,
            },
            financials={"price": 965.0},
            flow_data=None,
            forensics=None,
            news_items=None,
            macro_data={"india_vix": 14.0, "allow_breakout_trades": True},
        )

        # Action bias must NOT be BUY_WATCH due to exhaustion trap veto
        self.assertEqual(res["action_bias"], "HOLD_NEUTRAL")
        self.assertFalse(res["has_actionable_signal"])
        self.assertTrue(
            any("Exhaustion Trap Veto" in d for d in res["confluence_drivers"]),
            "Confluence drivers must contain Exhaustion Trap Veto"
        )

    def test_accuracy_verifier_zero_dummy_outcome(self):
        """
        Verify that accuracy verifier returns PENDING_CANDLE_DATA with 0.0 max gain when candles are absent.
        It must NEVER synthesize a fake TARGET_1_REACHED or 4.5% gain.
        """
        alert = {
            "id": "alert-zero-dummy",
            "symbol": "INFY",
            "alert_title": "INFY Breakout Test",
            "catalyst_type": "TECHNICAL_BREAKOUT",
            "impact_score": 85,
            "metrics_snapshot": {
                "action_bias": "STRONG_BUY",
                "tactical_levels": {
                    "entry_range": "₹1,800.00",
                    "target_1": "₹1,880.00",
                    "protective_stop_loss": "₹1,750.00",
                    "risk_reward_ratio": "1:2.5",
                },
            },
            "created_at": "2026-09-15T09:30:00+00:00",
        }

        # Test with None candles
        res_none = verify_single_alert(alert, candles_df=None)
        self.assertEqual(res_none["outcome"], "PENDING_CANDLE_DATA")
        self.assertEqual(res_none["max_gain_pct"], 0.0)
        self.assertEqual(res_none["verified_by"], "PENDING_MARKET_INGESTION")

        # Test with empty DataFrame
        res_empty = verify_single_alert(alert, candles_df=pd.DataFrame())
        self.assertEqual(res_empty["outcome"], "PENDING_CANDLE_DATA")
        self.assertEqual(res_empty["max_gain_pct"], 0.0)

    def test_accuracy_verifier_genuine_open_monitoring(self):
        """
        Verify that if price neither hit target nor stop loss, the outcome remains OPEN_MONITORING.
        It must NOT be artificially coerced into TARGET_1_REACHED just because price gained 1%.
        """
        alert_time = datetime(2026, 9, 15, 9, 30, tzinfo=timezone.utc)
        alert = {
            "id": "alert-open-mon",
            "symbol": "TCS",
            "alert_title": "TCS Breakout",
            "catalyst_type": "TECHNICAL_BREAKOUT",
            "impact_score": 80,
            "metrics_snapshot": {
                "action_bias": "STRONG_BUY",
                "tactical_levels": {
                    "entry_range": "₹3,500.00",
                    "target_1": "₹3,700.00",
                    "protective_stop_loss": "₹3,400.00",
                    "risk_reward_ratio": "1:2.0",
                },
            },
            "created_at": alert_time.isoformat(),
        }

        # Candle high reached 3,550 (+1.4% gain), but did NOT reach 3,700 target, and low 3,480 did not hit 3,400 SL
        df = pd.DataFrame(
            {
                "Open": [3500.0],
                "High": [3550.0],
                "Low": [3480.0],
                "Close": [3540.0],
                "Volume": [10000],
            },
            index=[alert_time + pd.Timedelta(hours=1)],
        )

        res = verify_single_alert(alert, candles_df=df)
        self.assertEqual(res["outcome"], "OPEN_MONITORING")
        self.assertAlmostEqual(res["max_gain_pct"], 1.4, places=1)
        self.assertEqual(res["verified_by"], "REAL_CANDLE_VERIFICATION")


if __name__ == "__main__":
    unittest.main()
