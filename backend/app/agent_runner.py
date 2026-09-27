import asyncio
import logging
import time
from datetime import date
from typing import List, Dict, Any, Optional

from app.config import settings
from app.technical_engine import (
    fetch_multi_timeframe_technicals,
    batch_fetch_multi_timeframe_technicals,
)
from app.flow_tracker import fetch_delivery_and_fo_flow
from app.macro_filter import fetch_macro_market_regime, evaluate_forensic_health
from app.alert_limiter import should_dispatch_alert
from app.notifications import (
    send_fcm_notification,
    send_telegram_notification,
    format_telegram_alert,
    build_telegram_inline_keyboard,
)
from app.market_cache import market_cache
from app.auth import mask_id

# Import from modular engine subpackages
from app.engine.portfolio_sync import (
    _DEMAT_PORTFOLIO_CACHE,
    _DEMAT_PORTFOLIO_CACHE_TTL,
    resolve_isin_to_nse_symbol,
    fetch_user_portfolio,
    invalidate_demat_portfolio_cache,
    update_demat_portfolio_cache,
)
from app.engine.data_fetcher import (
    _FINANCIALS_CACHE,
    _NEWS_CACHE,
    _NEWS_CACHE_TTL,
    _normalize_canonical_key,
    fetch_stock_financials,
    fetch_stock_news,
)
from app.engine.deterministic import (
    get_adaptive_weights,
    compute_tactical_levels,
    compute_deterministic_confluence,
    check_has_active_catalyst,
)
from app.engine.gemini_ai import (
    reset_ai_scan_counter,
    get_ai_scan_calls_count,
    increment_ai_scan_calls_count,
    _clean_json_text,
    _parse_and_validate_ai_response,
    evaluate_stock_with_ai,
)

logger = logging.getLogger("stokvigil.agent_runner")

# Target 1 Reached Dispatch Cache: key -> timestamp (Prevents spamming Target 1 hit alerts)
_TARGET_1_DISPATCHED_TODAY: Dict[str, float] = {}
_MAX_AI_CALLS_PER_SCAN: int = getattr(settings, "MAX_AI_CALLS_PER_SCAN", 15)


# ==========================================
# 5-MINUTE MULTI-TENANT SURVEILLANCE RUNNER
# ==========================================

