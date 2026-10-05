import os
import sys
import unittest
from datetime import datetime, timezone, timedelta
import pandas as pd

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.engine.deterministic import compute_tactical_levels
from app.accuracy_verifier import verify_single_alert, batch_verify_alerts


class TestAtrBuffersAndTrailingStops(unittest.TestCase):
    def setUp(self):
        self.base_time = datetime(2026, 9, 10, 9, 30, tzinfo=timezone.utc)

    def test_standard_vs_high_beta_regime_detection(self):
        """
        Verify that compute_tactical_levels dynamically identifies HIGH_BETA_EVENT
        when India VIX >= 18, stock beta >= 1.25, or Intraday Expansion Ratio >= 1.25.
        """
        # 1. Standard Day: VIX 14.0, Beta 1.0, Range = 20 (ATR = 25 -> IER = 0.8)
        std = compute_tactical_levels(
            current_price=1000.0,
            atr_val=25.0,
            h3=1010.0,
            h4=1020.0,
            l3=990.0,
            l4=980.0,
            action_bias="BUY",
            india_vix=14.0,
            stock_beta=1.0,
            day_high=1010.0,
            day_low=990.0
        )
        self.assertIsNotNone(std)
        self.assertEqual(std["volatility_regime"], "STANDARD_CAMARILLA")
        self.assertFalse(std["is_high_beta_event"])
        # Standard buffer: 0.10 * 25.0 = 2.5
        self.assertEqual(std["buffered_breakout_level"], "₹1,022.50")
        self.assertEqual(std["buffered_breakdown_level"], "₹977.50")
        # Standard trailing multiplier: 1.5x ATR
        self.assertIn("1.5x ATR Standard Trailing Ratchet", std["trailing_stop_rule"])

        # 2. High-Beta Event Day: VIX 19.5 (surpassed 18.0 threshold)
        hb_vix = compute_tactical_levels(
            current_price=1000.0,
            atr_val=25.0,
            h3=1010.0,
            h4=1020.0,
            l3=990.0,
            l4=980.0,
            action_bias="BUY",
            india_vix=19.5,
            stock_beta=1.0,
            day_high=1010.0,
            day_low=990.0
        )
        self.assertIsNotNone(hb_vix)
        self.assertEqual(hb_vix["volatility_regime"], "HIGH_BETA_EVENT")
        self.assertTrue(hb_vix["is_high_beta_event"])
        # High-Beta buffer: 0.25 * 25.0 = 6.25
        self.assertEqual(hb_vix["buffered_breakout_level"], "₹1,026.25")
        self.assertEqual(hb_vix["buffered_breakdown_level"], "₹973.75")
        # Event trailing multiplier: 2.0x ATR
        self.assertIn("2.0x ATR High-Beta Event Trailing Ratchet", hb_vix["trailing_stop_rule"])

        # 3. High Intraday Expansion Ratio: Day Range = 40 with ATR = 25 (IER = 1.6 >= 1.25)
        hb_ier = compute_tactical_levels(
            current_price=1000.0,
            atr_val=25.0,
            h3=1010.0,
            h4=1020.0,
            l3=990.0,
            l4=980.0,
            action_bias="BUY",
            india_vix=13.0,
            stock_beta=0.9,
            day_high=1030.0,
            day_low=990.0
        )
        self.assertIsNotNone(hb_ier)
        self.assertEqual(hb_ier["volatility_regime"], "HIGH_BETA_EVENT")
        self.assertTrue(hb_ier["is_high_beta_event"])

    def test_dynamic_trailing_ratchet_long_and_short(self):
        """
        Verify that Chandelier trailing stop ratchets upward as day_high advances
        and never loosens below the initial protective stop loss.
        """
        # Long trade (Standard regime: IER = (1040 - 1025) / 20 = 0.75 < 1.25, VIX 14 < 18):
        # price 1035, initial SL 980 (risk 20), ATR 20
        # If day_high reaches 1040 (+2.0R):
        # Trail (standard 1.5x ATR = 30) = 1040 - 30 = 1010 (locking in +10 pts profit!)
        tactical_long = compute_tactical_levels(
            current_price=1035.0,
            atr_val=20.0,
            h3=1010.0,
            h4=1020.0,
            l3=990.0,
            l4=980.0,
            action_bias="BUY",
            day_high=1040.0,
            day_low=1025.0,
            india_vix=14.0
        )
        self.assertIsNotNone(tactical_long)
        self.assertEqual(tactical_long["atr_trailing_stop"], "₹1,010.00")
        self.assertEqual(tactical_long["volatility_regime"], "STANDARD_CAMARILLA")

        # Long trade (High-Beta regime: IER = (1040 - 995) / 20 = 2.25 >= 1.25):
        # Trail (high-beta 2.0x ATR = 40) = 1040 - 40 = 1000
        tactical_long_hb = compute_tactical_levels(
            current_price=1035.0,
            atr_val=20.0,
            h3=1010.0,
            h4=1020.0,
            l3=990.0,
            l4=980.0,
            action_bias="BUY",
            day_high=1040.0,
            day_low=995.0,
            india_vix=19.0
        )
        self.assertEqual(tactical_long_hb["atr_trailing_stop"], "₹1,000.00")
        self.assertEqual(tactical_long_hb["volatility_regime"], "HIGH_BETA_EVENT")

        # Short trade (Standard regime: IER = (975 - 960) / 20 = 0.75 < 1.25, VIX 14 < 18):
        # price 965, initial SL 1020 (risk 20), ATR 20
        # If day_low reaches 950 (+2.0R downside):
        # Trail (standard 1.5x ATR = 30) = 950 + 30 = 980 (locking below initial 985 SL!)
        tactical_short = compute_tactical_levels(
            current_price=965.0,
            atr_val=20.0,
            h3=1010.0,
            h4=1020.0,
            l3=990.0,
            l4=980.0,
            action_bias="SELL_WATCH",
            day_high=968.0,
            day_low=950.0,
            india_vix=14.0
        )
        self.assertIsNotNone(tactical_short)
        self.assertEqual(tactical_short["atr_trailing_stop"], "₹980.00")
        self.assertEqual(tactical_short["volatility_regime"], "STANDARD_CAMARILLA")

    def test_accuracy_verifier_trailing_sl_locked_profit(self):
        """
        Verify that an alert that gains >= 1.0R and subsequently reverses
        exits via TRAILING_SL_LOCKED_PROFIT with positive realized R-multiple,
        rather than suffering a full initial stop-loss breach.
        """
        alert = {
            "id": "alert-trailing-lock",
            "symbol": "BAJFINANCE",
            "alert_title": "BAJFINANCE High-Beta Rally",
            "catalyst_type": "TECHNICAL_BREAKOUT",
            "is_high_beta_event": False,
            "metrics_snapshot": {
                "action_bias": "STRONG_BUY",
                "tactical_levels": {
                    "entry_range": "₹1,000.00",
                    "target_1": "₹1,060.00",  # 60 pts target (3.0R)
                    "protective_stop_loss": "₹980.00",  # 20 pts risk (1.0R)
                    "risk_reward_ratio": "1:3.0",
                },
            },
            "created_at": self.base_time.isoformat(),
        }

        # Day 1: Price rallies from 1000 to 1035 (+1.75R)
        # Trailing Ratchet: activates since peak (1035) >= 1000 + 20 = 1020
        # Ratchet = 1035 - (1.5 * 20) = 1035 - 30 = 1005 (above entry!)
        # Day 2: Price pulls back to 1000, touching active trailing SL 1005
        times = [
            self.base_time + timedelta(hours=1),
            self.base_time + timedelta(hours=2),
        ]
        df = pd.DataFrame(
            {
                "Open": [1000.0, 1025.0],
                "High": [1035.0, 1030.0],
                "Low": [995.0, 1000.0],   # Bar 2 low 1000 < active trailing SL 1005
                "Close": [1025.0, 1002.0],
                "Volume": [10000, 20000],
            },
            index=times,
        )

        res = verify_single_alert(alert, candles_df=df)
        self.assertEqual(res["outcome"], "TRAILING_SL_LOCKED_PROFIT")
        self.assertEqual(res["exit_price"], 1005.0)
        # Gain: 1005 - 1000 = 5 pts. Nominal risk = 20 pts. Realized R = 5 / 20 = +0.25R
        self.assertGreater(res["realized_r"], 0.0)
        self.assertEqual(res["realized_r"], 0.25)

    def test_batch_verify_includes_trailing_kpis(self):
        """
        Verify that batch_verify_alerts aggregates trailing_sl_locked_count and includes
        trailing stop gains in overall win_rate and gross_profits.
        """
        alert1 = {
            "id": "alert-batch-trail-1",
            "symbol": "TCS",
            "alert_title": "TCS Breakout",
            "catalyst_type": "TECHNICAL_BREAKOUT",
            "metrics_snapshot": {
                "action_bias": "STRONG_BUY",
                "tactical_levels": {
                    "entry_range": "₹1,000.00",
                    "target_1": "₹1,060.00",
                    "protective_stop_loss": "₹980.00",
                    "risk_reward_ratio": "1:3.0",
                },
            },
            "created_at": self.base_time.isoformat(),
        }

        times = [
            self.base_time + timedelta(hours=1),
            self.base_time + timedelta(hours=2),
        ]
        df_trail = pd.DataFrame(
            {
                "Open": [1000.0, 1025.0],
                "High": [1035.0, 1030.0],
                "Low": [995.0, 1000.0],
                "Close": [1025.0, 1002.0],
            },
            index=times,
        )

        result = batch_verify_alerts(
            [alert1],
            preloaded_candles={"TCS": df_trail}
        )

        summary = result["audited_summary"]
        self.assertEqual(summary["total_verified_signals"], 1)
        self.assertEqual(summary["trailing_sl_locked_count"], 1)
        self.assertEqual(summary["target_1_hits_count"], 0)
        self.assertEqual(summary["stopped_out_count"], 0)
        # Trailing stop locked in profit -> counted as win
        self.assertEqual(summary["win_rate_pct"], 100.0)


if __name__ == "__main__":
    unittest.main()
