import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app, get_supabase
from app.config import settings
from app.macro_filter import fetch_pre_market_war_room_data
from app.notifications import format_pre_market_war_room_telegram
from app.agent_runner import compute_deterministic_confluence


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

    def not_(self, *args, **kwargs):
        return self

    def is_(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        if self.table_name == "profiles":
            return MockDBResult([{
                "id": "test-user-123",
                "email": "trader@stokvigil.com",
                "telegram_chat_id": "999888777",
                "telegram_enabled": True,
                "fcm_device_token": "test_fcm_token",
                "fcm_enabled": True,
            }])
        return MockDBResult([])


class MockSupabaseClient:
    def table(self, table_name):
        return MockDBTable(table_name)


class TestPhase1Features(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_db = MockSupabaseClient()
        app.dependency_overrides[get_supabase] = lambda: cls.mock_db
        settings.CRON_SECRET_KEY = "test_cron_secret_2026"
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    def test_pre_market_war_room_data_structure(self):
        """Pre-market war room data must contain domestic, global, and sectoral indicators."""
        data = fetch_pre_market_war_room_data()
        self.assertIn("date", data)
        self.assertIn("nifty_price", data)
        self.assertIn("india_vix", data)
        self.assertIn("global_cues", data)
        self.assertIn("leading_sectors", data)
        self.assertIn("tactical_guidance", data)
        self.assertIsInstance(data["global_cues"], dict)
        self.assertIn("bias", data["global_cues"])

    def test_format_pre_market_war_room_telegram(self):
        """HTML formatted war room card must contain core headers and valid HTML."""
        sample_data = {
            "date": "2026-09-06",
            "nifty_price": 24500.0,
            "nifty_change_pct": 0.45,
            "sensex_price": 80100.0,
            "sensex_change_pct": 0.40,
            "india_vix": 13.8,
            "vix_regime": "LOW_VOLATILITY_TRENDING",
            "allow_breakout_trades": True,
            "global_cues": {
                "dow_jones_pct": 0.60,
                "nasdaq_pct": 0.75,
                "nikkei_pct": 1.10,
                "bias": "BULLISH_TAILWINDS"
            },
            "leading_sectors": [
                {"name": "NIFTY AUTO", "change_pct": 1.25},
                {"name": "NIFTY IT", "change_pct": 0.85}
            ],
            "tactical_guidance": "Favorable bullish tailwinds. Prioritize Smart Money Absorption."
        }
        msg = format_pre_market_war_room_telegram(sample_data)
        self.assertIn("PRE-MARKET WAR ROOM BRIEFING", msg)
        self.assertIn("NIFTY 50", msg)
        self.assertIn("+0.45%", msg)
        self.assertIn("BULLISH TAILWINDS", msg)
        self.assertIn("NIFTY AUTO", msg)

    def test_pre_market_briefing_endpoint_auth(self):
        """POST /api/cron/pre-market-briefing must reject unauthorized triggers and process authorized ones."""
        # 1. Reject missing secret
        res = self.client.post("/api/cron/pre-market-briefing")
        self.assertEqual(res.status_code, 403)

        # 2. Reject incorrect secret
        res = self.client.post(
            "/api/cron/pre-market-briefing",
            headers={"X-Cron-Secret": "wrong_secret_123"}
        )
        self.assertEqual(res.status_code, 403)

        # 3. Accept valid secret and execute briefing
        with patch("app.main.send_telegram_notification") as mock_tg, \
             patch("app.main.send_fcm_notification") as mock_fcm:
            mock_tg.return_value = True
            mock_fcm.return_value = True
            res = self.client.post(
                "/api/cron/pre-market-briefing",
                headers={"X-Cron-Secret": "test_cron_secret_2026"}
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data.get("status"), "completed")
            self.assertIn("briefed_users_count", data)

    def test_factor_breakdown_in_confluence(self):
        """Deterministic confluence must return factor_breakdown with all 4 component scores."""
        result = compute_deterministic_confluence(
            symbol="TESTSYM",
            technicals={"current_price": 1000.0, "technical_score": 75, "rsi_15m": 55, "vwap": 995.0, "atr_14": 15.0},
            flow_data={"flow_score": 70, "delivery_pct": 58.0, "vsa_regime": "SMART_MONEY_ABSORPTION"},
            macro_data={"allow_breakout_trades": True},
            forensics={"forensic_score": 80, "sector_name": "NIFTY AUTO"},
            financials={"pe_ratio": 22.0, "debt_to_equity": 0.3},
            news_items=[]
        )
        self.assertIn("factor_breakdown", result)
        fb = result["factor_breakdown"]
        self.assertIn("technicals", fb)
        self.assertIn("flow", fb)
        self.assertIn("forensics", fb)
        self.assertIn("catalysts", fb)
        self.assertGreater(fb["technicals"], 0)
        self.assertGreater(fb["flow"], 0)
        self.assertGreater(fb["forensics"], 0)


if __name__ == "__main__":
    unittest.main()