async def evaluate_single_symbol_full(
    symbol: str, 
    macro_data: Optional[Dict[str, Any]] = None,
    holding_info: Optional[Dict[str, Any]] = None,
    technicals: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates all institutional dimensions (technicals, macro, F&O flow, forensics, news, AI confluence)
    for a single symbol and caches the analysis into RAM.
    Uses Tier-1 Gatekeeper filtering to call Gemini AI only for active catalyst stocks (preserving free tier quota).
    """
    if macro_data is None:
        macro_data = await asyncio.to_thread(fetch_macro_market_regime)

    # 1. Technicals: use pre-computed batch if provided, otherwise fetch
    if technicals is None:
        technicals = await asyncio.to_thread(fetch_multi_timeframe_technicals, symbol)

    # 2. Concurrently fetch financials (non-blocking in 5m loop) and evaluate if news is needed
    financials_task = asyncio.to_thread(fetch_stock_financials, symbol, False)

    raw_vol = technicals.get("volume_multiple") or technicals.get("volume_surge_ratio") or 1.0
    try:
        vol_mult = float(raw_vol)
    except (ValueError, TypeError):
        vol_mult = 1.0
    raw_vwap = technicals.get("price_vs_vwap_pct") or 0.0
    try:
        vwap_pct = abs(float(raw_vwap))
    except (ValueError, TypeError):
        vwap_pct = 0.0

    needs_news = (vol_mult >= 1.5) or (vwap_pct >= 0.8) or (holding_info is not None)
    if needs_news:
        news_task = asyncio.to_thread(fetch_stock_news, symbol)
        financials, news_items = await asyncio.gather(financials_task, news_task)
    else:
        financials = await financials_task
        canonical_key = _normalize_canonical_key(symbol)
        cached_news_entry = _NEWS_CACHE.get(canonical_key)
        if cached_news_entry and (time.time() - cached_news_entry.get("timestamp", 0)) < _NEWS_CACHE_TTL:
            news_items = cached_news_entry.get("data", [])
        else:
            news_items = []

    flow_data = await asyncio.to_thread(
        fetch_delivery_and_fo_flow, 
        symbol, 
        technicals.get("price_vs_vwap_pct", 0.0),
        None,
        technicals.get("volume_multiple")
    )
    forensics = evaluate_forensic_health(symbol, financials)

    # Tier-1 Smart Gatekeeper Evaluation
    has_catalyst, catalyst_reason = check_has_active_catalyst(
        symbol=symbol,
        technicals=technicals,
        flow_data=flow_data,
        news_items=news_items,
        holding_info=holding_info
    )

    if has_catalyst and settings.GEMINI_API_KEY:
        logger.info(f"⚡ Active Catalyst Detected for {symbol}: {catalyst_reason}. Invoking Gemini AI...")
        analysis = await evaluate_stock_with_ai(
            symbol=symbol,
            technicals=technicals,
            flow_data=flow_data,
            macro_data=macro_data,
            forensics=forensics,
            financials=financials,
            news_items=news_items,
            holding_info=holding_info
        )
    else:
        analysis = compute_deterministic_confluence(
            symbol=symbol,
            technicals=technicals,
            flow_data=flow_data,
            macro_data=macro_data,
            forensics=forensics,
            financials=financials,
            news_items=news_items,
            holding_info=holding_info
        )

    stock_name = (
        financials.get("name") or 
        (holding_info.get("name") if holding_info else None) or 
        (holding_info.get("stock_name") if holding_info else None) or 
        symbol.replace(".BO", "").replace(".NS", "")
    )

    pack = {
        "symbol": symbol,
        "clean_symbol": symbol.replace(".BO", "").replace(".NS", "").strip().upper(),
        "name": stock_name,
        "technicals": technicals,
        "financials": financials,
        "flow_data": flow_data,
        "forensics": forensics,
        "news_items": news_items,
        "analysis": analysis,
        "current_price": technicals.get("current_price", 0.0),
        "confluence_score": analysis.get("confluence_score", 50),
        "action_bias": analysis.get("action_bias", "HOLD_NEUTRAL"),
        "tactical_levels": analysis.get("tactical_levels", {})
    }

    market_cache.set_stock(symbol, pack, ttl_seconds=900)
    return pack


def precompute_symbol_market_state(
    symbol: str,
    technicals: Dict[str, Any],
    macro_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    High-speed in-memory deterministic market state pre-computation for Step 1.
    Executes in < 0.001ms with 0 Gemini AI calls and 0 blocking network scrapers.
    Pre-computes price, technicals, Wyckoff VSA, Camarilla pivots, and deterministic confluence in RAM.
    """
    clean_sym = symbol.replace(".BO", "").replace(".NS", "").strip().upper()
    current_price = float(technicals.get("current_price") or 0.0)
    atr_val = float(technicals.get("atr_14") or ((current_price * 0.015) if current_price > 0 else 0.0))

    canonical_key = _normalize_canonical_key(clean_sym)
    cached_fin = _FINANCIALS_CACHE.get(canonical_key, {}).get("data") or _FINANCIALS_CACHE.get(clean_sym, {}).get("data")
    if cached_fin:
        financials = cached_fin
    else:
        financials = {
            "symbol": clean_sym,
            "name": clean_sym,
            "price": current_price,
            "pe_ratio": None,
            "forward_pe": None,
            "debt_to_equity": None,
            "revenue_growth_pct": None,
            "earnings_growth_pct": None,
            "profit_margin_pct": None,
            "roe_pct": None,
            "market_cap": None,
            "beta_volatility": None,
            "52_week_high": None,
            "52_week_low": None,
        }

    flow_data = fetch_delivery_and_fo_flow(
        symbol,
        technicals.get("price_vs_vwap_pct", 0.0),
        None,
        technicals.get("volume_multiple")
    )
    forensics = evaluate_forensic_health(symbol, financials)

    analysis = compute_deterministic_confluence(
        symbol=symbol,
        technicals=technicals,
        flow_data=flow_data,
        macro_data=macro_data or {},
        forensics=forensics,
        financials=financials,
        news_items=[]
    )

    if current_price > 0 and atr_val > 0:
        pivots = technicals.get("camarilla_pivots") if isinstance(technicals.get("camarilla_pivots"), dict) else {}
        swing_val = technicals.get("swing_high") or technicals.get("day_high") or 0.0
        swing_high = float(swing_val) if not isinstance(swing_val, dict) else 0.0
        tactical = compute_tactical_levels(
            current_price=current_price,
            atr_val=atr_val,
            swing_high=swing_high,
            h3=pivots.get("h3"),
            h4=pivots.get("h4"),
            l3=pivots.get("l3"),
            l4=pivots.get("l4"),
            vwap_val=technicals.get("vwap"),
            vwap_upper_1s=technicals.get("vwap_upper_1s"),
            action_bias=analysis.get("action_bias", "HOLD_NEUTRAL")
        )
        if tactical:
            analysis["tactical_levels"] = tactical

    stock_name = financials.get("name") or clean_sym
    pack = {
        "symbol": symbol,
        "clean_symbol": clean_sym,
        "name": stock_name,
        "technicals": technicals,
        "financials": financials,
        "flow_data": flow_data,
        "forensics": forensics,
        "news_items": [],
        "analysis": analysis,
        "current_price": current_price,
        "confluence_score": analysis.get("confluence_score", 50) if current_price > 0 else 0,
        "action_bias": analysis.get("action_bias", "HOLD_NEUTRAL") if current_price > 0 else "DATA_UNAVAILABLE",
        "tactical_levels": analysis.get("tactical_levels", {}) if current_price > 0 else {}
    }

    market_cache.set_stock(symbol, pack, ttl_seconds=900)
    market_cache.set_stock(clean_sym, pack, ttl_seconds=900)
    return pack


async def sync_market_cache_for_all_active_symbols(supabase_client) -> int:
    """
    Pre-computes and caches market state in RAM for all unique symbols across all user watchlists.
    Uses high-speed vectorized batch technical download (yf.download) with session-invariant daily cache.
    Executes 100% deterministic RAM math for all symbols with 0 Gemini calls in Step 1.
    """
    macro_data = await asyncio.to_thread(fetch_macro_market_regime)
    symbols = []
    try:
        from app.db_pool import fetch_all
        rows = await fetch_all("SELECT DISTINCT UPPER(TRIM(symbol)) as symbol FROM user_watchlists WHERE symbol IS NOT NULL")
        if rows is not None:
            symbols = list(set(r['symbol'].strip().upper() for r in rows if r.get('symbol')))
    except Exception as pool_err:
        logger.debug(f"Pooled symbol query note: {pool_err}")

    if not symbols:
        try:
            w_res = supabase_client.table("user_watchlists").select("symbol").limit(5000).execute()
            symbols = list(set(item['symbol'].strip().upper() for item in (w_res.data or []) if item.get('symbol')))
        except Exception as rest_err:
            logger.error(f"REST symbol query failed: {rest_err}")

    if not symbols:
        logger.info("No active symbols found across user watchlists to pre-compute.")
        return 0

    symbols_to_sync = [s for s in symbols if not market_cache.is_fresh(s, max_age_seconds=240)]
    synced_count = len(symbols) - len(symbols_to_sync)

    if symbols_to_sync:
        logger.info(f"⚡ Pre-computing institutional market state for {len(symbols_to_sync)} unique symbols via Vectorized Batch Engine...")
        batch_technicals = await asyncio.to_thread(batch_fetch_multi_timeframe_technicals, symbols_to_sync)
        sem = asyncio.Semaphore(20)

        async def _worker(sym: str):
            nonlocal synced_count
            async with sem:
                try:
                    tech = batch_technicals.get(sym) or batch_technicals.get(f"{sym}.NS") or batch_technicals.get(f"{sym}.BO") or {}
                    precompute_symbol_market_state(sym, tech, macro_data)
                    synced_count += 1
                    if synced_count % 20 == 0 or synced_count == len(symbols):
                        logger.info(f"⏳ Pre-computing market cache: {synced_count}/{len(symbols)} symbols ({round((synced_count / len(symbols)) * 100)}%)...")
                except Exception as e:
                    logger.error(f"Error pre-computing market cache for {sym}: {e}")

        await asyncio.gather(*(_worker(s) for s in symbols_to_sync))

    logger.info(f"✅ Market Cache Sync Complete: {synced_count}/{len(symbols)} unique symbols cached in RAM.")
    return synced_count


async def evaluate_user_portfolio_and_watchlists(
    user_id: str, 
    supabase_client, 
    macro_data: Optional[Dict[str, Any]] = None,
    preloaded_user_ctx: Optional[Dict[str, Any]] = None
) -> List[dict]:
    """
    Evaluates all tracked stocks for a user across demat holdings and manual watchlists.
    Uses high-speed In-Memory Market Cache for sub-millisecond per-stock lookups.
    Dispatches FCM Push and rich Telegram notifications for high-conviction catalysts.
    Supports preloaded_user_ctx to bypass per-user DB roundtrips in multi-user scans.
    """
    generated_alerts = []
    
    # 1. Fetch user profile & notification settings
    profile = None
    if preloaded_user_ctx and preloaded_user_ctx.get("profile"):
        profile = preloaded_user_ctx["profile"]
    else:
        try:
            from app.db_pool import fetch_one
            pooled_profile = await fetch_one("SELECT * FROM profiles WHERE id = $1", user_id)
            if pooled_profile:
                profile = pooled_profile
        except Exception as pool_err:
            logger.debug(f"Pooled profile query note for user {mask_id(user_id)}: {pool_err}")

        if profile is None:
            profile_res = supabase_client.table("profiles").select("*").eq("id", user_id).execute()
            if not profile_res.data:
                logger.warning(f"Profile not found for user {mask_id(user_id)}")
                return []
            profile = profile_res.data[0]

    fcm_token = profile.get("fcm_device_token")
    fcm_enabled = profile.get("fcm_enabled", False)
    telegram_chat_id = profile.get("telegram_chat_id")
    telegram_enabled = profile.get("telegram_enabled", False)
    alert_sensitivity = (profile.get("alert_sensitivity") or "HIGH").upper()

    # 2. Fetch user's active watchlist
    symbols = set()
    if preloaded_user_ctx and preloaded_user_ctx.get("symbols") is not None:
        symbols = set(preloaded_user_ctx["symbols"])
    else:
        try:
            from app.db_pool import fetch_all
            pooled_watchlists = await fetch_all("SELECT symbol FROM user_watchlists WHERE user_id = $1", user_id)
            if pooled_watchlists is not None:
                symbols = set(item['symbol'] for item in pooled_watchlists if item.get('symbol'))
        except Exception as pool_err:
            logger.debug(f"Pooled watchlist query note for user {mask_id(user_id)}: {pool_err}")

        if not symbols:
            watchlist_res = supabase_client.table("user_watchlists").select("symbol").eq("user_id", user_id).execute()
            symbols = set(item['symbol'] for item in (watchlist_res.data or []) if item.get('symbol'))

    # 3. Check credentials and Demat holdings
    holdings_map = {}
    cred = None
    if preloaded_user_ctx and "cred" in preloaded_user_ctx:
        cred = preloaded_user_ctx["cred"]
    else:
        try:
            from app.db_pool import fetch_one
            pooled_cred = await fetch_one("SELECT * FROM user_credentials WHERE user_id = $1", user_id)
            if pooled_cred:
                cred = pooled_cred
        except Exception as pool_err:
            logger.debug(f"Pooled cred query note for user {mask_id(user_id)}: {pool_err}")

        if cred is None:
            cred_res = supabase_client.table("user_credentials").select("*").eq("user_id", user_id).execute()
            if cred_res.data:
                cred = cred_res.data[0]

    if cred:
        today_str = str(date.today())
        token_date = str(cred.get("token_date", ""))

        if token_date == today_str:
            now = time.time()
            cached_holdings = None
            if user_id in _DEMAT_PORTFOLIO_CACHE:
                entry = _DEMAT_PORTFOLIO_CACHE[user_id]
                if (now - entry.get("timestamp", 0)) < _DEMAT_PORTFOLIO_CACHE_TTL:
                    cached_holdings = entry.get("holdings")

            holdings = cached_holdings or []
            for h in holdings:
                sym = h.get('symbol')
                clean_s = h.get('clean_symbol') or (sym.replace(".BO", "").replace(".NS", "").strip().upper() if sym else "")
                if sym:
                    symbols.add(sym)
                    holdings_map[sym] = h
                    if clean_s:
                        symbols.add(clean_s)
                        holdings_map[clean_s] = h
        else:
            logger.info(f"ICICI Session Token for user {mask_id(user_id)} is from {token_date} (expired today {today_str}). Scanning watchlist symbols only.")

    if macro_data is None:
        macro_data = await asyncio.to_thread(fetch_macro_market_regime)

    # 4. Evaluate each symbol concurrently
    sym_sem = asyncio.Semaphore(10)

    async def _eval_symbol_worker(symbol: str) -> Optional[dict]:
        async with sym_sem:
            try:
                cached_pack = market_cache.get_stock(symbol)
                holding_info = holdings_map.get(symbol)

                if cached_pack:
                    technicals = cached_pack.get("technicals", {})
                    financials = cached_pack.get("financials", {})
                    flow_data = cached_pack.get("flow_data", {})
                    analysis = dict(cached_pack.get("analysis", {}))

                    if holding_info:
                        curr_p = float(
                            technicals.get("current_price") or 
                            financials.get("price") or 
                            holding_info.get("current_market_price") or 
                            holding_info.get("last_price") or 
                            0.0
                        )
                        avg_p = float(holding_info.get("average_price", 0.0) or 0.0)
                        if avg_p > 0 and curr_p > 0:
                            pnl_pct = round(((curr_p - avg_p) / avg_p) * 100, 2)
                        elif holding_info.get("unrealized_pnl_pct") is not None:
                            pnl_pct = round(float(holding_info["unrealized_pnl_pct"]), 2)
                        elif holding_info.get("pnl_percentage") is not None:
                            pnl_pct = round(float(holding_info["pnl_percentage"]), 2)
                        else:
                            pnl_pct = 0.0
                        raw_rsi = technicals.get("rsi_15m")
                        rsi_15m = float(raw_rsi) if raw_rsi is not None else 50.0
                        
                        if pnl_pct <= -3.5:
                            analysis["action_bias"] = "TRAILING_SL_ALERT"
                            analysis["has_actionable_signal"] = True
                            analysis["catalyst_category"] = "TRAILING_STOP_TRIGGER"
                            analysis["alert_title"] = f"{symbol}: Stop-Loss Defense Trigger (P&L: {pnl_pct:+.1f}%)"
                            analysis["holding_guidance"] = f"CRITICAL RISK DEFENSE: Position down {pnl_pct:+.1f}%. Immediate capital preservation stop-loss active."
                            drivers = list(analysis.get("confluence_drivers", []))
                            drivers.insert(0, f"Portfolio Risk: Position dropped {pnl_pct:+.1f}%. Protective stop-loss breach.")
                            analysis["confluence_drivers"] = drivers
                        elif pnl_pct >= 5.0 and rsi_15m > 72.0:
                            analysis["action_bias"] = "TRAILING_SL_ALERT"
                            analysis["has_actionable_signal"] = True
                            analysis["catalyst_category"] = "TRAILING_STOP_TRIGGER"
                            analysis["alert_title"] = f"{symbol}: Trailing Stop-Loss Trigger (P&L: +{pnl_pct}%)"
                            analysis["holding_guidance"] = f"Position gained +{pnl_pct}%; 15m RSI reached {rsi_15m:.1f}. Trailing SL active."
                            drivers = list(analysis.get("confluence_drivers", []))
                            drivers.insert(0, f"Position has gained {pnl_pct}%; 15m RSI reached {rsi_15m:.1f} (Overbought zone).")
                            analysis["confluence_drivers"] = drivers
                else:
                    fresh_pack = await evaluate_single_symbol_full(symbol, macro_data=macro_data, holding_info=holding_info)
                    technicals = fresh_pack.get("technicals", {})
                    financials = fresh_pack.get("financials", {})
                    flow_data = fresh_pack.get("flow_data", {})
                    analysis = fresh_pack.get("analysis", {})
                
                raw_score = analysis.get("confluence_score")
                try:
                    confluence_score = int(raw_score) if raw_score is not None else 50
                except (ValueError, TypeError):
                    confluence_score = 50
                has_actionable = analysis.get("has_actionable_signal", False)
                action_bias = analysis.get("action_bias", "HOLD_NEUTRAL")
                alert_title = analysis.get("alert_title", f"{symbol} Market Update")
                catalyst_type = analysis.get("catalyst_category", "NEWS_CATALYST")
                confluence_drivers = analysis.get("confluence_drivers", [])
                tactical_levels = analysis.get("tactical_levels", {})
                holding_guidance = analysis.get("holding_guidance")

                curr_price_val = float(
                    technicals.get("current_price") or 
                    financials.get("price") or 
                    0.0
                )
                today_tag = date.today().isoformat()
                t1_cache_key = f"{user_id}:{symbol}:{today_tag}"

                if curr_price_val > 0 and t1_cache_key not in _TARGET_1_DISPATCHED_TODAY:
                    try:
                        recent_alert_res = supabase_client.table("stok_alerts") \
                            .select("id, signal_type, tactical_levels, created_at") \
                            .eq("symbol", symbol) \
                            .order("created_at", desc=True) \
                            .limit(1) \
                            .execute()
                        
                        if recent_alert_res.data:
                            last_alert = recent_alert_res.data[0]
                            last_sig = last_alert.get("signal_type")
                            last_tactical = last_alert.get("tactical_levels") or {}
                            t1_str = last_tactical.get("target_1") or last_tactical.get("tactical_resistance_1") or last_tactical.get("tactical_support_1")
                            
                            if t1_str and last_sig in ["BUY_WATCH", "SELL_WATCH"]:
                                t1_num = float(str(t1_str).replace("₹", "").replace(",", "").strip())
                                entry_range_str = last_tactical.get("entry_range", "N/A")
                                
                                if last_sig == "BUY_WATCH" and curr_price_val >= t1_num:
                                    action_bias = "TARGET_1_TRAIL_ALERT"
                                    has_actionable = True
                                    catalyst_type = "PRICE_BREAKOUT"
                                    alert_title = f"🎯 {symbol}: Tactical Resistance 1 Achieved (₹{curr_price_val:,.2f})"
                                    holding_guidance = (
                                        f"🎯 TACTICAL BENCHMARK 1 HIT: Price achieved ₹{t1_num:,.2f}. "
                                        f"Algorithmic execution rule: Lock in 50% profit immediately, and trail protective stop-loss to entry cost ({entry_range_str} / Breakeven). "
                                        f"Remaining position is now operating with ZERO capital risk."
                                    )
                                    confluence_drivers = [
                                        f"Tactical Resistance 1 (₹{t1_num:,.2f}, 1.5x ATR) hit with current price ₹{curr_price_val:,.2f}.",
                                        "Profit Lock Protocol: Bank 50% gains.",
                                        "Trailing Stop Protocol: Move SL to Cost/Breakeven to eliminate downside exposure."
                                    ]
                                    confluence_score = 90
                                    _TARGET_1_DISPATCHED_TODAY[t1_cache_key] = time.time()
                                elif last_sig == "SELL_WATCH" and curr_price_val <= t1_num:
                                    action_bias = "TARGET_1_TRAIL_ALERT"
                                    has_actionable = True
                                    catalyst_type = "PRICE_BREAKOUT"
                                    alert_title = f"🎯 {symbol}: Tactical Support 1 Achieved (₹{curr_price_val:,.2f})"
                                    holding_guidance = (
                                        f"🎯 TACTICAL SUPPORT 1 HIT: Price dropped to ₹{t1_num:,.2f}. "
                                        f"Algorithmic execution rule: Cover 50% short exposure immediately, and trail protective buy-stop to entry cost ({entry_range_str} / Breakeven). "
                                        f"Remaining position is now operating with ZERO capital risk."
                                    )
                                    confluence_drivers = [
                                        f"Tactical Support 1 (₹{t1_num:,.2f}, 1.5x ATR) hit with current price ₹{curr_price_val:,.2f}.",
                                        "Profit Lock Protocol: Cover 50% short exposure.",
                                        "Trailing Stop Protocol: Move Buy-Stop to Cost/Breakeven to eliminate upside exposure."
                                    ]
                                    confluence_score = 90
                                    _TARGET_1_DISPATCHED_TODAY[t1_cache_key] = time.time()
                    except Exception as t1_err:
                        logger.debug(f"Target 1 check note for {symbol}: {t1_err}")
                
                should_dispatch = False
                is_breakdown_or_sl = (action_bias in ["TRAILING_SL_ALERT", "SELL_WATCH", "TARGET_1_TRAIL_ALERT"] or confluence_score <= 35)

                if alert_sensitivity == "HIGH":
                    should_dispatch = (confluence_score >= 80) or is_breakdown_or_sl
                elif alert_sensitivity == "FII":
                    is_fii = (catalyst_type in ["BLOCK_DEAL", "DEBT_REDUCTION"] or flow_data.get("is_high_delivery"))
                    should_dispatch = (is_fii and (confluence_score >= 65 or has_actionable)) or is_breakdown_or_sl
                else: # ALL
                    should_dispatch = has_actionable or (confluence_score >= 65) or is_breakdown_or_sl

                if not should_dispatch:
                    return None

                is_tier1 = (confluence_score >= 88 or action_bias in ["TRAILING_SL_ALERT", "SELL_WATCH", "TARGET_1_TRAIL_ALERT"] or catalyst_type in ["BLOCK_DEAL", "TRAILING_STOP_TRIGGER", "PRICE_BREAKOUT"])
                allowed, reason = should_dispatch_alert(user_id, symbol, action_bias, confluence_score, is_tier1)
                
                if not allowed:
                    logger.info(f"Skipping dispatch for {symbol}: {reason}")
                    return None

                if settings.GEMINI_API_KEY and get_ai_scan_calls_count() < _MAX_AI_CALLS_PER_SCAN:
                    increment_ai_scan_calls_count()
                    try:
                        ai_evaluator = _get_active_ai_evaluator()
                        ai_res = await ai_evaluator(
                            symbol=symbol,
                            technicals=technicals,
                            flow_data=flow_data,
                            macro_data=macro_data,
                            forensics=forensics,
                            financials=financials,
                            news_items=cached_pack.get("news_items", []) if cached_pack else [],
                            holding_info=holding_info
                        )
                        if ai_res and isinstance(ai_res, dict):
                            analysis.update(ai_res)
                            alert_title = analysis.get("alert_title") or alert_title
                            catalyst_type = analysis.get("catalyst_category") or catalyst_type
                            confluence_drivers = analysis.get("confluence_drivers") or confluence_drivers
                            tactical_levels = analysis.get("tactical_levels") or tactical_levels
                            holding_guidance = analysis.get("holding_guidance") or holding_guidance
                    except Exception as ai_enrich_err:
                        logger.warning(f"AI enrichment fallback note for {symbol}: {ai_enrich_err}")

                demat_pos = None
                if holding_info:
                    curr_p = float(
                        technicals.get("current_price") or 
                        financials.get("price") or 
                        holding_info.get("current_market_price") or 
                        holding_info.get("last_price") or 
                        0.0
                    )
                    avg_p = float(holding_info.get("average_price", 0.0) or 0.0)
                    if avg_p > 0 and curr_p > 0:
                        pnl_pct = round(((curr_p - avg_p) / avg_p) * 100, 2)
                    elif holding_info.get("unrealized_pnl_pct") is not None:
                        pnl_pct = round(float(holding_info["unrealized_pnl_pct"]), 2)
                    elif holding_info.get("pnl_percentage") is not None:
                        pnl_pct = round(float(holding_info["pnl_percentage"]), 2)
                    else:
                        pnl_pct = 0.0
                    demat_pos = {
                        "is_in_portfolio": True,
                        "quantity": holding_info.get("quantity", 0),
                        "average_buy_price": avg_p,
                        "unrealized_pnl_pct": pnl_pct
                    }

                fcm_sent = False
                if fcm_token and fcm_enabled:
                    fcm_body = f"Score: {confluence_score}/100 | {action_bias.replace('_', ' ')} | Tactical Res: {tactical_levels.get('target_1', 'N/A')} | SL: {tactical_levels.get('protective_stop_loss', 'N/A')}"
                    fcm_sent = await send_fcm_notification(fcm_token, alert_title, fcm_body, {
                        "symbol": symbol,
                        "action_bias": action_bias,
                        "confluence_score": str(confluence_score),
                        "catalyst_type": catalyst_type
                    })

                telegram_sent = False
                if telegram_enabled and telegram_chat_id:
                    formatted_msg = format_telegram_alert(
                        symbol=symbol,
                        alert_title=alert_title,
                        action_bias=action_bias,
                        confluence_score=confluence_score,
                        catalyst_type=catalyst_type,
                        confluence_drivers=confluence_drivers,
                        tactical_levels=tactical_levels,
                        demat_position=demat_pos,
                        metrics_snapshot={
                            "current_price": technicals.get("current_price"),
                            "change_pct": technicals.get("change_pct"),
                            "orb_status": technicals.get("orb_status"),
                            "rsi_15m": technicals.get("rsi_15m"),
                            "rsi_5m": technicals.get("rsi_5m"),
                            "vwap": technicals.get("vwap"),
                            "delivery_pct": flow_data.get("delivery_pct"),
                            "vsa_regime": flow_data.get("vsa_regime"),
                            "factor_breakdown": analysis.get("factor_breakdown")
                        },
                        holding_guidance=holding_guidance
                    )
                    inline_buttons = build_telegram_inline_keyboard(symbol)
                    telegram_sent = await send_telegram_notification(telegram_chat_id, formatted_msg, reply_markup=inline_buttons)

                CATALYST_SYNONYM_MAP = {
                    "EARNINGS_SURPRISE": "EARNINGS_BEAT",
                    "DEBT_REDUCTION": "DEBT_CHANGE",
                    "PRICE_BREAKDOWN": "PRICE_BREAKOUT",
                    "STOP_LOSS_DEFENSE": "TRAILING_STOP_TRIGGER",
                    "TARGET_1_ACHIEVED": "PRICE_BREAKOUT"
                }
                normalized_catalyst = CATALYST_SYNONYM_MAP.get(catalyst_type, catalyst_type)
                VALID_CATALYST_TYPES = {
                    "BLOCK_DEAL", "EARNINGS_BEAT", "DEBT_CHANGE", "PRICE_BREAKOUT", 
                    "NEWS_CATALYST", "VOLUME_SURGE", "TECHNICAL_BREAKOUT", "TRAILING_STOP_TRIGGER"
                }
                resolved_catalyst = normalized_catalyst if normalized_catalyst in VALID_CATALYST_TYPES else "NEWS_CATALYST"

                clean_sym = symbol.replace(".BO", "").replace(".NS", "").strip().upper()
                is_bse = symbol.endswith(".BO") or (clean_sym.isdigit() and len(clean_sym) == 6)
                exch = "BSE" if is_bse else "NSE"
                stock_name = (
                    financials.get("name") or 
                    (holding_info.get("name") if holding_info else None) or 
                    (holding_info.get("stock_name") if holding_info else None) or 
                    clean_sym
                )

                alert_record = {
                    "user_id": user_id,
                    "symbol": clean_sym,
                    "alert_title": alert_title,
                    "catalyst_type": resolved_catalyst,
                    "impact_score": confluence_score,
                    "factual_reasons": confluence_drivers,
                    "metrics_snapshot": {
                        "clean_symbol": clean_sym,
                        "full_symbol": symbol,
                        "company_name": stock_name,
                        "exchange": exch,
                        "action_bias": action_bias,
                        "tactical_levels": tactical_levels,
                        "technicals": technicals,
                        "flow_data": flow_data,
                        "financials": financials,
                        "macro_data": macro_data,
                        "demat_position": demat_pos,
                        "factor_breakdown": analysis.get("factor_breakdown")
                    },
                    "sent_via_fcm": fcm_sent,
                    "sent_via_telegram": telegram_sent,
                }
                res = supabase_client.table("stok_alerts").insert(alert_record).execute()
                return res.data[0] if res.data else None

            except Exception as stock_err:
                logger.error(f"Error evaluating symbol {symbol} for user {mask_id(user_id)}: {stock_err}")
                return None

        if symbols:
            eval_results = await asyncio.gather(*(_eval_symbol_worker(s) for s in symbols), return_exceptions=False)
            for r in eval_results:
                if r:
                    generated_alerts.append(r)

        return generated_alerts
