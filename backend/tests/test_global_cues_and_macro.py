"""
Unit Tests for Dalal Street Macro Correlation & Commodity Shock Suite
Dual-Exchange (NSE & BSE) Compliant with Zero-Default Policy.
"""
import unittest

from app.macro_filter import check_crude_oil_sector_shock
from app.engine.deterministic import compute_deterministic_confluence


class TestGlobalCuesAndMacro(unittest.TestCase):

    def test_zero_default_on_none_crude(self):
        """Zero-Default Policy: When Brent crude data is None, returns clean unpopulated state."""
        res = check_crude_oil_sector_shock("NIFTY PAINTS", None)
        self.assertFalse(res["has_shock"])
        self.assertEqual(res["penalty_score"], 0)
        self.assertIsNone(res["driver"])

        # Also when sector is None
        res_sec = check_crude_oil_sector_shock(None, 3.5)
        self.assertFalse(res_sec["has_shock"])

    def test_crude_oil_spike_flags_paint_and_omc_sectors(self):
        """Crude spike >= 2.5% flags margin compression for Paints, OMCs, and Tyres."""
        # Asian Paints / Berger Paints sector
        paints_shock = check_crude_oil_sector_shock("NIFTY PAINTS", 2.8)
        self.assertTrue(paints_shock["has_shock"])
        self.assertGreaterEqual(paints_shock["penalty_score"], 8)
        self.assertIn("Crude Oil Margin Headwind", paints_shock["driver"])

        # Oil Marketing Companies (BPCL, HPCL, IOC)
        omc_shock = check_crude_oil_sector_shock("OIL & GAS", 3.0)
        self.assertTrue(omc_shock["has_shock"])

        # Unaffected sector (IT / Software) at 2.8%
        it_shock = check_crude_oil_sector_shock("NIFTY IT", 2.8)
        self.assertFalse(it_shock["has_shock"])

    def test_severe_crude_spike_broad_market_warning(self):
        """Crude surge >= 4.0% flags broad-market macro inflationary headwind."""
        broad_shock = check_crude_oil_sector_shock("NIFTY BANK", 4.5)
        self.assertTrue(broad_shock["has_shock"])
        self.assertIn("Macro Commodity Shock", broad_shock["driver"])

    def test_crude_surge_vetoes_asian_paints_breakout(self):
        """Brent crude surge >= 3.0% vetoes BUY_WATCH on Asian Paints."""
        technicals = {
            "current_price": 2800.0,
            "technical_score": 80,
            "rsi_15m": 58.0,
            "rsi_daily": 56.0,
            "ema_50": 2700.0,
            "ema_200": 2600.0,
            "vwap": 2790.0,
            "atr_14": 30.0,
            "camarilla_pivots": {"h4": 2795.0, "h3": 2770.0, "l3": 2730.0, "l4": 2700.0}
        }
        res = compute_deterministic_confluence(
            symbol="ASIANPAINT.NS",
            technicals=technicals,
            flow_data={"delivery_pct": 55.0},
            macro_data={
                "allow_breakout_trades": True,
                "global_cues": {"brent_crude_pct": 3.8} # Crude up 3.8%
            },
            forensics={"forensic_score": 85, "sector_name": "NIFTY PAINTS"},
            financials={},
            news_items=[],
            holding_info=None
        )

        self.assertEqual(res["action_bias"], "HOLD_NEUTRAL")
        self.assertFalse(res["has_actionable_signal"])
        self.assertTrue(any("Crude Shock Veto" in d for d in res["confluence_drivers"]))


if __name__ == "__main__":
    unittest.main()
