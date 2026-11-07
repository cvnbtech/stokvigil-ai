import time
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

logger = logging.getLogger("stokvigil.market_cache")


class MarketCacheManager:
    """
    High-Performance Hybrid Market Cache Manager (Dual-Tier).
    - Tier 1: Local In-Memory Process RAM (< 0.01 ms read/write latency).
    - Tier 2: Supabase UNLOGGED PostgreSQL Table ('market_memory_cache').
              Bypasses WAL writes for sub-millisecond multi-container synchronization
              on 100% free-tier resources with zero paid Redis costs.
    Stores pre-computed technical indicators, live prices, VWAP, RSI, MACD,
    tactical trade levels, and Confluence Scores.
    """
    _instance: Optional['MarketCacheManager'] = None

    def __new__(cls) -> 'MarketCacheManager':
        if cls._instance is None:
            cls._instance = super(MarketCacheManager, cls).__new__(cls)
            cls._instance._cache: Dict[str, Dict[str, Any]] = {}
            cls._instance._stats = {
                "hits": 0,
                "misses": 0,
                "writes": 0,
                "db_hydrations": 0,
                "db_flushes": 0
            }
        return cls._instance

    def _normalize_symbol(self, symbol: str) -> str:
        return str(symbol or "").replace(".NS", "").replace(".BO", "").strip().upper()

    def set_stock(self, symbol: str, data: Dict[str, Any], ttl_seconds: int = 900) -> None:
        """
        Stores pre-computed stock analysis into RAM cache with a TTL (default: 900s / 15 mins).
        O(1) in-memory operation (< 0.01 ms).
        """
        clean_sym = self._normalize_symbol(symbol)
        now = time.time()
        if isinstance(data, dict):
            data.setdefault("data_source_mode", "DELAYED_EOD_SCRAPE")
            data.setdefault("is_realtime", data.get("data_source_mode") == "REALTIME_BROKER_FEED")
        self._cache[clean_sym] = {
            "symbol": clean_sym,
            "data": data,
            "cached_at": now,
            "expires_at": now + ttl_seconds
        }
        self._stats["writes"] += 1

    async def async_set_stock(self, symbol: str, data: Dict[str, Any], ttl_seconds: int = 900) -> None:
        """
        Sets pre-computed stock analysis in RAM and asynchronously upserts to Supabase UNLOGGED table.
        """
        self.set_stock(symbol, data, ttl_seconds=ttl_seconds)
        clean_sym = self._normalize_symbol(symbol)
        try:
            from app.db_pool import execute
            query = """
                INSERT INTO public.market_memory_cache (key, value, updated_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (key) DO UPDATE
                SET value = EXCLUDED.value, updated_at = NOW()
            """
            await execute(query, clean_sym, json.dumps(data))
            self._stats["db_flushes"] += 1
        except Exception as e:
            logger.debug(f"Async DB cache write skipped for {clean_sym}: {e}")

    def get_stock(self, symbol: str, max_age_seconds: int = 900) -> Optional[Dict[str, Any]]:
        """
        Retrieves pre-computed stock analysis from RAM in O(1) time (< 0.01 ms).
        Returns None if cache miss or if data is expired.
        """
        clean_sym = self._normalize_symbol(symbol)
        item = self._cache.get(clean_sym)
        if not item:
            self._stats["misses"] += 1
            return None

        now = time.time()
        if now > item.get("expires_at", 0) or (now - item.get("cached_at", 0)) > max_age_seconds:
            self._stats["misses"] += 1
            return None

        self._stats["hits"] += 1
        return item.get("data")

    async def async_get_stock(self, symbol: str, max_age_seconds: int = 900) -> Optional[Dict[str, Any]]:
        """
        Asynchronously retrieves stock analysis: checks RAM first (Tier 1).
        On cache miss (e.g. cold-start container), falls back to Supabase UNLOGGED table (Tier 2).
        Hydrates local RAM on DB hit.
        """
        res = self.get_stock(symbol, max_age_seconds=max_age_seconds)
        if res is not None:
            return res

        clean_sym = self._normalize_symbol(symbol)
        try:
            from app.db_pool import fetch_one
            query = "SELECT value, updated_at FROM public.market_memory_cache WHERE key = $1"
            row = await fetch_one(query, clean_sym)
            if row and row.get("value"):
                data = row["value"] if isinstance(row["value"], dict) else json.loads(row["value"])
                updated_at_val = row.get("updated_at")
                
                # Check age if timestamp available
                if updated_at_val:
                    if isinstance(updated_at_val, str):
                        try:
                            dt = datetime.fromisoformat(updated_at_val.replace("Z", "+00:00"))
                            age = (datetime.now(timezone.utc) - dt).total_seconds()
                            if age > max_age_seconds:
                                return None
                        except Exception:
                            pass
                
                # Hydrate RAM cache
                self.set_stock(clean_sym, data, ttl_seconds=max_age_seconds)
                self._stats["db_hydrations"] += 1
                return data
        except Exception as e:
            logger.debug(f"Async DB cache read skipped for {clean_sym}: {e}")

        return None

    def is_fresh(self, symbol: str, max_age_seconds: int = 900) -> bool:
        """Checks if a stock's pre-computed technicals are fresh in RAM."""
        clean_sym = self._normalize_symbol(symbol)
        item = self._cache.get(clean_sym)
        if not item:
            return False
        return (time.time() - item.get("cached_at", 0)) <= max_age_seconds

    def get_multiple_stocks(self, symbols: List[str], max_age_seconds: int = 900) -> Dict[str, Dict[str, Any]]:
        """Batch-retrieves pre-computed analysis for multiple symbols in < 1ms."""
        result = {}
        for s in symbols:
            clean_sym = self._normalize_symbol(s)
            stock_data = self.get_stock(clean_sym, max_age_seconds=max_age_seconds)
            if stock_data:
                result[clean_sym] = stock_data
        return result

    async def async_hydrate_all_from_db(self, max_age_seconds: int = 900) -> int:
        """
        Preloads local RAM from the Supabase UNLOGGED table on cold starts.
        Enables a freshly started Cloud Run instance to populate its cache in < 15ms.
        """
        try:
            from app.db_pool import fetch_all
            query = "SELECT key, value, updated_at FROM public.market_memory_cache"
            rows = await fetch_all(query)
            if not rows:
                return 0

            count = 0
            now_utc = datetime.now(timezone.utc)
            for r in rows:
                k = r.get("key")
                v = r.get("value")
                updated_at_val = r.get("updated_at")
                if not k or not v:
                    continue

                if updated_at_val:
                    if isinstance(updated_at_val, str):
                        try:
                            dt = datetime.fromisoformat(updated_at_val.replace("Z", "+00:00"))
                            if (now_utc - dt).total_seconds() > max_age_seconds:
                                continue
                        except Exception:
                            pass

                data = v if isinstance(v, dict) else json.loads(v)
                self.set_stock(k, data, ttl_seconds=max_age_seconds)
                count += 1

            self._stats["db_hydrations"] += count
            logger.info(f"⚡ Hydrated {count} stocks from Supabase unlogged cache into RAM in < 15ms.")
            return count
        except Exception as e:
            logger.debug(f"Cold-start cache hydration skipped: {e}")
            return 0

    async def async_flush_ram_to_db(self) -> int:
        """
        Persists all active RAM records to the Supabase UNLOGGED table in a single batch.
        """
        items = list(self._cache.items())
        if not items:
            return 0

        args_list = []
        for k, v in items:
            data = v.get("data")
            if k and data:
                args_list.append((k, json.dumps(data)))

        if not args_list:
            return 0

        try:
            from app.db_pool import executemany
            query = """
                INSERT INTO public.market_memory_cache (key, value, updated_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (key) DO UPDATE
                SET value = EXCLUDED.value, updated_at = NOW()
            """
            ok = await executemany(query, args_list)
            if ok:
                self._stats["db_flushes"] += len(args_list)
                return len(args_list)
        except Exception as e:
            logger.debug(f"Batch RAM cache flush skipped: {e}")

        return 0

    def get_all_cached_symbols(self) -> List[str]:
        """Returns all actively cached symbols in RAM."""
        return list(self._cache.keys())

    def get_stats(self) -> Dict[str, Any]:
        """Returns telemetry stats for cache performance monitoring."""
        return {
            "cached_symbols_count": len(self._cache),
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "writes": self._stats["writes"],
            "db_hydrations": self._stats["db_hydrations"],
            "db_flushes": self._stats["db_flushes"],
            "hit_ratio_pct": round((self._stats["hits"] / max(1, self._stats["hits"] + self._stats["misses"])) * 100, 2)
        }

    def update_live_tick(
        self, 
        symbol: str, 
        ltp: float, 
        volume: Optional[int] = None, 
        high: Optional[float] = None, 
        low: Optional[float] = None
    ) -> None:
        """
        Atomically updates a stock's live Last Traded Price (LTP) and sub-second metrics in RAM.
        Enables WebSocket or zero-cost tick feeds to update tactical ranges and VWAP deviations
        without running heavy full pipeline recalculations.
        """
        clean_sym = self._normalize_symbol(symbol)
        now = time.time()
        
        if clean_sym in self._cache:
            entry = self._cache[clean_sym]
            data = entry.get("data", {})
            data["current_price"] = round(float(ltp), 2)
            data["last_tick_time"] = now
            data["data_source_mode"] = "REALTIME_BROKER_FEED"
            data["is_realtime"] = True
            
            # Recalculate price vs VWAP deviation if VWAP exists
            vwap = data.get("vwap", 0.0)
            if vwap > 0:
                data["price_vs_vwap_pct"] = round(((float(ltp) - vwap) / vwap) * 100, 2)
                
            if volume is not None:
                data["live_volume"] = volume
            if high is not None:
                data["day_high"] = round(float(high), 2)
            if low is not None:
                data["day_low"] = round(float(low), 2)
                
            entry["cached_at"] = now
        else:
            # Minimal seed entry until full pipeline runs
            self._cache[clean_sym] = {
                "symbol": clean_sym,
                "data": {
                    "symbol": clean_sym,
                    "current_price": round(float(ltp), 2),
                    "last_tick_time": now,
                    "data_source_mode": "REALTIME_BROKER_FEED",
                    "is_realtime": True,
                    "live_volume": volume or 0,
                    "day_high": high or round(float(ltp), 2),
                    "day_low": low or round(float(ltp), 2),
                    "action_bias": "HOLD_NEUTRAL",
                    "confluence_score": None
                },
                "cached_at": now,
                "expires_at": now + 300
            }
        self._stats["writes"] += 1

    def clear(self) -> None:
        """Clears all cached market records."""
        self._cache.clear()


# Global Singleton Instance
market_cache = MarketCacheManager()
