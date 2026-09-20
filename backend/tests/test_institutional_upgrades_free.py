"""
Unit and Integration Tests for StokVigil AI Institutional Upgrades:
1. Dynamic NSE & BSE Sector Universe Discovery
2. Mathematical 1% Position Sizing Engine
3. In-Memory Strategy Backtester Engine (Dual-Exchange NSE + BSE)
4. 03:45 PM Post-Market Closing Bell Telegram Digest
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Set UTF-8 encoding for Windows stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

# Set test environment to prevent vault production check abort
os.environ["ENVIRONMENT"] = "test"
os.environ["ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np

from app.macro_filter import (
    get_dynamic_sector_map,
    get_symbol_sector,
    calculate_sector_relative_strength,
    SECTOR_MAP,
    BSE_SCRIP_SECTOR_MAP
)
from app.agent_runner import compute_tactical_levels
from app.notifications import format_telegram_alert, format_post_market_summary_telegram
from app.backtester import (
    _resolve_exchange_candidates,
    calculate_rsi,
    calculate_atr,
    run_vectorized_strategy_backtest
)


class TestInstitutionalUpgrades(unittest.TestCase):

    # =========================================================================
    # 1. DYNAMIC SECTOR UNIVERSE & DUAL-EXCHANGE BSE RESOLUTION
    # =========================================================================

    def test_get_symbol_sector_nse_and_bse(self):
        """Tests that sector resolution works for NSE, BSE, bare, and 6-digit codes."""
        # NSE bare and .NS
        self.assertEqual(get_symbol_sector("HDFCBANK"), "NIFTY BANK")
        self.assertEqual(get_symbol_sector("HDFCBANK.NS"), "NIFTY BANK")
        self.assertEqual(get_symbol_sector("TCS"), "NIFTY IT")
        self.assertEqual(get_symbol_sector("TCS.NS"), "NIFTY IT")
        self.assertEqual(get_symbol_sector("TCS.BO"), "NIFTY IT")

        # BSE 6-digit scrips
        self.assertEqual(get_symbol_sector("500180"), "NIFTY BANK")  # HDFC Bank on BSE
        self.assertEqual(get_symbol_sector("500325"), "NIFTY ENERGY")  # Reliance on BSE
        self.assertEqual(get_symbol_sector("500209"), "NIFTY IT")  # Infosys on BSE
        self.assertEqual(get_symbol_sector("500570"), "NIFTY AUTO")  # Tata Motors on BSE

        # Unknown/Unmapped symbol returns None
        self.assertIsNone(get_symbol_sector("RANDOM_UNKNOWN_CO"))

    def test_calculate_sector_relative_strength_uses_dynamic_sector(self):
        """Tests that calculate_sector_relative_strength resolves BSE 6-digit scrips."""
        with patch("app.macro_filter.get_sector_20d_return", return_value=3.0):
            # Test with BSE 6-digit scrip for Reliance
            res = calculate_sector_relative_strength("500325", stock_20d_ret=8.5)
            self.assertEqual(res["sector_name"], "NIFTY ENERGY")
            self.assertEqual(res["sector_rs_rating"], 5.5)
            self.assertEqual(res["sector_rs_regime"], "SECTOR_LEADER")
            self.assertEqual(res["sector_trend"], "OUTPERFORMING")

    # =========================================================================
    # 2. MATHEMATICAL RISK-BASED POSITION SIZER (1% CAPITAL RULE)
    # =========================================================================

    def test_position_sizing_bullish_setup(self):
        """Tests position sizing calculation for standard BUY setup."""
        current_price = 1000.0
        atr = 20.0
        levels = compute_tactical_levels(
            current_price=current_price,
            atr_val=atr,
            action_bias="BUY_WATCH",
            risk_budget=2000.0
        )
        self.assertIsNotNone(levels)
        self.assertIn("recommended_quantity", levels)
        self.assertIn("capital_at_risk", levels)
        self.assertIn("estimated_position_value", levels)
        self.assertIn("risk_per_share", levels)
        self.assertIn("risk_budget", levels)

        # Stop loss is below price: price - 1.0 * atr = 980 (bounded to max 0.98 * price = 980)
        # Risk per share = 1000 - 980 = 20.0
        # Recommended quantity = 2000 // 20 = 100 shares
        self.assertEqual(levels["risk_per_share"], 20.0)
        self.assertEqual(levels["recommended_quantity"], 100)
        self.assertEqual(levels["capital_at_risk"], 2000.0)
        self.assertEqual(levels["estimated_position_value"], 100000.0)

    def test_position_sizing_sell_watch_setup(self):
        """Tests position sizing calculation for SELL_WATCH downside setup."""
        current_price = 2000.0
        atr = 30.0
        levels = compute_tactical_levels(
            current_price=current_price,
            atr_val=atr,
            action_bias="SELL_WATCH",
            risk_budget=3000.0
        )
        self.assertIsNotNone(levels)
        # Stop loss for sell is above price: price + 1.0 * atr = 2030, but bounded to at least 1.02 * price = 2040.0
        # Risk per share = 2040 - 2000 = 40.0
        # Recommended quantity = 3000 // 40 = 75 shares
        self.assertEqual(levels["risk_per_share"], 40.0)
        self.assertEqual(levels["recommended_quantity"], 75)
        self.assertEqual(levels["capital_at_risk"], 3000.0)

    def test_position_sizing_demat_portfolio_context(self):
        """Tests dynamic 1% risk budgeting based on user demat portfolio value."""
        current_price = 500.0
        atr = 10.0
        # Portfolio value ₹5,00,000 -> 1% risk budget = ₹5,000
        demat = {"portfolio_value": 500000.0, "is_in_portfolio": False}
        levels = compute_tactical_levels(
            current_price=current_price,
            atr_val=atr,
            demat_context=demat,
            action_bias="BUY_WATCH"
        )
        self.assertIsNotNone(levels)
        self.assertEqual(levels["risk_budget"], 5000.0)
        # Price 500, Stop Loss 490 (10 atr) -> risk per share = 10.0
        # Qty = 5000 // 10 = 500 shares
        self.assertEqual(levels["recommended_quantity"], 500)

    def test_telegram_alert_renders_position_sizing(self):
        """Tests that format_telegram_alert includes the 1% Position Sizing row."""
        tactical = {
            "entry_range": "₹995.00 - ₹1,005.00",
            "target_1": "₹1,030.00",
            "target_2": "₹1,050.00",
            "protective_stop_loss": "₹980.00",
            "risk_reward_ratio": "1:2.5",
            "recommended_quantity": 100,
            "capital_at_risk": 2000.0
        }
        msg = format_telegram_alert(
            symbol="RELIANCE.NS",
            alert_title="RELIANCE Camarilla H4 Breakout",
            action_bias="BUY_WATCH",
            confluence_score=85,
            catalyst_type="CAMARILLA_BREAKOUT",
            confluence_drivers=["Volume Expansion > 1.5x", "Camarilla H4 Cleared"],
            tactical_levels=tactical
        )
        self.assertIn("Position Sizing (1% Risk Rule):</b> 100 shares (Max Risk: ₹2,000.00)", msg)

    # =========================================================================
    # 3. IN-MEMORY STRATEGY BACKTESTER ENGINE
    # =========================================================================

    def test_resolve_exchange_candidates(self):
        """Tests dual-exchange candidate resolution for backtester."""
        self.assertEqual(_resolve_exchange_candidates("RELIANCE.NS"), ["RELIANCE.NS"])
        self.assertEqual(_resolve_exchange_candidates("TCS.BO"), ["TCS.BO"])
        self.assertEqual(_resolve_exchange_candidates("INFY"), ["INFY.NS", "INFY.BO"])
        self.assertEqual(_resolve_exchange_candidates("500325"), ["500325.BO", "500325.NS"])

    def test_backtester_with_synthetic_ohlcv(self):
        """Tests vectorized backtest calculations with known price sequence."""
        # Generate 60 days of synthetic price data with an upward breakout
        np.random.seed(42)
        dates = pd.date_range(start="2025-01-01", periods=60, freq="D")
        close_prices = 100.0 + np.cumsum(np.random.normal(0.5, 1.0, 60))
        # Inject deliberate breakout on bar 30
        close_prices[30:] += 15.0

        df = pd.DataFrame({
            "Open": close_prices - 0.5,
            "High": close_prices + 2.0,
            "Low": close_prices - 2.0,
            "Close": close_prices,
            "Volume": [1000000 + i * 20000 for i in range(60)]
        }, index=dates)

        with patch("yfinance.Ticker") as mock_ticker:
            mock_inst = MagicMock()
            mock_inst.history.return_value = df
            mock_ticker.return_value = mock_inst

            res = run_vectorized_strategy_backtest(
                symbol="TESTSTOCK.NS",
                period="6mo",
                interval="1d",
                strategy="camarilla_breakout",
                initial_capital=200000.0,
                risk_budget=2000.0
            )

            self.assertEqual(res["status"], "success")
            self.assertEqual(res["symbol"], "TESTSTOCK.NS")
            self.assertIn("win_rate_pct", res)
            self.assertIn("total_trades", res)
            self.assertIn("profit_factor", res)
            self.assertIn("max_drawdown_pct", res)
            self.assertIn("sharpe_ratio", res)
            self.assertIn("equity_curve", res)
            self.assertGreater(len(res["equity_curve"]), 0)

    def test_backtester_zero_default_on_empty(self):
        """Tests zero-default policy: returns clean error if data is empty."""
        with patch("yfinance.Ticker") as mock_ticker:
            mock_inst = MagicMock()
            mock_inst.history.return_value = pd.DataFrame()
            mock_ticker.return_value = mock_inst

            res = run_vectorized_strategy_backtest(
                symbol="UNLISTED_CO",
                period="1y"
            )
            self.assertEqual(res["status"], "error")
            self.assertIn("Insufficient historical market data", res["message"])
            self.assertEqual(res["total_trades"], 0)
            self.assertEqual(res["win_rate_pct"], 0.0)

    # =========================================================================
    # 4. 03:45 PM POST-MARKET EXECUTIVE TELEGRAM DIGEST
    # =========================================================================

    def test_format_post_market_summary_telegram(self):
        """Tests that post-market summary formats cleanly with all metrics."""
        data = {
            "date": "2026-09-20",
            "nifty_price": 25350.75,
            "nifty_change_pct": 0.65,
            "sensex_price": 82890.10,
            "sensex_change_pct": 0.58,
            "india_vix": 12.45,
            "vix_regime": "LOW_VOLATILITY",
            "adr_ratio": 1.68,
            "advances": 1850,
            "declines": 1100,
            "breadth_regime": "STRONG_BULLISH_BREADTH",
            "fii_net_cr": 1420.50,
            "dii_net_cr": 890.25,
            "fii_dii_sentiment": "STRONG_INSTITUTIONAL_BUYING",
            "total_scans_today": 84,
            "alerts_fired_today": 6,
            "target_1_hit_rate_pct": 83.3,
            "top_sectors": [{"name": "NIFTY BANK", "change_pct": 1.8}],
            "laggard_sectors": [{"name": "NIFTY IT", "change_pct": -0.4}],
            "notable_movers": [{"symbol": "TCS.BO", "change_pct": 2.1, "bias": "CAMARILLA_BREAKOUT"}]
        }

        html = format_post_market_summary_telegram(data)
        self.assertIn("POST-MARKET EXECUTIVE SUMMARY", html)
        self.assertIn("NIFTY 50:</b> ₹25,350.75 (<b>+0.65%</b>)", html)
        self.assertIn("BSE SENSEX:</b> 82,890.10 (<b>+0.58%</b>)", html)
        self.assertIn("India VIX:</b> 12.45", html)
        self.assertIn("ADR: 1.68", html)
        self.assertIn("FII Net:</b> +₹1,420.50 Cr", html)
        self.assertIn("Target 1 Mathematical Hit Rate:</b> <b>83.3%</b>", html)
        self.assertIn("NIFTY BANK", html)
        self.assertIn("TCS.BO", html)

    def test_post_market_summary_zero_default_adherence(self):
        """Tests that post-market summary cleanly handles missing feeds without crashing."""
        data = {
            "date": "2026-09-20",
            "nifty_price": None,
            "sensex_price": None,
            "india_vix": None,
            "advances": None,
            "declines": None,
            "fii_net_cr": None,
            "dii_net_cr": None,
            "total_scans_today": 75,
            "alerts_fired_today": 0
        }
        html = format_post_market_summary_telegram(data)
        self.assertIn("POST-MARKET EXECUTIVE SUMMARY", html)
        self.assertNotIn("₹0.00", html)
        self.assertNotIn("None", html)


if __name__ == "__main__":
    unittest.main()
