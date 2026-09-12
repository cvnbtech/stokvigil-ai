import sys
import os
import unittest

# Set test environment to prevent vault production check abort
os.environ["ENVIRONMENT"] = "test"
os.environ["ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.macro_filter import fetch_market_breadth_adr, fetch_macro_market_regime
from app.flow_tracker import fetch_delivery_and_fo_flow
from app.agent_runner import compute_deterministic_confluence, resolve_isin_to_nse_symbol
from app.market_cache import market_cache


class TestAdvancedAccuracy(unittest.TestCase):
    def test_market_breadth_adr(self):
        """Verify that Market Breadth Advance-Decline Ratio (ADR) computes successfully."""
        breadth = fetch_market_breadth_adr()
        self.assertIsInstance(breadth, dict)
        self.assertIn("adr_ratio", breadth)
        self.assertIn("advances", breadth)
        self.assertIn("declines", breadth)
        self.assertIn("breadth_regime", breadth)
        self.assertGreater(breadth["adr_ratio"], 0)
        self.assertIn(breadth["breadth_regime"], [
            "STRONG_BULLISH_BREADTH",
            "BALANCED_BREADTH",
            "MILD_BREADTH_WEAKNESS",
            "SEVERE_MARKET_DISTRIBUTION"
        ])

    def test_macro_regime_integration(self):
        """Verify macro regime incorporates breadth and enforces breakout trade rules."""
        macro = fetch_macro_market_regime()
        self.assertIn("adr_ratio", macro)
        self.assertIn("breadth_regime", macro)
        self.assertIn("allow_breakout_trades", macro)
        self.assertIsInstance(macro["allow_breakout_trades"], bool)
        if macro["adr_ratio"] < 0.60:
            self.assertFalse(macro["allow_breakout_trades"])

    def test_bse_cash_fallback_in_flow_tracker(self):
        """Verify BSE equity flow does not penalize absence of NSE F&O options."""
        flow = fetch_delivery_and_fo_flow("500325.BO", price_change_pct=1.2)
        self.assertEqual(flow["fo_oi_status"], "BSE_CASH_DELIVERY")
        self.assertEqual(flow["flow_bias"], "CASH_ACCUMULATION")
        self.assertFalse(flow["is_fo_stock"])
        self.assertEqual(flow["pcr"], 1.0)

    def test_max_pain_and_breadth_veto_in_deterministic_confluence(self):
        """
        Verify:
        1. Severe distribution breadth (ADR < 0.60) vetoes BUY_WATCH to HOLD_NEUTRAL.
        2. Bullish breadth with strong PCR and trading above Max Pain yields BUY_WATCH.
        """
        dummy_tech = {
            "technical_score": 88,
            "current_price": 2500.0,
            "ema_50": 2400.0,
            "ema_200": 2200.0,
            "ma_trend": "ABOVE_ALL_EMAS",
            "rsi_daily": 62.0,
            "rsi_15m": 58.0,
            "rsi_5m": 55.0,
            "price_vs_vwap_pct": 0.5,
            "vwap": 2485.0,
            "is_volume_surge": True,
            "volume_multiple": 2.2,
            "macd_trend": "BULLISH_CROSSOVER",
            "macd_histogram": 1.5,
            "adx_14": 28.0,
            "adx_regime": "STRONG_TREND",
            "rs_regime": "OUTPERFORMING_LEADER",
            "rs_rating": 4.5,
            "camarilla_pivots": {"h4": 2540.0, "h3": 2515.0, "l3": 2480.0, "l4": 2460.0},
            "atr_14": 30.0
        }
        dummy_flow_bullish = {
            "flow_score": 85,
            "delivery_pct": 65.0,
            "is_high_delivery": True,
            "fo_oi_status": "LONG_BUILDUP",
            "flow_bias": "INSTITUTIONAL_ACCUMULATION",
            "is_fo_stock": True,
            "pcr": 1.35,
            "max_pain_strike": 2460.0,
            "major_support_strike": 2450.0,
            "major_resistance_strike": 2550.0,
            "vsa_regime": "SMART_MONEY_ABSORPTION"
        }
        dummy_forensics = {
            "forensic_score": 80,
            "sector_name": "ENERGY",
            "red_flags": []
        }
        dummy_financials = {
            "pe_ratio": 22.0,
            "debt_to_equity": 0.35,
            "revenue_growth_pct": 15.0,
            "profit_margin_pct": 12.0
        }
        dummy_news = [{"title": "RELIANCE wins major institutional energy order", "link": "http://example.com"}]

        # Case A: Healthy Market Breadth (ADR = 1.40) -> Expect BUY_WATCH
        macro_bullish = {
            "nifty_trend": "BULLISH",
            "nifty_change_pct": 0.8,
            "india_vix": 13.5,
            "vix_regime": "NORMAL_VOLATILITY",
            "allow_breakout_trades": True,
            "adr_ratio": 1.40,
            "breadth_regime": "BALANCED_BREADTH",
            "advances": 35,
            "declines": 15
        }

        res_a = compute_deterministic_confluence(
            symbol="RELIANCE",
            technicals=dummy_tech,
            flow_data=dummy_flow_bullish,
            macro_data=macro_bullish,
            forensics=dummy_forensics,
            financials=dummy_financials,
            news_items=dummy_news
        )

        self.assertEqual(res_a["action_bias"], "BUY_WATCH")
        self.assertTrue(res_a["has_actionable_signal"])
        self.assertTrue(any("Option Chain: Bullish Put-Call Ratio" in d for d in res_a["confluence_drivers"]))
        self.assertTrue(any("F&O Bullish Driver" in d for d in res_a["confluence_drivers"]))
        self.assertEqual(res_a["derivatives_flow"]["pcr"], 1.35)
        self.assertEqual(res_a["derivatives_flow"]["max_pain_strike"], 2460.0)

        # Case B: Severe Distribution Market Breadth (ADR = 0.45 < 0.60) -> Expect VETO to HOLD_NEUTRAL
        macro_distribution = {
            "nifty_trend": "BEARISH",
            "nifty_change_pct": -1.2,
            "india_vix": 18.0,
            "vix_regime": "ELEVATED_VOLATILITY_CAUTION",
            "allow_breakout_trades": False,
            "adr_ratio": 0.45,
            "breadth_regime": "SEVERE_MARKET_DISTRIBUTION",
            "advances": 12,
            "declines": 38
        }

        res_b = compute_deterministic_confluence(
            symbol="RELIANCE",
            technicals=dummy_tech,
            flow_data=dummy_flow_bullish,
            macro_data=macro_distribution,
            forensics=dummy_forensics,
            financials=dummy_financials,
            news_items=dummy_news
        )

        self.assertEqual(res_b["action_bias"], "HOLD_NEUTRAL")
        self.assertFalse(res_b["has_actionable_signal"])
        self.assertTrue(any("Market Breadth Veto" in d for d in res_b["confluence_drivers"]))

    def test_bse_6_digit_scrip_resolution(self):
        """Verify 6-digit BSE scrip codes are correctly identified and normalized."""
        self.assertEqual(resolve_isin_to_nse_symbol("500325"), "500325.BO")
        self.assertEqual(resolve_isin_to_nse_symbol("500325.BO"), "500325.BO")
        self.assertEqual(resolve_isin_to_nse_symbol("RELIANCE.BO"), "RELIANCE.BO")
        self.assertEqual(resolve_isin_to_nse_symbol("INFY"), "INFY")

    def test_atomic_live_tick_update_in_cache(self):
        """Verify MarketCacheManager.update_live_tick updates sub-second LTP and recalculates VWAP dev in RAM."""
        market_cache.clear()
        symbol = "TCS"
        
        # 1. Seed cache entry with VWAP = 3500.0
        seed_pack = {
            "symbol": symbol,
            "current_price": 3500.0,
            "vwap": 3500.0,
            "price_vs_vwap_pct": 0.0,
            "action_bias": "HOLD_NEUTRAL",
            "confluence_score": 60
        }
        market_cache.set_stock(symbol, seed_pack, ttl_seconds=300)

        # 2. Simulate live WebSocket tick: LTP jumps to 3535 (+1% above VWAP)
        market_cache.update_live_tick(
            symbol=symbol,
            ltp=3535.0,
            volume=125000,
            high=3540.0,
            low=3495.0
        )

        updated = market_cache.get_stock(symbol)
        self.assertIsNotNone(updated)
        self.assertEqual(updated["current_price"], 3535.0)
        self.assertEqual(updated["live_volume"], 125000)
        self.assertEqual(updated["day_high"], 3540.0)
        self.assertEqual(updated["day_low"], 3495.0)
        self.assertEqual(updated["price_vs_vwap_pct"], 1.0)
        self.assertIn("last_tick_time", updated)


if __name__ == "__main__":
    unittest.main()
