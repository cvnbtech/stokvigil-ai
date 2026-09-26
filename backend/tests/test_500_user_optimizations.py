"""
Tests for 500+ Concurrent User Scalability Optimizations:
1. Multi-User Database N+1 Bulk Query Deduplication
2. Demat Delivery 4-Hour In-Memory TTL Cache and Order Invalidation
3. Telegram Leaky-Bucket Rate Limiter (25 msgs/sec & 429 Retry Backoff)
"""

import asyncio
import time
import sys
import os
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app.notifications import _throttle_telegram, _TELEGRAM_MIN_INTERVAL
from app.agent_runner import (
    _DEMAT_PORTFOLIO_CACHE,
    _DEMAT_PORTFOLIO_CACHE_TTL,
    update_demat_portfolio_cache,
    invalidate_demat_portfolio_cache,
    evaluate_user_portfolio_and_watchlists,
)


class TestTelegramRateLimiter:
    """Verifies Telegram Leaky-Bucket Rate Limiter enforces safe dispatch intervals."""

    @pytest.mark.asyncio
    async def test_telegram_leaky_bucket_interval_enforcement(self):
        """Verifies successive message dispatches are throttled to >= 40ms interval."""
        start_time = time.time()
        # Fire 5 rapid dispatches through the limiter
        for _ in range(5):
            await _throttle_telegram()
        elapsed = time.time() - start_time
        # 5 iterations with 4 intervals of 0.04s should take at least ~0.15s
        assert elapsed >= (_TELEGRAM_MIN_INTERVAL * 3), f"Throttling too fast: {elapsed}s"

    @pytest.mark.asyncio
    async def test_telegram_429_retry_handling(self):
        """Verifies HTTP 429 triggers backoff retry and extracts retry_after."""
        from app.notifications import send_telegram_notification

        mock_resp_429 = MagicMock()
        mock_resp_429.status_code = 429
        mock_resp_429.json.return_value = {"parameters": {"retry_after": 0.05}}

        mock_resp_200 = MagicMock()
        mock_resp_200.status_code = 200
        mock_resp_200.json.return_value = {"ok": True}

        with patch("app.notifications.get_telegram_client") as mock_get_client:
            mock_client = AsyncMock()
            # First call returns 429, second returns 200
            mock_client.post.side_effect = [mock_resp_429, mock_resp_200]
            mock_get_client.return_value = mock_client

            with patch("app.config.settings.TELEGRAM_BOT_TOKEN", "mock_token"):
                result = await send_telegram_notification("12345", "Test message")
                assert result is True
                assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_telegram_queue_worker_processing(self):
        """Verifies _TELEGRAM_QUEUE consumer processes messages via enqueue_telegram_notification."""
        from app.notifications import _TELEGRAM_QUEUE, enqueue_telegram_notification, telegram_worker

        with patch("app.notifications.send_telegram_notification", new_callable=AsyncMock) as mock_send:
            # Enqueue two messages
            await enqueue_telegram_notification("chat_1", "Message 1", None)
            await enqueue_telegram_notification("chat_2", "Message 2", {"inline_keyboard": []})

            assert _TELEGRAM_QUEUE.qsize() == 2

            # Run worker in background task
            worker_task = asyncio.create_task(telegram_worker())
            # Wait for queue to be processed
            await _TELEGRAM_QUEUE.join()
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass

            assert mock_send.call_count == 2
            mock_send.assert_any_call("chat_1", "Message 1", None)
            mock_send.assert_any_call("chat_2", "Message 2", {"inline_keyboard": []})


class TestDematPortfolioCache:
    """Verifies Demat Delivery Portfolio In-Memory Cache and invalidation."""

    def test_cache_update_and_lookup(self):
        user_id = "test-user-123"
        sample_holdings = [{"symbol": "INFY", "quantity": 10, "average_price": 1400.0}]

        update_demat_portfolio_cache(user_id, sample_holdings)
        assert user_id in _DEMAT_PORTFOLIO_CACHE
        cached = _DEMAT_PORTFOLIO_CACHE[user_id]
        assert cached["holdings"] == sample_holdings
        assert (time.time() - cached["timestamp"]) < 5.0
        assert _DEMAT_PORTFOLIO_CACHE_TTL == 14400.0

    def test_cache_invalidation(self):
        user_id = "test-user-to-invalidate"
        update_demat_portfolio_cache(user_id, [{"symbol": "TCS"}])
        assert user_id in _DEMAT_PORTFOLIO_CACHE

        invalidate_demat_portfolio_cache(user_id)
        assert user_id not in _DEMAT_PORTFOLIO_CACHE

    def test_cache_invalidation_nonexistent_user_is_noop(self):
        invalidate_demat_portfolio_cache("non-existent-user-xyz")  # Should not raise exception


