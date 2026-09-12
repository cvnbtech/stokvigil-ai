"""
StokVigil AI — Automated Database Maintenance & Retention Policies
Periodically prunes historical alert logs older than retention thresholds
to ensure Supabase free tier (500 MB) storage stays lean and high-performance.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from supabase import Client

logger = logging.getLogger("stokvigil.maintenance")

async def prune_historical_alerts(db: Client, retention_days: int = 30) -> Dict[str, Any]:
    """
    Purges historical alerts older than `retention_days` from `public.stok_alerts`.
    Uses direct asyncpg pool if available, otherwise falls back to Supabase REST client.
    """
    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=retention_days)
    cutoff_iso = cutoff_dt.isoformat()
    
    # 1. Try high-performance direct SQL via PgBouncer pool
    try:
        from app.db_pool import execute_query
        result = await execute_query(
            "DELETE FROM public.stok_alerts WHERE created_at < $1",
            cutoff_dt
        )
        if result is not None:
            logger.info(f"✅ Pruned historical alerts older than {retention_days} days via database pool: {result}")
            return {"status": "success", "method": "db_pool", "details": str(result), "cutoff": cutoff_iso}
    except Exception as e:
        logger.debug(f"Direct pool pruning note: {e}")

    # 2. Fallback to Supabase PostgREST client
    try:
        res = db.table("stok_alerts").delete().lt("created_at", cutoff_iso).execute()
        deleted_count = len(res.data) if res.data else 0
        logger.info(f"✅ Pruned historical alerts older than {retention_days} days via REST API: {deleted_count} records removed.")
        return {"status": "success", "method": "rest", "deleted_count": deleted_count, "cutoff": cutoff_iso}
    except Exception as e:
        logger.error(f"❌ Error during historical alert pruning: {e}")
        return {"status": "error", "error": str(e), "cutoff": cutoff_iso}
