import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Set UTF-8 encoding for Windows stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

# Set test environment to prevent vault production check abort
os.environ["ENVIRONMENT"] = "test"
os.environ["ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pydantic import ValidationError
from fastapi import HTTPException

from app.agent_runner import compute_tactical_levels
from app.notifications import format_telegram_alert
from app.main import (
    PlaceOrderRequest,
    snap_to_exchange_tick,
    is_indian_market_open,
    get_market_session_status,
    place_trade_order,
)


class TestFinancialTradeFlaws(unittest.TestCase):
    """
    Test suite verifying fixes for 5 critical financial trade flaws:
    1. Direction-aware tactical levels for SELL_WATCH vs BUY_WATCH.
    2. Rich notification labeling reflecting bearish downside vs bullish targets.
    3. Mandatory positive price validation for LIMIT orders.
    4. Indian exchange standard ₹0.05 tick size snapping.
    5. Market hours session awareness.
    6. ICICI Breeze silent RMS rejection (Status 500 / Error) error handling (HTTP 422).
    7. SEBI Intraday MIS Short regulatory disclosure for unheld stock selling.
    """

    def test_tactical_levels_sell_watch_downside_targets(self):
        """Flaw 1: SELL_WATCH must calculate downside targets and protective buy-stops."""
        current_price = 1000.0
        atr = 20.0
        levels = compute_tactical_levels(
            current_price=current_price,
            atr_val=atr,
            action_bias="SELL_WATCH"
        )
        self.assertIsNotNone(levels)
        # Parse targets and stop loss
        t1_val = float(levels["target_1"].replace("₹", "").replace(",", ""))
        t2_val = float(levels["target_2"].replace("₹", "").replace(",", ""))
        sl_val = float(levels["protective_stop_loss"].replace("₹", "").replace(",", ""))

        # Downside targets must be strictly below current price
        self.assertLess(t1_val, current_price, "Target 1 must be below current price for SELL_WATCH")
        self.assertLess(t2_val, t1_val, "Target 2 must be deeper than Target 1 for SELL_WATCH")
        self.assertLessEqual(t1_val, current_price * 0.98, "Target 1 must be at least -2% below price")
        self.assertLessEqual(t2_val, current_price * 0.95, "Target 2 must be at least -5% below price")

        # Protective buy-stop must be strictly above current price
        self.assertGreater(sl_val, current_price, "Stop-loss must be above current price for SELL_WATCH (buy-stop)")
        self.assertGreaterEqual(sl_val, current_price * 1.02, "Stop-loss must be at least +2% above price")

    def test_tactical_levels_buy_watch_upside_targets(self):
        """Flaw 1: BUY_WATCH must calculate upside targets and stop loss below price."""
        current_price = 1000.0
        atr = 20.0
        levels = compute_tactical_levels(
            current_price=current_price,
            atr_val=atr,
            action_bias="BUY_WATCH"
        )
        self.assertIsNotNone(levels)
        t1_val = float(levels["target_1"].replace("₹", "").replace(",", ""))
        t2_val = float(levels["target_2"].replace("₹", "").replace(",", ""))
        sl_val = float(levels["protective_stop_loss"].replace("₹", "").replace(",", ""))

        self.assertGreater(t1_val, current_price, "Target 1 must be above current price for BUY_WATCH")
        self.assertGreater(t2_val, t1_val, "Target 2 must be higher than Target 1 for BUY_WATCH")
        self.assertLess(sl_val, current_price, "Stop-loss must be below current price for BUY_WATCH")

    def test_format_telegram_alert_directional_labeling(self):
        """Notification formatting must reflect bearish defense / downside levels."""
        tactical_levels = {
            "entry_range": "₹995.00 - ₹1,005.00",
            "target_1": "₹970.00",
            "target_2": "₹950.00",
            "protective_stop_loss": "₹1,020.00",
            "risk_reward_ratio": "1:2.5"
        }
        # SELL_WATCH alert formatting
        sell_msg = format_telegram_alert(
            symbol="INFY.NS",
            alert_title="Bearish Breakdown Detected",
            action_bias="SELL_WATCH",
            confluence_score=82,
            catalyst_type="TECHNICAL_BREAKDOWN",
            confluence_drivers=["Below VWAP", "Heavy Distribution"],
            tactical_levels=tactical_levels
        )
        self.assertIn("Tactical Defense & Downside Levels", sell_msg)
        self.assertIn("Sell / Short Zone", sell_msg)
        self.assertIn("Tactical Support 1", sell_msg)
        self.assertIn("Protective Buy-Stop", sell_msg)

        # TRAILING_SL_ALERT formatting
        sl_msg = format_telegram_alert(
            symbol="TCS.NS",
            alert_title="Stop Loss Triggered",
            action_bias="TRAILING_SL_ALERT",
            confluence_score=75,
            catalyst_type="RISK_MANAGEMENT",
            confluence_drivers=["Breached Chandelier Exit"],
            tactical_levels=tactical_levels
        )
        self.assertIn("Capital Defense & Exit Levels", sl_msg)
        self.assertIn("Trailing SL (Exit)", sl_msg)

    def test_place_order_limit_price_validation(self):
        """Flaw 3: Limit orders strictly require a positive non-zero price."""
        # Invalid: Limit order with 0.0 price
        with self.assertRaises(ValidationError):
            PlaceOrderRequest(
                user_id="user_123",
                symbol="RELIANCE",
                action="BUY",
                order_type="LIMIT",
                quantity=10,
                price=0.0
            )

        # Invalid: Limit order with negative price
        with self.assertRaises(ValidationError):
            PlaceOrderRequest(
                user_id="user_123",
                symbol="RELIANCE",
                action="BUY",
                order_type="LIMIT",
                quantity=10,
                price=-150.0
            )

        # Valid: Limit order with positive price
        req_valid = PlaceOrderRequest(
            user_id="user_123",
            symbol="RELIANCE",
            action="BUY",
            order_type="LIMIT",
            quantity=10,
            price=2850.50
        )
        self.assertEqual(req_valid.price, 2850.50)

        # Valid: Market order with 0.0 price
        req_market = PlaceOrderRequest(
            user_id="user_123",
            symbol="RELIANCE",
            action="BUY",
            order_type="MARKET",
            quantity=10,
            price=0.0
        )
        self.assertEqual(req_market.price, 0.0)

    def test_snap_to_exchange_tick(self):
        """Flaw 3: Prices must snap to Indian exchange standard ₹0.05 tick size."""
        self.assertEqual(snap_to_exchange_tick(1245.33), 1245.35)
        self.assertEqual(snap_to_exchange_tick(1245.31), 1245.30)
        self.assertEqual(snap_to_exchange_tick(1245.32), 1245.30)
        self.assertEqual(snap_to_exchange_tick(1245.325), 1245.35)
        self.assertEqual(snap_to_exchange_tick(100.01), 100.00)
        self.assertEqual(snap_to_exchange_tick(100.04), 100.05)
        self.assertEqual(snap_to_exchange_tick(0.0), 0.0)
        self.assertEqual(snap_to_exchange_tick(None), 0.0)

    def test_is_indian_market_open_helper(self):
        """Flaw 5: Indian market session helper returns boolean and descriptive status."""
        is_open, msg = get_market_session_status()
        self.assertIsInstance(is_open, bool)
        self.assertIsInstance(msg, str)
        self.assertTrue(len(msg) > 0)
        self.assertIsInstance(is_indian_market_open(), bool)

    @patch("app.main.fetch_user_portfolio")
    @patch("app.main.vault")
    def test_place_order_broker_rms_rejection_handling(self, mock_vault, mock_portfolio):
        """Flaw 2: Breeze silent RMS 500 error must raise HTTP 422 rather than masking as success."""
        mock_vault.decrypt.side_effect = lambda x: f"decrypted_{x}"
        mock_portfolio.return_value = []

        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{
            "encrypted_app_key": "k",
            "encrypted_secret_key": "s",
            "encrypted_session_token": "t"
        }]

        req = PlaceOrderRequest(
            user_id="user_test_rms",
            symbol="SBIN",
            action="BUY",
            order_type="MARKET",
            quantity=100
        )

        mock_breeze_mod = MagicMock()
        MockBreeze = mock_breeze_mod.BreezeConnect
        with patch.dict("sys.modules", {"breeze_connect": mock_breeze_mod}):
            instance = MockBreeze.return_value
            # Simulate ICICI Breeze silent RMS failure (Status 500 with Error message, no python exception)
            instance.place_order.return_value = {
                "Status": 500,
                "Success": None,
                "Error": "RMS: Margin Shortage: Required ₹82,000, Available ₹15,000"
            }

            with self.assertRaises(HTTPException) as ctx:
                place_trade_order(
                    req=req,
                    x_idempotency_key="rms_test_key_1",
                    auth_user_id="user_test_rms",
                    db=mock_db
                )

            self.assertEqual(ctx.exception.status_code, 422)
            self.assertIn("Broker RMS rejected order", ctx.exception.detail)
            self.assertIn("RMS: Margin Shortage", ctx.exception.detail)

    @patch("app.main.fetch_user_portfolio")
    @patch("app.main.vault")
    def test_place_order_unheld_sell_sebi_notice(self, mock_vault, mock_portfolio):
        """Flaw 4: Selling unheld shares must be routed as margin with mandatory SEBI notice."""
        mock_vault.decrypt.side_effect = lambda x: f"decrypted_{x}"
        # User holds NO shares of TATASTEEL
        mock_portfolio.return_value = []

        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{
            "encrypted_app_key": "k",
            "encrypted_secret_key": "s",
            "encrypted_session_token": "t"
        }]

        req = PlaceOrderRequest(
            user_id="user_test_sebi",
            symbol="TATASTEEL",
            action="SELL",
            order_type="MARKET",
            quantity=50
        )

        mock_breeze_mod = MagicMock()
        MockBreeze = mock_breeze_mod.BreezeConnect
        with patch.dict("sys.modules", {"breeze_connect": mock_breeze_mod}):
            instance = MockBreeze.return_value
            instance.place_order.return_value = {
                "Status": 200,
                "Success": {"order_id": "ORD1234567"},
                "Error": None
            }

            res = place_trade_order(
                req=req,
                x_idempotency_key="sebi_test_key_1",
                auth_user_id="user_test_sebi",
                db=mock_db
            )

            self.assertEqual(res["status"], "success")
            self.assertEqual(res["product"], "margin")
            self.assertTrue(res["is_intraday_short"])
            self.assertIsNotNone(res["sebi_notice"])
            self.assertIn("SEBI Notice", res["sebi_notice"])
            self.assertIn("03:15 PM IST", res["sebi_notice"])
            self.assertIn("auction penalty", res["sebi_notice"])

    def test_place_order_sl_m_ban_and_sl_l_validation(self):
        """SEBI/NSE SL-M ban: Reject MARKET stop-loss orders and enforce SL-L limit price."""
        # 1. SL-M order must raise ValidationError under SEBI/NSE prohibition
        with self.assertRaises(ValidationError) as ctx:
            PlaceOrderRequest(
                user_id="user_sl_test",
                symbol="NIFTY",
                action="SELL",
                order_type="MARKET",
                quantity=25,
                trigger_price=24500.0
            )
        self.assertIn("SL-M", str(ctx.exception))
        self.assertIn("prohibited", str(ctx.exception).lower())

        # 2. SL-L order missing limit price must raise ValidationError
        with self.assertRaises(ValidationError) as ctx:
            PlaceOrderRequest(
                user_id="user_sl_test",
                symbol="NIFTY",
                action="SELL",
                order_type="LIMIT",
                quantity=25,
                price=0.0,
                trigger_price=24500.0
            )
        self.assertIn("price > 0.0", str(ctx.exception))

        # 3. Valid SL-L order with both price and trigger_price succeeds
        req_sl_l = PlaceOrderRequest(
            user_id="user_sl_test",
            symbol="NIFTY",
            action="SELL",
            order_type="LIMIT",
            quantity=25,
            price=24480.0,
            trigger_price=24500.0
        )
        self.assertEqual(req_sl_l.order_type, "LIMIT")
        self.assertEqual(req_sl_l.price, 24480.0)
        self.assertEqual(req_sl_l.trigger_price, 24500.0)


if __name__ == "__main__":
    unittest.main()