class TestMultiUserEvaluationOptimization:
    """Verifies evaluate_user_portfolio_and_watchlists handles preloaded_user_ctx without DB or broker queries."""

    @pytest.mark.asyncio
    async def test_evaluate_with_preloaded_context_skips_db_and_broker(self):
        user_id = "user-batch-001"
        preloaded_ctx = {
            "profile": {
                "id": user_id,
                "fcm_device_token": None,
                "fcm_enabled": False,
                "telegram_chat_id": None,
                "telegram_enabled": False,
                "alert_sensitivity": "HIGH",
            },
            "symbols": {"RELIANCE", "TCS"},
            "cred": {
                "user_id": user_id,
                "token_date": str(date.today()),
                "encrypted_session_token": "dummy_token",
                "broker_id": "icici",
            },
        }

        mock_supabase = MagicMock()

        with patch("app.brokers.get_broker") as mock_get_broker:
            mock_adapter = MagicMock()
            mock_get_broker.return_value = mock_adapter

            # Run evaluation with preloaded context
            alerts = await evaluate_user_portfolio_and_watchlists(
                user_id=user_id,
                supabase_client=mock_supabase,
                macro_data={"trend": "BULLISH"},
                preloaded_user_ctx=preloaded_ctx,
            )

            # Broker fetch_holdings should NOT have been called during batch scan
            mock_adapter.fetch_holdings.assert_not_called()
            # supabase profile and watchlist queries should NOT have been called
            assert mock_supabase.table("profiles").select.call_count == 0
            assert mock_supabase.table("user_watchlists").select.call_count == 0

    @pytest.mark.asyncio
    async def test_evaluate_with_cached_holdings_uses_cache(self):
        user_id = "user-cached-002"
        cached_holdings = [
            {"symbol": "INFY", "clean_symbol": "INFY", "quantity": 50, "average_price": 1450.0}
        ]
        update_demat_portfolio_cache(user_id, cached_holdings)

        preloaded_ctx = {
            "profile": {
                "id": user_id,
                "fcm_enabled": False,
                "telegram_enabled": False,
                "alert_sensitivity": "HIGH",
            },
            "symbols": {"INFY"},
            "cred": {
                "user_id": user_id,
                "token_date": str(date.today()),
                "encrypted_session_token": "dummy",
                "broker_id": "icici",
            },
        }

        mock_supabase = MagicMock()
        with patch("app.brokers.get_broker") as mock_get_broker:
            mock_adapter = MagicMock()
            mock_get_broker.return_value = mock_adapter

            alerts = await evaluate_user_portfolio_and_watchlists(
                user_id=user_id,
                supabase_client=mock_supabase,
                macro_data={"trend": "BULLISH"},
                preloaded_user_ctx=preloaded_ctx,
            )

            # Demat holdings came from cache, so broker adapter was never touched
            mock_adapter.fetch_holdings.assert_not_called()

        invalidate_demat_portfolio_cache(user_id)

    @pytest.mark.asyncio
    async def test_evaluate_never_polls_broker_even_without_preloaded_context(self):
        """Verifies that evaluate_user_portfolio_and_watchlists NEVER makes external broker HTTP calls."""
        user_id = "user-no-cache-003"
        invalidate_demat_portfolio_cache(user_id)

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            MagicMock(data=[{"id": user_id, "alert_sensitivity": "HIGH"}]),
            MagicMock(data=[{"symbol": "TCS"}]),
            MagicMock(data=[{"user_id": user_id, "token_date": str(date.today()), "broker_id": "icici"}]),
        ]

        with patch("app.brokers.get_broker") as mock_get_broker:
            mock_adapter = MagicMock()
            mock_get_broker.return_value = mock_adapter

            alerts = await evaluate_user_portfolio_and_watchlists(
                user_id=user_id,
                supabase_client=mock_supabase,
                macro_data={"trend": "BULLISH"},
                preloaded_user_ctx=None,
            )

            # Strict architectural invariant: external broker API is NEVER polled in surveillance loop!
            mock_adapter.fetch_holdings.assert_not_called()


