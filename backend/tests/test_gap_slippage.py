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

from app.accuracy_verifier import (
    verify_single_alert,
    batch_verify_alerts,
)


class TestOvernightGapSlippage(unittest.TestCase):
    def setUp(self):
        self.base_time = datetime(2026, 9, 10, 9, 30, tzinfo=timezone.utc)

    def test_long_gap_down_past_stop_loss(self):
        """
        Verify that when a long position gaps down below the stop loss at open,
        the fill is modeled at bar_open (not the theoretical stop loss price),
        detecting gap slippage with realized_r > 1.0.
        """
        alert = {
            "id": "alert-long-gap-down",
            "symbol": "TATASTEEL",
            "alert_title": "TATASTEEL Breakout",
            "catalyst_type": "TECHNICAL_BREAKOUT",
            "metrics_snapshot": {
                "action_bias": "STRONG_BUY",
                "tactical_levels": {
                    "entry_range": "₹1,000.00",
                    "target_1": "₹1,060.00",
                    "protective_stop_loss": "₹970.00",  # 30 pts nominal risk
                    "risk_reward_ratio": "1:2.0",
                },
            },
            "created_at": self.base_time.isoformat(),
        }

        # Day 1: normal trading, Day 2: gaps down to 940 (30 pts below SL 970)
        times = [
            self.base_time + timedelta(hours=1),
            self.base_time + timedelta(days=1),
        ]
        df = pd.DataFrame(
            {
                "Open": [1000.0, 940.0],   # Open at 940 (< 970 SL)
                "High": [1010.0, 945.0],
                "Low": [990.0, 930.0],
                "Close": [995.0, 935.0],
                "Volume": [10000, 25000],
            },
            index=times,
        )

        res = verify_single_alert(alert, candles_df=df)
        self.assertEqual(res["outcome"], "STOP_LOSS_DEFENDED")
        self.assertEqual(res["exit_price"], 940.0)
        self.assertTrue(res["gap_slippage_detected"])
        # nominal risk = 1000 - 970 = 30. Loss = 1000 - 940 = 60 -> realized_r = 60 / 30 = 2.0R
        self.assertEqual(res["realized_r"], 2.0)
        # slippage_drag_pct = (970 - 940) / 1000 * 100 = 3.0%
        self.assertEqual(res["slippage_drag_pct"], 3.0)

    def test_long_gap_up_past_target(self):
        """
        Verify that when a long position gaps up past target 1 at open,
        the exit is captured at bar_open, awarding favorable slippage with realized_r > nominal RR.
        """
        alert = {
            "id": "alert-long-gap-up",
            "symbol": "INFY",
            "alert_title": "INFY Earnings Gap",
            "catalyst_type": "EARNINGS_SURPRISE",
            "metrics_snapshot": {
                "action_bias": "BUY",
                "tactical_levels": {
                    "entry_range": "₹1,500.00",
                    "target_1": "₹1,560.00",  # 60 pts target
                    "protective_stop_loss": "₹1,470.00",  # 30 pts risk
                    "risk_reward_ratio": "1:2.0",
                },
            },
            "created_at": self.base_time.isoformat(),
        }

        times = [
            self.base_time + timedelta(hours=1),
            self.base_time + timedelta(days=1),
        ]
        df = pd.DataFrame(
            {
                "Open": [1500.0, 1600.0],  # Gaps open at 1600 (> 1560 target)
                "High": [1515.0, 1610.0],
                "Low": [1495.0, 1590.0],
                "Close": [1510.0, 1605.0],
                "Volume": [20000, 50000],
            },
            index=times,
        )

        res = verify_single_alert(alert, candles_df=df)
        self.assertEqual(res["outcome"], "TARGET_1_REACHED")
        self.assertEqual(res["exit_price"], 1600.0)
        self.assertTrue(res["gap_slippage_detected"])
        # nominal risk = 1500 - 1470 = 30. Gain = 1600 - 1500 = 100 -> realized_r = 100 / 30 = 3.33R
        self.assertEqual(res["realized_r"], 3.33)
        # slippage_drag_pct = (1600 - 1560) / 1500 * 100 = 2.67%
        self.assertEqual(res["slippage_drag_pct"], 2.67)

    def test_long_normal_intraday_breach_no_gap(self):
        """
        Verify that when a stop loss is touched during intraday trading without an opening gap,
        exit is filled exactly at the stop loss price (1.0R loss).
        """
        alert = {
            "id": "alert-long-normal-sl",
            "symbol": "RELIANCE",
            "alert_title": "RELIANCE Reversal",
            "catalyst_type": "MOMENTUM_EXPANSION",
            "metrics_snapshot": {
                "action_bias": "BUY",
                "tactical_levels": {
                    "entry_range": "₹2,500.00",
                    "target_1": "₹2,600.00",
                    "protective_stop_loss": "₹2,450.00",  # 50 pts risk
                    "risk_reward_ratio": "1:2.0",
                },
            },
            "created_at": self.base_time.isoformat(),
        }

        times = [
            self.base_time + timedelta(hours=1),
        ]
        df = pd.DataFrame(
            {
                "Open": [2490.0],  # Open is above SL 2450
                "High": [2510.0],
                "Low": [2440.0],   # Intraday wick touches through 2450
                "Close": [2445.0],
                "Volume": [15000],
            },
            index=times,
        )

        res = verify_single_alert(alert, candles_df=df)
        self.assertEqual(res["outcome"], "STOP_LOSS_DEFENDED")
        self.assertEqual(res["exit_price"], 2450.0)
        self.assertFalse(res["gap_slippage_detected"])
        self.assertEqual(res["realized_r"], 1.0)
        self.assertEqual(res["slippage_drag_pct"], 0.0)

    def test_bearish_short_gap_up_past_stop_loss(self):
        """
        Verify that for short trades, opening gaps above the stop loss are filled at bar_open,
        producing realized_r > 1.0 and slippage detection.
        """
        alert = {
            "id": "alert-short-gap-up-sl",
            "symbol": "HDFCBANK",
            "alert_title": "HDFCBANK Breakdown",
            "catalyst_type": "LIQUIDITY_HUNT",
            "metrics_snapshot": {
                "action_bias": "SELL",
                "tactical_levels": {
                    "entry_range": "₹1,600.00",
                    "target_1": "₹1,540.00",
                    "protective_stop_loss": "₹1,630.00",  # 30 pts risk
                    "risk_reward_ratio": "1:2.0",
                },
            },
            "created_at": self.base_time.isoformat(),
        }

        times = [
            self.base_time + timedelta(hours=1),
            self.base_time + timedelta(days=1),
        ]
        df = pd.DataFrame(
            {
                "Open": [1600.0, 1660.0],  # Gaps up to 1660 (> 1630 SL)
                "High": [1605.0, 1665.0],
                "Low": [1590.0, 1655.0],
                "Close": [1595.0, 1660.0],
                "Volume": [10000, 30000],
            },
            index=times,
        )

        res = verify_single_alert(alert, candles_df=df)
        self.assertEqual(res["outcome"], "STOP_LOSS_DEFENDED")
        self.assertEqual(res["exit_price"], 1660.0)
        self.assertTrue(res["gap_slippage_detected"])
        # nominal risk = 1630 - 1600 = 30. Loss = 1660 - 1600 = 60 -> realized_r = 60 / 30 = 2.0R
        self.assertEqual(res["realized_r"], 2.0)
        # slippage_drag_pct = (1660 - 1630) / 1600 * 100 = 1.88%
        self.assertEqual(res["slippage_drag_pct"], 1.88)

    def test_batch_verify_slippage_kpis(self):
        """
        Verify that batch_verify_alerts aggregates slippage events, computes average gap slippage,
        and factors realized R-multiples into gross losses and profit factor.
        """
        alert1 = {
            "id": "alert-batch-1",
            "symbol": "TATASTEEL",
            "alert_title": "TATASTEEL Breakout",
            "catalyst_type": "TECHNICAL_BREAKOUT",
            "metrics_snapshot": {
                "action_bias": "STRONG_BUY",
                "tactical_levels": {
                    "entry_range": "₹1,000.00",
                    "target_1": "₹1,060.00",
                    "protective_stop_loss": "₹970.00",
                    "risk_reward_ratio": "1:2.0",
                },
            },
            "created_at": self.base_time.isoformat(),
        }
        alert2 = {
            "id": "alert-batch-2",
            "symbol": "INFY",
            "alert_title": "INFY Rally",
            "catalyst_type": "TECHNICAL_BREAKOUT",
            "metrics_snapshot": {
                "action_bias": "BUY",
                "tactical_levels": {
                    "entry_range": "₹1,000.00",
                    "target_1": "₹1,060.00",
                    "protective_stop_loss": "₹970.00",
                    "risk_reward_ratio": "1:2.0",
                },
            },
            "created_at": self.base_time.isoformat(),
        }

        # Provide pre-built candles through monkeypatch or direct candle mapping
        # Since batch_verify_alerts fetches symbols via yfinance unless mocked, let's test via direct verify_single_alert aggregation logic
        # Or mock fetch_historical_candles_batch
        times = [
            self.base_time + timedelta(hours=1),
            self.base_time + timedelta(days=1),
        ]
        df_gap_sl = pd.DataFrame(
            {"Open": [1000.0, 940.0], "High": [1005.0, 945.0], "Low": [995.0, 930.0], "Close": [1000.0, 935.0]},
            index=times,
        )
        df_target = pd.DataFrame(
            {"Open": [1000.0, 1020.0], "High": [1010.0, 1070.0], "Low": [995.0, 1015.0], "Close": [1005.0, 1065.0]},
            index=times,
        )

        result = batch_verify_alerts(
            [alert1, alert2],
            preloaded_candles={
                "TATASTEEL": df_gap_sl,
                "INFY": df_target,
            }
        )

        summary = result["audited_summary"]
        self.assertEqual(summary["total_verified_signals"], 2)
        self.assertEqual(summary["win_rate_pct"], 50.0)
        self.assertEqual(summary["slippage_events_count"], 1)
        self.assertEqual(summary["avg_gap_slippage_pct"], "3.0%")
        # Gross profits: INFY nominal RR = 2.0. Gross losses: TATASTEEL realized_r = 2.0. Profit factor = 2.0 / 2.0 = 1.0
        self.assertEqual(summary["profit_factor"], 1.0)


if __name__ == "__main__":
    unittest.main()
