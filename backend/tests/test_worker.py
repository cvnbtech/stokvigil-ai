import pytest
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock, patch, MagicMock

from app.worker import MarketTickWorker, is_market_hours_ist

IST = ZoneInfo("Asia/Kolkata")


class TestWorkerMarketHours:
    """Verifies market hours IST schedule checks."""

    def test_weekday_market_hours_active(self):
        # Wednesday 10:30 AM IST -> Active
        dt = datetime(2026, 11, 4, 10, 30, tzinfo=IST)
        assert is_market_hours_ist(dt) is True

    def test_weekday_pre_market_buffer(self):
        # Wednesday 09:14 AM IST -> Active (Pre-market buffer active)
        dt = datetime(2026, 11, 4, 9, 14, tzinfo=IST)
        assert is_market_hours_ist(dt) is True

    def test_weekday_before_open(self):
        # Wednesday 09:00 AM IST -> Inactive
        dt = datetime(2026, 11, 4, 9, 0, tzinfo=IST)
        assert is_market_hours_ist(dt) is False

    def test_weekday_after_close(self):
        # Wednesday 03:32 PM IST -> Inactive
        dt = datetime(2026, 11, 4, 15, 32, tzinfo=IST)
        assert is_market_hours_ist(dt) is False

    def test_weekend_inactive(self):
        # Saturday 11:00 AM IST -> Inactive
        dt_sat = datetime(2026, 11, 7, 11, 0, tzinfo=IST)
        assert is_market_hours_ist(dt_sat) is False
        # Sunday 11:00 AM IST -> Inactive
        dt_sun = datetime(2026, 11, 8, 11, 0, tzinfo=IST)
        assert is_market_hours_ist(dt_sun) is False


class TestMarketTickWorkerLifecycle:
    """Verifies MarketTickWorker initialization, execution, and graceful shutdown."""

    @pytest.mark.asyncio
    async def test_worker_initialization(self):
        worker = MarketTickWorker(flush_interval_seconds=0.1, enforce_market_hours=False)

        with patch("app.worker.get_db_pool", new_callable=AsyncMock) as mock_get_pool, \
             patch("app.market_cache.market_cache.async_hydrate_all_from_db", new_callable=AsyncMock) as mock_hydrate:

            mock_hydrate.return_value = 15
            success = await worker.initialize()
            assert success is True
            assert mock_hydrate.called

    @pytest.mark.asyncio
    async def test_worker_run_and_shutdown(self):
        worker = MarketTickWorker(flush_interval_seconds=0.05, enforce_market_hours=False)

        with patch("app.engine.ticker_stream.ticker_manager.start", new_callable=AsyncMock) as mock_start, \
             patch("app.engine.ticker_stream.ticker_manager.stop") as mock_stop, \
             patch("app.market_cache.market_cache.async_flush_ram_to_db", new_callable=AsyncMock) as mock_flush, \
             patch("app.worker.close_db_pool", new_callable=AsyncMock):

            mock_start.return_value = True
            mock_flush.return_value = 5

            # Run worker in background task
            worker_task = asyncio.create_task(worker.run(force=True))
            await asyncio.sleep(0.12)  # Allow loop to execute flushes

            await worker.shutdown()
            await worker_task

            assert mock_start.called
            assert mock_flush.called
            assert mock_stop.called

    @pytest.mark.asyncio
    async def test_worker_skips_run_outside_market_hours(self):
        worker = MarketTickWorker(enforce_market_hours=True)

        # Mock is_market_hours_ist to False
        with patch("app.worker.is_market_hours_ist", return_value=False), \
             patch("app.engine.ticker_stream.ticker_manager.start", new_callable=AsyncMock) as mock_start:

            await worker.run(force=False)
            # Should have exited immediately without starting WebSocket stream
            assert not mock_start.called
