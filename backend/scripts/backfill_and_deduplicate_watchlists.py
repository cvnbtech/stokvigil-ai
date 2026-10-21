"""
StokVigil AI — Watchlist ISIN Backfill & Deduplication Script
Resolves all legacy symbols and ICICI codes (TELCO, INFTEC, HDFBAN) in user_watchlists to official ISINs.
Merges duplicate rows per user, preserving cost-basis and quantities, and enforces canonical consistency.
Supports --dry-run mode to inspect proposed changes before writing to PostgreSQL.
"""

import sys
import os
import json
import asyncio
import logging
from typing import Dict, List, Any, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv(".env")
load_dotenv("backend/.env")

from app.config import settings
from app.engine.security_master import init_security_master, resolve_security, is_valid_isin
from app.db_pool import fetch_all, get_db_connection
from supabase import create_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("stokvigil.scripts.backfill_isin")


async def run_backfill(dry_run: bool = True):
    logger.info(f"🚀 Starting Watchlist ISIN Backfill & Deduplication (Dry-Run: {dry_run})...")
    init_security_master()

    # 1. Fetch all rows from user_watchlists
    rows = []
    use_pool = False
    try:
        pooled = await fetch_all("SELECT id, user_id, symbol, is_auto_synced, average_buy_price, quantity, created_at FROM user_watchlists")
        if pooled is not None:
            rows = [dict(r) for r in pooled]
            use_pool = True
    except Exception as pool_err:
        logger.debug(f"Direct pool query note: {pool_err}")

    sb = None
    if not rows:
        key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
        if not key or not settings.SUPABASE_URL:
            logger.error("No valid database connection or Supabase credentials found.")
            return
        sb = create_client(settings.SUPABASE_URL, key)
        res = sb.table("user_watchlists").select("*").limit(50000).execute()
        rows = res.data or []

    total_initial_rows = len(rows)
    logger.info(f"📊 Loaded {total_initial_rows} total rows from user_watchlists.")

    if not rows:
        logger.info("user_watchlists is empty. Nothing to deduplicate.")
        return

    # 2. Save pre-migration backup snapshot
    backup_path = os.path.join(os.path.dirname(__file__), "..", "app", "data", "user_watchlists_backup.json")
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    with open(backup_path, "w", encoding="utf-8") as f:
        # Convert non-serializable fields (like datetime/UUID) to string
        serializable_rows = []
        for r in rows:
            sr = {k: str(v) if v is not None and not isinstance(v, (int, float, bool, str)) else v for k, v in r.items()}
            serializable_rows.append(sr)
        json.dump(serializable_rows, f, indent=2)
    logger.info(f"💾 Pre-migration backup snapshot saved to {backup_path}")

    # 3. Group by (user_id, canonical_key)
    # canonical_key is ISIN if resolved, otherwise canonical symbol
    user_groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}

    for row in rows:
        uid = str(row.get("user_id"))
        raw_sym = str(row.get("symbol") or "").strip()
        sec = resolve_security(raw_sym)
        isin = sec.get("isin")
        canonical_sym = sec.get("symbol") or raw_sym.replace(".NS", "").replace(".BO", "").strip().upper()
        comp_name = sec.get("company_name")

        canonical_key = isin if (isin and is_valid_isin(isin)) else canonical_sym
        group_key = (uid, canonical_key)

        row["_resolved_isin"] = isin
        row["_resolved_symbol"] = canonical_sym
        row["_resolved_name"] = comp_name

        if group_key not in user_groups:
            user_groups[group_key] = []
        user_groups[group_key].append(row)

    unique_securities_count = len(user_groups)
    logger.info(f"🔍 Grouped {total_initial_rows} rows into {unique_securities_count} unique user securities.")

    rows_to_update = []
    ids_to_delete = []

    for (uid, can_key), group in user_groups.items():
        if len(group) == 1:
            item = group[0]
            # Single row: prepare update with canonical values
            rows_to_update.append({
                "id": str(item["id"]),
                "isin": item["_resolved_isin"],
                "symbol": item["_resolved_symbol"],
                "company_name": item["_resolved_name"],
                "average_buy_price": item.get("average_buy_price"),
                "quantity": item.get("quantity"),
                "is_auto_synced": bool(item.get("is_auto_synced"))
            })
        else:
            # Duplicate group! Find the best master row to preserve
            # Priority: 1. Row with average_buy_price > 0, 2. Row with is_auto_synced, 3. Oldest row
            sorted_group = sorted(
                group,
                key=lambda x: (
                    1 if (x.get("average_buy_price") and float(x.get("average_buy_price") or 0) > 0) else 0,
                    1 if x.get("is_auto_synced") else 0,
                    x.get("created_at") or ""
                ),
                reverse=True
            )
            master = sorted_group[0]
            duplicates = sorted_group[1:]

            # Merge cost basis or quantity if master was missing it
            merged_avg = master.get("average_buy_price")
            merged_qty = master.get("quantity")
            merged_auto = master.get("is_auto_synced")

            for dup in duplicates:
                ids_to_delete.append(str(dup["id"]))
                if (merged_avg is None or float(merged_avg or 0) <= 0) and dup.get("average_buy_price"):
                    merged_avg = dup.get("average_buy_price")
                if (merged_qty is None or int(merged_qty or 0) <= 0) and dup.get("quantity"):
                    merged_qty = dup.get("quantity")
                if dup.get("is_auto_synced"):
                    merged_auto = True

            rows_to_update.append({
                "id": str(master["id"]),
                "isin": master["_resolved_isin"],
                "symbol": master["_resolved_symbol"],
                "company_name": master["_resolved_name"],
                "average_buy_price": merged_avg,
                "quantity": merged_qty,
                "is_auto_synced": bool(merged_auto)
            })

    duplicate_rows_count = len(ids_to_delete)
    logger.info(f"✨ Deduplication summary: {total_initial_rows} initial -> {unique_securities_count} unique ({duplicate_rows_count} duplicates to delete).")

    if dry_run:
        logger.info("ℹ️ Dry-run completed. No database changes were applied.")
        logger.info(f"Sample updates (first 5): {rows_to_update[:5]}")
        logger.info(f"Sample duplicate IDs to delete (first 10): {ids_to_delete[:10]}")
        return

    # 4. Apply Database Migration & Execute Updates
    logger.info("⚡ Executing database changes in Supabase...")

    if use_pool:
        async with get_db_connection() as conn:
            if conn:
                try:
                    await conn.execute("ALTER TABLE public.user_watchlists ADD COLUMN IF NOT EXISTS isin VARCHAR(12) DEFAULT NULL")
                    await conn.execute("ALTER TABLE public.user_watchlists ADD COLUMN IF NOT EXISTS company_name TEXT DEFAULT NULL")
                except Exception as alt_err:
                    logger.debug(f"Alter table note: {alt_err}")

                if ids_to_delete:
                    logger.info(f"🗑️ Deleting {len(ids_to_delete)} duplicate rows...")
                    for d_id in ids_to_delete:
                        await conn.execute("DELETE FROM public.user_watchlists WHERE id = $1", d_id)

                logger.info(f"📝 Updating {len(rows_to_update)} canonical master rows...")
                for item in rows_to_update:
                    r_id = item["id"]
                    await conn.execute(
                        "UPDATE public.user_watchlists SET symbol = $1, isin = $2, company_name = $3, average_buy_price = $4, quantity = $5, is_auto_synced = $6 WHERE id = $7",
                        item["symbol"], item.get("isin"), item["company_name"], item["average_buy_price"], item["quantity"], item["is_auto_synced"], r_id
                    )

                try:
                    await conn.execute("ALTER TABLE public.user_watchlists DROP CONSTRAINT IF EXISTS user_watchlists_user_id_symbol_key")
                    await conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_user_watchlists_user_isin ON public.user_watchlists (user_id, isin) WHERE isin IS NOT NULL")
                    await conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_user_watchlists_user_canonical_symbol ON public.user_watchlists (user_id, UPPER(TRIM(REPLACE(symbol, '.NS', '')))) WHERE isin IS NULL")
                    logger.info("🔒 Unique constraint uq_user_watchlists_user_isin enforced successfully.")
                except Exception as c_err:
                    logger.warning(f"Constraint application note: {c_err}")
    elif sb:
        if ids_to_delete:
            logger.info(f"🗑️ Deleting {len(ids_to_delete)} duplicate rows...")
            chunk_size = 50
            for i in range(0, len(ids_to_delete), chunk_size):
                chunk = ids_to_delete[i:i + chunk_size]
                sb.table("user_watchlists").delete().in_("id", chunk).execute()

        logger.info(f"📝 Updating {len(rows_to_update)} canonical master rows...")
        for item in rows_to_update:
            r_id = item["id"]
            update_dict = {
                "symbol": item["symbol"],
                "company_name": item["company_name"],
                "average_buy_price": item["average_buy_price"],
                "quantity": item["quantity"],
                "is_auto_synced": item["is_auto_synced"]
            }
            if item.get("isin"):
                update_dict["isin"] = item["isin"]
            try:
                sb.table("user_watchlists").update(update_dict).eq("id", r_id).execute()
            except Exception:
                update_dict.pop("isin", None)
                sb.table("user_watchlists").update(update_dict).eq("id", r_id).execute()

    logger.info(f"✅ Success! user_watchlists cleaned and deduplicated: {total_initial_rows} -> {unique_securities_count} rows.")


if __name__ == "__main__":
    is_dry = "--apply" not in sys.argv
    asyncio.run(run_backfill(dry_run=is_dry))
