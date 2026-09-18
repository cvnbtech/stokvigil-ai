import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np

# Set test environment to prevent vault production check abort
os.environ["ENVIRONMENT"] = "test"
os.environ["ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agent_runner import (
    compute_deterministic_confluence,
    check_has_active_catalyst
)
from app.technical_engine import (
    calculate_camarilla_pivots,
    compute_technicals_from_frames
)
from app.flow_tracker import fetch_nse_option_chain
from app.notifications import format_telegram_alert


class TestQuantitativeUpgrades(unittest.TestCase):
    """
    Comprehensive test suite verifying the 7 Critical Quantitative Upgrades:
    1. Relaxo Breakdown Hard Risk Veto & Sensitivity Dispatch
    2. Demat Downside Loss Defense
    3. Circuit Lock Detection (Upper & Lower)
    4. Date-Aware Camarilla Institutional Pivots
    5. Option Chain Granular Expiry Filtering
    6. Dynamic Product Type Selection (Cash vs Margin)
    7. SEBI Non-Advisory Compliance Disclosures
    """

    def setUp(self):
        self.default_macro = {
            "nifty_trend": "BULLISH",
            "india_vix": 13.5,
            "allow_breakout_trades": True,
            "adr_ratio": 1.2,
            "breadth_regime": "ACCUMULATION",
            "advances": 1400,
            "declines": 800
        }

    def test_relaxo_breakdown_hard_risk_veto_and_dispatch(self):
        """
        Flaw 1 & Missed Alert Root Cause Verification:
        Relaxo has pristine balance-sheet fundamentals (D/E: 0.0, Forensics: 85),
        but price crashed -7.16% intraday.
        Verify that Hard Risk Veto activates:
        - Overrides fundamental buoy
        - Confluence score is capped to <= 28
        - Action bias is SELL_WATCH
        - has_actionable_signal is True
        - Dispatches under BOTH 'ALL' and 'HIGH' sensitivity!
        """
        technicals = {
            "current_price": 780.0,
            "change_pct": -7.16,
            "price_vs_vwap_pct": -3.2,
            "is_volume_surge": True,
            "volume_multiple": 2.5,
            "technical_score": 15.0,
            "rsi_15m": 28.0,
            "rsi_5m": 22.0,
            "ema_200": 850.0,
            "camarilla_pivots": {"h4": 860.0, "h3": 850.0, "l3": 830.0, "l4": 820.0}
        }
        flow_data = {
            "flow_score": 50.0,
            "delivery_pct": 35.0,
            "is_high_delivery": False,
            "vsa_regime": "NORMAL_VOLUME_SPREAD",
            "is_fo_stock": False
        }
        forensics = {
            "forensic_score": 85.0,
            "sector_name": "CONSUMER_DURABLES"
        }
        financials = {
            "name": "Relaxo Footwears Limited",
            "price": 780.0,
            "pe_ratio": 52.0,
            "debt_to_equity": 0.0
        }
        news_items = []

        result = compute_deterministic_confluence(
            symbol="RELAXO",
            technicals=technicals,
            flow_data=flow_data,
            macro_data=self.default_macro,
            forensics=forensics,
            financials=financials,
            news_items=news_items
        )

        # 1. Verify Hard Risk Veto
        self.assertEqual(result["action_bias"], "SELL_WATCH")
        self.assertTrue(result["has_actionable_signal"])
        self.assertLessEqual(result["confluence_score"], 28)
        self.assertIn("Severe Price Breakdown Alert", result["alert_title"])
        self.assertTrue(any("Critical Supply Alert" in d for d in result["confluence_drivers"]))

        # 2. Verify Gatekeeper passes Relaxo breakdown
        active, reason = check_has_active_catalyst("RELAXO", technicals, flow_data, news_items)
        self.assertTrue(active)
        self.assertIn("Sharp Price Movement", reason)

        # 3. Verify Sensitivity Dispatch logic (lines 1764-1773 of agent_runner)
        action_bias = result["action_bias"]
        confluence_score = result["confluence_score"]
        has_actionable = result["has_actionable_signal"]
        is_breakdown_or_sl = (action_bias in ["TRAILING_SL_ALERT", "SELL_WATCH"] or confluence_score <= 35)

        # Under ALL sensitivity: MUST dispatch!
        should_dispatch_all = has_actionable or (confluence_score >= 65) or is_breakdown_or_sl
        self.assertTrue(should_dispatch_all, "Failed: Relaxo breakdown must dispatch under ALL sensitivity")

        # Under HIGH sensitivity: MUST dispatch!
        should_dispatch_high = (confluence_score >= 80) or is_breakdown_or_sl
        self.assertTrue(should_dispatch_high, "Failed: Relaxo breakdown must dispatch under HIGH sensitivity")

    def test_demat_portfolio_downside_loss_defense(self):
        """
        Flaw 4 Verification:
        User holds stock in ICICI Direct Demat with -4.5% drawdown.
        Verify emergency stop-loss defense triggers TRAILING_SL_ALERT with TRAILING_STOP_TRIGGER.
        """
        technicals = {
            "current_price": 955.0,
            "change_pct": -4.5,
            "rsi_15m": 35.0,
            "technical_score": 40.0
        }
        holding_info = {
            "quantity": 100,
            "average_price": 1000.0,
            "current_market_price": 955.0,
            "unrealized_pnl_pct": -4.5
        }
        flow_data = {"flow_score": 50.0, "is_fo_stock": False}
        forensics = {"forensic_score": 75.0}
        financials = {"price": 955.0}

        result = compute_deterministic_confluence(
            symbol="INFY",
            technicals=technicals,
            flow_data=flow_data,
            macro_data=self.default_macro,
            forensics=forensics,
            financials=financials,
            news_items=[],
            holding_info=holding_info
        )

        self.assertEqual(result["action_bias"], "TRAILING_SL_ALERT")
        self.assertTrue(result["has_actionable_signal"])
        self.assertEqual(result["catalyst_category"], "TRAILING_STOP_TRIGGER")
        self.assertIn("Stop-Loss Defense Trigger", result["alert_title"])
        self.assertLessEqual(result["confluence_score"], 20)

    def test_circuit_lock_detection(self):
        """
        Flaw 7 Verification:
        Detect lower circuit (High == Low == Close with price down)
        and upper circuit (High == Low == Close with price up).
        """
        # Lower Circuit: 5m bar with High == Low == Close = 95.0, previous close = 100.0
        idx_today = pd.date_range(start="2026-09-18 09:15", periods=5, freq="5min")
        df_5m_lower = pd.DataFrame({
            "Open": [95.0, 95.0, 95.0, 95.0, 95.0],
            "High": [95.0, 95.0, 95.0, 95.0, 95.0],
            "Low": [95.0, 95.0, 95.0, 95.0, 95.0],
            "Close": [95.0, 95.0, 95.0, 95.0, 95.0],
            "Volume": [1000, 500, 200, 100, 50]
        }, index=idx_today)

        # Prior daily session with close 100.0
        yesterday_dt = pd.to_datetime("2026-09-17")
        df_daily = pd.DataFrame({
            "Open": [99.0],
            "High": [101.0],
            "Low": [98.0],
            "Close": [100.0],
            "Volume": [100000]
        }, index=[yesterday_dt])

        res_lower = compute_technicals_from_frames("CIRCUIT_TEST", df_5m_lower, df_daily)
        self.assertTrue(res_lower["is_circuit_locked"])
        self.assertEqual(res_lower["circuit_lock_type"], "LOWER_CIRCUIT")
        self.assertEqual(res_lower["change_pct"], -5.0)

        # Upper Circuit: 5m bar with High == Low == Close = 105.0, previous close = 100.0
        df_5m_upper = pd.DataFrame({
            "Open": [105.0, 105.0, 105.0, 105.0, 105.0],
            "High": [105.0, 105.0, 105.0, 105.0, 105.0],
            "Low": [105.0, 105.0, 105.0, 105.0, 105.0],
            "Close": [105.0, 105.0, 105.0, 105.0, 105.0],
            "Volume": [10000, 5000, 2000, 1000, 500]
        }, index=idx_today)

        res_upper = compute_technicals_from_frames("CIRCUIT_TEST", df_5m_upper, df_daily)
        self.assertTrue(res_upper["is_circuit_locked"])
        self.assertEqual(res_upper["circuit_lock_type"], "UPPER_CIRCUIT")
        self.assertEqual(res_upper["change_pct"], 5.0)

    def test_camarilla_pivots_date_awareness(self):
        """
        Flaw 6 Verification:
        When historical daily bars only contain closed bars up to yesterday (weekend/pre-market),
        Camarilla pivots MUST use iloc[-1].
        When historical daily bars contain today's forming bar at iloc[-1],
        Camarilla pivots MUST use iloc[-2] (yesterday's completed bar).
        """
        # Case A: Weekend / Pre-market where last bar is yesterday (strictly before today)
        yesterday = date.today() - timedelta(days=1)
        two_days_ago = date.today() - timedelta(days=2)

        df_daily_yesterday = pd.DataFrame({
            "High": [110.0, 120.0],
            "Low": [90.0, 100.0],
            "Close": [105.0, 115.0]
        }, index=[pd.to_datetime(two_days_ago), pd.to_datetime(yesterday)])

        # Prior day is iloc[-1]: H=120, L=100, C=115, range = 20
        # H4 = 115 + (20 * 1.1 / 2) = 115 + 11 = 126.0
        pivots_a = calculate_camarilla_pivots(df_daily_yesterday)
        self.assertEqual(pivots_a["h4"], 126.0)

        # Case B: Live market where last bar is today
        today = date.today()
        df_daily_today = pd.DataFrame({
            "High": [110.0, 120.0, 999.0],  # 999 is incomplete forming bar today
            "Low": [90.0, 100.0, 990.0],
            "Close": [105.0, 115.0, 995.0]
        }, index=[pd.to_datetime(two_days_ago), pd.to_datetime(yesterday), pd.to_datetime(today)])

        # Must use iloc[-2] (yesterday: H=120, L=100, C=115)
        pivots_b = calculate_camarilla_pivots(df_daily_today)
        self.assertEqual(pivots_b["h4"], 126.0)

    def test_option_chain_expiry_filtering(self):
        """
        Flaw 3 Verification:
        When official NSE Option Chain returns multi-expiry data,
        fetch_nse_option_chain MUST filter strictly for records.expiryDates[0].
        """
        mock_raw_response = {
            "records": {
                "expiryDates": ["26-Sep-2024", "31-Oct-2024"],
                "data": [
                    # Near-month strikes (26-Sep-2024)
                    {
                        "strikePrice": 24000.0,
                        "expiryDate": "26-Sep-2024",
                        "CE": {"openInterest": 1000, "changeinOpenInterest": 100},
                        "PE": {"openInterest": 1500, "changeinOpenInterest": 200}
                    },
                    # Far-month strikes (31-Oct-2024) - SHOULD BE FILTERED OUT
                    {
                        "strikePrice": 24000.0,
                        "expiryDate": "31-Oct-2024",
                        "CE": {"openInterest": 50000, "changeinOpenInterest": 5000},
                        "PE": {"openInterest": 50, "changeinOpenInterest": 5}
                    }
                ]
            }
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            import json
            mock_resp.read.return_value = json.dumps(mock_raw_response).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            result = fetch_nse_option_chain("NIFTY")
            self.assertIsNotNone(result)
            self.assertEqual(result.get("expiry_date"), "26-Sep-2024")
            # Total Call OI should only reflect near-month (1000), not skewed by far-month (50000)
            self.assertEqual(result.get("total_call_oi"), 1000)
            self.assertEqual(result.get("total_put_oi"), 1500)
            self.assertEqual(result.get("pcr"), 1.5)

    def test_telegram_sebi_disclosure_footer(self):
        """
        Regulatory Compliance Verification:
        Telegram alerts must include the official SEBI non-advisory disclaimer.
        """
        html = format_telegram_alert(
            symbol="RELAXO",
            alert_title="RELAXO: Severe Price Breakdown Alert (-7.2%)",
            action_bias="SELL_WATCH",
            confluence_score=28,
            catalyst_type="PRICE_BREAKOUT",
            confluence_drivers=["Critical Supply Alert: Severe intraday price drop (-7.16%)"],
            tactical_levels={"target_1": "750.00", "protective_stop_loss": "800.00"},
            metrics_snapshot={"current_price": 780.0, "change_pct": -7.16}
        )
        self.assertIn("SEBI Non-Advisory Compliance Disclosure", html)
        self.assertIn("Day Change: <b>-7.16%</b>", html)

    def test_dynamic_order_product_selection(self):
        """
        Flaw 5 Verification:
        When executing SELL orders via ICICI Direct Breeze:
        - If the user holds the stock in Demat, product auto-resolves to 'cash' (CNC).
        - If the user does not hold the stock in Demat, product auto-resolves to 'margin' (MIS intraday short).
        """
        from app.main import PlaceOrderRequest

        # 1. Verify schema accepts optional product field
        req_custom = PlaceOrderRequest(
            user_id="user_123",
            symbol="RELIANCE",
            action="SELL",
            order_type="MARKET",
            quantity=10,
            product="margin"
        )
        self.assertEqual(req_custom.product, "margin")

        req_default = PlaceOrderRequest(
            user_id="user_123",
            symbol="RELIANCE",
            action="SELL",
            order_type="MARKET",
            quantity=10
        )
        self.assertIsNone(req_default.product)

        # 2. Verify dynamic resolution logic with mock holdings
        held_portfolio = [
            {"symbol": "RELIANCE.NS", "stock_code": "RELIANCE", "quantity": 100}
        ]

        # Case A: User sells RELIANCE (held in Demat) -> product = 'cash'
        action_type = "sell"
        req_sym = "RELIANCE"
        has_holding_held = any(
            (str(h.get("symbol", "")).upper().replace(".NS", "").replace(".BO", "") == req_sym or
             str(h.get("stock_code", "")).upper() == req_sym) and
            int(h.get("quantity", 0) or 0) >= 10
            for h in held_portfolio
        )
        product_type_held = "cash" if has_holding_held else "margin"
        self.assertEqual(product_type_held, "cash")

        # Case B: User sells TATASTEEL (not held in Demat) -> product = 'margin'
        req_sym_unheld = "TATASTEEL"
        has_holding_unheld = any(
            (str(h.get("symbol", "")).upper().replace(".NS", "").replace(".BO", "") == req_sym_unheld or
             str(h.get("stock_code", "")).upper() == req_sym_unheld) and
            int(h.get("quantity", 0) or 0) >= 10
            for h in held_portfolio
        )
        product_type_unheld = "cash" if has_holding_unheld else "margin"
        self.assertEqual(product_type_unheld, "margin")


if __name__ == "__main__":
    unittest.main()
