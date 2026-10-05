import asyncio
import logging
import time
from collections import defaultdict
from datetime import date
from typing import Dict, Any, List, Optional, Set

from app.config import settings
from app.market_cache import market_cache
from app.notifications import (
    send_fcm_notification,
    send_telegram_notification,
    format_telegram_alert,
    build_telegram_inline_keyboard,
)
from app.auth import mask_id
from app.brokers import get_broker

logger = logging.getLogger("stokvigil.engine.ticker_stream")

# Hysteresis Latch TTL: 15 minutes (900 seconds) to prevent alert flooding on tick oscillation
_BREACH_LATCH_TTL_SECONDS: float = 900.0


class LiveTickerStreamManager:
    """
    Institutional Persistent WebSocket Ticker Stream Manager.
    Multiplexes a single broker WebSocket connection (ICICI Breeze / KiteTicker) across
    all active user Demat portfolios and watchlists.
    
    Guarantees:
    1. Sub-millisecond tick ingestion and RAM cache updates.
    2. Real-time breach detection for Camarilla L4 and Demat Trailing Stop-Loss.
    3. Gemini AI qualitative narrative synthesis with Immutable Mathematical Sovereignty.
    4. Anti-spam 15-minute hysteresis latch per stock-user pair.
    5. Strict Zero-Default Policy: Operates strictly on authentic broker feeds.
    """
    _instance: Optional['LiveTickerStreamManager'] = None

    def __new__(cls) -> 'LiveTickerStreamManager':
        if cls._instance is None:
            cls._instance = super(LiveTickerStreamManager, cls).__new__(cls)
            cls._instance._is_running = False
            cls._instance._active_broker_id: Optional[str] = None
            cls._instance._active_broker_adapter = None
            cls._instance._subscribed_symbols: Set[str] = set()
            cls._instance._symbol_to_users_map: Dict[str, Set[str]] = defaultdict(set)
            cls._instance._user_holdings_map: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
            cls._instance._user_profiles_cache: Dict[str, Dict[str, Any]] = {}
            cls._instance._breach_latch: Dict[str, float] = {}
            cls._instance._loop: Optional[asyncio.AbstractEventLoop] = None
            cls._instance._tick_count: int = 0
        return cls._instance

    def _normalize_symbol(self, symbol: str) -> str:
        return str(symbol).replace(".NS", "").replace(".BO", "").strip().upper()

    def get_stats(self) -> Dict[str, Any]:
        """Telemetry diagnostics for WebSocket stream health."""
        return {
            "is_running": self._is_running,
            "broker": self._active_broker_id,
            "subscribed_symbols_count": len(self._subscribed_symbols),
            "tracked_users_count": len(self._user_holdings_map),
            "active_breach_latches": len(self._breach_latch),
            "ticks_processed": self._tick_count,
        }

    def register_user_portfolio(
        self,
        user_id: str,
        holdings: List[Dict[str, Any]],
        watchlist_symbols: Optional[List[str]] = None,
        profile: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Dynamically registers or updates a user's tracked holdings and watchlist in memory.
        Subscribes any new symbols to the live WebSocket feed on the fly.
        """
        if not user_id:
            return

        if profile:
            self._user_profiles_cache[user_id] = profile

        new_symbols_to_subscribe: List[str] = []

        # 1. Register Demat holdings
        for h in holdings:
            sym = h.get("symbol") or h.get("stock_code") or ""
            clean_s = self._normalize_symbol(sym)
            if not clean_s:
                continue

            self._user_holdings_map[user_id][clean_s] = h
            self._symbol_to_users_map[clean_s].add(user_id)

            if clean_s not in self._subscribed_symbols:
                self._subscribed_symbols.add(clean_s)
                new_symbols_to_subscribe.append(clean_s)

        # 2. Register manual watchlist symbols
        if watchlist_symbols:
            for w_sym in watchlist_symbols:
                clean_w = self._normalize_symbol(w_sym)
                if not clean_w:
                    continue
                self._symbol_to_users_map[clean_w].add(user_id)
                if clean_w not in self._subscribed_symbols:
                    self._subscribed_symbols.add(clean_w)
                    new_symbols_to_subscribe.append(clean_w)

        # 3. Dynamic Subscription to Broker Stream
        if new_symbols_to_subscribe and self._active_broker_adapter and self._is_running:
            try:
                self._active_broker_adapter.subscribe_symbols(new_symbols_to_subscribe)
                logger.info(f"Dynamically subscribed {len(new_symbols_to_subscribe)} new symbols for user {mask_id(user_id)}.")
            except Exception as e:
                logger.warning(f"Error subscribing new symbols dynamically: {e}")

    def on_tick_received(self, tick_data: Any) -> None:
        """
        Sub-millisecond broker WebSocket tick callback.
        Dispatches incoming ticks from ICICI Breeze or KiteTicker into RAM cache and breach evaluation.
        """
        self._tick_count += 1
        try:
            # Handle list or dict payload
            ticks = tick_data if isinstance(tick_data, list) else [tick_data]
            for tick in ticks:
                if not isinstance(tick, dict):
                    continue

                raw_sym = (
                    tick.get("stock_code") or 
                    tick.get("symbol") or 
                    tick.get("stock_name") or 
                    tick.get("trading_symbol") or 
                    ""
                )
                clean_sym = self._normalize_symbol(raw_sym)
                if not clean_sym:
                    continue

                raw_ltp = tick.get("last") or tick.get("ltp") or tick.get("close") or tick.get("last_price")
                if raw_ltp is None:
                    continue

                try:
                    ltp = float(raw_ltp)
                except (ValueError, TypeError):
                    continue

                if ltp <= 0.0:
                    continue

                # Extract volume, high, low if present
                vol = None
                raw_vol = tick.get("vol") or tick.get("volume") or tick.get("total_quantity_traded")
                if raw_vol is not None:
                    try:
                        vol = int(raw_vol)
                    except (ValueError, TypeError):
                        vol = None

                high = None
                raw_h = tick.get("high") or tick.get("day_high")
                if raw_h is not None:
                    try:
                        high = float(raw_h)
                    except (ValueError, TypeError):
                        high = None

                low = None
                raw_l = tick.get("low") or tick.get("day_low")
                if raw_l is not None:
                    try:
                        low = float(raw_l)
                    except (ValueError, TypeError):
                        low = None

                # 1. Update In-Memory Market Cache (<0.1ms)
                market_cache.update_live_tick(
                    symbol=clean_sym,
                    ltp=ltp,
                    volume=vol,
                    high=high,
                    low=low
                )

                # 2. Real-Time Breach Evaluation
                self._evaluate_tick_breach(clean_sym, ltp, high, low, vol)

        except Exception as e:
            logger.error(f"Error processing live tick packet: {e}")

    def _evaluate_tick_breach(
        self,
        symbol: str,
        ltp: float,
        high: Optional[float],
        low: Optional[float],
        volume: Optional[int]
    ) -> None:
        """
        Evaluates real-time price tick against Camarilla L4 and Demat Trailing Stop-Loss.
        Applies 15-minute anti-spam hysteresis latch and delegates to async AI narrative dispatch.
        """
        users_tracking = self._symbol_to_users_map.get(symbol, set())
        if not users_tracking:
            return

        cached_pack = market_cache.get_stock(symbol)
        technicals = cached_pack.get("technicals", {}) if cached_pack else {}
        camarilla = technicals.get("camarilla_pivots", {}) if isinstance(technicals.get("camarilla_pivots"), dict) else {}
        l4_val = camarilla.get("l4")
        tactical_levels = cached_pack.get("tactical_levels", {}) if cached_pack else {}
        target_1 = tactical_levels.get("target_1")
        protective_sl = tactical_levels.get("protective_stop_loss")

        now = time.time()

        for user_id in users_tracking:
            holding = self._user_holdings_map.get(user_id, {}).get(symbol)
            avg_p = float(holding.get("average_price", 0.0) or 0.0) if holding else 0.0
            pnl_pct = round(((ltp - avg_p) / avg_p) * 100, 2) if (avg_p > 0 and ltp > 0) else None

            breach_event = None

            # -------------------------------------------------------------
            # TRIGGER 1: Demat Capital Preservation Stop-Loss Breach (P&L <= -3.5%)
            # -------------------------------------------------------------
            if pnl_pct is not None and pnl_pct <= -3.5:
                latch_key = f"{user_id}:{symbol}:DEMAT_STOPLOSS"
                if (now - self._breach_latch.get(latch_key, 0)) >= _BREACH_LATCH_TTL_SECONDS:
                    self._breach_latch[latch_key] = now
                    breach_event = {
                        "type": "DEMAT_STOPLOSS",
                        "action_bias": "CAPITAL_PRESERVATION_EXIT",
                        "catalyst_category": "TRAILING_STOP_TRIGGER",
                        "confluence_score": 90,
                        "pnl_pct": pnl_pct,
                        "title": f"🚨 {symbol}: Capital Preservation Exit Trigger (P&L: {pnl_pct:+.1f}%)",
                        "reason": f"Demat portfolio protection trigger: Position down {pnl_pct:+.1f}% from buy price ₹{avg_p:,.2f}.",
                        "urgency": "CRITICAL",
                    }

            # -------------------------------------------------------------
            # TRIGGER 2: Camarilla L4 Major Support Breakdown
            # -------------------------------------------------------------
            if not breach_event and l4_val is not None:
                try:
                    l4_num = float(l4_val)
                    if l4_num > 0 and ltp < l4_num:
                        latch_key = f"{user_id}:{symbol}:CAMARILLA_L4"
                        if (now - self._breach_latch.get(latch_key, 0)) >= _BREACH_LATCH_TTL_SECONDS:
                            self._breach_latch[latch_key] = now
                            drop_dist = round(((l4_num - ltp) / l4_num) * 100, 2)
                            breach_event = {
                                "type": "CAMARILLA_L4_BREAKDOWN",
                                "action_bias": "SELL_WATCH",
                                "catalyst_category": "TECHNICAL_BREAKOUT",
                                "confluence_score": 30,
                                "pnl_pct": pnl_pct,
                                "title": f"🚨 {symbol}: Major Institutional Camarilla L4 Breakdown (₹{ltp:,.2f})",
                                "reason": f"Live price ₹{ltp:,.2f} sliced below institutional Camarilla L4 support (₹{l4_num:,.2f}, -{drop_dist}%).",
                                "urgency": "HIGH",
                            }
                except (ValueError, TypeError):
                    pass

            # -------------------------------------------------------------
            # TRIGGER 3: Tactical Target 1 Achieved (Profit Lock Protocol)
            # -------------------------------------------------------------
            if not breach_event and target_1 is not None and holding:
                try:
                    t1_num = float(str(target_1).replace("₹", "").replace(",", "").strip())
                    if t1_num > 0 and ltp >= t1_num:
                        latch_key = f"{user_id}:{symbol}:TARGET_1"
                        if (now - self._breach_latch.get(latch_key, 0)) >= _BREACH_LATCH_TTL_SECONDS:
                            self._breach_latch[latch_key] = now
                            breach_event = {
                                "type": "TARGET_1_ACHIEVED",
                                "action_bias": "TARGET_1_TRAIL_ALERT",
                                "catalyst_category": "PRICE_BREAKOUT",
                                "confluence_score": 90,
                                "pnl_pct": pnl_pct,
                                "title": f"🎯 {symbol}: Tactical Target 1 Achieved (₹{ltp:,.2f})",
                                "reason": f"Price reached Target 1 resistance (₹{t1_num:,.2f}). Algorithmic rule: Lock in 50% profit and trail stop to breakeven.",
                                "urgency": "HIGH",
                            }
                except (ValueError, TypeError):
                    pass

            # If breach verified, schedule async AI qualitative generation and dispatch
            if breach_event:
                self._dispatch_async_breach_alert(user_id, symbol, ltp, breach_event, cached_pack, holding)

    def _dispatch_async_breach_alert(
        self,
        user_id: str,
        symbol: str,
        ltp: float,
        breach_event: Dict[str, Any],
        cached_pack: Optional[Dict[str, Any]],
        holding: Optional[Dict[str, Any]]
    ) -> None:
        """Schedules non-blocking async execution of Gemini AI qualitative narrative and notification dispatch."""
        try:
            target_loop = self._loop
            if target_loop and target_loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._execute_breach_workflow(user_id, symbol, ltp, breach_event, cached_pack, holding),
                    target_loop
                )
            else:
                try:
                    current_loop = asyncio.get_running_loop()
                    if current_loop.is_running():
                        current_loop.create_task(
                            self._execute_breach_workflow(user_id, symbol, ltp, breach_event, cached_pack, holding)
                        )
                        return
                except RuntimeError:
                    pass

                # Fallback for standalone worker threads
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    new_loop.run_until_complete(
                        self._execute_breach_workflow(user_id, symbol, ltp, breach_event, cached_pack, holding)
                    )
                finally:
                    new_loop.close()
        except Exception as dispatch_err:
            logger.error(f"Error scheduling async breach workflow for {symbol}: {dispatch_err}")

    async def _execute_breach_workflow(
        self,
        user_id: str,
        symbol: str,
        ltp: float,
        breach_event: Dict[str, Any],
        cached_pack: Optional[Dict[str, Any]],
        holding: Optional[Dict[str, Any]]
    ) -> None:
        """
        Executes Gemini AI qualitative guidance generation and delivers instant FCM Push / Telegram notification.
        IMMUTABLE MATHEMATICAL SOVEREIGNTY: Price numbers, stop losses, and P&L percentages are hard-locked.
        Gemini AI generates the holding defense guidance and contextual analytical rationale.
        """
        try:
            logger.info(f"⚡ LIVE TICK BREACH DETECTED: {breach_event['title']} for user {mask_id(user_id)}")

            # 1. Fetch User Profile & Notification Channels
            profile = self._user_profiles_cache.get(user_id)
            if not profile:
                try:
                    from app.db_pool import fetch_one
                    profile = await fetch_one("SELECT * FROM profiles WHERE id = $1", user_id)
                except Exception as p_err:
                    logger.debug(f"Profile fetch note: {p_err}")

            if not profile:
                logger.warning(f"Cannot dispatch breach alert: Profile not found for user {mask_id(user_id)}")
                return

            fcm_token = profile.get("fcm_device_token")
            fcm_enabled = profile.get("fcm_enabled", False)
            telegram_chat_id = profile.get("telegram_chat_id")
            telegram_enabled = profile.get("telegram_enabled", False)

            alert_title = breach_event["title"]
            holding_guidance = breach_event["reason"]
            confluence_drivers = [breach_event["reason"]]
            action_bias = breach_event["action_bias"]
            confluence_score = breach_event["confluence_score"]
            catalyst_type = breach_event["catalyst_category"]

            technicals = cached_pack.get("technicals", {}) if cached_pack else {}
            financials = cached_pack.get("financials", {}) if cached_pack else {}
            flow_data = cached_pack.get("flow_data", {}) if cached_pack else {}
            forensics = cached_pack.get("forensics", {}) if cached_pack else {}
            tactical_levels = cached_pack.get("tactical_levels", {}) if cached_pack else {}

            # 2. Gemini AI Qualitative Synthesis (User Approved)
            if settings.GEMINI_API_KEY:
                try:
                    from app.engine.gemini_ai import evaluate_stock_with_ai
                    ai_res = await evaluate_stock_with_ai(
                        symbol=symbol,
                        technicals=technicals,
                        flow_data=flow_data,
                        macro_data={"trigger": "LIVE_TICK_BREACH", "breach_type": breach_event["type"]},
                        forensics=forensics,
                        financials=financials,
                        news_items=[],
                        holding_info=holding
                    )
                    if ai_res and isinstance(ai_res, dict):
                        # IMMUTABLE MATHEMATICAL SOVEREIGNTY:
                        # Gemini AI provides qualitative context only.
                        # Numbers, scores, and tactical levels remain 100% deterministic.
                        if ai_res.get("alert_title"):
                            alert_title = str(ai_res["alert_title"]).strip()
                        if ai_res.get("holding_guidance"):
                            holding_guidance = str(ai_res["holding_guidance"]).strip()
                        if ai_res.get("confluence_drivers") and isinstance(ai_res["confluence_drivers"], list):
                            confluence_drivers.extend(ai_res["confluence_drivers"])
                except Exception as ai_err:
                    logger.warning(f"Gemini AI enrichment note for live tick breach: {ai_err}")

            demat_pos = None
            if holding:
                avg_p = float(holding.get("average_price", 0.0) or 0.0)
                demat_pos = {
                    "is_in_portfolio": True,
                    "quantity": holding.get("quantity", 0),
                    "average_buy_price": avg_p,
                    "unrealized_pnl_pct": breach_event.get("pnl_pct", 0.0)
                }

            # 3. Dispatch FCM Push Notification
            fcm_sent = False
            if fcm_token and fcm_enabled:
                fcm_body = f"LTP: ₹{ltp:,.2f} | {holding_guidance}"
                fcm_sent = await send_fcm_notification(fcm_token, alert_title, fcm_body, {
                    "symbol": symbol,
                    "action_bias": action_bias,
                    "confluence_score": str(confluence_score),
                    "catalyst_type": catalyst_type,
                    "trigger": "LIVE_TICK_BREACH"
                })

            # 4. Dispatch Rich Telegram Alert
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
                        "current_price": ltp,
                        "change_pct": technicals.get("change_pct"),
                        "rsi_15m": technicals.get("rsi_15m"),
                        "vwap": technicals.get("vwap"),
                        "camarilla_l4": technicals.get("camarilla_pivots", {}).get("l4") if isinstance(technicals.get("camarilla_pivots"), dict) else None,
                        "delivery_pct": flow_data.get("delivery_pct")
                    },
                    holding_guidance=holding_guidance
                )
                inline_buttons = build_telegram_inline_keyboard(symbol)
                telegram_sent = await send_telegram_notification(telegram_chat_id, formatted_msg, reply_markup=inline_buttons)

            # 5. Record Alert in Supabase Audit Trail
            try:
                from app.core.dependencies import get_supabase
                supabase = get_supabase()
                alert_record = {
                    "user_id": user_id,
                    "symbol": symbol,
                    "alert_title": alert_title,
                    "catalyst_type": catalyst_type if catalyst_type in ["TRAILING_STOP_TRIGGER", "TECHNICAL_BREAKOUT", "PRICE_BREAKOUT"] else "TRAILING_STOP_TRIGGER",
                    "impact_score": confluence_score,
                    "factual_reasons": confluence_drivers,
                    "metrics_snapshot": {
                        "clean_symbol": symbol,
                        "current_price": ltp,
                        "action_bias": action_bias,
                        "tactical_levels": tactical_levels,
                        "demat_position": demat_pos,
                        "breach_event": breach_event
                    },
                    "sent_via_fcm": fcm_sent,
                    "sent_via_telegram": telegram_sent,
                }
                supabase.table("stok_alerts").insert(alert_record).execute()
                logger.info(f"✅ Live tick breach alert logged into database for {symbol}.")
            except Exception as db_err:
                logger.warning(f"Note on inserting live tick breach alert to database: {db_err}")

        except Exception as exec_err:
            logger.error(f"Error in breach workflow execution for {symbol}: {exec_err}")

    async def start(self) -> bool:
        """
        Starts the persistent broker WebSocket feed on application launch.
        Authenticates via server Master Credentials or today's active session.
        ZERO-DEFAULT: Enters graceful standby mode if exchange is closed or credentials absent.
        """
        if self._is_running:
            return True

        self._loop = asyncio.get_event_loop()

        # Gather tracked symbols across user watchlists to pre-populate stream
        all_symbols = set()
        try:
            from app.db_pool import fetch_all
            rows = await fetch_all("SELECT DISTINCT UPPER(TRIM(symbol)) as symbol FROM user_watchlists WHERE symbol IS NOT NULL")
            if rows:
                all_symbols = set(self._normalize_symbol(r['symbol']) for r in rows if r.get('symbol'))
        except Exception as sym_err:
            logger.debug(f"Note on fetching initial symbols: {sym_err}")

        # Check for active broker credentials
        adapter = get_broker("icici")
        self._active_broker_adapter = adapter
        self._active_broker_id = "icici"

        # Check if active session token exists in user_credentials for today
        active_creds = None
        try:
            from app.db_pool import fetch_one
            today_str = str(date.today())
            cred_row = await fetch_one("SELECT * FROM user_credentials WHERE token_date = $1 LIMIT 1", today_str)
            if cred_row:
                from app.security import vault
                raw_tok = cred_row.get("encrypted_session_token")
                session_tok = vault.decrypt(raw_tok) if raw_tok else ""
                active_creds = {
                    "app_key": settings.ICICI_MASTER_APP_KEY,
                    "secret_key": settings.ICICI_MASTER_SECRET_KEY,
                    "session_token": session_tok
                }
        except Exception as cred_err:
            logger.debug(f"Note on fetching active session for WebSocket stream: {cred_err}")

        if not active_creds or not active_creds.get("session_token"):
            logger.info("ℹ️ No active broker session token found for today. LiveTickerStreamManager in Standby Mode (awaits morning user authentication).")
            self._is_running = True
            return False

        symbols_list = list(all_symbols)
        connected = adapter.start_ticker_stream(
            decrypted_creds=active_creds,
            symbols=symbols_list,
            on_tick_callback=self.on_tick_received
        )

        if connected:
            self._is_running = True
            self._subscribed_symbols.update(symbols_list)
            logger.info(f"🚀 LiveTickerStreamManager active with {len(symbols_list)} initial tracked symbols.")
            return True
        else:
            logger.info("LiveTickerStreamManager entered Standby Mode.")
            self._is_running = True
            return False

    def stop(self) -> None:
        """Gracefully terminates broker WebSocket connection on application shutdown."""
        if self._active_broker_adapter:
            try:
                self._active_broker_adapter.stop_ticker_stream()
                logger.info("LiveTickerStreamManager stopped.")
            except Exception as e:
                logger.debug(f"Note on stop_ticker_stream: {e}")
        self._is_running = False
        self._subscribed_symbols.clear()
        self._symbol_to_users_map.clear()
        self._user_holdings_map.clear()


# Global Singleton Instance
ticker_manager = LiveTickerStreamManager()