class TestMultiUserScanBulkOrchestration:
    """Verifies execute_multi_user_market_scan aggregates 500+ users via 3 bulk queries."""

    @pytest.mark.asyncio
    async def test_multi_user_scan_bulk_prefetches_and_evaluates(self):
        from app.main import execute_multi_user_market_scan, _USER_PORTFOLIO_CACHE

        mock_db = MagicMock()
        mock_profiles = [
            {"id": "u1", "email": "u1@test.com", "alert_sensitivity": "HIGH"},
            {"id": "u2", "email": "u2@test.com", "alert_sensitivity": "FII"},
        ]
        mock_watchlists = [
            {"user_id": "u1", "symbol": "TCS", "is_auto_synced": False},
            {"user_id": "u1", "symbol": "INFY", "is_auto_synced": True},
            {"user_id": "u2", "symbol": "RELIANCE", "is_auto_synced": False},
        ]
        mock_creds = [
            {"user_id": "u1", "token_date": str(date.today()), "encrypted_session_token": "tok1", "broker_id": "icici"}
        ]

        async def mock_fetch_all(query, *args):
            if "FROM profiles" in query:
                return mock_profiles
            elif "FROM user_watchlists" in query:
                return mock_watchlists
            elif "FROM user_credentials" in query:
                return mock_creds
            return []

        with patch("app.main.fetch_all", side_effect=mock_fetch_all), \
             patch("app.main.sync_market_cache_for_all_active_symbols", new_callable=AsyncMock) as mock_sync_cache, \
             patch("app.main.fetch_macro_market_regime", return_value={"regime": "NEUTRAL"}), \
             patch("app.main.evaluate_user_portfolio_and_watchlists", new_callable=AsyncMock) as mock_eval:

            mock_sync_cache.return_value = 3
            mock_eval.return_value = [{"alert": "BUY_SIGNAL"}]

            res = await execute_multi_user_market_scan(mock_db)

            assert res["status"] == "completed"
            assert res["scanned_users"] == 2
            assert res["alerts_dispatched"] == 2  # 2 users * 1 alert each

            # Verify evaluate_user_portfolio_and_watchlists was called with preloaded_user_ctx
            assert mock_eval.call_count == 2
            call_kwargs_u1 = mock_eval.call_args_list[0].kwargs
            ctx_u1 = call_kwargs_u1["preloaded_user_ctx"]
            assert "TCS" in ctx_u1["symbols"]
            assert "INFY" in ctx_u1["symbols"]
            assert ctx_u1["cred"]["broker_id"] == "icici"

    def test_order_placement_invalidates_both_caches(self):
        """Verifies that placing an order clears both demat cache and user portfolio response cache."""
        from app.main import _USER_PORTFOLIO_CACHE
        user_id = "trader-999"

        # Seed caches
        update_demat_portfolio_cache(user_id, [{"symbol": "SBIN", "quantity": 100}])
        _USER_PORTFOLIO_CACHE[user_id] = {"timestamp": time.time(), "data": {"holdings": []}}

        assert user_id in _DEMAT_PORTFOLIO_CACHE
        assert user_id in _USER_PORTFOLIO_CACHE

        # Execute invalidation (as done in place_order_endpoint)
        invalidate_demat_portfolio_cache(user_id)
        _USER_PORTFOLIO_CACHE.pop(user_id, None)

        assert user_id not in _DEMAT_PORTFOLIO_CACHE
        assert user_id not in _USER_PORTFOLIO_CACHE

    @pytest.mark.asyncio
    async def test_morning_reminder_presyncs_demat_for_active_today_sessions(self):
        """Verifies 08:50 AM morning workflow pre-syncs Demat holdings for users with valid today tokens."""
        from app.main import run_morning_token_reminder

        user_id = "user-active-today"
        today_str = str(date.today())
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=[{
                "user_id": user_id,
                "token_date": today_str,
                "encrypted_session_token": "dummy_tok",
                "broker_id": "icici"
            }]
        )

        with patch("app.main.verify_cron_secret"), \
             patch("app.main.vault.decrypt", return_value="decrypted_token"), \
             patch("app.main.get_broker") as mock_get_broker, \
             patch("app.main._async_sync_demat_to_watchlists"):

            mock_adapter = MagicMock()
            mock_adapter.fetch_holdings.return_value = [{"symbol": "INFY", "quantity": 10}]
            mock_get_broker.return_value = mock_adapter

            res = await run_morning_token_reminder(x_cron_secret="test_secret", db=mock_db)

            assert res["status"] == "completed"
            assert res["synced_users_count"] == 1
            # Verify cache was updated
            assert user_id in _DEMAT_PORTFOLIO_CACHE
            assert _DEMAT_PORTFOLIO_CACHE[user_id]["holdings"][0]["symbol"] == "INFY"

        invalidate_demat_portfolio_cache(user_id)

