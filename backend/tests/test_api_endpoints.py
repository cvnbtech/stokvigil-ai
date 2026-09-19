import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Set UTF-8 encoding for Windows stdout
sys.stdout.reconfigure(encoding='utf-8')

# Set test environment to prevent vault production check abort
os.environ["ENVIRONMENT"] = "test"
os.environ["ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app, get_supabase
from app.auth import get_current_user_id, mask_id, mask_telegram_token
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

    def lt(self, *args, **kwargs):
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
        cls.orig_env = settings.ENVIRONMENT
        settings.ENVIRONMENT = "test"
        cls.mock_db = MockSupabaseClient()
        app.dependency_overrides[get_supabase] = lambda: cls.mock_db
        # By default authenticate as test-user-123
        app.dependency_overrides[get_current_user_id] = lambda: "test-user-123"
        settings.CRON_SECRET_KEY = "test_cron_secret_2026"
        settings.TELEGRAM_WEBHOOK_SECRET = "test_telegram_secret_2026"
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        settings.ENVIRONMENT = cls.orig_env
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
        q = data["quotes"]["RELIANCE"]
        self.assertIn("price", q)
        self.assertIn("target", q)
        self.assertIn("stop_loss", q)
        self.assertIn("signal", q)
        self.assertIn("signal_type", q)
        self.assertIn("disclaimer", q)
        if q.get("price") and q["price"] > 0:
            self.assertIsNotNone(q["target"])
            self.assertIsNotNone(q["stop_loss"])
            self.assertIsNotNone(q["signal"])
            self.assertIn(q["signal"], ["HOLD", "BUY", "STRONG BUY", "ACCUMULATE", "SELL", "PULLBACK WATCH"])

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

    # 9. Get User Credentials - Authorized with Master App Publisher Model
    def test_09_get_user_credentials(self):
        res = self.client.get("/api/user/credentials?user_id=test-user-123")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["has_credentials"])
        self.assertIn("login_url", data)
        self.assertEqual(data.get("broker"), "icici")

    # 10. Save User Credentials - Authorized with Vault Encryption (Pure Master Model)
    def test_10_save_user_credentials(self):
        payload = {
            "user_id": "test-user-123",
            "session_token": "NEW_SESSION_TOKEN",
            "broker": "icici"
        }
        res = self.client.post("/api/user/credentials", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data.get("broker"), "icici")

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
        data = res.json()
        self.assertEqual(data["status"], "linked")
        self.assertEqual(data["user_param"], "***-123")
        self.assertEqual(data["chat_id"], "***5678")

    # 15b. Telegram Webhook - Rejects Email linking for security
    def test_15b_telegram_webhook_rejects_email(self):
        webhook_headers = {"X-Telegram-Bot-Api-Secret-Token": settings.TELEGRAM_WEBHOOK_SECRET}
        payload = {
            "update_id": 10002,
            "message": {
                "message_id": 2,
                "chat": {"id": 12345678, "type": "private"},
                "from": {"id": 12345678, "first_name": "Attacker"},
                "text": "/start victim@example.com"
            }
        }
        res = self.client.post("/api/telegram/webhook", json=payload, headers=webhook_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "rejected")
        self.assertEqual(data["reason"], "email_not_permitted")

    # 15c. Mask ID utility unit tests
    def test_15c_mask_id_utility(self):
        self.assertEqual(mask_id("987654321"), "***4321")
        self.assertEqual(mask_id("test-user-123"), "***-123")
        self.assertEqual(mask_id("5000"), "***5000")
        self.assertEqual(mask_id("500"), "***500")
        self.assertEqual(mask_id("12"), "***12")
        self.assertEqual(mask_id(""), "***")
        self.assertEqual(mask_id(None), "***")

    # 15d. Mask Telegram Bot Token in URLs utility tests
    def test_15d_mask_telegram_token(self):
        sample_url = "https://api.telegram.org/bot967613667:ASS4z7iSupOe6ZzDxfSbS7bWJuYnMcVsAM4/sendMessage"
        masked = mask_telegram_token(sample_url)
        self.assertEqual(masked, "https://api.telegram.org/bot***sAM4/sendMessage")
        self.assertNotIn("ASS4z7iSupOe6ZzDxfSbS7bWJuYnMcVsAM4", masked)

        # Test other endpoints and short tokens
        self.assertEqual(
            mask_telegram_token("https://api.telegram.org/bot12345/getMe"),
            "https://api.telegram.org/bot***2345/getMe"
        )
        self.assertEqual(
            mask_telegram_token("https://api.telegram.org/bot123/setWebhook"),
            "https://api.telegram.org/bot***123/setWebhook"
        )
        self.assertEqual(mask_telegram_token(""), "")
        self.assertEqual(mask_telegram_token(None), "")

    # 15e. SensitiveDataFilter tests with custom object and URL in record.args
    def test_15e_sensitive_data_filter(self):
        from app.auth import SensitiveDataFilter
        import logging
        import httpx

        f = SensitiveDataFilter()
        
        # Test 1: LogRecord with httpx.URL in args (exactly how httpx emits logs)
        raw_url = httpx.URL("https://api.telegram.org/bot967613667:ASS4z7iSupOe6ZzDxfSbS7bWJuYnMcVsAM4/sendMessage")
        record = logging.LogRecord(
            name="httpx",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg='HTTP Request: %s %s "%s %d %s"',
            args=('POST', raw_url, 'HTTP/1.1', 200, 'OK'),
            exc_info=None
        )
        self.assertTrue(f.filter(record))
        self.assertNotIn("ASS4z7iSupOe6ZzDxfSbS7bWJuYnMcVsAM4", record.getMessage())
        self.assertIn("***sAM4", record.getMessage())

        # Test 2: LogRecord with direct string in msg
        record2 = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=2,
            msg="Telegram error at https://api.telegram.org/bot12345/getMe",
            args=(),
            exc_info=None
        )
        self.assertTrue(f.filter(record2))
        self.assertIn("***2345", record2.getMessage())

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

    # 20. Security: Malformed Authorization Header Rejected (Non-Bearer format)
    def test_20_malformed_auth_header_rejected(self):
        orig_env = settings.ENVIRONMENT
        orig_override = app.dependency_overrides.pop(get_current_user_id, None)
        try:
            settings.ENVIRONMENT = "production"
            res = self.client.get(
                "/api/user/profile?user_id=test-user-123",
                headers={"Authorization": "Basic dXNlcjpwYXNz"}
            )
            self.assertEqual(res.status_code, 401)
            self.assertIn("Invalid Authorization header format", res.json().get("detail", ""))
        finally:
            settings.ENVIRONMENT = orig_env
            if orig_override is not None:
                app.dependency_overrides[get_current_user_id] = orig_override

    # 21. Security: Telegram Webhook Secret Mismatch Blocked
    def test_21_telegram_webhook_mismatched_secret_blocked(self):
        orig_secret = settings.TELEGRAM_WEBHOOK_SECRET
        try:
            settings.TELEGRAM_WEBHOOK_SECRET = "super_secure_webhook_secret_999"
            payload = {
                "update_id": 99999,
                "message": {"chat": {"id": 12345}, "text": "/start test-user-123"}
            }
            res = self.client.post(
                "/api/telegram/webhook",
                json=payload,
                headers={"X-Telegram-Bot-Api-Secret-Token": "attacker_wrong_token"}
            )
            self.assertEqual(res.status_code, 403)
        finally:
            settings.TELEGRAM_WEBHOOK_SECRET = orig_secret

    # 22. Security: Telegram HTML Alert Injection & Entity Escaping
    def test_22_telegram_alert_html_escaping(self):
        from app.notifications import format_telegram_alert
        card = format_telegram_alert(
            symbol="TCS",
            alert_title="Malicious <script>alert('pwned')</script> & Stock",
            action_bias="BUY_WATCH",
            confluence_score=85,
            catalyst_type="BREAKOUT_<TAG>",
            confluence_drivers=["Exchange Filing: Q3 Profit > 50% & Debt < 0.2"],
            holding_guidance="Hold target < 4000 & SL > 3500"
        )
        self.assertNotIn("<script>", card)
        self.assertIn("&lt;script&gt;", card)
        self.assertIn("&amp;", card)
        self.assertIn("&gt;", card)
        self.assertIn("&lt;", card)

    # 23. Security: Cron Secret Production Placeholder Blocked
    def test_23_cron_secret_production_placeholder_enforcement(self):
        orig_env = settings.ENVIRONMENT
        orig_key = settings.CRON_SECRET_KEY
        try:
            settings.ENVIRONMENT = "production"
            settings.CRON_SECRET_KEY = "stokvigil_cron_default_secret_2026"
            res = self.client.post(
                "/api/cron/multi-user-scan",
                headers={"X-Cron-Secret": "stokvigil_cron_default_secret_2026"}
            )
            self.assertEqual(res.status_code, 503)
            self.assertIn("Cron service is unconfigured in production mode", res.json().get("detail", ""))

            # With dedicated production key, authorized call succeeds
            settings.CRON_SECRET_KEY = "production_dedicated_secret_key_abc123"
            res_auth = self.client.post(
                "/api/cron/multi-user-scan",
                headers={"X-Cron-Secret": "production_dedicated_secret_key_abc123"}
            )
            self.assertEqual(res_auth.status_code, 200)
        finally:
            settings.ENVIRONMENT = orig_env
            settings.CRON_SECRET_KEY = orig_key

    # 24. Security: Order Placement Honest Error in Production
    def test_24_order_placement_production_honest_error(self):
        orig_env = settings.ENVIRONMENT
        try:
            settings.ENVIRONMENT = "production"
            order_payload = {
                "user_id": "test-user-123",
                "symbol": "TCS",
                "action": "BUY",
                "quantity": 5,
                "order_type": "MARKET"
            }
            # When BreezeConnect fails or credentials invalid in production, raises 502
            res = self.client.post("/api/v1/orders/place", json=order_payload)
            self.assertEqual(res.status_code, 502)
            self.assertIn("Broker order placement failed", res.json().get("detail", ""))
        finally:
            settings.ENVIRONMENT = orig_env

    # 25. Security: Market Cache Stats Redacted for Public Unauthenticated Callers
    def test_25_market_cache_stats_redacted_for_public(self):
        res = self.client.get("/api/market/cache-stats")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "active")
        self.assertIn("cache_stats", data)
        self.assertEqual(data["cached_symbols"], "[REDACTED - Administrator Authentication Required]")
        self.assertFalse(data["admin_access"])

    # 26. Security: Market Cache Stats Accessible for Authenticated Administrators
    def test_26_market_cache_stats_authorized_for_admin(self):
        orig_admin = settings.ADMIN_SECRET_KEY
        try:
            settings.ADMIN_SECRET_KEY = "test-admin-secret"
            # 1. Via X-Admin-Secret
            res_admin = self.client.get(
                "/api/market/cache-stats",
                headers={"X-Admin-Secret": "test-admin-secret"}
            )
            self.assertEqual(res_admin.status_code, 200)
            data_admin = res_admin.json()
            self.assertTrue(data_admin["admin_access"])
            self.assertIsInstance(data_admin["cached_symbols"], list)

            # 2. Via X-Cron-Secret
            res_cron = self.client.get(
                "/api/market/cache-stats",
                headers={"X-Cron-Secret": settings.active_cron_secret}
            )
            self.assertEqual(res_cron.status_code, 200)
            data_cron = res_cron.json()
            self.assertTrue(data_cron["admin_access"])
            self.assertIsInstance(data_cron["cached_symbols"], list)
        finally:
            settings.ADMIN_SECRET_KEY = orig_admin

    # 27. Security & Integrity: Order Placement Idempotency Replay
    def test_27_order_placement_idempotency_replay(self):
        order_payload = {
            "user_id": "test-user-123",
            "symbol": "INFY",
            "action": "BUY",
            "quantity": 10,
            "order_type": "MARKET",
            "idempotency_key": "test-idempotency-key-001"
        }
        # First attempt: Fresh execution
        res1 = self.client.post("/api/v1/orders/place", json=order_payload)
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertEqual(data1["status"], "simulated")
        self.assertFalse(data1.get("idempotent_replay", False))

        # Second attempt with same idempotency key: Returns cached execution with idempotent_replay=True
        res2 = self.client.post(
            "/api/v1/orders/place",
            json=order_payload,
            headers={"X-Idempotency-Key": "test-idempotency-key-001"}
        )
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertEqual(data2["status"], "simulated")
        self.assertTrue(data2.get("idempotent_replay", False))
        self.assertEqual(data2["symbol"], "INFY")

    # 28. Security & Integrity: Order Placement Concurrent In-Flight Conflict
    def test_28_order_placement_concurrent_conflict(self):
        from app.main import _ORDER_IDEMPOTENCY_CACHE, _ORDER_IDEMPOTENCY_LOCK
        import time

        flight_key = "custom:test-user-123:inflight-key-999"
        with _ORDER_IDEMPOTENCY_LOCK:
            _ORDER_IDEMPOTENCY_CACHE[flight_key] = {
                "status": "in_flight",
                "timestamp": time.time(),
                "ttl": 60.0,
                "response": None,
                "user_id": "test-user-123"
            }

        try:
            order_payload = {
                "user_id": "test-user-123",
                "symbol": "INFY",
                "action": "BUY",
                "quantity": 10,
                "order_type": "MARKET",
                "idempotency_key": "inflight-key-999"
            }
            res = self.client.post("/api/v1/orders/place", json=order_payload)
            self.assertEqual(res.status_code, 409)
            self.assertIn("in progress", res.json().get("detail", "").lower())
        finally:
            with _ORDER_IDEMPOTENCY_LOCK:
                _ORDER_IDEMPOTENCY_CACHE.pop(flight_key, None)
    # 29. Database Maintenance: Prune Historical Alerts
    def test_29_historical_alert_pruning(self):
        import asyncio
        from app.maintenance import prune_historical_alerts
        mock_db = self.mock_db
        res = asyncio.run(prune_historical_alerts(mock_db, retention_days=30))
        self.assertEqual(res.get("status"), "success")
        self.assertIn("cutoff", res)

    # 30. Security: CryptoVault Production Mode Initialization
    def test_30_cryptovault_production_initialization(self):
        from app.vault import CryptoVault
        orig_env = settings.ENVIRONMENT
        orig_key = settings.ENCRYPTION_KEY
        try:
            # 1. Valid production key initialization
            settings.ENVIRONMENT = "production"
            settings.ENCRYPTION_KEY = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
            prod_vault = CryptoVault()
            encrypted = prod_vault.encrypt("test_secret_payload_123")
            self.assertTrue(encrypted.startswith("gAAAAA"))
            decrypted = prod_vault.decrypt(encrypted)
            self.assertEqual(decrypted, "test_secret_payload_123")

            # 2. Missing/placeholder key in production must raise RuntimeError
            settings.ENCRYPTION_KEY = ""
            with self.assertRaises(RuntimeError):
                CryptoVault()
        finally:
            settings.ENVIRONMENT = orig_env
            settings.ENCRYPTION_KEY = orig_key


    # 31. Security: Rate Limiter Proxy IP Extraction & Pruning
    def test_31_rate_limiter_proxy_ip_extraction_and_pruning(self):
        from app.main import _extract_client_ip, _prune_rate_limit_buckets, _RATE_LIMIT_BUCKETS
        from unittest.mock import MagicMock
        import time

        # 1. Cloudflare header precedence
        req_cf = MagicMock()
        req_cf.headers = {"cf-connecting-ip": "203.0.113.195", "x-forwarded-for": "198.51.100.10"}
        req_cf.client.host = "10.0.0.1"
        self.assertEqual(_extract_client_ip(req_cf), "203.0.113.195")

        # 2. X-Forwarded-For multi-proxy chain extraction (first IP is client)
        req_xff = MagicMock()
        req_xff.headers = {"x-forwarded-for": "198.51.100.10, 10.0.0.2, 10.0.0.3"}
        req_xff.client.host = "10.0.0.1"
        self.assertEqual(_extract_client_ip(req_xff), "198.51.100.10")

        # 3. Direct host fallback
        req_direct = MagicMock()
        req_direct.headers = {}
        req_direct.client.host = "192.0.2.1"
        self.assertEqual(_extract_client_ip(req_direct), "192.0.2.1")

        # 4. Pruning expired keys
        now = time.time()
        _RATE_LIMIT_BUCKETS["expired_ip"] = [now - 120.0, now - 90.0]
        _RATE_LIMIT_BUCKETS["active_ip"] = [now - 10.0]
        _prune_rate_limit_buckets(now)
        self.assertNotIn("expired_ip", _RATE_LIMIT_BUCKETS)
        self.assertIn("active_ip", _RATE_LIMIT_BUCKETS)
        _RATE_LIMIT_BUCKETS.pop("active_ip", None)

    # 32. Security: Rate Limiter Memory Cap / Hard Capacity Eviction
    def test_32_rate_limiter_max_capacity_eviction(self):
        from app.main import _prune_rate_limit_buckets, _RATE_LIMIT_BUCKETS
        import time
        now = time.time()
        # Seed 1050 buckets with active timestamps
        for i in range(1050):
            _RATE_LIMIT_BUCKETS[f"flood_ip_{i}"] = [now]

        with patch("app.main._RATE_LIMIT_MAX_BUCKETS", 1000):
            _prune_rate_limit_buckets(now)
            # Eviction should have reduced the count below 1000
            self.assertLessEqual(len(_RATE_LIMIT_BUCKETS), 1000)

        # Cleanup
        _RATE_LIMIT_BUCKETS.clear()

    # 33. Security: Information Disclosure Sanitization in Production Mode
    def test_33_exception_sanitization_in_production(self):
        orig_env = settings.ENVIRONMENT
        try:
            settings.ENVIRONMENT = "production"
            # Simulate broken database connection on /api/health/db
            with patch("app.main.get_db_pool", side_effect=Exception("FATAL: password authentication failed for user postgres at internal-db.internal:5432")):
                res = self.client.get("/api/health/db")
                self.assertEqual(res.status_code, 200)
                data = res.json()
                self.assertEqual(data["status"], "degraded")
                self.assertEqual(data["error"], "Database connectivity degraded.")
                # Must not contain internal connection or host details
                self.assertNotIn("internal-db", data["error"])
                self.assertNotIn("password authentication failed", data["error"])
        finally:
            settings.ENVIRONMENT = orig_env


if __name__ == "__main__":
    unittest.main()


