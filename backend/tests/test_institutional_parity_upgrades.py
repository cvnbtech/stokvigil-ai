import os
import sys
import unittest
from datetime import datetime, timezone, timedelta

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="

from app.engine.deterministic import compute_deterministic_confluence
from app.market_cache import market_cache

IST = timezone(timedelta(hours=5, minutes=30))


class TestInstitutionalParityUpgrades(unittest.TestCase):
    """
    Test suite for:
    1. Veto Filter #6: Bid-Ask Spread & Illiquidity Gatekeeper (< ₹2 Cr BSE / < ₹5 Cr NSE / Wide spread).
    2. Overnight Value-at-Risk (VaR) Engine: 1-day 95% gap risk on Demat holdings when VIX >= 17.5.
    3. Quotes and Analysis Router Enrichment: liquidity_info and overnight_risk payload exposure.
    """

    def setUp(self):
        # Base bullish technicals that would otherwise trigger a BUY_WATCH / STRONG_BUY
        self.bullish_technicals = {
            "current_price": 500.0,
            "technical_score": 85,
            "rsi_15m": 62.0,
            "rsi_5m": 58.0,
            "rsi_divergence": "BULLISH_CONVERGENCE",
            "volume_surge_ratio": 2.2,
            "is_volume_surge": True,
            "volume_multiple": 2.2,
            "live_volume": 50000,
            "volume": 50000,
            "macd_trend": "BULLISH_CROSSOVER",
            "vwap": 496.0,
            "price_vs_vwap_pct": 0.8,
            "atr_14": 8.0,
            "day_high": 505.0,
            "day_low": 490.0,
            "camarilla_pivots": {
                "h3": 498.0,
                "h4": 502.0,
                "h5": 510.0,
                "l3": 492.0,
                "l4": 488.0,
                "l5": 480.0
            },
            "turnover_cr": 1.2,  # Thin turnover ₹1.2 Cr (below NSE 5 Cr and BSE 2 Cr)
            "bid_ask_spread_pct": 0.15
        }

        self.bullish_flow = {
            "flow_score": 80,
            "is_fo_stock": True,
            "fo_oi_status": "LONG_BUILDUP",
            "pcr": 1.15,
            "max_pain_strike": 500.0,
            "major_support_strike": 490.0,
            "major_resistance_strike": 520.0,
            "delivery_pct": 55.0,
            "vsa_regime": "SMART_MONEY_ABSORPTION"
        }

        self.neutral_macro = {
            "india_vix": 14.2,
            "nifty_regime": "BULLISH_TREND",
            "adr_ratio": 1.4,
            "breadth_regime": "POSITIVE_BREADTH"
        }

        self.clean_forensics = {
            "forensic_risk_score": 10,
            "has_high_promoter_pledge": False,
            "has_auditor_resignation": False,
            "has_asm_gsm_flag": False
        }

        self.clean_financials = {
            "name": "Test Alpha Industries",
            "pe_ratio": 22.0,
            "debt_to_equity": 0.4,
            "beta_volatility": 1.2
        }

    # -------------------------------------------------------------
    # 1. Veto Filter #6: Illiquidity & Bid-Ask Spread Gatekeeper
    # -------------------------------------------------------------
    def test_veto_filter_6_thin_turnover_blocks_nse_buy(self):
        """NSE equity with daily turnover < ₹5 Cr must veto BUY_WATCH to HOLD_NEUTRAL."""
        tech = dict(self.bullish_technicals)
        tech["turnover_cr"] = 3.5  # < ₹5 Cr threshold for NSE

        res = compute_deterministic_confluence(
            symbol="THINNSE.NS",
            technicals=tech,
            flow_data=self.bullish_flow,
            macro_data=self.neutral_macro,
            forensics=self.clean_forensics,
            financials=self.clean_financials,
            news_items=[],
            holding_info=None,
            current_time_ist=datetime.now(IST)
        )

        self.assertEqual(res["action_bias"], "HOLD_NEUTRAL")
        self.assertTrue(res["liquidity_info"]["is_illiquid"])
        self.assertIn("Daily turnover", res["liquidity_info"]["illiquid_reason"])
        self.assertTrue(any("Illiquidity" in d for d in res["confluence_drivers"]))

    def test_veto_filter_6_thin_turnover_blocks_bse_buy(self):
        """BSE equity (.BO) with daily turnover < ₹2 Cr must veto BUY_WATCH to HOLD_NEUTRAL."""
        tech = dict(self.bullish_technicals)
        tech["turnover_cr"] = 1.1  # < ₹2 Cr threshold for BSE

        res = compute_deterministic_confluence(
            symbol="500123.BO",
            technicals=tech,
            flow_data=self.bullish_flow,
            macro_data=self.neutral_macro,
            forensics=self.clean_forensics,
            financials=self.clean_financials,
            news_items=[],
            holding_info=None,
            current_time_ist=datetime.now(IST)
        )

        self.assertEqual(res["action_bias"], "HOLD_NEUTRAL")
        self.assertTrue(res["liquidity_info"]["is_illiquid"])
        self.assertIn("Daily turnover", res["liquidity_info"]["illiquid_reason"])

    def test_veto_filter_6_wide_spread_blocks_buy(self):
        """NSE equity with excessive bid-ask spread (> 0.25%) must veto BUY_WATCH to HOLD_NEUTRAL."""
        tech = dict(self.bullish_technicals)
        tech["turnover_cr"] = 15.0  # Adequate turnover
        tech["bid_ask_spread_pct"] = 0.45  # > 0.25% threshold for NSE

        res = compute_deterministic_confluence(
            symbol="WIDESPREAD.NS",
            technicals=tech,
            flow_data=self.bullish_flow,
            macro_data=self.neutral_macro,
            forensics=self.clean_forensics,
            financials=self.clean_financials,
            news_items=[],
            holding_info=None,
            current_time_ist=datetime.now(IST)
        )

        self.assertEqual(res["action_bias"], "HOLD_NEUTRAL")
        self.assertTrue(res["liquidity_info"]["is_illiquid"])
        self.assertIn("Wide bid-ask spread", res["liquidity_info"]["illiquid_reason"])

    def test_veto_filter_6_adequate_liquidity_passes(self):
        """High-turnover, tight-spread equity passes Veto Filter #6 cleanly."""
        tech = dict(self.bullish_technicals)
        tech["turnover_cr"] = 45.0  # Well above ₹5 Cr
        tech["bid_ask_spread_pct"] = 0.04  # Tight spread

        res = compute_deterministic_confluence(
            symbol="LIQUIDSTOCK.NS",
            technicals=tech,
            flow_data=self.bullish_flow,
            macro_data=self.neutral_macro,
            forensics=self.clean_forensics,
            financials=self.clean_financials,
            news_items=[],
            holding_info=None,
            current_time_ist=datetime.now(IST)
        )

        self.assertFalse(res["liquidity_info"]["is_illiquid"])
        self.assertIsNone(res["liquidity_info"]["illiquid_reason"])

    # -------------------------------------------------------------
    # 2. Overnight Value-at-Risk (VaR) Engine
    # -------------------------------------------------------------
    def test_overnight_var_triggers_on_elevated_vix_for_demat_holding(self):
        """When India VIX >= 17.5 and stock is in Demat portfolio, 1-Day 95% VaR is calculated and alerted."""
        tech = dict(self.bullish_technicals)
        tech["turnover_cr"] = 25.0
        tech["bid_ask_spread_pct"] = 0.05

        high_vix_macro = {
            "india_vix": 19.5,  # Elevated volatility regime (VIX > 17.5)
            "nifty_regime": "VOLATILITY_CHOP",
            "adr_ratio": 0.9,
            "breadth_regime": "NEUTRAL_BREADTH"
        }

        demat_holding = {
            "symbol": "TATASTEEL",
            "quantity": 100,
            "average_price": 140.0,
            "current_price": 150.0
        }

        res = compute_deterministic_confluence(
            symbol="TATASTEEL.NS",
            technicals=tech,
            flow_data=self.bullish_flow,
            macro_data=high_vix_macro,
            forensics=self.clean_forensics,
            financials=self.clean_financials,
            news_items=[],
            holding_info=demat_holding,
            current_time_ist=datetime.now(IST)
        )

        ovn_risk = res.get("overnight_risk", {})
        self.assertTrue(ovn_risk.get("has_gap_risk"))
        self.assertIsNotNone(ovn_risk.get("estimated_var_pct"))
        self.assertGreater(ovn_risk.get("estimated_var_pct"), 2.0)
        self.assertEqual(ovn_risk.get("india_vix"), 19.5)
        self.assertIn("High overnight gap risk", ovn_risk.get("guidance", ""))

        # Check tactical levels integration
        tactical = res.get("tactical_levels")
        if tactical:
            self.assertIn("overnight_gap_risk", tactical)

    def test_overnight_var_dormant_on_normal_vix(self):
        """When India VIX < 17.5 and normal beta, overnight gap risk remains dormant."""
        tech = dict(self.bullish_technicals)
        tech["turnover_cr"] = 25.0
        tech["bid_ask_spread_pct"] = 0.05

        normal_vix_macro = {
            "india_vix": 13.5,
            "nifty_regime": "BULLISH_TREND",
            "adr_ratio": 1.5,
            "breadth_regime": "POSITIVE_BREADTH"
        }

        demat_holding = {
            "symbol": "INFY",
            "quantity": 50,
            "average_price": 1500.0,
            "current_price": 1600.0
        }

        fin = dict(self.clean_financials)
        fin["beta_volatility"] = 0.9

        res = compute_deterministic_confluence(
            symbol="INFY.NS",
            technicals=tech,
            flow_data=self.bullish_flow,
            macro_data=normal_vix_macro,
            forensics=self.clean_forensics,
            financials=fin,
            news_items=[],
            holding_info=demat_holding,
            current_time_ist=datetime.now(IST)
        )

        ovn_risk = res.get("overnight_risk", {})
        self.assertFalse(ovn_risk.get("has_gap_risk"))

    # -------------------------------------------------------------
    # 3. Router Quotes & Analysis Payload Enrichment
    # -------------------------------------------------------------
    def test_router_quote_enrichment_exposes_liquidity_and_overnight(self):
        """FastAPI quote router enriches quotes dictionary with liquidity_info and overnight_risk."""
        import time
        from app.routers.stocks import get_batch_stock_quotes, _QUOTE_CACHE

        _QUOTE_CACHE["PARITYTEST"] = {
            "timestamp": time.time(),
            "data": {
                "symbol": "PARITYTEST",
                "clean_symbol": "PARITYTEST",
                "price": 250.0,
                "change_pct": 2.5,
                "is_positive": True
            }
        }

        mock_pack = {
            "symbol": "PARITYTEST",
            "clean_symbol": "PARITYTEST",
            "current_price": 250.0,
            "action_bias": "STRONG_BUY",
            "confluence_score": 85,
            "technicals": {
                "current_price": 250.0,
                "change_pct": 2.5,
                "turnover_cr": 45.0,
            },
            "analysis": {
                "action_bias": "STRONG_BUY",
                "tactical_levels": {
                    "target_1": "₹265.00",
                    "protective_stop_loss": "₹242.00",
                },
                "liquidity_info": {
                    "turnover_cr": 45.0,
                    "is_illiquid": False,
                    "bid_ask_spread_pct": 0.05,
                    "illiquid_reason": None
                },
                "overnight_risk": {
                    "has_gap_risk": True,
                    "estimated_var_pct": 2.85,
                    "india_vix": 18.2,
                    "stock_beta": 1.4
                }
            }
        }

        market_cache.set_stock("PARITYTEST", mock_pack, ttl_seconds=60)

        # Call get_batch_stock_quotes
        res = get_batch_stock_quotes("PARITYTEST")
        quotes = res.get("quotes", {})
        q_entry = quotes.get("PARITYTEST")

        self.assertIsNotNone(q_entry)
        self.assertIn("liquidity_info", q_entry)
        self.assertFalse(q_entry["liquidity_info"]["is_illiquid"])
        self.assertIn("overnight_risk", q_entry)
        self.assertTrue(q_entry["overnight_risk"]["has_gap_risk"])
        self.assertEqual(q_entry["overnight_risk"]["estimated_var_pct"], 2.85)


if __name__ == "__main__":
    unittest.main()
