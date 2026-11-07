import sys
import os
import unittest
from datetime import datetime, timezone, timedelta

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ["ENVIRONMENT"] = "test"
os.environ["ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="

from app.engine.deterministic import (
    compute_deterministic_confluence,
    check_has_active_catalyst
)
from app.notifications import format_telegram_alert
from app.alert_limiter import should_dispatch_alert

IST = timezone(timedelta(hours=5, minutes=30))


class TestPortfolioLifecycleAlerts(unittest.TestCase):
    """
    SEBI-Compliant Institutional 5-State Portfolio Lifecycle Alert System Tests:
    1. ACCUMULATE_WATCH (Pyramiding into winners when P&L >= 0%)
    2. HOLD_STEADY via Anti-Averaging-Down Guardrail (When breakout triggers on losing position P&L < 0%)
    3. DEFENSIVE_TRIM_ALERT (Intraday VWAP loss / Institutional Block Dump on active holdings)
    4. CAPITAL_PRESERVATION_EXIT (Hard Stop-Loss at P&L <= -3.5% or severe breakdown)
    5. TRAILING_SL_ALERT (Overbought RSI > 72 with P&L >= +5%)
    6. Telegram formatting & Alert Limiter Tier-1 Bypass
    """

    def setUp(self):
        # Baseline technicals for a strong institutional setup (e.g. HDFCBANK)
        self.bullish_technicals = {
            "technical_score": 85,
            "current_price": 1750.0,
            "change_pct": 1.85,
            "day_high": 1758.0,
            "day_low": 1720.0,
            "atr_14": 22.5,
            "ema_20": 1715.0,
            "ema_50": 1690.0,
            "ema_200": 1640.0,  # Above 200 EMA (Macro Bullish)
            "vwap": 1735.0,
            "price_vs_vwap_pct": 0.86,
            "rsi_15m": 64.2,
            "is_volume_surge": True,
            "volume_multiple": 2.18,
            "macd_trend": "BULLISH_CROSSOVER",
            "camarilla_pivots": {
                "h3": 1738.0,
                "h4": 1752.0,
                "l3": 1710.0,
                "l4": 1698.0
            }
        }

        self.bullish_flow = {
            "flow_score": 85,
            "delivery_pct": 63.2,
            "is_high_delivery": True,
            "vsa_regime": "SMART_MONEY_ABSORPTION",
            "is_fo_stock": True,
            "pcr": 1.15,
            "fo_oi_status": "LONG_BUILDUP"
        }

        self.macro_neutral = {
            "allow_breakout_trades": True,
            "india_vix": 13.2,
            "adr_ratio": 1.45,
            "breadth_regime": "HEALTHY_EXPANSION",
            "nifty_change_pct": 0.42
        }

        self.forensics_clean = {
            "forensic_score": 88,
            "sector_name": "BANKING",
            "pe_ratio": 18.5,
            "debt_to_equity": 0.12,
            "profit_margin_pct": 24.5
        }

        self.financials_hdfc = {
            "symbol": "HDFCBANK",
            "name": "HDFC Bank Ltd.",
            "price": 1750.0,
            "pe_ratio": 18.5,
            "debt_to_equity": 0.12
        }

    def test_hdfcbank_pyramid_accumulate_when_profitable(self):
        """
        State 1: ACCUMULATE_WATCH
        User owns HDFCBANK at avg buy ₹1,700 (Current price ₹1,750 -> P&L = +2.94%).
        With high confluence (score >= 72) and positive P&L, system MUST trigger ACCUMULATE_WATCH.
        """
        holding = {
            "symbol": "HDFCBANK",
            "quantity": 50,
            "average_price": 1700.0,
            "current_market_price": 1750.0
        }

        res = compute_deterministic_confluence(
            symbol="HDFCBANK.NS",
            technicals=self.bullish_technicals,
            flow_data=self.bullish_flow,
            macro_data=self.macro_neutral,
            forensics=self.forensics_clean,
            financials=self.financials_hdfc,
            holding_info=holding,
            current_time_ist=datetime(2026, 11, 7, 10, 15, tzinfo=IST)
        )

        self.assertTrue(res["has_actionable_signal"])
        self.assertEqual(res["action_bias"], "ACCUMULATE_WATCH")
        self.assertEqual(res["catalyst_category"], "PRICE_BREAKOUT")
        self.assertIn("HDFCBANK", res["alert_title"])
        self.assertIn("Accumulation / Pyramiding", res["alert_title"])
        self.assertIn("INSTITUTIONAL PYRAMIDING", res["holding_guidance"])
        self.assertIn("Safe to add 25-30% allocation", res["holding_guidance"])

    def test_hdfcbank_anti_averaging_down_guardrail_when_loss(self):
        """
        State 2: Anti-Averaging-Down Guardrail
        User owns HDFCBANK at avg buy ₹1,800 (Current price ₹1,750 -> P&L = -2.78%).
        Even though the stock is experiencing a bullish technical surge, institutional risk management
        and SEBI best practices STRICTLY FORBID averaging down on a losing position.
        The system MUST downgrade the signal to HOLD_STEADY with has_actionable_signal = False.
        """
        holding = {
            "symbol": "HDFCBANK",
            "quantity": 50,
            "average_price": 1800.0,
            "current_market_price": 1750.0
        }

        res = compute_deterministic_confluence(
            symbol="HDFCBANK.NS",
            technicals=self.bullish_technicals,
            flow_data=self.bullish_flow,
            macro_data=self.macro_neutral,
            forensics=self.forensics_clean,
            financials=self.financials_hdfc,
            holding_info=holding,
            current_time_ist=datetime(2026, 11, 7, 10, 15, tzinfo=IST)
        )

        self.assertFalse(res["has_actionable_signal"])
        self.assertEqual(res["action_bias"], "HOLD_STEADY")
        # Ensure anti-averaging-down explanation is explicitly documented in drivers
        self.assertTrue(any("Averaging down into losing positions is strictly prohibited" in d for d in res["confluence_drivers"]))

    def test_capital_preservation_exit_at_loss_breach(self):
        """
        State 3: CAPITAL_PRESERVATION_EXIT
        User owns position that has breached protective stop loss (P&L <= -3.5%).
        System MUST trigger CAPITAL_PRESERVATION_EXIT immediately.
        """
        holding = {
            "symbol": "HDFCBANK",
            "quantity": 50,
            "average_price": 1820.0,
            "current_market_price": 1750.0  # P&L = -3.85%
        }

        res = compute_deterministic_confluence(
            symbol="HDFCBANK.NS",
            technicals=self.bullish_technicals,
            flow_data=self.bullish_flow,
            macro_data=self.macro_neutral,
            forensics=self.forensics_clean,
            financials=self.financials_hdfc,
            holding_info=holding,
            current_time_ist=datetime(2026, 11, 7, 10, 15, tzinfo=IST)
        )

        self.assertTrue(res["has_actionable_signal"])
        self.assertEqual(res["action_bias"], "CAPITAL_PRESERVATION_EXIT")
        self.assertEqual(res["catalyst_category"], "TRAILING_STOP_TRIGGER")
        self.assertIn("Capital Preservation Exit Trigger", res["alert_title"])
        self.assertIn("CRITICAL DEFENSE", res["holding_guidance"])

    def test_defensive_trim_alert_on_vwap_breakdown(self):
        """
        State 4: DEFENSIVE_TRIM_ALERT
        User holds position in small profit/breakeven (+0.4%), but price breaks below intraday VWAP by -0.95%.
        System MUST trigger DEFENSIVE_TRIM_ALERT to lock in gains and prevent position turning into loss.
        """
        breakdown_tech = dict(self.bullish_technicals)
        breakdown_tech["vwap"] = 1765.0
        breakdown_tech["price_vs_vwap_pct"] = -0.95
        breakdown_tech["current_price"] = 1748.0

        holding = {
            "symbol": "HDFCBANK",
            "quantity": 50,
            "average_price": 1740.0,
            "current_market_price": 1748.0  # P&L = +0.46%
        }

        res = compute_deterministic_confluence(
            symbol="HDFCBANK.NS",
            technicals=breakdown_tech,
            flow_data=self.bullish_flow,
            macro_data=self.macro_neutral,
            forensics=self.forensics_clean,
            financials=self.financials_hdfc,
            holding_info=holding,
            current_time_ist=datetime(2026, 11, 7, 10, 15, tzinfo=IST)
        )

        self.assertTrue(res["has_actionable_signal"])
        self.assertEqual(res["action_bias"], "DEFENSIVE_TRIM_ALERT")
        self.assertIn("Defensive Profit Protection Warning", res["alert_title"])
        self.assertIn("DEFENSIVE PROTOCOL", res["holding_guidance"])

    def test_trailing_stop_loss_alert_on_rsi_parabolic(self):
        """
        State 5: TRAILING_SL_ALERT
        User holds position with +6.2% profit and 15m RSI reaches 74.0 (Overbought).
        System MUST trigger TRAILING_SL_ALERT to trail protective stop-loss.
        """
        parabolic_tech = dict(self.bullish_technicals)
        parabolic_tech["rsi_15m"] = 74.5
        parabolic_tech["current_price"] = 1805.0

        holding = {
            "symbol": "HDFCBANK",
            "quantity": 50,
            "average_price": 1700.0,
            "current_market_price": 1805.0  # P&L = +6.18%
        }

        res = compute_deterministic_confluence(
            symbol="HDFCBANK.NS",
            technicals=parabolic_tech,
            flow_data=self.bullish_flow,
            macro_data=self.macro_neutral,
            forensics=self.forensics_clean,
            financials=self.financials_hdfc,
            holding_info=holding,
            current_time_ist=datetime(2026, 11, 7, 10, 15, tzinfo=IST)
        )

        self.assertTrue(res["has_actionable_signal"])
        self.assertEqual(res["action_bias"], "TRAILING_SL_ALERT")
        self.assertEqual(res["catalyst_category"], "TRAILING_STOP_TRIGGER")
        self.assertIn("Trailing Stop-Loss Trigger", res["alert_title"])

    def test_telegram_header_badges_for_all_portfolio_states(self):
        """
        Telegram Notification HTML Badge Verification:
        Ensures distinct, high-impact institutional headers render for each lifecycle state.
        """
        test_cases = [
            ("ACCUMULATE_WATCH", "INSTITUTIONAL ACCUMULATION & PYRAMID"),
            ("DEFENSIVE_TRIM_ALERT", "DEFENSIVE PROFIT PROTECTION WARNING"),
            ("CAPITAL_PRESERVATION_EXIT", "CAPITAL PRESERVATION EXIT TRIGGER"),
            ("TRAILING_SL_ALERT", "TRAILING STOP-LOSS TRIGGER"),
            ("TARGET_1_TRAIL_ALERT", "TACTICAL LEVEL 1 REACHED & TRAIL TO COST"),
            ("HOLD_STEADY", "POSITION HEALTHY & STEADY"),
        ]

        demat_pos = {
            "is_in_portfolio": True,
            "quantity": 50,
            "average_buy_price": 1700.0,
            "unrealized_pnl_pct": 2.94
        }

        for action_bias, expected_badge_text in test_cases:
            msg = format_telegram_alert(
                symbol="HDFCBANK.NS",
                alert_title=f"HDFCBANK: Test {action_bias}",
                action_bias=action_bias,
                confluence_score=85,
                catalyst_type="PRICE_BREAKOUT",
                confluence_drivers=["Volume surge", "Delivery accumulation"],
                tactical_levels={"entry_range": "₹1,740 - ₹1,755", "target_1": "₹1,785.00", "protective_stop_loss": "₹1,710.00"},
                demat_position=demat_pos,
                holding_guidance="Algorithmic test guidance"
            )
            self.assertIn(expected_badge_text, msg)
            self.assertIn("HDFCBANK", msg)
            self.assertIn("ICICI Direct Demat Snapshot", msg)

    def test_alert_limiter_tier1_bypass_for_portfolio_exits(self):
        """
        Alert Limiter Cooldown Verification:
        Critical portfolio actions (CAPITAL_PRESERVATION_EXIT, DEFENSIVE_TRIM_ALERT, ACCUMULATE_WATCH)
        must bypass normal symbol cooldowns to guarantee real-time delivery.
        """
        allowed, reason = should_dispatch_alert("user_123", "HDFCBANK", "CAPITAL_PRESERVATION_EXIT", 90, is_tier1_catalyst=True)
        self.assertTrue(allowed)

        allowed2, reason2 = should_dispatch_alert("user_123", "HDFCBANK", "DEFENSIVE_TRIM_ALERT", 45, is_tier1_catalyst=True)
        self.assertTrue(allowed2)

        allowed3, reason3 = should_dispatch_alert("user_123", "HDFCBANK", "ACCUMULATE_WATCH", 88, is_tier1_catalyst=True)
        self.assertTrue(allowed3)


if __name__ == "__main__":
    unittest.main()
