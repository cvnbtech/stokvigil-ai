import sys
import os
import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

# Set UTF-8 encoding for Windows stdout
sys.stdout.reconfigure(encoding='utf-8')

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app, get_supabase
from app.auth import get_current_user_id
from app.config import settings
from app.vault import vault

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

    def insert(self, payload, *args, **kwargs):
        return self

    def update(self, payload, *args, **kwargs):
        return self

    def upsert(self, payload, *args, **kwargs):
        return self

    def delete(self, *args, **kwargs):
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
                "fcm_device_token": "fcm_test_tok",
                "fcm_enabled": True,
                "telegram_chat_id": "999888777",
                "telegram_enabled": True,
                "alert_sensitivity": "HIGH",
                "execution_mode": "INSTANT",
                "demat_auto_sync": True,
                "tnc_accepted": True
            }])
        elif self.table_name == "user_credentials":
            return MockDBResult([{
                "id": "cred-123",
                "user_id": "test-user-123",
                "encrypted_app_key": vault.encrypt("TEST_APP_KEY"),
                "encrypted_secret_key": vault.encrypt("TEST_SECRET_KEY"),
                "encrypted_session_token": vault.encrypt("TEST_SESSION_TOKEN"),
                "token_date": "2026-09-05"
            }])
        elif self.table_name == "user_watchlists":
            return MockDBResult([
                {"symbol": "RELIANCE", "is_auto_synced": True},
                {"symbol": "TCS", "is_auto_synced": False}
            ])
        elif self.table_name == "stok_alerts":
            return MockDBResult([{
                "id": "alert-1",
                "user_id": "test-user-123",
                "symbol": "RELIANCE",
                "alert_title": "RELIANCE: Technical Breakout",
                "catalyst_type": "TECHNICAL_BREAKOUT",
                "impact_score": 82,
                "created_at": "2026-09-05T10:00:00Z"
            }])
        return MockDBResult([])

class MockSupabaseClient:
    def __init__(self):
        self.auth = MagicMock()
        self.auth.admin = MagicMock()
        self.auth.admin.delete_user.return_value = True

    def table(self, table_name):
        return MockDBTable(table_name)

class TestApiEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_db = MockSupabaseClient()
        app.dependency_overrides[get_supabase] = lambda: cls.mock_db
        # By default authenticate as test-user-123
        app.dependency_overrides[get_current_user_id] = lambda: "test-user-123"
        settings.CRON_SECRET_KEY = "test_cron_secret_2026"
        settings.TELEGRAM_WEBHOOK_SECRET = "test_telegram_secret_2026"
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    # 1. Health Check
    def test_01_health_check(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "online")
        self.assertIn("Non-Advisory", data["mode"])

    # 2. Market Cache Stats
    def test_02_market_cache_stats(self):
        res = self.client.get("/api/market/cache-stats")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "active")
        self.assertIn("cache_stats", data)

    # 3. Live Stock Search
    def test_03_stock_search(self):
        res = self.client.get("/api/stocks/search?q=RELIANCE")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("stocks", data)
        self.assertGreater(len(data["stocks"]), 0)
        self.assertEqual(data["stocks"][0]["symbol"], "RELIANCE")

    # 4. Live Stock Validation
    def test_04_stock_validate(self):
        res = self.client.get("/api/stocks/validate?symbol=RELIANCE")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("is_valid", False))

    # 5. Live Stock Quotes
    def test_05_stock_quotes(self):
        res = self.client.get("/api/stocks/quotes?symbols=RELIANCE,TCS")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("quotes", data)
        self.assertIn("RELIANCE", data["quotes"])
        self.assertIn("price", data["quotes"]["RELIANCE"])

    # 6. User Profile - Authorized
    def test_06_user_profile_authorized(self):
        res = self.client.get("/api/user/profile?user_id=test-user-123")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["profile"]["id"], "test-user-123")

    # 7. User Profile - IDOR Protection (BOLA)
    def test_07_user_profile_idor_blocked(self):
        res = self.client.get("/api/user/profile?user_id=attacker-user-999")
        self.assertEqual(res.status_code, 403)
        self.assertIn("Access forbidden", res.json()["detail"])

    # 8. Device Registration - Authorized
    def test_08_register_device(self):
        payload = {
            "user_id": "test-user-123",
            "fcm_device_token": "new_fcm_token_xyz",
            "fcm_enabled": True,
            "telegram_chat_id": "12345678",
            "telegram_enabled": True,
            "alert_sensitivity": "HIGH",
            "execution_mode": "INSTANT",
            "demat_auto_sync": True
        }
        res = self.client.post("/api/auth/register-device", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")

    # 9. Get User Credentials - Authorized with Vault Decryption
    def test_09_get_user_credentials(self):
        res = self.client.get("/api/user/credentials?user_id=test-user-123")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["has_credentials"])
        self.assertEqual(data["app_key"], "TEST_APP_KEY")
        self.assertEqual(data["secret_key"], "TEST_SECRET_KEY")

    # 10. Save User Credentials - Authorized with Vault Encryption
    def test_10_save_user_credentials(self):
        payload = {
            "user_id": "test-user-123",
            "app_key": "NEW_APP_KEY",
            "secret_key": "NEW_SECRET_KEY",
            "session_token": "NEW_SESSION_TOKEN"
        }
        res = self.client.post("/api/user/credentials", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")

    # 11. 5-Minute Cron - Missing X-Cron-Secret Blocked
    def test_11_cron_multi_user_scan_missing_secret(self):
        res = self.client.post("/api/cron/multi-user-scan")
        self.assertEqual(res.status_code, 403)

    # 12. 5-Minute Cron - Invalid X-Cron-Secret Blocked
    def test_12_cron_multi_user_scan_invalid_secret(self):
        res = self.client.post("/api/cron/multi-user-scan", headers={"X-Cron-Secret": "invalid_bad_key"})
        self.assertEqual(res.status_code, 403)

    # 13. Morning Token Reminder - Missing X-Cron-Secret Blocked
    def test_13_morning_token_reminder_missing_secret(self):
        res = self.client.post("/api/cron/morning-token-reminder")
        self.assertEqual(res.status_code, 403)

    # 14. Morning Token Reminder - Authorized
    def test_14_morning_token_reminder_authorized(self):
        res = self.client.post(
            "/api/cron/morning-token-reminder",
            headers={"X-Cron-Secret": settings.CRON_SECRET_KEY}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "completed")

    # 15. Telegram Webhook - /start <USER_ID> linking
    def test_15_telegram_webhook(self):
        webhook_headers = {"X-Telegram-Bot-Api-Secret-Token": settings.TELEGRAM_WEBHOOK_SECRET}
        payload = {
            "update_id": 10001,
            "message": {
                "message_id": 1,
                "chat": {"id": 12345678, "type": "private"},
                "from": {"id": 12345678, "first_name": "Trader"},
                "text": "/start test-user-123"
            }
        }
        res = self.client.post("/api/telegram/webhook", json=payload, headers=webhook_headers)
        self.assertEqual(res.status_code, 200)

    # 16. User Accuracy Stats - Authorized
    def test_16_accuracy_stats(self):
        res = self.client.get("/api/user/accuracy-stats?user_id=test-user-123")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("win_rate_estimate_pct", data)

    # 17. User Alerts Ledger - Authorized
    def test_17_user_alerts(self):
        res = self.client.get("/api/user/alerts?user_id=test-user-123")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("alerts", data)
        self.assertIsInstance(data["alerts"], list)

    # 18. Order Placement - IDOR Protected
    def test_18_order_placement_idor_blocked(self):
        order_payload = {
            "user_id": "other-user-999",
            "symbol": "RELIANCE",
            "action": "BUY",
            "quantity": 10,
            "order_type": "MARKET"
        }
        res = self.client.post("/api/v1/orders/place", json=order_payload)
        self.assertEqual(res.status_code, 403)

    # 19. Delete Account - Authorized
    def test_19_delete_account(self):
        res = self.client.post("/api/user/delete-account", json={"user_id": "test-user-123"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")

if __name__ == "__main__":
    unittest.main()
