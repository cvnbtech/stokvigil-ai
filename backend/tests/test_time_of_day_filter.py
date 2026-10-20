import unittest
from datetime import datetime, timezone, timedelta
from app.engine.deterministic import compute_deterministic_confluence

IST = timezone(timedelta(hours=5, minutes=30))


class TestTimeOfDayAndBSEFilter(unittest.TestCase):
    """
    Unit test suite for the Time-of-Day Asymmetric Regime Filter (The 'Lunch-Hour Trap' Blocker).
    Validates institutional microstructure across both NSE and BSE equities:
    - 11:30 AM - 01:30 PM IST: Gating BUY_WATCH unless extraordinary institutional surge (RVOL >= 3.0x).
    - Unthrottled defense: Block Sells, Wyckoff Supply Dumps, and Circuit Freezes are NEVER vetoed.
    """

    def setUp(self):
        # Base bullish technical pack (CAM H4 breakout setup)
        self.base_bullish_tech = {
            "current_price": 2500.0,
            "change_pct": 2.2,
            "price_vs_vwap_pct": 1.1,
            "vwap": 2470.0,
            "ema_20": 2460.0,
            "ema_50": 2420.0,
            "ema_200": 2300.0,
            "is_above_200_ema": True,
            "rsi_15m": 64.0,
            "technical_score": 85,
            "volume_multiple": 1.8,
            "is_volume_surge": True,
            "atr_14": 25.0,
            "adx_14": 28.0,
            "adx_regime": "STRONG_TREND",
            "rs_rating": 3.5,
            "rs_regime": "OUTPERFORMING_LEADER",
            "camarilla_pivots": {"h4": 2490.0, "h3": 2475.0, "l3": 2425.0, "l4": 2410.0}
        }
        self.bullish_flow = {
            "flow_score": 82,
            "delivery_pct": 65.0,
            "is_high_delivery": True,
            "fo_oi_status": "LONG_BUILDUP",
            "flow_bias": "INSTITUTIONAL_ACCUMULATION",
            "pcr": 1.25,
            "max_pain_strike": 2500.0
        }
        self.bullish_macro = {
            "nifty_trend": "BULLISH",
            "nifty_change_pct": 0.65,
            "india_vix": 13.8,
            "allow_breakout_trades": True,
            "adr_ratio": 1.35
        }
        self.healthy_forensics = {
            "forensic_score": 85,
            "sector_name": "ENERGY",
            "red_flags": []
        }
        self.healthy_financials = {
            "price": 2500.0,
            "pe_ratio": 22.0,
            "debt_to_equity": 0.30
        }

    def test_01_morning_momentum_nse_buy_watch_allowed(self):
        """09:30 - 11:30 AM Morning Momentum: Normal breakout detection passes at RVOL 1.8x."""
        morning_time = datetime(2026, 10, 20, 10, 15, tzinfo=IST)
        res = compute_deterministic_confluence(
            symbol="RELIANCE.NS",
            technicals=self.base_bullish_tech,
            flow_data=self.bullish_flow,
            macro_data=self.bullish_macro,
            forensics=self.healthy_forensics,
            financials=self.healthy_financials,
            current_time_ist=morning_time
        )
        self.assertEqual(res["action_bias"], "BUY_WATCH")
        self.assertTrue(res["has_actionable_signal"])
        self.assertGreaterEqual(res["confluence_score"], 72)
        self.assertFalse(any("Lunch-Hour Trap Veto" in d for d in res["confluence_drivers"]))

    def test_02_lunch_lull_nse_buy_watch_vetoed_to_hold(self):
        """11:30 AM - 01:30 PM Lunch Lull: RVOL 1.8x (< 3.0x) is vetoed to HOLD_NEUTRAL on NSE."""
        lunch_time = datetime(2026, 10, 20, 12, 15, tzinfo=IST)
        res = compute_deterministic_confluence(
            symbol="RELIANCE.NS",
            technicals=self.base_bullish_tech,
            flow_data=self.bullish_flow,
            macro_data=self.bullish_macro,
            forensics=self.healthy_forensics,
            financials=self.healthy_financials,
            current_time_ist=lunch_time
        )
        self.assertEqual(res["action_bias"], "HOLD_NEUTRAL")
        self.assertFalse(res["has_actionable_signal"])
        self.assertLessEqual(res["confluence_score"], 58)
        self.assertTrue(any("Lunch-Hour Trap Veto" in d for d in res["confluence_drivers"]))

    def test_03_lunch_lull_nse_institutional_surge_overrides_veto(self):
        """11:30 AM - 01:30 PM Lunch Lull: Extraordinary surge (RVOL 3.4x >= 3.0x) permits BUY_WATCH."""
        lunch_time = datetime(2026, 10, 20, 12, 45, tzinfo=IST)
        tech_surge = dict(self.base_bullish_tech)
        tech_surge["volume_multiple"] = 3.4

        res = compute_deterministic_confluence(
            symbol="RELIANCE.NS",
            technicals=tech_surge,
            flow_data=self.bullish_flow,
            macro_data=self.bullish_macro,
            forensics=self.healthy_forensics,
            financials=self.healthy_financials,
            current_time_ist=lunch_time
        )
        self.assertEqual(res["action_bias"], "BUY_WATCH")
        self.assertTrue(res["has_actionable_signal"])
        self.assertTrue(any("Lunch-Hour Institutional Surge" in d for d in res["confluence_drivers"]))

    def test_04_lunch_lull_bse_buy_watch_vetoed_with_bse_warning(self):
        """11:30 AM - 01:30 PM Lunch Lull: BSE counter (.BO) is vetoed with BSE-specific warning."""
        lunch_time = datetime(2026, 10, 20, 12, 20, tzinfo=IST)
        res = compute_deterministic_confluence(
            symbol="500325.BO",
            technicals=self.base_bullish_tech,
            flow_data=self.bullish_flow,
            macro_data=self.bullish_macro,
            forensics=self.healthy_forensics,
            financials=self.healthy_financials,
            current_time_ist=lunch_time
        )
        self.assertEqual(res["action_bias"], "HOLD_NEUTRAL")
        self.assertFalse(res["has_actionable_signal"])
        self.assertTrue(any("BSE Lunch Lull Veto" in d for d in res["confluence_drivers"]))

    def test_05_lunch_lull_block_dump_demat_exit_never_vetoed(self):
        """11:30 AM - 01:30 PM Lunch Lull: Wyckoff Institutional Block Dump in Demat triggers immediate EXIT with ZERO veto."""
        lunch_time = datetime(2026, 10, 20, 12, 30, tzinfo=IST)
        dump_tech = {
            "current_price": 950.0,
            "change_pct": -1.8,
            "candle_5m_change_pct": -1.2,
            "price_vs_vwap_pct": -1.2,
            "vwap": 962.0,
            "volume_multiple": 2.5,
            "is_volume_surge": True,
            "close_location_pct": 0.18,  # Closed in lower 18% of candle (institutional dump)
            "ema_200": 920.0,
            "is_above_200_ema": True,
            "atr_14": 12.0,
            "camarilla_pivots": {"l4": 940.0}
        }
        res = compute_deterministic_confluence(
            symbol="TATAMOTORS",
            technicals=dump_tech,
            flow_data={"flow_score": 30},
            macro_data=self.bullish_macro,
            forensics=self.healthy_forensics,
            financials=self.healthy_financials,
            holding_info={"quantity": 100, "average_price": 980.0, "current_market_price": 950.0},
            current_time_ist=lunch_time
        )
        # Defense signal MUST be dispatched immediately regardless of lunch hour!
        self.assertEqual(res["action_bias"], "CAPITAL_PRESERVATION_EXIT")
        self.assertTrue(res["has_actionable_signal"])
        self.assertTrue(res["is_block_dump"])
        self.assertIn("BLOCK_DEAL", res["catalyst_category"])
        self.assertTrue(any("Portfolio Defense Override" in d for d in res["confluence_drivers"]))

    def test_06_lunch_lull_block_dump_bse_watchlist_triggers_sell_watch(self):
        """11:30 AM - 01:30 PM Lunch Lull: Wyckoff Block Dump on BSE Watchlist triggers SELL_WATCH (not MIS short)."""
        lunch_time = datetime(2026, 10, 20, 12, 35, tzinfo=IST)
        dump_tech_bse = {
            "current_price": 500.0,
            "change_pct": -2.0,
            "candle_5m_change_pct": -1.5,
            "price_vs_vwap_pct": -1.4,
            "vwap": 507.0,
            "volume_multiple": 2.8,
            "is_volume_surge": True,
            "close_location_pct": 0.20,
            "ema_200": 480.0,
            "is_above_200_ema": True,
            "atr_14": 8.0,
            "camarilla_pivots": {"l4": 495.0}
        }
        res = compute_deterministic_confluence(
            symbol="500209.BO",
            technicals=dump_tech_bse,
            flow_data={"fo_oi_status": "BSE_CASH_DELIVERY"},
            macro_data=self.bullish_macro,
            forensics=self.healthy_forensics,
            financials=self.healthy_financials,
            holding_info=None,
            current_time_ist=lunch_time
        )
        self.assertEqual(res["action_bias"], "SELL_WATCH")
        self.assertTrue(res["has_actionable_signal"])
        self.assertTrue(res["is_block_dump"])
        self.assertTrue(any("BSE Cash Market: Delivery liquidation" in d for d in res["confluence_drivers"]))

    def test_07_lunch_lull_lower_circuit_lock_bse_immediate_sell(self):
        """11:30 AM - 01:30 PM Lunch Lull: Lower Circuit Lock triggers immediate SELL_WATCH."""
        lunch_time = datetime(2026, 10, 20, 11, 45, tzinfo=IST)
        circuit_tech = {
            "current_price": 120.0,
            "change_pct": -5.0,
            "is_circuit_locked": True,
            "circuit_lock_type": "LOWER_CIRCUIT",
            "atr_14": 4.0
        }
        res = compute_deterministic_confluence(
            symbol="532540.BO",
            technicals=circuit_tech,
            flow_data=None,
            macro_data=self.bullish_macro,
            forensics=None,
            financials={"price": 120.0},
            holding_info=None,
            current_time_ist=lunch_time
        )
        self.assertEqual(res["action_bias"], "SELL_WATCH")
        self.assertTrue(res["has_actionable_signal"])
        self.assertTrue(any("Circuit Lock Warning" in d for d in res["confluence_drivers"]))

    def test_08_closing_rush_breakouts_re_enabled(self):
        """01:30 - 03:15 PM Closing Rush: Normal breakout detection is fully re-enabled."""
        closing_time = datetime(2026, 10, 20, 14, 15, tzinfo=IST)
        res = compute_deterministic_confluence(
            symbol="RELIANCE.NS",
            technicals=self.base_bullish_tech,
            flow_data=self.bullish_flow,
            macro_data=self.bullish_macro,
            forensics=self.healthy_forensics,
            financials=self.healthy_financials,
            current_time_ist=closing_time
        )
        self.assertEqual(res["action_bias"], "BUY_WATCH")
        self.assertTrue(res["has_actionable_signal"])
        self.assertFalse(any("Lunch-Hour Trap Veto" in d for d in res["confluence_drivers"]))


if __name__ == "__main__":
    unittest.main()
