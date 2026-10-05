import os
import sys
import unittest
from datetime import date
from unittest.mock import patch, MagicMock
import pandas as pd
import pytest

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ["ENVIRONMENT"] = "test"
os.environ["ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="

from app.engine.deterministic import compute_deterministic_confluence
from app.technical_engine import _calculate_rolling_multiday_stats, compute_technicals_from_frames
from app.agent_runner import (
    evaluate_and_dispatch_macro_risk_alert,
    _MACRO_CRASH_DISPATCHED_DATE,
    _MACRO_LAST_DISPATCHED_VIX,
)
import app.agent_runner as ar


class TestAlgorithmicBiasAndDrawdown(unittest.IsolatedAsyncioTestCase):
    """
    Test suite verifying fixes for:
    1. Forensic Decoupling: Pristine balance sheets do NOT buoy a falling stock into HOLD_NEUTRAL.
    2. Rolling Multi-Day Drawdown: Catches multi-session market liquidations (-4% over 3 days below 20 EMA).
    3. 200 EMA Bull Trend Veto Bypass on Multi-Day Drawdowns.
    4. CAPITAL_DEFENSE_MODE: Real-time systemic alert when India VIX > 16.5 and ADR < 0.70.
    5. Strict Zero-Default Policy: Operates strictly on authentic data; returns None on insufficient bars.
    """

    def setUp(self):
        # Reset state latch before each test
        ar._MACRO_CRASH_DISPATCHED_DATE = None
        ar._MACRO_LAST_DISPATCHED_VIX = 0.0
        ar._MACRO_LAST_DISPATCHED_NIFTY = 0.0

    def test_forensics_decoupled_from_intraday_direction_bluechip(self):
        """
        Verify that a blue-chip stock with exceptional fundamentals (Zero debt, high margins)
        is forced to SELL_WATCH when its technical score is low (<= 40),
        and confluence score is capped at <= 35, eliminating the HOLD_NEUTRAL buoy trap.
        """
        technicals = {
            "current_price": 2800.0,
            "change_pct": -1.8,
            "technical_score": 25,  # Weak price momentum / breakdown
            "vwap": 2840.0,
            "price_vs_vwap_pct": -1.4,
            "rsi_15m": 34.0,
            "camarilla_pivots": {"l4": 2750.0, "h4": 2880.0},
        }
        flow_data = {
            "delivery_pct": 35.0,
            "flow_score": 30,
            "vsa_regime": "NORMAL_VOLUME_SPREAD",
        }
        # Exceptional corporate fundamentals (Forensics score ~ 90)
        forensics = {
            "debt_to_equity": 0.05,
            "pe_ratio": 22.0,
            "profit_margin_pct": 28.0,
            "forensic_score": 92,
        }
        financials = {
            "debt_to_equity": 0.05,
            "pe_ratio": 22.0,
            "profit_margin_pct": 28.0,
            "price": 2800.0,
        }
        macro_data = {"india_vix": 17.5, "adr_ratio": 0.65, "allow_breakout_trades": True}

        res = compute_deterministic_confluence(
            symbol="TCS",
            technicals=technicals,
            flow_data=flow_data,
            macro_data=macro_data,
            forensics=forensics,
            financials=financials,
        )

        # directional_score = (25 * 0.60) + (30 * 0.40) = 15 + 12 = 27 (<= 40)
        self.assertEqual(res["action_bias"], "SELL_WATCH")
        self.assertTrue(res["has_actionable_signal"])
        self.assertLessEqual(res["confluence_score"], 35)
        # Verify reason was added
        self.assertTrue(any("Directional Breakdown" in d for d in res["confluence_drivers"]))

    def test_multi_day_drawdown_detection_grinding_bleed(self):
        """
        Verify that a stock experiencing a multi-day grinding bleed (-4.5% over 3 days below 20 EMA)
        triggers a breakdown alert even if today's change is only -0.8% (which would fail single-day -3.5% shock).
        """
        technicals = {
            "current_price": 1450.0,
            "change_pct": -0.8,  # Minor daily drop - fails single-day -3.5% threshold!
            "rolling_3d_change_pct": -4.5,  # 3-day cumulative liquidation
            "rolling_5d_change_pct": -5.8,
            "consecutive_below_ema20": True,
            "technical_score": 35,
            "camarilla_pivots": {"l4": 1420.0, "h4": 1500.0},
        }
        res = compute_deterministic_confluence(
            symbol="HDFCBANK",
            technicals=technicals,
            flow_data={"flow_score": 40},
            macro_data={"india_vix": 17.0, "adr_ratio": 0.62},
            forensics={"forensic_score": 85},
            financials={"price": 1450.0},
        )

        self.assertEqual(res["action_bias"], "SELL_WATCH")
        self.assertTrue(res["has_actionable_signal"])
        self.assertLessEqual(res["confluence_score"], 25)
        self.assertIn("Multi-Day Downtrend Breakdown", res["alert_title"])
        self.assertTrue(any("3-Day Cumulative Loss" in d for d in res["confluence_drivers"]))

    def test_multi_day_drawdown_portfolio_exit_demat(self):
        """
        Verify that for Demat portfolio positions, multi-day drawdown triggers CAPITAL_PRESERVATION_EXIT.
        """
        technicals = {
            "current_price": 950.0,
            "change_pct": -0.6,
            "rolling_3d_change_pct": -4.2,
            "consecutive_below_ema20": True,
            "technical_score": 32,
        }
        holding_info = {
            "symbol": "INFY",
            "average_price": 995.0,
            "quantity": 50,
            "unrealized_pnl_pct": -4.52,
        }
        res = compute_deterministic_confluence(
            symbol="INFY",
            technicals=technicals,
            flow_data={},
            macro_data={"india_vix": 16.8, "adr_ratio": 0.68},
            forensics={},
            financials={"price": 950.0},
            holding_info=holding_info,
        )

        self.assertEqual(res["action_bias"], "CAPITAL_PRESERVATION_EXIT")
        self.assertTrue(res["has_actionable_signal"])
        self.assertLessEqual(res["confluence_score"], 20)

    def test_200_ema_uptrend_veto_bypassed_on_multiday_breakdown(self):
        """
        Verify that a stock trading above its 200 EMA (macro bull trend) is NOT vetoed into
        HOLD_NEUTRAL when a multi-day drawdown or directional breakdown is active.
        """
        technicals = {
            "current_price": 1200.0,
            "ema_200": 1100.0,  # Macro uptrend active (price > 200 EMA)
            "change_pct": -1.2,
            "rolling_3d_change_pct": -4.6,
            "consecutive_below_ema20": True,
            "technical_score": 30,
            "atr_14": 22.0,
        }
        res = compute_deterministic_confluence(
            symbol="RELIANCE",
            technicals=technicals,
            flow_data={"flow_score": 35},
            macro_data={"india_vix": 18.0, "adr_ratio": 0.58},
            forensics={"forensic_score": 88},
            financials={"price": 1200.0},
        )

        # Must NOT be vetoed to HOLD_NEUTRAL!
        self.assertEqual(res["action_bias"], "SELL_WATCH")
        self.assertTrue(res["has_actionable_signal"])
        self.assertTrue(any("Supply Shock Override" in d for d in res["confluence_drivers"]))

    @patch("app.agent_runner.send_fcm_notification")
    @patch("app.agent_runner.send_telegram_notification")
    async def test_capital_defense_mode_macro_broadcast(self, mock_tg, mock_fcm):
        """
        Verify that evaluate_and_dispatch_macro_risk_alert fires CAPITAL_DEFENSE_MODE
        when India VIX > 16.5 and Market Breadth ADR < 0.70.
        """
        mock_fcm.return_value = True
        mock_tg.return_value = True

        mock_supabase = MagicMock()
        mock_supabase.table().select().execute.return_value.data = [
            {"id": "usr-1", "fcm_device_token": "token-1", "telegram_chat_id": "12345", "telegram_enabled": True}
        ]

        macro_data = {
            "nifty_change_pct": -0.65,
            "india_vix": 17.8,  # > 16.5
            "adr_ratio": 0.42,  # < 0.70
            "advances": 380,
            "declines": 1720,
        }

        with patch("app.db_pool.fetch_all", return_value=None):
            fired = await evaluate_and_dispatch_macro_risk_alert(macro_data, mock_supabase)

        self.assertTrue(fired)
        mock_fcm.assert_called_once()
        fcm_call_args = mock_fcm.call_args[0]
        self.assertIn("CAPITAL DEFENSE MODE", fcm_call_args[1])
        self.assertIn("82% of stocks are declining", fcm_call_args[2])

        mock_tg.assert_called_once()
        tg_call_args = mock_tg.call_args[0]
        self.assertIn("CAPITAL DEFENSE MODE", tg_call_args[1])
        self.assertIn("82% of stocks are declining", tg_call_args[1])

    async def test_zero_default_policy_macro_alert_skipped_when_data_missing(self):
        """
        Strict Zero-Default Policy: If VIX and Nifty change are unavailable (None),
        evaluate_and_dispatch_macro_risk_alert must NOT fire synthetic alerts.
        """
        mock_supabase = MagicMock()
        macro_data = {
            "nifty_change_pct": None,
            "india_vix": None,
            "adr_ratio": None,
        }
        fired = await evaluate_and_dispatch_macro_risk_alert(macro_data, mock_supabase)
        self.assertFalse(fired)

    def test_calculate_rolling_multiday_stats_insufficient_data(self):
        """
        Verify that _calculate_rolling_multiday_stats returns (None, None, False)
        when daily candle history is insufficient, adhering to the Zero-Default Policy.
        """
        short_df = pd.DataFrame({"Close": [100.0, 102.0]})
        r_3d, r_5d, below_ema = _calculate_rolling_multiday_stats(short_df, 101.0)
        self.assertIsNone(r_3d)
        self.assertIsNone(r_5d)
        self.assertFalse(below_ema)


if __name__ == "__main__":
    unittest.main()
