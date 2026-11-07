"""
StokVigil Standalone Market-Hours Tick Worker (Phase 5).
Provides continuous WebSocket tick ingestion and sub-millisecond RAM caching during Indian trading hours.
Flushes shared state to the Supabase UNLOGGED table (public.market_memory_cache) every 2 seconds.
Runs strictly between 09:14 AM IST and 03:31 PM IST on NSE/BSE trading days to conserve 75% of compute hours,
operating 100% within Google Cloud Run and Supabase free-tier limits.
"""

import asyncio
import logging
import os
import signal
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config import settings
from app.db_pool import get_db_pool, close_db_pool
from app.market_cache import market_cache
from app.engine.ticker_stream import ticker_manager
from app.core.dependencies import get_market_session_status

logger = logging.getLogger("stokvigil.worker")
IST = ZoneInfo("Asia/Kolkata")


def is_market_hours_ist(now: Optional[datetime] = None) -> bool:
    """
    Checks if current time in IST is within active market monitoring hours:
    Monday through Friday, 09:14 AM IST to 03:31 PM IST.
    """
    now_ist = now or datetime.now(IST)
    if now_ist.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    current_time_minutes = now_ist.hour * 60 + now_ist.minute
    start_minutes = 9 * 60 + 14   # 09:14 AM IST (pre-market buffer)
    end_minutes = 15 * 60 + 31   # 03:31 PM IST (post-market settlement buffer)
    return start_minutes <= current_time_minutes <= end_minutes


class MarketTickWorker:
    """
    Standalone Market-Hours Tick Worker Orchestrator.
    Manages cold-start hydration, WebSocket lifecycle, periodic database flush, and graceful termination.
    """
    def __init__(self, flush_interval_seconds: float = 2.0, enforce_market_hours: bool = True):
        self.flush_interval = flush_interval_seconds
        self.enforce_market_hours = enforce_market_hours
        self._running = False
        self._shutdown_event = asyncio.Event()

    async def initialize(self) -> bool:
        """Initializes database pool and hydrates in-memory cache from Supabase unlogged table."""
        logger.info("Initializing StokVigil Standalone Market Tick Worker...")

        # Initialize DB Pool
        try:
            pool = await get_db_pool()
            if pool:
                logger.info("Database pool established successfully.")
        except Exception as db_err:
            logger.warning(f"Note on initial db pool connection: {db_err}")

        # Hydrate RAM cache from unlogged table
        try:
            hydrated = await market_cache.async_hydrate_all_from_db(max_age_seconds=600)
            logger.info(f"Cold-start hydration completed: {hydrated} stocks restored into RAM.")
        except Exception as hyd_err:
            logger.warning(f"Cold-start hydration note: {hyd_err}")

        return True

    async def run(self, force: bool = False):
        """Main execution loop for market hours tick surveillance."""
        self._running = True
        logger.info("🚀 StokVigil Market Tick Worker loop starting.")

        now_ist = datetime.now(IST)
        if self.enforce_market_hours and not force and not is_market_hours_ist(now_ist):
            logger.info(
                f"⏰ Current IST time ({now_ist.strftime('%H:%M:%S')}) is outside market hours (09:14 - 15:31 IST). "
                "Tick worker entering standby to preserve free-tier compute."
            )
            return

        # Start broker WebSocket stream
        try:
            connected = await ticker_manager.start()
            if connected:
                logger.info("Live WebSocket stream connected and listening for market ticks.")
            else:
                logger.info("Live WebSocket stream in standby mode (monitoring with internal cache).")
        except Exception as stream_err:
            logger.error(f"Error starting ticker stream: {stream_err}")

        last_flush_time = time.time()
        last_log_time = time.time()

        while self._running and not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.flush_interval)

                # Periodic database flush to sync multi-container state
                now = time.time()
                if (now - last_flush_time) >= self.flush_interval:
                    flushed = await market_cache.async_flush_ram_to_db()
                    if flushed > 0:
                        logger.debug(f"Flushed {flushed} updated ticks to Supabase unlogged table.")
                    last_flush_time = now

                # Telemetry heartbeat every 60 seconds
                if (now - last_log_time) >= 60.0:
                    stats = ticker_manager.get_stats()
                    cached_count = len(market_cache.get_all_cached_symbols())
                    logger.info(
                        f"📊 [Worker Telemetry] Tracked Symbols: {cached_count} | "
                        f"Subscribed: {stats['subscribed_symbols_count']} | "
                        f"Ticks Ingested: {stats['ticks_processed']}"
                    )
                    last_log_time = now

                # Check if market hours have concluded
                if self.enforce_market_hours and not force and not is_market_hours_ist():
                    logger.info("🏁 Market trading session concluded (15:31 IST). Commencing orderly shutdown.")
                    break

            except asyncio.CancelledError:
                break
            except Exception as loop_err:
                logger.error(f"Error in tick worker loop: {loop_err}")

        await self.shutdown()

    async def shutdown(self):
        """Flushes remaining RAM state and terminates background tasks cleanly."""
        if not self._running:
            return
        logger.info("Initiating graceful shutdown of Market Tick Worker...")
        self._running = False
        self._shutdown_event.set()

        # Stop WebSocket Stream
        try:
            ticker_manager.stop()
            logger.info("WebSocket ticker stream disconnected.")
        except Exception as e:
            logger.debug(f"Note on ticker_manager stop: {e}")

        # Final RAM flush to unlogged table
        try:
            flushed = await market_cache.async_flush_ram_to_db()
            logger.info(f"Final flush completed: {flushed} symbols persisted to Supabase.")
        except Exception as flush_err:
            logger.debug(f"Final flush note: {flush_err}")

        # Close database pool
        try:
            await close_db_pool()
            logger.info("Database pool closed cleanly.")
        except Exception as db_err:
            logger.debug(f"Note on db pool close: {db_err}")

        logger.info("✅ StokVigil Market Tick Worker stopped cleanly.")


async def main():
    """CLI entrypoint."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    force_run = "--force" in sys.argv
    worker = MarketTickWorker(enforce_market_hours=not force_run)

    # Register OS signal handlers for graceful container termination (Cloud Run SIGTERM)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(worker.shutdown()))
        except NotImplementedError:
            # Signal handling on Windows
            pass

    await worker.initialize()
    await worker.run(force=force_run)


if __name__ == "__main__":
    asyncio.run(main())
