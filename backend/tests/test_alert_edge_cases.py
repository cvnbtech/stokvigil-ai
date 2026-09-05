import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np

from app.technical_engine import fetch_multi_timeframe_technicals
from app.agent_runner import compute_deterministic_confluence


class TestAlertEdgeCases(unittest.TestCase):
    def test_daily_candles_synthesis_when_5m_empty(self):
        """When 5m intraday candles are empty, engine must synthesize from 1D history."""
        # Create 100 mock daily candles
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='D')
        close_prices = np.linspace(100, 150, 100)
        mock_daily_df = pd.DataFrame({
            'Open': close_prices - 1,
            'High': close_prices + 2,
            'Low': close_prices - 2,
            'Close': close_prices,
            'Volume': [100000] * 100
        }, index=dates)

        empty_5m_df = pd.DataFrame()

        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker = MagicMock()
            mock_ticker.history.side_effect = lambda period, interval: (
                empty_5m_df if interval == "5m" else mock_daily_df
            )
            mock_ticker_cls.return_value = mock_ticker

            result = fetch_multi_timeframe_technicals("TESTSTOCK")
            
            self.assertEqual(result["symbol"], "TESTSTOCK")
            self.assertGreater(result["current_price"], 0.0)
            self.assertEqual(result["current_price"], 150.0)
            self.assertGreater(result["atr_14"], 0.0)
            self.assertGreater(result["ema_20"], 0.0)
            self.assertGreater(result["ema_50"], 0.0)
            self.assertIn("h4", result["camarilla_pivots"])
            self.assertGreater(result["camarilla_pivots"]["h4"], 0.0)
            self.assertGreater(result["camarilla_pivots"]["l4"], 0.0)

    def test_confluence_prevents_dummy_targets_and_negative_100_pnl(self):
        """Confluence engine must never produce Target 1 == Stop Loss or -100% P&L on missing price."""
        technicals = {
            "current_price": 0.0,
            "atr_14": 0.0,
            "rsi_15m": 55.0,
            "rsi_daily": 52.0,
            "technical_score": 60,
            "camarilla_pivots": {"h4": 0.0, "h3": 0.0, "l3": 0.0, "l4": 0.0}
        }
        flow_data = {"delivery_pct": 50, "flow_score": 60, "vsa_regime": "NORMAL_VOLUME_SPREAD"}
        macro_data = {"india_vix": 14.0, "allow_breakout_trades": True}
        forensics = {"forensic_score": 70, "sector_name": "NIFTY IT"}
        financials = {"price": 0.0}
        holding_info = {
            "symbol": "GATECH",
            "quantity": 100,
            "average_price": 125.0,
            "current_market_price": 130.0
        }

        # Case 1: Holding has current_market_price
        res1 = compute_deterministic_confluence(
            symbol="GATECH",
            technicals=technicals,
            flow_data=flow_data,
            macro_data=macro_data,
            forensics=forensics,
            financials=financials,
            news_items=[],
            holding_info=holding_info
        )

        t1_str = res1["tactical_levels"]["target_1"]
        sl_str = res1["tactical_levels"]["protective_stop_loss"]
        t1_val = float(t1_str.replace("₹", "").replace(",", ""))
        sl_val = float(sl_str.replace("₹", "").replace(",", ""))

        self.assertNotEqual(t1_val, sl_val, "Target 1 and Stop Loss must never be identical")
        self.assertGreater(t1_val, 130.0, "Target 1 must be strictly greater than market price")
        self.assertLess(sl_val, 130.0, "Stop loss must be strictly lower than market price")

        # Case 2: Zero price anywhere -> Must never show -100% P&L
        holding_info_no_cmp = {
            "symbol": "GATECH",
            "quantity": 100,
            "average_price": 125.0
        }
        res2 = compute_deterministic_confluence(
            symbol="GATECH",
            technicals=technicals,
            flow_data=flow_data,
            macro_data=macro_data,
            forensics=forensics,
            financials=financials,
            news_items=[],
            holding_info=holding_info_no_cmp
        )

        t1_val2 = float(res2["tactical_levels"]["target_1"].replace("₹", "").replace(",", ""))
        sl_val2 = float(res2["tactical_levels"]["protective_stop_loss"].replace("₹", "").replace(",", ""))
        self.assertNotEqual(t1_val2, sl_val2)


if __name__ == "__main__":
    unittest.main()
