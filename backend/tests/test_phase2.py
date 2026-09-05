import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import pandas as pd

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app, get_supabase
from app.config import settings
from app.fii_dii_tracker import classify_institutional_sentiment, fetch_daily_fii_dii_flows


class MockDBResult:
    def __init__(self, data=None):
        self.data = data or []


class MockDBTable:
    def __init__(self, table_name):
        self.table_name = table_name

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        if self.table_name == "stok_alerts":
            return MockDBResult([{
                "id": "alert-test-01",
                "symbol": "RELIANCE",
                "alert_title": "RELIANCE: Smart Money Breakout Above H4",
                "catalyst_type": "TECHNICAL_BREAKOUT",
                "impact_score": 85,
                "metrics_snapshot": {
                    "action_bias": "STRONG_BUY",
                    "tactical_levels": {
                        "entry_range": "₹1,320.00 - ₹1,325.00",
                        "target_1": "₹1,365.00",
                        "protective_stop_loss": "₹1,302.00",
                        "risk_reward_ratio": "1:2.8"
                    }
                },
                "created_at": "2026-09-05T09:35:00Z"
            }])
        elif self.table_name == "fii_dii_flows":
            return MockDBResult([{
                "trade_date": "2026-09-05",
                "fii_buy_cr": 12500.0,
                "fii_sell_cr": 11000.0,
                "fii_net_cr": 1500.0,
                "dii_buy_cr": 9500.0,
                "dii_sell_cr": 8500.0,
                "dii_net_cr": 1000.0,
                "combined_net_cr": 2500.0,
                "sentiment_bias": "STRONG_ACCUMULATION"
            }])
        return MockDBResult([])


class MockSupabaseClient:
    def table(self, table_name):
        return MockDBTable(table_name)


class TestPhase2Features(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_db = MockSupabaseClient()
        app.dependency_overrides[get_supabase] = lambda: cls.mock_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    def test_institutional_sentiment_classification(self):
        """FII/DII sentiment logic must correctly classify accumulation vs distribution."""
        # Strong institutional accumulation
        self.assertEqual(classify_institutional_sentiment(1500.0, 500.0), "STRONG_ACCUMULATION")
        # Heavy distribution
        self.assertEqual(classify_institutional_sentiment(-1200.0, -500.0), "HEAVY_DISTRIBUTION")
        # Domestic defending
        self.assertEqual(classify_institutional_sentiment(-800.0, 600.0), "DOMESTIC_DII_SUPPORT_DEFENDING")

    def test_fii_dii_flows_endpoint(self):
        """GET /api/market/fii-dii-flows must return institutional net flow metrics and history."""
        res = self.client.get("/api/market/fii-dii-flows")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("fii", data)
        self.assertIn("dii", data)
        self.assertIn("combined_net", data)
        self.assertIn("sentiment", data)
        self.assertIn("history", data)
        self.assertIsInstance(data["history"], list)
        self.assertGreater(len(data["history"]), 0)

    def test_accuracy_ledger_endpoint(self):
        """GET /api/market/accuracy-ledger must return audited non-custodial performance stats."""
        res = self.client.get("/api/market/accuracy-ledger")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("audited_summary", data)
        self.assertIn("ledger", data)
        summary = data["audited_summary"]
        self.assertIn("win_rate_pct", summary)
        self.assertIn("total_verified_signals", summary)
        self.assertIn("avg_risk_reward", summary)
        self.assertGreater(summary["win_rate_pct"], 50.0)

    def test_stock_candles_endpoint_validation(self):
        """GET /api/stocks/candles must reject malicious/invalid symbols with HTTP 400."""
        res = self.client.get("/api/stocks/candles?symbol=INVALID$$$STOCK")
        self.assertEqual(res.status_code, 400)

    def test_stock_candles_endpoint_success(self):
        """GET /api/stocks/candles must return OHLCV candles with Camarilla, VWAP, and Chandelier SL."""
        # Mock yfinance ticker history
        dummy_df = pd.DataFrame({
            "Open": [100.0, 102.0, 101.5],
            "High": [103.0, 104.5, 103.0],
            "Low": [99.5, 101.0, 101.0],
            "Close": [102.0, 101.5, 102.8],
            "Volume": [10000, 15000, 12000]
        }, index=pd.date_range("2026-09-05 09:15:00", periods=3, freq="5min"))

        with patch("yfinance.Ticker") as mock_ticker:
            mock_inst = MagicMock()
            mock_inst.history.return_value = dummy_df
            mock_ticker.return_value = mock_inst

            res = self.client.get("/api/stocks/candles?symbol=RELIANCE&interval=5m&period=1d")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["symbol"], "RELIANCE")
            self.assertIn("candles", data)
            self.assertIn("camarilla", data)
            self.assertGreater(len(data["candles"]), 0)
            candle = data["candles"][0]
            self.assertIn("open", candle)
            self.assertIn("high", candle)
            self.assertIn("low", candle)
            self.assertIn("close", candle)
            self.assertIn("vwap", candle)
            self.assertIn("chandelier_sl", candle)


if __name__ == "__main__":
    unittest.main()
