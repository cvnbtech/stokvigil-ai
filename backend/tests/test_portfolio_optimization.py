import os
import sys
import time
import unittest
from unittest.mock import patch, MagicMock

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ["ENVIRONMENT"] = "test"
os.environ["ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="

from app.main import (
    _get_holding_fundamentals,
    _async_pre_warm_holding_fundamentals,
    _FUNDAMENTALS_CACHE,
    _FUNDAMENTALS_CACHE_TTL,
    get_user_portfolio,
    _USER_PORTFOLIO_CACHE
)


class TestPortfolioOptimization(unittest.TestCase):
    def setUp(self):
        _FUNDAMENTALS_CACHE.clear()
        _USER_PORTFOLIO_CACHE.clear()

    def test_fundamentals_cache_retrieval_and_ttl(self):
        """_get_holding_fundamentals returns (None, None) on cache miss (non-blocking), and caches for 24h once warmed."""
        now = time.time()
        mock_fin = {
            "symbol": "RELIANCE",
            "price": 2980.5,
            "pe_ratio": 28.45,
            "debt_to_equity": 0.38
        }

        with patch("app.main.fetch_stock_financials", return_value=mock_fin) as mock_fetch:
            # 1. First synchronous call on cold cache: returns (None, None) immediately without blocking
            pe, de = _get_holding_fundamentals("RELIANCE", now)
            self.assertIsNone(pe)
            self.assertIsNone(de)
            self.assertEqual(mock_fetch.call_count, 0)

            # 2. Background pre-warm task fetches and populates the cache
            _async_pre_warm_holding_fundamentals(["RELIANCE"])
            self.assertEqual(mock_fetch.call_count, 1)

            # 3. Subsequent call within 24h: Cache hit -> zero new API calls
            pe2, de2 = _get_holding_fundamentals("RELIANCE", now + 3600)  # 1 hour later
            self.assertEqual(pe2, 28.45)
            self.assertEqual(de2, 0.38)
            self.assertEqual(mock_fetch.call_count, 1)  # Still 1!

            # 4. Normalized exchange suffix (.NS or .BO) must hit the same cache
            pe3, de3 = _get_holding_fundamentals("RELIANCE.NS", now + 7200)
            self.assertEqual(pe3, 28.45)
            self.assertEqual(de3, 0.38)
            self.assertEqual(mock_fetch.call_count, 1)  # Still 1!

    def test_fundamentals_cache_market_cache_fallback(self):
        """If market_cache has pre-computed data, use it without calling fetch_stock_financials."""
        now = time.time()
        mock_market_pack = {
            "financials": {
                "pe_ratio": 32.10,
                "debt_to_equity": 0.15
            }
        }

        with patch("app.main.market_cache.get_stock", return_value=mock_market_pack):
            with patch("app.main.fetch_stock_financials") as mock_fetch:
                pe, de = _get_holding_fundamentals("TCS", now)
                self.assertEqual(pe, 32.10)
                self.assertEqual(de, 0.15)
                mock_fetch.assert_not_called()

    def test_portfolio_response_sub_second_and_pre_warm(self):
        """get_user_portfolio returns immediately with CMP/PnL and queues background task to pre-warm fundamentals."""
        mock_db = MagicMock()
        mock_cred_data = [{
            "user_id": "test_user_1",
            "token_date": str(time.strftime("%Y-%m-%d")),
            "encrypted_app_key": "enc_app",
            "encrypted_secret_key": "enc_sec",
            "encrypted_session_token": "enc_sess"
        }]
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = mock_cred_data

        mock_holdings = [
            {"symbol": "INFY", "quantity": 50, "average_price": 1800.0, "current_market_price": 1850.0},
            {"symbol": "HDFCBANK", "quantity": 100, "average_price": 1600.0, "current_market_price": 1640.0}
        ]

        mock_quotes = {
            "INFY": {"price": 1860.0, "change_pct": 0.54},
            "HDFCBANK": {"price": 1650.0, "change_pct": 0.61}
        }

        def mock_quote_fn(sym):
            return mock_quotes.get(sym)

        mock_fin_map = {
            "INFY": {"pe_ratio": 24.2, "debt_to_equity": 0.08},
            "HDFCBANK": {"pe_ratio": 18.5, "debt_to_equity": 1.12}
        }

        def mock_fin_fn(sym):
            return mock_fin_map.get(sym, {})

        with patch("app.main.verify_user_access"), \
             patch("app.main.vault.decrypt", return_value="decrypted_val"), \
             patch("app.main.fetch_user_portfolio", return_value=mock_holdings), \
             patch("app.main._fetch_single_stock_quote", side_effect=mock_quote_fn), \
             patch("app.main.fetch_stock_financials", side_effect=mock_fin_fn):

            # 1. Cold fetch: returns immediately with prices and P&L, zero synchronous fundamentals delay
            result = get_user_portfolio(
                user_id="test_user_1",
                refresh=True,
                auth_user_id="test_user_1",
                db=mock_db
            )

            self.assertTrue(result["has_credentials"])
            self.assertEqual(len(result["holdings"]), 2)

            infy = next(h for h in result["holdings"] if h["symbol"] == "INFY")
            self.assertEqual(infy["current_price"], 1860.0)
            self.assertEqual(infy["pnl"], round((1860.0 - 1800.0) * 50, 2))

            hdfc = next(h for h in result["holdings"] if h["symbol"] == "HDFCBANK")
            self.assertEqual(hdfc["current_price"], 1650.0)
            self.assertEqual(hdfc["pnl"], round((1650.0 - 1600.0) * 100, 2))

            # 2. Execute background pre-warm task (as FastAPI BackgroundTasks does)
            _async_pre_warm_holding_fundamentals(["INFY", "HDFCBANK"], user_id="test_user_1")

            # 3. Verify fundamentals are now cached and patched in portfolio cache
            cached_res = get_user_portfolio(
                user_id="test_user_1",
                refresh=False,
                auth_user_id="test_user_1",
                db=mock_db
            )
            infy_cached = next(h for h in cached_res["holdings"] if h["symbol"] == "INFY")
            self.assertEqual(infy_cached["pe_ratio"], 24.2)
            self.assertEqual(infy_cached["debt_to_equity"], 0.08)

            hdfc_cached = next(h for h in cached_res["holdings"] if h["symbol"] == "HDFCBANK")
            self.assertEqual(hdfc_cached["pe_ratio"], 18.5)
            self.assertEqual(hdfc_cached["debt_to_equity"], 1.12)


if __name__ == "__main__":
    unittest.main()
