"""
Unit Tests for Forward Corporate Earnings & Event Lockout Calendar
Dual-Exchange (NSE & BSE) Compliant with Zero-Default Policy.
"""
import unittest
from datetime import date, timedelta

from app.corporate_calendar import (
    register_upcoming_corporate_event,
    check_corporate_event_risk,
    _CORPORATE_EVENTS_REGISTRY
)
from app.engine.deterministic import compute_deterministic_confluence


class TestCorporateEarningsLockout(unittest.TestCase):

    def setUp(self):
        _CORPORATE_EVENTS_REGISTRY.clear()

    def test_zero_default_on_unregistered_symbol(self):
        """Zero-Default Policy: Returns clean unpopulated event risk when no event exists."""
        res = check_corporate_event_risk("RANDOM_STOCK.NS")
        self.assertFalse(res["has_imminent_event_risk"])
        self.assertIsNone(res["days_to_earnings"])
        self.assertIsNone(res["event_date"])
        self.assertFalse(res["lockout_active"])

    def test_imminent_event_detection_within_48h(self):
        """Verifies that an event scheduled tomorrow or in 2 days triggers imminent event risk."""
        today = date(2026, 11, 22)
        event_day = today + timedelta(days=1) # Tomorrow

        register_upcoming_corporate_event(
            symbol="INFY",
            event_date=event_day,
            event_type="QUARTERLY_RESULTS",
            description="Board Meeting to consider Q3 Financial Results"
        )

        res = check_corporate_event_risk("INFY.NS", current_date=today)
        self.assertTrue(res["has_imminent_event_risk"])
        self.assertEqual(res["days_to_earnings"], 1)
        self.assertTrue(res["lockout_active"])
        self.assertIn("Q3 Financial Results", res["event_description"])

    def test_far_event_does_not_lock_trading(self):
        """Events scheduled 10 days out must not trigger lockout."""
        today = date(2026, 11, 22)
        far_event = today + timedelta(days=10)

        register_upcoming_corporate_event(
            symbol="TCS",
            event_date=far_event,
            event_type="QUARTERLY_RESULTS"
        )

        res = check_corporate_event_risk("TCS.BO", current_date=today)
        self.assertFalse(res["has_imminent_event_risk"])
        self.assertEqual(res["days_to_earnings"], 10)
        self.assertFalse(res["lockout_active"])

    def test_earnings_lockout_vetoes_breakout_buy(self):
        """When earnings are imminent (within 48h), BUY_WATCH is vetoed to HOLD_NEUTRAL."""
        today = date.today()
        register_upcoming_corporate_event(
            symbol="RELIANCE",
            event_date=today + timedelta(days=1), # Tomorrow
            event_type="QUARTERLY_RESULTS",
            description="Q3 FY26 Earnings Declaration"
        )

        technicals = {
            "current_price": 2500.0,
            "technical_score": 85,
            "rsi_15m": 60.0,
            "rsi_daily": 58.0,
            "ema_50": 2400.0,
            "ema_200": 2300.0,
            "vwap": 2490.0,
            "atr_14": 30.0,
            "camarilla_pivots": {"h4": 2495.0, "h3": 2470.0, "l3": 2430.0, "l4": 2410.0}
        }
        res = compute_deterministic_confluence(
            symbol="RELIANCE.NS",
            technicals=technicals,
            flow_data={"delivery_pct": 60.0},
            macro_data={"allow_breakout_trades": True},
            forensics={"forensic_score": 85},
            financials={},
            news_items=[],
            holding_info=None
        )

        self.assertEqual(res["action_bias"], "HOLD_NEUTRAL")
        self.assertFalse(res["has_actionable_signal"])
        self.assertTrue(any("Binary Event Risk Veto" in d for d in res["confluence_drivers"]))

    def test_demat_exit_defense_never_vetoed_by_earnings(self):
        """Asymmetric Risk Rule: Demat capital preservation exits are NEVER vetoed by earnings."""
        today = date.today()
        register_upcoming_corporate_event(
            symbol="TATAMOTORS",
            event_date=today,
            event_type="QUARTERLY_RESULTS"
        )

        # User holds TATAMOTORS at ₹1000, now dropping to ₹950 (-5.0% loss)
        holding_info = {
            "symbol": "TATAMOTORS",
            "quantity": 50,
            "average_price": 1000.0
        }
        technicals = {
            "current_price": 950.0,
            "technical_score": 30,
            "rsi_15m": 32.0,
            "rsi_daily": 35.0,
            "ema_50": 980.0,
            "ema_200": 990.0,
            "atr_14": 15.0,
            "vwap": 965.0,
            "camarilla_pivots": {"h4": 990.0, "h3": 980.0, "l3": 960.0, "l4": 955.0} # Breached L4
        }
        res = compute_deterministic_confluence(
            symbol="TATAMOTORS.NS",
            technicals=technicals,
            flow_data={},
            macro_data={},
            forensics={},
            financials={},
            news_items=[],
            holding_info=holding_info
        )

        # Must preserve capital exit regardless of earnings
        self.assertEqual(res["action_bias"], "CAPITAL_PRESERVATION_EXIT")
        self.assertTrue(res["has_actionable_signal"])


if __name__ == "__main__":
    unittest.main()
