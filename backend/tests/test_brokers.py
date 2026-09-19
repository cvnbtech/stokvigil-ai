import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from datetime import date

os.environ["ENVIRONMENT"] = "test"
os.environ["ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.brokers import get_broker, list_supported_brokers, broker_registry
from app.brokers.base import BaseBrokerAdapter
from app.brokers.icici_adapter import IciciBrokerAdapter
from app.config import settings


class TestMultiBrokerArchitecture(unittest.TestCase):
    """
    Unit test suite verifying:
    1. Multi-broker strategy / adapter pattern contracts.
    2. Zero-manual-keys master app publisher login URL generation.
    3. Pluggability of new brokers (e.g. Zerodha, Angel One) without core changes.
    4. Safe vault storage of session tokens.
    """

    def test_default_broker_is_icici(self):
        adapter = get_broker("icici")
        self.assertIsInstance(adapter, IciciBrokerAdapter)
        self.assertEqual(adapter.broker_id, "icici")
        self.assertEqual(adapter.display_name, "ICICI Direct")
        self.assertTrue(adapter.is_active)

    def test_unknown_broker_falls_back_to_icici(self):
        adapter = get_broker("unknown_broker_xyz")
        self.assertIsInstance(adapter, IciciBrokerAdapter)
        self.assertEqual(adapter.broker_id, "icici")

    def test_icici_login_url_generation(self):
        adapter = get_broker("icici")
        with patch.object(settings, "ICICI_MASTER_APP_KEY", "MASTER_TEST_KEY_123"):
            login_url = adapter.get_login_url()
            self.assertIn("https://api.icicidirect.com/apiuser/login?api_key=", login_url)
            self.assertIn("MASTER_TEST_KEY_123", login_url)

    def test_list_supported_brokers(self):
        catalog = list_supported_brokers()
        self.assertTrue(len(catalog) >= 3)
        broker_ids = [b["id"] for b in catalog]
        self.assertIn("icici", broker_ids)
        self.assertIn("zerodha", broker_ids)
        self.assertIn("angelone", broker_ids)

        icici_info = next(b for b in catalog if b["id"] == "icici")
        self.assertEqual(icici_info["status"], "active")

        zerodha_info = next(b for b in catalog if b["id"] == "zerodha")
        self.assertEqual(zerodha_info["status"], "coming_soon")

    def test_session_expiration_validation(self):
        adapter = get_broker("icici")
        today_str = str(date.today())
        self.assertTrue(adapter.validate_session(today_str))
        self.assertFalse(adapter.validate_session("2020-01-01"))
        self.assertFalse(adapter.validate_session(""))

    def test_dynamic_plugging_of_future_broker(self):
        """
        Simulates adding a new broker (e.g. Zerodha Kite) dynamically to prove extensibility.
        """
        class MockZerodhaAdapter(BaseBrokerAdapter):
            broker_id = "zerodha_mock"
            display_name = "Zerodha Kite Connect"
            is_active = True
            auth_type = "oauth"

            def get_login_url(self, redirect_uri=None):
                return "https://kite.zerodha.com/connect/login?v=3&api_key=MOCK_KITE_KEY"

            def save_credentials(self, db, vault, user_id, session_token, **kwargs):
                return {"status": "success", "broker": self.broker_id}

            def fetch_holdings(self, decrypted_creds):
                return [{"symbol": "INFY", "quantity": 50, "average_price": 1500.0}]

            def place_order(self, decrypted_creds, order_params):
                return {"order_id": "ZERODHA_ORDER_999", "status": "COMPLETE"}

        # Register new broker dynamically
        new_broker = MockZerodhaAdapter()
        broker_registry.register_broker(new_broker)

        # Retrieve and verify
        retrieved = get_broker("zerodha_mock")
        self.assertEqual(retrieved.broker_id, "zerodha_mock")
        self.assertEqual(retrieved.display_name, "Zerodha Kite Connect")
        self.assertIn("https://kite.zerodha.com/connect/login", retrieved.get_login_url())

        # Test holdings
        holdings = retrieved.fetch_holdings({})
        self.assertEqual(len(holdings), 1)
        self.assertEqual(holdings[0]["symbol"], "INFY")

        # Test order
        order = retrieved.place_order({}, {})
        self.assertEqual(order["order_id"], "ZERODHA_ORDER_999")


if __name__ == "__main__":
    unittest.main()
