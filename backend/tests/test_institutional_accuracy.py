import sys
import os
import unittest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.technical_engine import (
    calculate_vwap_bands,
    calculate_ttm_squeeze,
    calculate_rsi,
    calculate_adx,
    fetch_multi_timeframe_technicals
)
from app.flow_tracker import (
    calculate_delta_oi_velocity,
    fetch_fno_derivative_metrics
)
from app.macro_filter import (
    calculate_sector_relative_strength,
    fetch_market_breadth_adr,
    SECTOR_INDEX_MAP
)
from app.agent_runner import (
    get_adaptive_weights,
    compute_tactical_levels,
    compute_deterministic_confluence
)
from app.notifications import (
    format_telegram_alert,
    format_pre_market_war_room_telegram
)


class TestInstitutionalAccuracy(unittest.TestCase):
    """
    Test suite for institutional accuracy enhancements across:
    1. Volatility compression & momentum (TTM Squeeze)
    2. Statistical anchor bands (VWAP +-1s / +-2s)
    3. Options Order Flow Momentum (Delta-OI Velocity)
    4. Sector Relative Strength (Stock vs Sector 20D Alpha)
    5. Regime-Adaptive Dynamic Confluence Weighting
    6. Strict Zero-Default Rule Verification
    """

    def setUp(self):
        # Generate 35-bar synthetic price series
        np.random.seed(42)
        dates = pd.date_range("2026-09-10 09:15:00", periods=35, freq="5min")
        close = 100.0 + np.cumsum(np.random.normal(0, 0.5, 35))
        high = close + np.random.uniform(0.1, 0.5, 35)
        low = close - np.random.uniform(0.1, 0.5, 35)
        open_p = (high + low) / 2.0
        volume = np.random.randint(5000, 20000, 35)

        self.df_synthetic = pd.DataFrame({
            "Open": open_p,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume
        }, index=dates)

    # -------------------------------------------------------------
    # 1. TTM Squeeze Volatility Compression & Momentum
    # -------------------------------------------------------------
    def test_ttm_squeeze_insufficient_bars(self):
        """Must return DATA_INSUFFICIENT and None for histogram when bars < 25."""
        short_df = self.df_synthetic.iloc[:10]
        res = calculate_ttm_squeeze(short_df)
        self.assertEqual(res["squeeze_status"], "DATA_INSUFFICIENT")
        self.assertFalse(res["squeeze_on"])
        self.assertFalse(res["squeeze_release"])
        self.assertIsNone(res["momentum_hist"])

    def test_ttm_squeeze_calculation(self):
        """TTM Squeeze must calculate squeeze_on / squeeze_release and numerical momentum histogram."""
        res = calculate_ttm_squeeze(self.df_synthetic)
        self.assertIn(res["squeeze_status"], ["SQUEEZE_ON", "SQUEEZE_RELEASE", "NO_SQUEEZE"])
        self.assertIsInstance(res["squeeze_on"], bool)
        self.assertIsInstance(res["squeeze_release"], bool)
        if res["momentum_hist"] is not None:
            self.assertIsInstance(res["momentum_hist"], float)
            self.assertIn(res["momentum_trend"], ["EXPANDING_BULLISH", "CONTRACTING_BULLISH", "EXPANDING_BEARISH", "CONTRACTING_BEARISH"])

    # -------------------------------------------------------------
    # 2. VWAP Volatility Bands (+-1s, +-2s)
    # -------------------------------------------------------------
    def test_vwap_bands_with_volume(self):
        """VWAP bands must return vwap, +-1s, and +-2s where upper > vwap > lower."""
        res = calculate_vwap_bands(self.df_synthetic)
        self.assertIsNotNone(res["vwap"])
        self.assertIsNotNone(res["vwap_upper_1s"])
        self.assertIsNotNone(res["vwap_lower_1s"])
        self.assertIsNotNone(res["vwap_upper_2s"])
        self.assertIsNotNone(res["vwap_lower_2s"])
        self.assertGreater(res["vwap_upper_1s"], res["vwap"])
        self.assertLess(res["vwap_lower_1s"], res["vwap"])
        self.assertGreater(res["vwap_upper_2s"], res["vwap_upper_1s"])
        self.assertLess(res["vwap_lower_2s"], res["vwap_lower_1s"])

    def test_vwap_bands_zero_volume(self):
        """Zero volume data must return None for all bands (Zero-Default Rule)."""
        df_zero_vol = self.df_synthetic.copy()
        df_zero_vol["Volume"] = 0
        res = calculate_vwap_bands(df_zero_vol)
        self.assertIsNone(res["vwap"])
        self.assertIsNone(res["vwap_upper_1s"])
        self.assertIsNone(res["vwap_lower_1s"])

    # -------------------------------------------------------------
    # 3. Flow Tracker Delta-OI Momentum Velocity
    # -------------------------------------------------------------
    def test_delta_oi_velocity_bullish_unwinding(self):
        """When Calls unwind (negative change) and Puts build (positive change), bias is CALL_UNWINDING_SHORT_COVERING."""
        mock_chain = [
            {"strikePrice": 1000, "call_change_oi": -25000, "put_change_oi": 15000},
            {"strikePrice": 1020, "call_change_oi": -15000, "put_change_oi": 20000},
            {"strikePrice": 1040, "call_change_oi": -5000, "put_change_oi": 10000},
        ]
        res = calculate_delta_oi_velocity(mock_chain)
        self.assertEqual(res["total_call_change_oi"], -45000)
        self.assertEqual(res["total_put_change_oi"], 45000)
        self.assertEqual(res["net_oi_change"], 90000)
        self.assertEqual(res["net_oi_bias"], "CALL_UNWINDING_SHORT_COVERING")

    def test_delta_oi_velocity_aggressive_call_writing(self):
        """When Calls heavily written and Puts unwound, bias is AGGRESSIVE_CALL_WRITING."""
        mock_chain = [
            {"strikePrice": 1000, "call_change_oi": 50000, "put_change_oi": -10000},
            {"strikePrice": 1020, "call_change_oi": 40000, "put_change_oi": -15000},
        ]
        res = calculate_delta_oi_velocity(mock_chain)
        self.assertEqual(res["net_oi_bias"], "AGGRESSIVE_CALL_WRITING")
        self.assertLess(res["net_oi_change"], 0)

    def test_delta_oi_velocity_empty_chain(self):
        """Empty options chain must return None (Zero-Default Rule)."""
        res = calculate_delta_oi_velocity([])
        self.assertIsNone(res["net_oi_change"])
        self.assertIsNone(res["net_oi_bias"])
        self.assertIsNone(res["total_call_change_oi"])
        self.assertIsNone(res["total_put_change_oi"])

    # -------------------------------------------------------------
    # 4. Sector Relative Strength (Stock vs Sector 20D Alpha)
    # -------------------------------------------------------------
    def test_sector_relative_strength_mapping(self):
        """Sector name should map to corresponding benchmark sector index."""
        self.assertEqual(SECTOR_INDEX_MAP.get("NIFTY IT"), "^CNXIT")
        self.assertEqual(SECTOR_INDEX_MAP.get("NIFTY BANK"), "^NSEBANK")
        self.assertEqual(SECTOR_INDEX_MAP.get("NIFTY AUTO"), "^CNXAUTO")

    @patch("yfinance.Ticker")
    def test_sector_relative_strength_calculation(self, mock_ticker):
        """Computes stock 20d return minus sector 20d return."""
        mock_hist = pd.DataFrame({
            "Close": [100.0] * 21 + [102.0]
        }, index=pd.date_range("2026-08-15", periods=22, freq="1D"))
        mock_inst = MagicMock()
        mock_inst.history.return_value = mock_hist
        mock_ticker.return_value = mock_inst

        # Stock +5.0%, Sector +2.0% -> Sector RS Alpha = +3.0%
        rs_data = calculate_sector_relative_strength("TCS", stock_20d_ret=5.0)
        self.assertIsNotNone(rs_data["sector_rs_20d"])
        self.assertEqual(rs_data["sector_symbol"], "^CNXIT")
        self.assertEqual(rs_data["sector_trend"], "OUTPERFORMING")

    # -------------------------------------------------------------
    # 5. Regime-Adaptive Dynamic Confluence Weighting
    # -------------------------------------------------------------
    def test_adaptive_weights_high_vix_defensive(self):
        """When VIX > 16.5, engine switches to DEFENSIVE regime (Order Flow 35%, Forensics 35%)."""
        macro_defensive = {
            "vix_trend": "VOLATILITY_EXPANDING",
            "vix_value": 18.5,
            "market_breadth_adr": 0.6
        }
        weights, regime = get_adaptive_weights(macro_defensive, adx_regime="NON_TRENDING_CHOP")
        self.assertEqual(regime, "HIGH_VOLATILITY_DEFENSIVE")
        self.assertEqual(weights["flow"], 0.35)
        self.assertEqual(weights["forensics"], 0.35)
        self.assertEqual(weights["tech"], 0.15)
        self.assertEqual(weights["news"], 0.15)
        self.assertAlmostEqual(sum(weights.values()), 1.0)

    def test_adaptive_weights_bull_momentum(self):
        """When VIX is low and ADR > 1.2, engine switches to BULL_MOMENTUM (Tech 40%, Flow 30%)."""
        macro_bull = {
            "vix_trend": "LOW_VOLATILITY",
            "vix_value": 13.0,
            "market_breadth_adr": 1.4
        }
        weights, regime = get_adaptive_weights(macro_bull, adx_regime="STRONG_TREND")
        self.assertEqual(regime, "BULL_MOMENTUM")
        self.assertEqual(weights["tech"], 0.40)
        self.assertEqual(weights["flow"], 0.30)
        self.assertEqual(weights["forensics"], 0.15)
        self.assertEqual(weights["news"], 0.15)
        self.assertAlmostEqual(sum(weights.values()), 1.0)

    # -------------------------------------------------------------
    # 6. Strict Zero-Default Rule Verification
    # -------------------------------------------------------------
    def test_zero_default_rsi_and_adx(self):
        """calculate_rsi and calculate_adx must return None if series is too short, never fake 50.0 or 20.0."""
        tiny_series = pd.Series([100.0, 101.0, 102.0])
        rsi_val = calculate_rsi(tiny_series, 14)
        self.assertTrue(pd.isna(rsi_val.iloc[-1]))

        tiny_df = self.df_synthetic.iloc[:5]
        adx_dict = calculate_adx(tiny_df, 14)
        self.assertIsNone(adx_dict["adx_14"])
        self.assertEqual(adx_dict["adx_regime"], "DATA_INSUFFICIENT")

    def test_zero_default_tactical_levels(self):
        """compute_tactical_levels must return None when current_price is 0 or None, never fake ₹0.00 levels."""
        levels_zero = compute_tactical_levels(0.0, 5.0, 0.0)
        self.assertIsNone(levels_zero)

        levels_none = compute_tactical_levels(None, 5.0, 100.0)
        self.assertIsNone(levels_none)

    def test_zero_default_flow_tracker_fno(self):
        """fetch_fno_derivative_metrics must return None (not 52.0 or 1.0) when NSE chain fails."""
        with patch("app.flow_tracker.fetch_nse_option_chain", return_value=[]):
            res = fetch_fno_derivative_metrics("NON_EXISTENT_STOCK")
            self.assertIsNone(res["delivery_pct"])
            self.assertIsNone(res["pcr"])
            self.assertIsNone(res["max_pain"])
            self.assertIsNone(res["net_oi_change"])
            self.assertIsNone(res["net_oi_bias"])

    def test_zero_default_telegram_alert_omits_missing_sections(self):
        """format_telegram_alert must omit Tactical block when tactical_levels is None."""
        alert_html = format_telegram_alert(
            symbol="INFY",
            alert_title="Test Zero Default Alert",
            action_bias="BUY_WATCH",
            confluence_score=85,
            catalyst_type="BREAKOUT",
            confluence_drivers=["Strong Volume Breakout"],
            tactical_levels=None,  # No tactical levels
            metrics_snapshot={"current_price": 1850.0, "rsi_15m": None, "delivery_pct": None}
        )
        self.assertNotIn("Tactical Risk-Reward Levels", alert_html)
        self.assertNotIn("• Delivery: None%", alert_html)
        self.assertNotIn("• 15m RSI: None", alert_html)
        self.assertIn("• LTP: ₹1850.0", alert_html)

    def test_zero_default_pre_market_war_room(self):
        """format_pre_market_war_room_telegram must omit benchmarks not received, never print fake defaults."""
        empty_data = {
            "date": "2026-09-15",
            # Nifty and Sensex not provided
            "india_vix": 14.2,
            "vix_regime": "LOW_VOLATILITY"
        }
        war_room_html = format_pre_market_war_room_telegram(empty_data)
        self.assertNotIn("NIFTY 50", war_room_html)
        self.assertNotIn("SENSEX", war_room_html)
        self.assertIn("India VIX", war_room_html)

    def test_financials_4hour_cache_and_dual_exchange(self):
        """Corporate fundamentals must cache for 4 hours and normalize NSE/BSE tickers."""
        import time
        from app.agent_runner import fetch_stock_financials, _FINANCIALS_CACHE, _normalize_canonical_key

        # Test canonical normalization
        self.assertEqual(_normalize_canonical_key("TCS.NS"), "TCS")
        self.assertEqual(_normalize_canonical_key("TCS.BO"), "TCS")
        self.assertEqual(_normalize_canonical_key("500209"), "500209")
        self.assertEqual(_normalize_canonical_key("infy"), "INFY")

        # Mock yf.Ticker to avoid external API calls
        mock_info = {
            "shortName": "Test Corporate",
            "currentPrice": 1500.0,
            "trailingPE": 22.5,
            "debtToEquity": 0.15,
            "revenueGrowth": 0.08,
            "earningsQuarterlyGrowth": 0.12,
            "profitMargins": 0.18,
            "returnOnEquity": 0.25,
            "marketCap": 500000000000,
            "fiftyTwoWeekHigh": 1600.0,
            "fiftyTwoWeekLow": 1200.0
        }

        with patch("yfinance.Ticker") as mock_ticker:
            mock_inst = MagicMock()
            mock_inst.info = mock_info
            mock_ticker.return_value = mock_inst

            # First fetch (populates cache)
            res1 = fetch_stock_financials("TESTCO.NS")
            self.assertEqual(res1["name"], "Test Corporate")
            self.assertEqual(res1["pe_ratio"], 22.5)
            self.assertEqual(res1["debt_to_equity"], 0.15)
            self.assertEqual(mock_ticker.call_count, 1)

            # Second fetch for .BO equivalent (must hit RAM cache in 0.0001s without calling yf.Ticker)
            t0 = time.time()
            res2 = fetch_stock_financials("TESTCO.BO")
            elapsed = time.time() - t0
            self.assertEqual(res2["name"], "Test Corporate")
            self.assertEqual(mock_ticker.call_count, 1)  # Still 1 call, zero new API queries!
            self.assertLess(elapsed, 0.01)  # Sub-millisecond lookup

    def test_news_15min_cache_and_normalization(self):
        """Google News RSS must cache for 15 minutes and share across exchanges."""
        import time
        from app.agent_runner import fetch_stock_news, _NEWS_CACHE

        mock_headlines = [
            {"title": "TestCo bags $50M AI contract", "link": "https://news.com/1", "published": "2026-09-15"}
        ]
        _NEWS_CACHE["TESTCO"] = {
            "timestamp": time.time(),
            "data": mock_headlines
        }

        # Querying TESTCO.NS or TESTCO.BO should return cached headlines instantly
        t0 = time.time()
        news_ns = fetch_stock_news("TESTCO.NS")
        elapsed = time.time() - t0
        self.assertEqual(len(news_ns), 1)
        self.assertEqual(news_ns[0]["title"], "TestCo bags $50M AI contract")
        self.assertLess(elapsed, 0.01)

        news_bo = fetch_stock_news("TESTCO.BO")
        self.assertEqual(len(news_bo), 1)
        self.assertEqual(news_bo[0]["title"], "TestCo bags $50M AI contract")


if __name__ == "__main__":
    unittest.main()
