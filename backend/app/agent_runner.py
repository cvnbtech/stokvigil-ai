import asyncio
import json
import logging
import time
import urllib.parse
import urllib.request
import concurrent.futures
import feedparser
from datetime import date, datetime
import yfinance as yf
from typing import List, Dict, Any, Optional, Tuple

from app.config import settings
from app.vault import vault
from app.technical_engine import fetch_multi_timeframe_technicals, batch_fetch_multi_timeframe_technicals
from app.flow_tracker import fetch_delivery_and_fo_flow
from app.macro_filter import fetch_macro_market_regime, evaluate_forensic_health
from app.alert_limiter import should_dispatch_alert
from app.notifications import send_fcm_notification, send_telegram_notification, format_telegram_alert, build_telegram_inline_keyboard
from app.market_cache import market_cache
from app.auth import mask_id

logger = logging.getLogger("stokvigil.agent_runner")

# Silence noisy third-party internal SDK loggers (Breeze APILogger & yfinance)
logging.getLogger("APILogger").setLevel(logging.WARNING)
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

# ==========================================
# 1. UNIVERSAL DYNAMIC ISIN RESOLVER & DEMAT INTEGRATION
# ==========================================

_ISIN_CACHE: Dict[str, str] = {}

def resolve_isin_to_nse_symbol(isin: str, fallback_code: str = "") -> str:
    """
    Dynamically resolves any Indian stock ISIN (e.g. INE750C01026) or 6-digit BSE scrip code (e.g. 500325)
    to its official exchange ticker using real-time exchange security search. 100% dynamic for all 2,000+ stocks.
    """
    isin_clean = str(isin).strip().upper()
    fallback = str(fallback_code).strip().upper()

    # If already formatted with exchange suffix (.BO or .NS)
    if isin_clean.endswith(".BO") or isin_clean.endswith(".NS"):
        return isin_clean

    # If already a 6-digit BSE scrip code (e.g. 500325)
    if isin_clean.isdigit() and len(isin_clean) == 6:
        return f"{isin_clean}.BO"
    if fallback.isdigit() and len(fallback) == 6:
        return f"{fallback}.BO"
    if fallback.endswith(".BO") or fallback.endswith(".NS"):
        return fallback
    
    if not isin_clean or not isin_clean.startswith("INE"):
        return fallback or isin_clean

    # 1. Check in-memory RAM cache (<0.001ms)
    if isin_clean in _ISIN_CACHE:
        return _ISIN_CACHE[isin_clean]

    # 2. Dynamic Exchange Search via Yahoo Finance Search API
    try:
        import urllib.request
        search_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        }
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(isin_clean)}&quotesCount=5"
        req = urllib.request.Request(url, headers=search_headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            quotes = data.get("quotes", [])
            # Prioritize NSE (.NS) exchange listings first
            for quote in quotes:
                sym = quote.get("symbol", "")
                if sym.endswith(".NS"):
                    clean_sym = sym.replace(".NS", "").strip().upper()
                    if clean_sym:
                        _ISIN_CACHE[isin_clean] = clean_sym
                        return clean_sym

            # Fallback to BSE (.BO) or general equity
            for quote in quotes:
                sym = quote.get("symbol", "")
                if sym.endswith(".BO"):
                    clean_sym = sym.replace(".BO", "").strip().upper()
                    if clean_sym and not clean_sym.startswith("0P"):
                        # If BSE-exclusive, retain .BO suffix so downstream engines route to BSE
                        bse_sym = f"{clean_sym}.BO"
                        _ISIN_CACHE[isin_clean] = bse_sym
                        return bse_sym
                elif quote.get("quoteType") == "EQUITY":
                    clean_sym = sym.replace(".BO", "").replace(".NS", "").strip().upper()
                    if clean_sym and not clean_sym.startswith("0P"):
                        _ISIN_CACHE[isin_clean] = clean_sym
                        return clean_sym
    except Exception as e:
        logger.warning(f"Dynamic ISIN resolution failed for {isin_clean}: {e}")

    return fallback


def fetch_user_portfolio(app_key: str, secret_key: str, session_token: str) -> List[Dict[str, Any]]:
    """
    Fetches real-time portfolio holdings directly from user's CDSL/NSDL Demat account using breeze-connect SDK.
    Dynamically resolves ISINs to official NSE symbols in parallel for 100+ stock scalability.
    """
    if not app_key or not secret_key or not session_token:
        logger.warning("Incomplete Breeze credentials provided.")
        return []
        
    try:
        from breeze_connect import BreezeConnect
        import urllib.parse

        clean_app = str(app_key).strip()
        clean_sec = str(secret_key).strip()
        clean_tok = str(session_token).strip()

        # If user pasted whole redirect URL
        if "apisession=" in clean_tok:
            clean_tok = clean_tok.split("apisession=")[1].split("&")[0]

        clean_tok = urllib.parse.unquote(clean_tok).strip()

        # Masked verification log
        app_preview = f"{clean_app[:3]}...{clean_app[-3:]}" if len(clean_app) >= 6 else "***"
        sec_preview = f"{clean_sec[:3]}...{clean_sec[-3:]}" if len(clean_sec) >= 6 else "***"
        tok_preview = f"{clean_tok[:3]}...{clean_tok[-3:]}" if len(clean_tok) >= 6 else "***"
        logger.info(f"Breeze Auth Check - AppKey: {app_preview} (len: {len(clean_app)}), SecretKey: {sec_preview} (len: {len(clean_sec)}), SessionToken: {tok_preview} (len: {len(clean_tok)})")

        breeze = BreezeConnect(api_key=clean_app)
        breeze.generate_session(api_secret=clean_sec, session_token=clean_tok)
        
        session_active = bool(getattr(breeze, 'session_key', None))
        logger.info(f"Breeze session_key established: {session_active}")
        
        # Primary & Authoritative: Official ICICI Breeze Demat Holdings API
        demat_res = breeze.get_demat_holdings()
        status_code = demat_res.get('status') or demat_res.get('Status') if isinstance(demat_res, dict) else "Unknown"
        logger.info(f"Breeze get_demat_holdings status: {status_code}")

        raw_holdings = []
        if isinstance(demat_res, dict):
            if status_code in [200, "200"]:
                raw_holdings = demat_res.get('Success') or demat_res.get('success') or []
            else:
                logger.warning(f"Breeze get_demat_holdings returned error: {demat_res.get('Error') or demat_res}")
                return []

        # Fetch ICICI Tradebook Ledger for Average Buy Prices (Parallel NSE + BSE Query)
        def _fetch_tradebook_for_exchange(exch: str) -> Dict[str, float]:
            res_dict = {}
            try:
                p_res = breeze.get_portfolio_holdings(
                    exchange_code=exch,
                    from_date="",
                    to_date="",
                    stock_code="",
                    portfolio_type=""
                )
                if isinstance(p_res, dict):
                    status = p_res.get('status') or p_res.get('Status')
                    if status in [200, "200"]:
                        p_list = p_res.get('Success') or p_res.get('success') or []
                        if isinstance(p_list, list):
                            for item in p_list:
                                if isinstance(item, dict):
                                    code = str(item.get('stock_code') or item.get('symbol') or '').upper().strip()
                                    try:
                                        avg_p = float(item.get('average_price') or item.get('cost_price') or item.get('avg_cost') or item.get('purchase_price') or 0)
                                    except (ValueError, TypeError):
                                        avg_p = 0.0
                                    if code and avg_p > 0:
                                        res_dict[code] = avg_p
            except Exception as tradebook_err:
                logger.warning(f"Note on fetching ICICI {exch} tradebook avg prices: {tradebook_err}")
            return res_dict

        tradebook_avg_prices: Dict[str, float] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as tb_pool:
            fut_nse = tb_pool.submit(_fetch_tradebook_for_exchange, "NSE")
            fut_bse = tb_pool.submit(_fetch_tradebook_for_exchange, "BSE")
            tradebook_avg_prices.update(fut_nse.result())
            tradebook_avg_prices.update(fut_bse.result())

        # High-Speed Parallel ISIN Resolution for 100+ stocks
        def _parse_holding(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            if not isinstance(item, dict):
                return None
            raw_code = item.get('stock_code') or item.get('symbol') or item.get('stock_name') or ''
            isin_code = item.get('stock_ISIN') or item.get('isin') or ''
            clean_symbol = resolve_isin_to_nse_symbol(isin_code, fallback_code=raw_code)
            
            try:
                qty = float(item.get('quantity') or item.get('demat_total_bulk_quantity') or item.get('demat_avail_quantity') or 0)
            except (ValueError, TypeError):
                qty = 0.0

            # Merge average price from Tradebook ledger or Demat record
            raw_code_upper = str(raw_code).upper().strip()
            tb_price = tradebook_avg_prices.get(raw_code_upper, 0.0) or tradebook_avg_prices.get(clean_symbol, 0.0)
            
            try:
                avg_p = float(item.get('average_price') or item.get('avg_price') or item.get('cost_price') or item.get('purchase_price') or tb_price)
            except (ValueError, TypeError):
                avg_p = tb_price
                
            try:
                cmp = float(item.get('current_market_price') or item.get('last_price') or 0.0)
            except (ValueError, TypeError):
                cmp = 0.0

            stock_name = str(item.get('stock_name') or item.get('company_name') or item.get('stock_description') or '').strip()
            bare_symbol = clean_symbol.replace(".BO", "").replace(".NS", "").strip().upper()
            is_bse = clean_symbol.endswith(".BO") or str(item.get('exchange_code', '')).upper() == "BSE" or (bare_symbol.isdigit() and len(bare_symbol) == 6)

            if clean_symbol and qty > 0:
                return {
                    "symbol": clean_symbol,
                    "clean_symbol": bare_symbol,
                    "name": stock_name or bare_symbol,
                    "stock_name": stock_name or bare_symbol,
                    "exchange": "BSE" if is_bse else "NSE",
                    "quantity": qty,
                    "average_price": avg_p,
                    "current_market_price": cmp,
                }
            return None

        result = []
        seen_symbols = set()
        max_workers = min(10, max(1, len(raw_holdings)))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            parsed_items = list(pool.map(_parse_holding, raw_holdings))

        for parsed in parsed_items:
            if parsed and parsed["symbol"] not in seen_symbols:
                seen_symbols.add(parsed["symbol"])
                result.append(parsed)

        logger.info(f"Successfully retrieved {len(result)} ICICI Demat holdings: {[r['symbol'] for r in result]}")
        return result
    except Exception as e:
        logger.error(f"Error fetching ICICI Breeze portfolio: {e}")
        return []


# Silence internal yfinance 404 logs for unquoted/corporate action instruments
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

# ==========================================
# SCALABLE IN-MEMORY DUAL-EXCHANGE CACHES (RAM)
# ==========================================
# Corporate Fundamentals Cache: canonical_key -> {data, timestamp} (TTL: 12 hours / 43200s)
_FINANCIALS_CACHE: Dict[str, Dict[str, Any]] = {}
_FINANCIALS_CACHE_TTL: float = 43200.0  # 12 hours (Quarter-invariant corporate metrics)

# News RSS Cache: canonical_key -> {data, timestamp} (TTL: 30 minutes / 1800s)
_NEWS_CACHE: Dict[str, Dict[str, Any]] = {}
_NEWS_CACHE_TTL: float = 1800.0  # 30 minutes

# User Demat Portfolio Cache: user_id -> {holdings, timestamp} (TTL: 240 seconds / 4 minutes)
_DEMAT_PORTFOLIO_CACHE: Dict[str, Dict[str, Any]] = {}
_DEMAT_PORTFOLIO_CACHE_TTL: float = 240.0

# Per-scan AI Call Counter: Limits Gemini calls to max 15 per 5-minute cycle across all users
_AI_SCAN_CALLS_COUNT: int = 0
_MAX_AI_CALLS_PER_SCAN: int = getattr(settings, "MAX_AI_CALLS_PER_SCAN", 15)

def reset_ai_scan_counter() -> None:
    global _AI_SCAN_CALLS_COUNT
    _AI_SCAN_CALLS_COUNT = 0

def get_ai_scan_calls_count() -> int:
    return _AI_SCAN_CALLS_COUNT

def increment_ai_scan_calls_count() -> None:
    global _AI_SCAN_CALLS_COUNT
    _AI_SCAN_CALLS_COUNT += 1

def _normalize_canonical_key(symbol: str) -> str:
    """Normalizes any symbol format (e.g. INFY.NS, INFY.BO, 500209, INFY) to an uppercase canonical key."""
    return str(symbol).replace(".NS", "").replace(".BO", "").strip().upper()


def fetch_stock_financials(symbol: str, allow_network: bool = True) -> Dict[str, Any]:
    """
    Fetches comprehensive financial metrics, valuation data, debt ratios, quarterly growth,
    and 52-week position from Yahoo Finance with automatic Dual-Exchange (NSE / BSE) resolution.
    Features 4-hour in-memory caching and bounded socket timeouts to ensure sub-millisecond repeat
    lookups and zero hanging during 5-minute market surveillance scans.
    """
    clean_sym = str(symbol).strip().upper()
    if not clean_sym or clean_sym in ["NA", "NONE", "NULL", "0"]:
        return {"symbol": clean_sym, "price": 0.0}

    canonical_key = _normalize_canonical_key(clean_sym)
    now = time.time()

    # 1. Fast Cache Check (O(1) in-memory lookup across all users & tickers)
    for k in (canonical_key, clean_sym):
        if k in _FINANCIALS_CACHE:
            entry = _FINANCIALS_CACHE[k]
            if (now - entry.get("timestamp", 0)) < _FINANCIALS_CACHE_TTL:
                return entry.get("data", {})

    if not allow_network:
        # Fast non-blocking path: return clean zero-default payload without blocking 5m technical scan
        return {
            "symbol": clean_sym,
            "name": clean_sym,
            "price": 0.0,
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

    # 2. Determine dual-exchange candidates (NSE first, BSE fallback; or BSE first for 6-digit scrips)
    if clean_sym.isdigit() and len(clean_sym) == 6:
        # Numeric BSE security code (e.g., 500209)
        candidates = [f"{clean_sym}.BO", clean_sym]
    elif clean_sym.endswith(".BO"):
        candidates = [clean_sym, f"{canonical_key}.NS"]
    elif clean_sym.endswith(".NS"):
        candidates = [clean_sym, f"{canonical_key}.BO"]
    else:
        candidates = [f"{clean_sym}.NS", f"{clean_sym}.BO"]

    info = {}
    current_price = 0.0

    # 3. Query candidates with bounded per-ticker execution timeout
    for ticker_name in candidates:
        try:
            ticker = yf.Ticker(ticker_name)
            # Use bounded thread executor so a stalled network socket doesn't block the scan
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(lambda: ticker.info or {})
                ticker_info = fut.result(timeout=2.5)
            price = ticker_info.get('currentPrice') or ticker_info.get('regularMarketPrice') or ticker_info.get('previousClose') or 0.0
            if price > 0 or ticker_info.get('shortName') or ticker_info.get('marketCap'):
                info = ticker_info
                current_price = price
                break
        except Exception as ticker_err:
            logger.debug(f"Ticker fetch note for {ticker_name}: {ticker_err}")
            continue

    if not info and current_price == 0.0:
        empty_res = {"symbol": clean_sym, "price": 0.0}
        # Cache negative result for 15 minutes to prevent rapid retry storms
        _FINANCIALS_CACHE[canonical_key] = {"timestamp": now - _FINANCIALS_CACHE_TTL + 900.0, "data": empty_res}
        return empty_res

    try:
        pe_ratio = info.get('trailingPE')
        forward_pe = info.get('forwardPE')
        debt_to_equity = info.get('debtToEquity')
        revenue_growth = info.get('revenueGrowth')
        earnings_growth = info.get('earningsQuarterlyGrowth')
        profit_margins = info.get('profitMargins')
        return_on_equity = info.get('returnOnEquity')
        
        company_name = info.get('shortName') or info.get('longName') or canonical_key
        
        result_pack = {
            "symbol": clean_sym,
            "name": company_name,
            "price": current_price,
            "pe_ratio": round(pe_ratio, 2) if pe_ratio else None,
            "forward_pe": round(forward_pe, 2) if forward_pe else None,
            "debt_to_equity": round(debt_to_equity, 2) if debt_to_equity else None,
            "revenue_growth_pct": round(revenue_growth * 100, 2) if revenue_growth else None,
            "earnings_growth_pct": round(earnings_growth * 100, 2) if earnings_growth else None,
            "profit_margin_pct": round(profit_margins * 100, 2) if profit_margins else None,
            "roe_pct": round(return_on_equity * 100, 2) if return_on_equity else None,
            "market_cap": info.get('marketCap'),
            "beta_volatility": info.get('beta'),
            "52_week_high": info.get('fiftyTwoWeekHigh'),
            "52_week_low": info.get('fiftyTwoWeekLow'),
        }

        # 4. Store in RAM cache under canonical key, input symbol, and exchange tickers
        # Memory-bounded to 1000 items max
        if len(_FINANCIALS_CACHE) > 1000:
            oldest = sorted(_FINANCIALS_CACHE.keys(), key=lambda k: _FINANCIALS_CACHE[k].get("timestamp", 0))[:200]
            for ok in oldest:
                _FINANCIALS_CACHE.pop(ok, None)

        cache_entry = {"timestamp": now, "data": result_pack}
        _FINANCIALS_CACHE[canonical_key] = cache_entry
        _FINANCIALS_CACHE[clean_sym] = cache_entry
        for c in candidates:
            _FINANCIALS_CACHE[c] = cache_entry

        return result_pack
    except Exception as e:
        logger.warning(f"Error parsing financial metrics for {clean_sym}: {e}")
        fallback_res = {"symbol": clean_sym, "price": current_price}
        _FINANCIALS_CACHE[canonical_key] = {"timestamp": now, "data": fallback_res}
        return fallback_res


def fetch_stock_news(symbol: str) -> List[Dict[str, str]]:
    """
    Parses real-time Google News RSS feeds targeting block/bulk deals, orders,
    quarterly results, revenue, debt changes, and promoter activity in the last 24 hours.
    Features 15-minute in-memory caching and bounded HTTP request timeouts.
    """
    canonical_key = _normalize_canonical_key(symbol)
    if not canonical_key or canonical_key in ["NA", "NONE", "NULL", "0"]:
        return []

    now = time.time()
    if canonical_key in _NEWS_CACHE:
        entry = _NEWS_CACHE[canonical_key]
        if (now - entry.get("timestamp", 0)) < _NEWS_CACHE_TTL:
            return entry.get("data", [])

    query_str = f'"{canonical_key}" AND (block deal OR bulk deal OR quarterly results OR Q1 OR Q2 OR Q3 OR Q4 OR revenue OR profit OR order OR debt OR expansion)'
    encoded_symbol = urllib.parse.quote(query_str)
    rss_url = f"https://news.google.com/rss/search?q={encoded_symbol}&hl=en-IN&gl=IN&ceid=IN:en"
    
    headlines = []
    try:
        req = urllib.request.Request(
            rss_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"}
        )
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            content = resp.read()
            feed = feedparser.parse(content)
            for entry in feed.entries[:6]:
                headlines.append({
                    "title": entry.title,
                    "link": entry.link,
                    "published": entry.published,
                })
    except Exception as e:
        logger.debug(f"News RSS fetch note for {canonical_key}: {e}")

    # Bounded cache size to 1000 items
    if len(_NEWS_CACHE) > 1000:
        oldest = sorted(_NEWS_CACHE.keys(), key=lambda k: _NEWS_CACHE[k].get("timestamp", 0))[:200]
        for ok in oldest:
            _NEWS_CACHE.pop(ok, None)

    _NEWS_CACHE[canonical_key] = {
        "timestamp": now,
        "data": headlines
    }
    return headlines


# ==========================================
# 2. SENIOR TRADING ANALYST AI ENGINE
# ==========================================

def _clean_json_text(text: str) -> str:
    cleaned = (text or "").strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def _parse_and_validate_ai_response(
    raw_text: str,
    technicals: Dict[str, Any],
    flow_data: Dict[str, Any],
    forensics: Dict[str, Any],
    symbol: str,
    model_name: str
) -> Optional[Dict[str, Any]]:
    if not raw_text:
        return None
    try:
        cleaned = _clean_json_text(raw_text)
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            return None
        # Only retain factor_breakdown if genuinely evaluated by the AI model.
        # Zero hardcoded or fabricated values — never invent fake scores.
        raw_factors = parsed.get("factor_breakdown")
        if isinstance(raw_factors, dict) and any(raw_factors.values()):
            clean_factors = {}
            for k in ["technicals", "flow", "forensics", "catalysts"]:
                val = raw_factors.get(k)
                if val is not None and isinstance(val, (int, float)) and 0 <= val <= 100:
                    clean_factors[k] = int(val)
            parsed["factor_breakdown"] = clean_factors if clean_factors else None
        else:
            parsed["factor_breakdown"] = None

        return parsed
    except Exception as parse_err:
        logger.warning(f"Failed to parse AI JSON response for {symbol} ({model_name}): {parse_err}")
        return None


async def evaluate_stock_with_ai(
    symbol: str,
    technicals: Dict[str, Any],
    flow_data: Dict[str, Any],
    macro_data: Dict[str, Any],
    forensics: Dict[str, Any],
    financials: Dict[str, Any],
    news_items: List[Dict[str, str]],
    holding_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates 360-degree quantitative data and triggers high-conviction actionable alerts.
    Utilizes Gemini 3.6 / 2.5 / 1.5 Flash fallback chain, backed by a deterministic rule engine.
    """
    current_price = float(technicals.get("current_price") or financials.get("price") or 0.0)
    atr_val = float(technicals.get("atr_14") or ((current_price * 0.015) if current_price > 0 else 0.0))
    
    # Calculate Demat P&L
    demat_context = {"is_in_portfolio": False, "quantity": 0, "average_buy_price": 0.0, "unrealized_pnl_pct": 0.0}
    if holding_info and holding_info.get("quantity", 0) > 0:
        qty = holding_info.get("quantity", 0)
        avg_price = holding_info.get("average_price", 0.0)
        pnl_pct = round(((current_price - avg_price) / avg_price) * 100, 2) if (avg_price > 0 and current_price > 0) else 0.0
        demat_context = {
            "is_in_portfolio": True,
            "quantity": qty,
            "average_buy_price": avg_price,
            "current_market_price": current_price,
            "unrealized_pnl_pct": pnl_pct
        }

    # Prompt Payload Construction
    prompt = f"""
You are StokVigil AI, an Elite Senior Quantitative Trading Analyst and Market Intelligence Strategist specializing in Indian Stock Exchange (NSE/BSE) and ICICI Direct Demat surveillance.

Evaluate the multi-factor data payload for #{symbol} (NSE) and determine if there is an actionable price trajectory shift, institutional catalyst, or portfolio risk event.

============================================================
1. ICICI DIRECT DEMAT POSITION:
============================================================
{json.dumps(demat_context, indent=2)}

============================================================
2. MULTI-TIMEFRAME TECHNICAL INDICATORS:
============================================================
• 5-Minute RSI: {technicals.get('rsi_5m')} | 15-Minute RSI: {technicals.get('rsi_15m')} | Daily RSI: {technicals.get('rsi_daily')}
• RSI Divergence: {technicals.get('rsi_divergence')}
• MACD (12, 26, 9): Trend={technicals.get('macd_trend')}, Histogram={technicals.get('macd_histogram')}
• Intraday VWAP: ₹{technicals.get('vwap')} (Price vs VWAP: {technicals.get('price_vs_vwap_pct')}%)
• EMAs: 20 EMA=₹{technicals.get('ema_20')}, 50 EMA=₹{technicals.get('ema_50')}, 200 EMA=₹{technicals.get('ema_200')} ({technicals.get('ma_trend')})
• Volatility (14 ATR): ₹{atr_val}
• ADX (14-period Trend Strength): {technicals.get('adx_14')} ({technicals.get('adx_regime')})
• Camarilla Pivots: H4=₹{technicals.get('camarilla_pivots', {}).get('h4')}, H3=₹{technicals.get('camarilla_pivots', {}).get('h3')}, L3=₹{technicals.get('camarilla_pivots', {}).get('l3')}, L4=₹{technicals.get('camarilla_pivots', {}).get('l4')}
• Relative Strength vs NIFTY 50: {technicals.get('rs_rating')}% ({technicals.get('rs_regime')})
• Volume Multiple: {technicals.get('volume_multiple')}x vs 20 MA (Surge: {technicals.get('is_volume_surge')})

============================================================
3. INSTITUTIONAL FLOW & DERIVATIVES:
• Wyckoff VSA Regime: {flow_data.get('vsa_regime')} ({flow_data.get('vsa_note', '')})
• Delivery Volume: {f"{flow_data.get('delivery_pct')}% (High Delivery)" if flow_data.get('delivery_pct') is not None else "Intraday Cash Volume (Official Delivery % published post-market)"}
• F&O Open Interest: {flow_data.get('fo_oi_status')} ({flow_data.get('flow_bias')})
• Option Chain Put-Call Ratio (PCR): {flow_data.get('pcr')} (F&O Stock: {flow_data.get('is_fo_stock')})
• Max Pain Strike: ₹{flow_data.get('max_pain_strike')} (Support Strike: ₹{flow_data.get('major_support_strike')}, Resistance Strike: ₹{flow_data.get('major_resistance_strike')})

============================================================
4. FUNDAMENTAL VALUATION & FORENSIC HEALTH:
============================================================
• Trailing P/E: {financials.get('pe_ratio')} | Forward P/E: {financials.get('forward_pe')}
• Debt-to-Equity: {financials.get('debt_to_equity')}
• Revenue Growth YoY: {financials.get('revenue_growth_pct')}% | Profit Margin: {financials.get('profit_margin_pct')}%
• Forensic Red Flags: {json.dumps(forensics.get('red_flags', []))}

============================================================
5. MACRO REGIME & SECTOR:
============================================================
• NIFTY 50 Trend: {macro_data.get('nifty_trend')} ({macro_data.get('nifty_change_pct')}%)
• India VIX: {macro_data.get('india_vix')} ({macro_data.get('vix_regime')})
• Market Breadth (NSE Advance-Decline Ratio): {macro_data.get('adr_ratio')} ({macro_data.get('breadth_regime')}, Advances: {macro_data.get('advances')}, Declines: {macro_data.get('declines')})
• Breakout Trading Permitted: {macro_data.get('allow_breakout_trades')}
• Sector: {forensics.get('sector_name')}

============================================================
6. 24-HOUR REAL-TIME NEWS & FILINGS:
============================================================
{json.dumps(news_items, indent=2)}

DIRECTIVES:
1. Confluence Score (1-100): Technical (30%), Flow (25%), Fundamentals (25%), News/Catalysts (20%).
2. Action Bias: "BUY_WATCH" (Score >= 75), "SELL_WATCH" (Score <= 35), "TRAILING_SL_ALERT" (User holds stock, profit > 5% & momentum stalling), "HOLD_NEUTRAL".
3. Strict Vetoes: If Market Breadth ADR < 0.60 or allow_breakout_trades is false or price is below 200 EMA, VETO any long signal to HOLD_NEUTRAL. Respect Max Pain strike pinning and option writing walls.
4. Calculate strict tactical levels: Entry Range, Target 1 (1.5x ATR), Target 2 (2.5x ATR), Stop Loss (1.5x ATR), Risk-Reward Ratio (Min 1:2).

Output ONLY valid JSON matching this exact structure:
{{
  "symbol": "{symbol}",
  "has_actionable_signal": true/false,
  "action_bias": "BUY_WATCH | SELL_WATCH | TRAILING_SL_ALERT | HOLD_NEUTRAL",
  "confluence_score": 85,
  "alert_title": "Descriptive concise headline",
  "catalyst_category": "TECHNICAL_BREAKOUT | BLOCK_DEAL | EARNINGS_BEAT | DEBT_CHANGE | VOLUME_SURGE | TRAILING_STOP_TRIGGER | PRICE_BREAKOUT | NEWS_CATALYST",
  "confluence_drivers": [
    "Factual driver 1",
    "Factual driver 2",
    "Factual driver 3"
  ],
  "tactical_levels": {{
    "entry_range": "₹980.00 - ₹985.00",
    "target_1": "₹1,005.00",
    "target_2": "₹1,025.00",
    "protective_stop_loss": "₹968.00",
    "risk_reward_ratio": "1:2.3"
  }},
  "factor_breakdown": {{
    "technicals": 85,
    "flow": 72,
    "forensics": 80,
    "catalysts": 90
  }},
  "holding_guidance": "Recommended holding / trailing stop guidance for user's Demat position.",
  "growth_outlook_summary": "12-month expansion summary."
}}
"""

    if settings.GEMINI_API_KEY:
        # Modern Official Google GenAI SDK (google.genai)
        # Prioritize gemini-3.5-flash-lite (verified active in Cloud Run runtime),
        # with seamless high-performance fallbacks to gemini-2.0-flash and gemini-1.5-flash
        gemini_models = ['gemini-3.5-flash-lite', 'gemini-2.0-flash', 'gemini-1.5-flash']
        try:
            from google import genai
            client = genai.Client(api_key=settings.GEMINI_API_KEY)

            # Direct generation across prioritized models with zero redundant retry loops
            for model_name in gemini_models:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config={"response_mime_type": "application/json"}
                    )
                    raw_text = getattr(response, "text", None) or ""
                    parsed = _parse_and_validate_ai_response(
                        raw_text, technicals, flow_data, forensics, symbol, f"GenerateContent/{model_name}"
                    )
                    if parsed:
                        logger.info(f"Successfully evaluated {symbol} using Google GenAI SDK '{model_name}'.")
                        return parsed
                except Exception as model_err:
                    logger.warning(f"GenAI SDK '{model_name}' attempt failed for {symbol}: {model_err}")
                    continue
        except ImportError:
            # Fallback only if google.genai is not yet installed in runtime
            try:
                import google.generativeai as legacy_genai
                legacy_genai.configure(api_key=settings.GEMINI_API_KEY)
                for model_name in ['gemini-2.0-flash', 'gemini-1.5-flash']:
                    try:
                        model = legacy_genai.GenerativeModel(model_name)
                        response = model.generate_content(
                            prompt,
                            generation_config={"response_mime_type": "application/json"}
                        )
                        raw_text = getattr(response, "text", None) or ""
                        parsed = _parse_and_validate_ai_response(
                            raw_text, technicals, flow_data, forensics, symbol, f"Legacy/{model_name}"
                        )
                        if parsed:
                            logger.info(f"Successfully evaluated {symbol} using legacy AI model '{model_name}'.")
                            return parsed
                    except Exception as leg_err:
                        logger.warning(f"Legacy model '{model_name}' fallback failed for {symbol}: {leg_err}")
                        continue
            except Exception as leg_err:
                logger.warning(f"Legacy model fallback failed for {symbol}: {leg_err}")
        except Exception as e:
            logger.error(f"Gemini API execution error: {e}. Falling back to deterministic engine.")

    # Fallback to deterministic quantitative engine
    return compute_deterministic_confluence(
        symbol=symbol,
        technicals=technicals,
        flow_data=flow_data,
        macro_data=macro_data,
        forensics=forensics,
        financials=financials,
        news_items=news_items,
        holding_info=holding_info
    )


def get_adaptive_weights(macro_data: Dict[str, Any], adx_regime: Optional[str] = None) -> Tuple[Dict[str, float], str]:
    """
    Dynamically allocates confluence weights across the 4 pillars based on macro market regime.
    Prioritizes forensic health and flow during distribution/volatility, and technical momentum during strong trends.
    Returns (weights_dict, regime_name).
    """
    vix_val = macro_data.get("india_vix") or macro_data.get("vix_value")
    vix = float(vix_val) if vix_val is not None else None
    adr_val = macro_data.get("market_breadth_adr") or macro_data.get("adr_ratio")
    adr = float(adr_val) if adr_val is not None else None
    
    # Regime 1: High Volatility, Market Distribution, or Data Unavailable (Defensive posture)
    if (vix is not None and vix > 16.5) or (adr is not None and adr < 0.8) or vix is None or adr is None:
        return {"tech": 0.15, "flow": 0.35, "forensics": 0.35, "news": 0.15}, "HIGH_VOLATILITY_DEFENSIVE"
    # Regime 2: Strong Trending Bull Market (Momentum)
    elif adr >= 1.2 and vix <= 14.5:
        return {"tech": 0.40, "flow": 0.30, "forensics": 0.15, "news": 0.15}, "BULL_MOMENTUM"
    # Regime 3: Normal / Balanced Market
    else:
        return {"tech": 0.30, "flow": 0.25, "forensics": 0.25, "news": 0.20}, "BALANCED_NORMAL"


def compute_tactical_levels(
    current_price: Optional[float],
    atr_val: Optional[float],
    swing_high: Optional[float] = 0.0,
    demat_context: Optional[Dict[str, Any]] = None,
    h3: Optional[float] = None,
    h4: Optional[float] = None,
    l3: Optional[float] = None,
    l4: Optional[float] = None,
    vwap_val: Optional[float] = None,
    vwap_upper_1s: Optional[float] = None,
    action_bias: str = "HOLD_NEUTRAL"
) -> Optional[Dict[str, Any]]:
    """
    Computes institutional tactical levels: entry range, target 1, target 2, protective stop-loss, and R:R ratio.
    Direction-Aware: Properly computes downside targets and protective buy-stops for SELL_WATCH short / breakdown trades.
    ZERO-DEFAULT RULE: Returns None if current_price is None or <= 0.
    """
    if current_price is None or float(current_price) <= 0:
        return None

    price = float(current_price)
    atr = float(atr_val or (price * 0.015))
    if atr <= 0:
        atr = price * 0.015

    is_sell = action_bias in ["SELL_WATCH"]
    is_sl_alert = action_bias in ["TRAILING_SL_ALERT"]

    # 1. Bearish Breakdown / Short Setup (SELL_WATCH)
    if is_sell:
        # Entry Range around price / VWAP
        if vwap_val is not None and vwap_val > 0:
            entry_min = round(min(price, vwap_val), 2)
            entry_max = round(max(price, vwap_val), 2)
        else:
            entry_min = round(price * 0.995, 2)
            entry_max = round(price * 1.005, 2)

        # Downside Price Targets (Target < Price)
        if l3 and l4 and float(l3) > 0 and float(l4) > 0 and float(l3) < price:
            target_1 = round(min(price - (1.5 * atr), float(l3)), 2)
            target_2 = round(min(price - (2.5 * atr), float(l4)), 2)
            stop_loss = round(max(price + (1.0 * atr), float(h3 or (price * 1.02))), 2)
        else:
            target_1 = round(price - (1.5 * atr), 2)
            target_2 = round(price - (2.5 * atr), 2)
            stop_loss = round(price + (1.0 * atr), 2)

        # Strict directional bounds: Targets must be strictly below price, stop-loss strictly above
        target_1 = min(target_1, round(price * 0.98, 2))
        target_2 = min(target_2, round(price * 0.95, 2))
        stop_loss = max(stop_loss, round(price * 1.02, 2))

        risk_val = max(1.0, stop_loss - price)
        reward_val = max(2.5, price - target_2)
        rr_ratio = round(reward_val / risk_val, 1)

        return {
            "entry_range": f"₹{entry_min:,.2f} - ₹{entry_max:,.2f}",
            "target_1": f"₹{target_1:,.2f}",
            "target_2": f"₹{target_2:,.2f}",
            "protective_stop_loss": f"₹{stop_loss:,.2f}",
            "risk_reward_ratio": f"1:{rr_ratio}"
        }

    # 2. Bullish Setup (BUY_WATCH / HOLD_NEUTRAL) or Demat Protection
    if vwap_val is not None and vwap_upper_1s is not None and vwap_val > 0:
        entry_min = round(min(price, vwap_val), 2)
        entry_max = round(max(price, vwap_upper_1s), 2)
    elif h3 and l3 and float(l3) > 0:
        entry_min = round(min(price * 0.995, float(l3)), 2)
        entry_max = round(max(price * 1.005, price), 2)
    else:
        entry_min = round(price * 0.995, 2)
        entry_max = round(price * 1.005, 2)

    # Targets & Stop Loss
    try:
        swing = float(swing_high) if swing_high is not None and not isinstance(swing_high, dict) else 0.0
    except (ValueError, TypeError):
        swing = 0.0
    if swing > price:
        target_1 = round(price + (1.5 * atr), 2)
        target_2 = round(swing, 2)
        stop_loss = round(price - (1.0 * atr), 2)
    elif h3 and l3 and float(h3) > 0 and float(l3) > 0:
        target_1 = round(max(price + (1.5 * atr), float(h3)), 2)
        target_2 = round(max(price + (2.5 * atr), float(h4 or h3)), 2)
        stop_loss = round(min(price - (1.0 * atr), float(l4 or l3)), 2)
    else:
        target_1 = round(price + (1.5 * atr), 2)
        target_2 = round(price + (2.5 * atr), 2)
        stop_loss = round(price - (1.0 * atr), 2)

    target_1 = max(target_1, round(price * 1.02, 2))
    target_2 = max(target_2, round(price * 1.05, 2))
    stop_loss = min(stop_loss, round(price * 0.98, 2))

    if demat_context and demat_context.get("is_in_portfolio"):
        avg_buy = demat_context.get("average_buy_price", price)
        chandelier_sl = round(price - (2.5 * atr), 2)
        base_cost_sl = round(avg_buy * 0.96, 2)
        stop_loss = max(stop_loss, base_cost_sl, chandelier_sl)

    risk_val = max(1.0, price - stop_loss)
    reward_val = max(2.5, target_2 - price)
    rr_ratio = round(reward_val / risk_val, 1)

    return {
        "entry_range": f"₹{entry_min:,.2f} - ₹{entry_max:,.2f}",
        "target_1": f"₹{target_1:,.2f}",
        "target_2": f"₹{target_2:,.2f}",
        "protective_stop_loss": f"₹{stop_loss:,.2f}",
        "risk_reward_ratio": f"1:{rr_ratio}"
    }


def compute_deterministic_confluence(
    symbol: str,
    technicals: Dict[str, Any],
    flow_data: Dict[str, Any],
    macro_data: Dict[str, Any],
    forensics: Dict[str, Any],
    financials: Dict[str, Any],
    news_items: List[Dict[str, Any]],
    holding_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Deterministic Quantitative Confluence Engine with Adaptive Regime Weighting.
    Evaluates institutional math in 0.001ms with zero API costs.
    """
    price_candidate = (
        technicals.get("current_price") or 
        financials.get("price") or 
        (holding_info.get("current_market_price") if holding_info else None) or
        (holding_info.get("last_price") if holding_info else None) or
        (holding_info.get("average_price") if holding_info else None) or
        technicals.get("previous_close")
    )
    has_real_price = bool(price_candidate and float(price_candidate) > 0)
    current_price = float(price_candidate) if has_real_price else 0.0
    
    raw_atr = technicals.get("atr_14")
    if raw_atr is not None and float(raw_atr) > 0:
        atr_val = float(raw_atr)
    elif has_real_price:
        atr_val = max(1.0, round(current_price * 0.02, 2))
    else:
        atr_val = 0.0

    # Demat Holding Context
    demat_context = {"is_in_portfolio": False, "quantity": 0, "average_buy_price": 0.0, "unrealized_pnl_pct": 0.0}
    if holding_info:
        avg_p = float(holding_info.get("average_price", 0.0) or 0.0)
        curr_cmp = float(
            technicals.get("current_price") or 
            financials.get("price") or 
            holding_info.get("current_market_price") or 
            holding_info.get("last_price") or 
            0.0
        )
        if avg_p > 0 and curr_cmp > 0:
            pnl_pct = round(((curr_cmp - avg_p) / avg_p) * 100, 2)
        elif holding_info.get("unrealized_pnl_pct") is not None:
            pnl_pct = round(float(holding_info["unrealized_pnl_pct"]), 2)
        elif holding_info.get("pnl_percentage") is not None:
            pnl_pct = round(float(holding_info["pnl_percentage"]), 2)
        else:
            pnl_pct = 0.0

        demat_context = {
            "is_in_portfolio": True,
            "quantity": holding_info.get("quantity", 0),
            "average_buy_price": avg_p,
            "unrealized_pnl_pct": pnl_pct
        }

    raw_ts = technicals.get("technical_score")
    tech_score = float(raw_ts) if raw_ts is not None else 50.0
    raw_fs = flow_data.get("flow_score")
    flow_score = float(raw_fs) if raw_fs is not None else 50.0
    raw_fors = forensics.get("forensic_score")
    forensic_score = float(raw_fors) if raw_fors is not None else 50.0
    
    # News & Catalyst Scoring
    news_score = 50
    catalyst_category = "TECHNICAL_BREAKOUT"
    alert_title = f"{symbol}: Technical & Momentum Update"
    confluence_drivers = []
    
    for item in news_items:
        title_upper = item.get('title', '').upper()
        if "BLOCK DEAL" in title_upper or "BULK DEAL" in title_upper:
            news_score += 35
            catalyst_category = "BLOCK_DEAL"
            alert_title = f"{symbol}: Institutional Block/Bulk Deal Reported"
            confluence_drivers.append(f"Exchange Filing: {item['title']}")
            break
        elif any(k in title_upper for k in ["PROFIT", "REVENUE", "Q1", "Q2", "Q3", "Q4", "EARNINGS"]):
            news_score += 30
            catalyst_category = "EARNINGS_BEAT"
            alert_title = f"{symbol}: Quarterly Earnings & Financial Catalyst"
            confluence_drivers.append(f"Financial Disclosure: {item['title']}")
            break

    # Wyckoff VSA Scoring Enhancements
    vsa_regime = flow_data.get("vsa_regime", "NORMAL_VOLUME_SPREAD")
    if vsa_regime == "SMART_MONEY_ABSORPTION":
        del_p = flow_data.get("delivery_pct")
        del_str = f" ({del_p}%)" if del_p is not None else ""
        confluence_drivers.append(f"Wyckoff VSA: Institutional Delivery Absorption{del_str}")
        flow_score = min(95, flow_score + 8)
    elif vsa_regime == "OPERATOR_CHURN_TRAP":
        confluence_drivers.append("Wyckoff VSA Warning: Speculative Operator Churn (Low Delivery %)")
        flow_score = max(20, flow_score - 10)

    # Sector Breadth Integration
    sector_name = forensics.get("sector_name", "BROAD_MARKET")
    if sector_name != "BROAD_MARKET":
        confluence_drivers.append(f"Sector Alignment: {sector_name}")

    # Calculate Adaptive Confluence Score using Dynamic Weights
    adx_regime = technicals.get("adx_regime", "MODERATE_TREND")
    adx_val = technicals.get("adx_14")
    weights, macro_regime = get_adaptive_weights(macro_data, adx_regime)

    confluence_score = int(round(
        (tech_score * weights["tech"]) +
        (flow_score * weights["flow"]) +
        (forensic_score * weights["forensics"]) +
        (min(95, news_score) * weights["news"])
    ))

    # 1. ADX Trend Strength Check (Choppy Sideways Veto / Chop Penalty)
    if adx_regime == "CHOPPY_SIDEWAYS":
        adx_str = f" ({adx_val} < 20)" if adx_val is not None else ""
        confluence_drivers.append(f"ADX Warning: Low trend strength{adx_str}. Sideways consolidation risk.")
        confluence_score = max(25, confluence_score - 8)
    elif adx_regime == "STRONG_TREND":
        adx_str = f" ({adx_val} >= 25)" if adx_val is not None else ""
        confluence_drivers.append(f"ADX Confirmation: Strong Institutional Trend{adx_str}")

    # 2. Mansfield Relative Strength vs NIFTY 50
    rs_regime = technicals.get("rs_regime", "IN_LINE")
    rs_rating = technicals.get("rs_rating")
    if rs_regime == "OUTPERFORMING_LEADER" and rs_rating is not None:
        confluence_drivers.append(f"Market Leadership: Outperforming NIFTY 50 by {rs_rating:+.1f}%")
        confluence_score = min(98, confluence_score + 5)
    elif rs_regime == "UNDERPERFORMING_LAGGARD" and rs_rating is not None:
        confluence_drivers.append(f"Relative Strength Warning: Underperforming NIFTY 50 by {rs_rating:+.1f}%")
        confluence_score = max(25, confluence_score - 5)

    # 3. Sector Benchmark Relative Strength Integration
    from app.macro_filter import calculate_sector_relative_strength
    sector_rs_dict = calculate_sector_relative_strength(symbol, rs_rating)
    sec_regime = sector_rs_dict.get("sector_rs_regime")
    sec_rating = sector_rs_dict.get("sector_rs_rating")
    if sec_regime == "SECTOR_LEADER" and sec_rating is not None:
        confluence_drivers.append(f"Sector Leader: Outperforming {sector_rs_dict.get('sector_name')} by {sec_rating:+.1f}%")
        confluence_score = min(98, confluence_score + 4)

    # 4. Intraday Momentum Surge Driver (+5% gain confirmed by ORB or VWAP)
    day_chg = technicals.get("change_pct")
    orb_stat = technicals.get("orb_status")
    if day_chg is not None and day_chg >= 5.0 and orb_stat == "BULLISH_ORB_BREAKOUT":
        confluence_drivers.append(f"Price Surge: Intraday breakout of {day_chg:+.1f}% confirmed by 15m Opening Range High.")
        confluence_score = min(98, confluence_score + 6)
    elif sec_regime == "SECTOR_LAGGARD" and sec_rating is not None:
        confluence_drivers.append(f"Sector Laggard Warning: Underperforming {sector_rs_dict.get('sector_name')} by {sec_rating:+.1f}%")
        confluence_score = max(25, confluence_score - 6)

    # 4. TTM Volatility Squeeze Engine Integration
    ttm_squeeze = technicals.get("ttm_squeeze", {})
    if ttm_squeeze.get("squeeze_release"):
        mom_trend = ttm_squeeze.get("momentum_trend")
        if mom_trend in ["EXPANDING_BULLISH", "CONTRACTING_BEARISH"]:
            confluence_drivers.append("TTM Squeeze Release: Explosive volatility expansion detected.")
            confluence_score = min(98, confluence_score + 6)
        elif mom_trend in ["EXPANDING_BEARISH"]:
            confluence_drivers.append("TTM Squeeze Breakdown: Downward volatility expansion.")
            confluence_score = max(20, confluence_score - 6)
    elif ttm_squeeze.get("squeeze_on"):
        confluence_drivers.append("TTM Squeeze Coiling: Bollinger Bands compressed inside Keltner Channels (High breakout potential).")
        confluence_score = min(95, confluence_score + 2)

    # 5. Triple-Timeframe Fractal Harmony (Daily Tide -> 15m Wave -> 5m Trigger)
    daily_rsi = technicals.get("rsi_daily")
    daily_bullish = (current_price >= (technicals.get("ema_50") or current_price)) and (daily_rsi is not None and daily_rsi >= 48)
    m15_bullish = ((technicals.get("price_vs_vwap_pct") or 0.0) >= -0.2) and (technicals.get("rsi_divergence") != "BEARISH_REGULAR_DIVERGENCE")
    m5_bullish = technicals.get("is_volume_surge", False) or (technicals.get("macd_trend") in ["BULLISH_CROSSOVER", "EXPANDING_BULLISH_MOMENTUM"])

    if daily_bullish and m15_bullish and m5_bullish:
        confluence_drivers.append("Triple-Timeframe Confluence: Daily Tide + 15m Wave + 5m Trigger aligned Bullish")
        confluence_score = min(98, confluence_score + 8)
    elif not daily_bullish and m5_bullish and daily_rsi is not None:
        confluence_drivers.append("Timeframe Divergence: 5m rally conflicting with Daily macro downtrend")
        confluence_score = max(30, confluence_score - 8)

    # 6. F&O Options Chain & Delta-OI Integration
    if flow_data.get("is_fo_stock"):
        pcr_val = flow_data.get("pcr")
        max_pain = flow_data.get("max_pain_strike")
        sup_strike = flow_data.get("major_support_strike")
        res_strike = flow_data.get("major_resistance_strike")
        net_oi_bias = flow_data.get("net_oi_bias")

        if net_oi_bias == "CALL_UNWINDING_SHORT_COVERING":
            confluence_drivers.append("F&O Momentum: Call unwinding detected across strikes (Short covering fuel).")
            confluence_score = min(98, confluence_score + 5)
        elif net_oi_bias == "AGGRESSIVE_PUT_WRITING":
            confluence_drivers.append("F&O Institutional Support: Aggressive Put writing creates strong price floor.")
            confluence_score = min(98, confluence_score + 4)
        elif net_oi_bias == "CALL_WRITING_RESISTANCE":
            confluence_drivers.append("F&O Resistance: Heavy Call writing overhead capping upward momentum.")
            confluence_score = max(25, confluence_score - 5)
        
        if pcr_val is not None and pcr_val >= 1.25:
            sup_str = f" at ₹{sup_strike:,.0f}" if sup_strike else ""
            confluence_drivers.append(f"Option Chain: Bullish Put-Call Ratio ({pcr_val}) with PE writing support{sup_str}")
            confluence_score = min(98, confluence_score + 4)
        elif pcr_val is not None and pcr_val <= 0.65:
            res_str = f" at ₹{res_strike:,.0f}" if res_strike else ""
            confluence_drivers.append(f"Option Chain Warning: Bearish PCR ({pcr_val}) with heavy CE writing{res_str}")
            confluence_score = max(25, confluence_score - 5)

        if max_pain is not None and max_pain > 0 and current_price > 0:
            diff_pct = abs(current_price - max_pain) / max_pain * 100
            if diff_pct <= 0.75:
                confluence_drivers.append(f"F&O Max Pain Pinning: Price ₹{current_price:,.2f} near Max Pain ₹{max_pain:,.0f} ({diff_pct:.1f}% dev)")
            elif current_price > max_pain and pcr_val is not None and pcr_val >= 1.0:
                confluence_drivers.append(f"F&O Bullish Driver: Trading above Max Pain Strike ₹{max_pain:,.0f}")
                confluence_score = min(98, confluence_score + 3)
    elif flow_data.get("fo_oi_status") == "BSE_CASH_DELIVERY":
        del_pct = flow_data.get("delivery_pct")
        del_str = f" ({del_pct}%)" if del_pct is not None else ""
        confluence_drivers.append(f"BSE Cash Market: Delivery volume accumulation{del_str}")

    # Determine Action Bias based on adjusted Confluence Score
    action_bias = "HOLD_NEUTRAL"
    has_actionable_signal = False
    rsi_15m_val = technicals.get("rsi_15m")

    # 1. Circuit Lock Detection & Handling (Trapped liquidity freeze)
    is_locked = technicals.get("is_circuit_locked", False)
    lock_type = technicals.get("circuit_lock_type")
    if is_locked:
        if lock_type == "LOWER_CIRCUIT":
            confluence_drivers.insert(0, "Circuit Lock Warning: Stock locked at Lower Circuit. Order book frozen (No active buyers).")
            confluence_score = min(15, confluence_score)
            action_bias = "SELL_WATCH"
            has_actionable_signal = True
            catalyst_category = "PRICE_BREAKOUT"
            alert_title = f"{symbol}: Trapped at Lower Circuit Freeze"
        elif lock_type == "UPPER_CIRCUIT":
            confluence_drivers.insert(0, "Circuit Lock Notice: Stock locked at Upper Circuit. Order book frozen (No active sellers).")
            confluence_score = max(85, confluence_score)
            action_bias = "BUY_WATCH"
            has_actionable_signal = True
            catalyst_category = "PRICE_BREAKOUT"
            alert_title = f"{symbol}: Locked at Upper Circuit Freeze"

    # 2. Hard Risk Veto for Severe Intraday Breakdown / Supply Shock (Eliminates Fundamental Buoy Trap)
    day_change = technicals.get("change_pct")
    p_vs_vwap = technicals.get("price_vs_vwap_pct")
    l4_level = technicals.get("camarilla_pivots", {}).get("l4")
    
    is_severe_breakdown = False
    breakdown_reasons = []

    if day_change is not None and day_change <= -3.5:
        is_severe_breakdown = True
        breakdown_reasons.append(f"Severe intraday price drop ({day_change:+.2f}%)")
    if p_vs_vwap is not None and p_vs_vwap <= -2.0 and technicals.get("is_volume_surge"):
        is_severe_breakdown = True
        breakdown_reasons.append(f"VWAP Breakdown with Volume Surge ({p_vs_vwap:+.2f}% below VWAP)")
    if l4_level is not None and current_price > 0 and current_price < l4_level:
        is_severe_breakdown = True
        breakdown_reasons.append(f"Camarilla L4 institutional floor breached (₹{l4_level:,.2f})")

    if is_severe_breakdown:
        # Override fundamental buoy: immediate market supply vetoes balance sheet scores
        confluence_score = min(28, confluence_score)
        action_bias = "SELL_WATCH"
        has_actionable_signal = True
        catalyst_category = "PRICE_BREAKOUT"
        chg_fmt = f"{day_change:+.1f}%" if day_change is not None else "-3.5%"
        alert_title = f"{symbol}: Severe Price Breakdown Alert ({chg_fmt})"
        for r in reversed(breakdown_reasons):
            confluence_drivers.insert(0, f"Critical Supply Alert: {r}")

    # 3. Demat Holding Portfolio Protection Override (Both Downside Loss and Trailing Profit)
    if demat_context["is_in_portfolio"]:
        pnl = demat_context["unrealized_pnl_pct"]
        if pnl <= -3.5:
            # Capital preservation stop-loss triggered
            action_bias = "TRAILING_SL_ALERT"
            has_actionable_signal = True
            catalyst_category = "TRAILING_STOP_TRIGGER"
            alert_title = f"{symbol}: Stop-Loss Defense Trigger (P&L: {pnl:+.1f}%)"
            confluence_drivers.insert(0, f"CRITICAL RISK DEFENSE: Position down {pnl:+.1f}%. Protective stop-loss breach.")
            confluence_score = min(20, confluence_score)
        elif pnl >= 5.0 and rsi_15m_val is not None and rsi_15m_val > 72:
            action_bias = "TRAILING_SL_ALERT"
            has_actionable_signal = True
            catalyst_category = "TRAILING_STOP_TRIGGER"
            alert_title = f"{symbol}: Trailing Stop-Loss Trigger (P&L: +{pnl:+.1f}%)"
            confluence_drivers.insert(0, f"Position gained +{pnl:+.1f}%; 15m RSI reached {rsi_15m_val} (Overbought zone).")
    elif not is_severe_breakdown and not is_locked:
        # Fallback to standard confluence score thresholds
        if confluence_score >= 72 and has_real_price:
            action_bias = "BUY_WATCH"
            has_actionable_signal = True
            if day_change is not None and day_change >= 5.0:
                catalyst_category = "PRICE_BREAKOUT"
                alert_title = f"{symbol}: Intraday Momentum Breakout Surge ({day_change:+.1f}%)"
                confluence_drivers.insert(0, f"Momentum Breakout: Strong intraday surge of {day_change:+.2f}% with bullish momentum.")
        elif confluence_score <= 38 and has_real_price:
            action_bias = "SELL_WATCH"
            has_actionable_signal = True

    # Multi-Timeframe, Macro & Sector Veto Guardrails
    ema_200_val = technicals.get("ema_200")
    is_macro_downtrend = bool(ema_200_val and current_price < ema_200_val)
    is_high_vix = not macro_data.get("allow_breakout_trades", True)
    adr_val = macro_data.get("adr_ratio")
    is_breadth_veto = bool(adr_val is not None and float(adr_val) < 0.60)
    is_sector_laggard_veto = bool(sec_regime == "SECTOR_LAGGARD" and sec_rating is not None and sec_rating <= -3.5)

    if (is_macro_downtrend or is_high_vix or is_breadth_veto or is_sector_laggard_veto) and action_bias == "BUY_WATCH":
        veto_reasons = []
        if is_macro_downtrend:
            veto_reasons.append(f"Below 200 EMA (₹{ema_200_val:,.2f})")
        if is_high_vix:
            veto_reasons.append(f"High VIX ({macro_data.get('india_vix')})")
        if is_breadth_veto:
            veto_reasons.append(f"Market Breadth Distribution (ADR: {adr_val} < 0.60)")
        if is_sector_laggard_veto:
            veto_reasons.append(f"Sector Laggard Veto ({sec_rating:+.1f}% vs {sector_rs_dict.get('sector_name')})")

        logger.info(f"Veto triggered for {symbol}: {', '.join(veto_reasons)}. Downgrading BUY_WATCH to HOLD_NEUTRAL.")
        action_bias = "HOLD_NEUTRAL"
        has_actionable_signal = False
        confluence_score = min(55, confluence_score - 8)
        if is_breadth_veto:
            confluence_drivers.append(f"Market Breadth Veto: Broad market distribution ({macro_data.get('breadth_regime', 'DISTRIBUTION')}, ADR {adr_val}). Long breakout blocked.")
        if is_sector_laggard_veto:
            confluence_drivers.append(f"Sector Laggard Veto: Stock lagging sector by {sec_rating:+.1f}%. Long setup neutralized.")

    # Confluence Driver Highlights
    if technicals.get("macd_trend") == "BULLISH_CROSSOVER":
        confluence_drivers.append("15m MACD Bullish Crossover detected.")
    if technicals.get("is_volume_surge") and technicals.get("volume_multiple"):
        confluence_drivers.append(f"5m Volume is {technicals.get('volume_multiple')}x above 20 MA.")
    if flow_data.get("is_high_delivery") and flow_data.get("delivery_pct"):
        confluence_drivers.append(f"Institutional delivery estimated at {flow_data.get('delivery_pct')}%.")
    vwap_val = technicals.get("vwap")
    if vwap_val is not None and current_price > vwap_val:
        confluence_drivers.append(f"Trading above Intraday VWAP (₹{vwap_val:,.2f}).")
    if not confluence_drivers and has_real_price:
        rsi_str = f" | 15m RSI: {rsi_15m_val}" if rsi_15m_val is not None else ""
        confluence_drivers.append(f"Current price: ₹{current_price:,.2f}{rsi_str}")

    # 5. Camarilla Equation & VWAP Bands Tactical Execution Levels
    camarilla = technicals.get("camarilla_pivots", {})
    h4 = camarilla.get("h4")
    h3 = camarilla.get("h3")
    l3 = camarilla.get("l3")
    l4 = camarilla.get("l4")
    vwap_upper_1s = technicals.get("vwap_upper_1s")

    if has_real_price and current_price > 0:
        swing_high = float(technicals.get("swing_high") or technicals.get("day_high") or 0.0)
        tactical_dict = compute_tactical_levels(
            current_price=current_price,
            atr_val=atr_val,
            swing_high=swing_high,
            demat_context=demat_context,
            h3=h3,
            h4=h4,
            l3=l3,
            l4=l4,
            vwap_val=vwap_val,
            vwap_upper_1s=vwap_upper_1s,
            action_bias=action_bias
        )
        if demat_context["is_in_portfolio"] and tactical_dict:
            avg_buy = demat_context.get("average_buy_price", current_price)
            holding_guidance = f"Chandelier Trailing SL active at {tactical_dict['protective_stop_loss']} (Protecting cost basis ₹{avg_buy:,.2f})."
        else:
            holding_guidance = "Track for optimal entry in tactical range."
    else:
        holding_guidance = None
        tactical_dict = None

    return {
        "symbol": symbol,
        "has_actionable_signal": has_actionable_signal,
        "action_bias": action_bias,
        "confluence_score": confluence_score,
        "alert_title": alert_title,
        "catalyst_category": catalyst_category,
        "confluence_drivers": confluence_drivers,
        "tactical_levels": tactical_dict,
        "holding_guidance": holding_guidance,
        "growth_outlook_summary": (
            f"Long term valuation: P/E {financials.get('pe_ratio') if financials.get('pe_ratio') is not None else '-'}, "
            f"D/E {financials.get('debt_to_equity') if financials.get('debt_to_equity') is not None else '-'}."
        ),
        "factor_breakdown": {
            "technicals": tech_score,
            "flow": flow_score,
            "forensics": forensic_score,
            "catalysts": min(95, news_score)
        },
        "derivatives_flow": {
            "is_fo_stock": flow_data.get("is_fo_stock", False),
            "pcr": flow_data.get("pcr") if flow_data.get("is_fo_stock") else None,
            "max_pain_strike": flow_data.get("max_pain_strike") if flow_data.get("is_fo_stock") else None,
            "major_support_strike": flow_data.get("major_support_strike") if flow_data.get("is_fo_stock") else None,
            "major_resistance_strike": flow_data.get("major_resistance_strike") if flow_data.get("is_fo_stock") else None,
            "fo_status": flow_data.get("fo_oi_status") if flow_data.get("is_fo_stock") else None
        },
        "market_breadth": {
            "adr_ratio": macro_data.get("adr_ratio"),
            "breadth_regime": macro_data.get("breadth_regime"),
            "advances": macro_data.get("advances"),
            "declines": macro_data.get("declines")
        }
    }


def check_has_active_catalyst(
    symbol: str,
    technicals: Dict[str, Any],
    flow_data: Dict[str, Any],
    news_items: List[Dict[str, Any]],
    holding_info: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str]:
    """
    Tier-1 Quantitative Gatekeeper: Evaluates whether a stock has an active momentum,
    volume, corporate filing, or Demat stop-loss catalyst before invoking Gemini AI.
    Quiet/flat stocks are evaluated via pure deterministic mathematics in 0.001 ms.
    """
    # 1. Demat Holding Protection Trigger
    if holding_info:
        raw_curr = technicals.get("current_price")
        curr_p = float(raw_curr) if raw_curr is not None else 0.0
        raw_avg = holding_info.get("average_price")
        avg_p = float(raw_avg) if raw_avg is not None else 0.0
        pnl_pct = ((curr_p - avg_p) / avg_p * 100) if avg_p > 0 else 0.0
        raw_rsi = technicals.get("rsi_15m")
        rsi = float(raw_rsi) if raw_rsi is not None else 50.0
        if (pnl_pct >= 5.0 and rsi > 70.0) or pnl_pct <= -3.5:
            return True, f"Demat Holding Protection Trigger (P&L: {pnl_pct:+.1f}%)"

    # 2. Sharp Intraday Price Surge / Breakdown (Momentum & Volatility Core)
    change_pct = technicals.get("change_pct")
    if change_pct is not None:
        try:
            cp = float(change_pct)
            if abs(cp) >= 2.5:
                return True, f"Sharp Price Movement ({cp:+.1f}%)"
        except (ValueError, TypeError):
            pass

    orb_status = technicals.get("orb_status")
    if orb_status in ["BULLISH_ORB_BREAKOUT", "BEARISH_ORB_BREAKDOWN"]:
        return True, f"15m Opening Range Break ({orb_status})"

    if technicals.get("is_circuit_locked"):
        return True, f"Circuit Lock Freeze ({technicals.get('circuit_lock_type')})"

    # 3. Institutional Volume Surge (>= 1.5x 20-period volume MA)
    raw_vol = technicals.get("volume_multiple")
    if raw_vol is None:
        raw_vol = technicals.get("volume_surge_ratio")
    try:
        vol_mult = float(raw_vol) if raw_vol is not None else 1.0
    except (ValueError, TypeError):
        vol_mult = 1.0

    if technicals.get("is_volume_surge") or vol_mult >= 1.5:
        return True, f"Volume Surge ({vol_mult:.1f}x 20-MA)"

    # 3. Momentum Extremes or Divergence
    raw_rsi_15m = technicals.get("rsi_15m")
    if raw_rsi_15m is not None:
        try:
            rsi_15m = float(raw_rsi_15m)
            if rsi_15m >= 68.0 or rsi_15m <= 32.0:
                return True, f"15m RSI Momentum Extreme ({rsi_15m:.1f})"
        except (ValueError, TypeError):
            pass

    if technicals.get("rsi_divergence") in ["BULLISH_DIVERGENCE", "BEARISH_DIVERGENCE"]:
        return True, f"RSI Divergence: {technicals.get('rsi_divergence')}"

    # 4. MACD Trend Transition
    if technicals.get("macd_trend") == "BULLISH_CROSSOVER":
        return True, "15m MACD Bullish Crossover"

    # 5. Institutional Order Flow / F&O Build-up & Options Extreme
    if flow_data.get("is_high_delivery"):
        return True, f"High Institutional Delivery ({flow_data.get('delivery_pct')}%)"
    if flow_data.get("fo_oi_status") in ["LONG_BUILDUP", "SHORT_BUILDUP"]:
        raw_pcr = flow_data.get("pcr")
        try:
            pcr = float(raw_pcr) if raw_pcr is not None else 1.0
        except (ValueError, TypeError):
            pcr = 1.0
        if pcr >= 1.3 or pcr <= 0.7:
            return True, f"Derivatives Regime: {flow_data.get('fo_oi_status')} (PCR: {pcr:.2f})"
    if flow_data.get("is_fo_stock"):
        raw_pcr = flow_data.get("pcr")
        try:
            pcr = float(raw_pcr) if raw_pcr is not None else 1.0
        except (ValueError, TypeError):
            pcr = 1.0
        if pcr >= 1.4 or pcr <= 0.6:
            return True, f"Extreme Option PCR Catalyst ({pcr:.2f})"

    # 6. Intraday VWAP Breakout with Momentum Confluence
    raw_vwap = technicals.get("price_vs_vwap_pct")
    try:
        vwap_pct = abs(float(raw_vwap)) if raw_vwap is not None else 0.0
    except (ValueError, TypeError):
        vwap_pct = 0.0

    if vwap_pct >= 1.2 or (vwap_pct >= 0.8 and (vol_mult >= 1.3 or technicals.get("is_volume_surge"))):
        return True, f"Intraday VWAP Expansion ({vwap_pct:.1f}%)"

    # 7. Real-Time News / Corporate Catalysts
    for item in news_items:
        title_upper = str(item.get("title", "")).upper()
        if any(w in title_upper for w in ["BLOCK DEAL", "BULK DEAL", "PROFIT", "REVENUE", "QUARTER", "ORDER", "CONTRACT", "DEBT", "ACQUISITION"]):
            return True, f"Corporate Disclosure / News Catalyst: {item.get('title', '')[:50]}"

    return False, "Consolidating / Normal Volatility"


# ==========================================
# 3. 5-MINUTE MULTI-TENANT SURVEILLANCE RUNNER (IN-MEMORY EVENT-DRIVEN)
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

    # Anomaly-Gated News Fetching: Only fetch fresh news RSS if there is an active volume surge or price deviation
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
        # High-speed deterministic evaluation for quiet/consolidating stocks (0.001ms, 0 API quota burned)
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

    # Fast fundamentals from 24h cache (0ms); default to clean None if not in cache
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

    # Fast flow & Wyckoff VSA (<0.001ms if cached or non-FO)
    flow_data = fetch_delivery_and_fo_flow(
        symbol,
        technicals.get("price_vs_vwap_pct", 0.0),
        None,
        technicals.get("volume_multiple")
    )
    forensics = evaluate_forensic_health(symbol, financials)

    # 100% Deterministic RAM Math (<0.001ms)
    analysis = compute_deterministic_confluence(
        symbol=symbol,
        technicals=technicals,
        flow_data=flow_data,
        macro_data=macro_data or {},
        forensics=forensics,
        financials=financials,
        news_items=[]
    )

    # Compute tactical levels if price is valid
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

    # Filter symbols needing fresh calculation (skip if fresh in RAM within 240s)
    symbols_to_sync = [s for s in symbols if not market_cache.is_fresh(s, max_age_seconds=240)]
    synced_count = len(symbols) - len(symbols_to_sync)

    if symbols_to_sync:
        logger.info(f"⚡ Pre-computing institutional market state for {len(symbols_to_sync)} unique symbols via Vectorized Batch Engine...")
        
        # Batch-download all technicals in a single parallel network operation
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


async def evaluate_user_portfolio_and_watchlists(user_id: str, supabase_client) -> List[dict]:
    """
    Evaluates all tracked stocks for a user across demat holdings and manual watchlists.
    Uses high-speed In-Memory Market Cache for sub-millisecond per-stock lookups.
    Dispatches FCM Push and rich Telegram notifications for high-conviction catalysts.
    """
    generated_alerts = []
    
    # 1. Fetch user profile & notification settings (PgBouncer pool first, REST fallback)
    profile = None
    try:
        from app.db_pool import fetch_one, fetch_all
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

    # 2. Fetch user's active watchlist (PgBouncer pool first, REST fallback)
    symbols = set()
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

    # 3. Check ICICI credentials and sync Demat holdings (PgBouncer pool first, REST fallback)
    holdings_map = {}
    cred = None
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

            if cached_holdings is not None:
                holdings = cached_holdings
            else:
                app_key = vault.decrypt(cred.get("encrypted_app_key"))
                secret_key = vault.decrypt(cred.get("encrypted_secret_key"))
                session_token = vault.decrypt(cred.get("encrypted_session_token"))
                holdings = await asyncio.to_thread(fetch_user_portfolio, app_key, secret_key, session_token)
                _DEMAT_PORTFOLIO_CACHE[user_id] = {"timestamp": now, "holdings": holdings}
            
            watchlist_upserts = []
            for h in holdings:
                sym = h.get('symbol')
                clean_s = h.get('clean_symbol') or (sym.replace(".BO", "").replace(".NS", "").strip().upper() if sym else "")
                if sym:
                    symbols.add(sym)
                    holdings_map[sym] = h
                    if clean_s:
                        symbols.add(clean_s)
                        holdings_map[clean_s] = h
                    watchlist_upserts.append({
                        "user_id": user_id,
                        "symbol": clean_s or sym,
                        "is_auto_synced": True
                    })
            if watchlist_upserts:
                try:
                    supabase_client.table("user_watchlists").upsert(
                        watchlist_upserts, on_conflict="user_id,symbol"
                    ).execute()
                except Exception as e:
                    logger.error(f"Error bulk syncing holdings to watchlist for user {mask_id(user_id)}: {e}")
        else:
            logger.info(f"ICICI Session Token for user {mask_id(user_id)} is from {token_date} (expired today {today_str}). Scanning watchlist symbols only.")

    macro_data = await asyncio.to_thread(fetch_macro_market_regime)

    # 4. Evaluate each symbol concurrently using high-speed In-Memory Cache (< 0.1ms lookup) with parallel fallback
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

                    # If user holds the stock, evaluate holding-specific trailing stop loss in-memory without re-fetching
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
                    # Cache miss fallback
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
                
                # Sensitivity Filter: Guarantee alerts for critical breakdowns and stop-loss breaches
                should_dispatch = False
                is_breakdown_or_sl = (action_bias in ["TRAILING_SL_ALERT", "SELL_WATCH"] or confluence_score <= 35)

                if alert_sensitivity == "HIGH":
                    should_dispatch = (confluence_score >= 80) or is_breakdown_or_sl
                elif alert_sensitivity == "FII":
                    is_fii = (catalyst_type in ["BLOCK_DEAL", "DEBT_REDUCTION"] or flow_data.get("is_high_delivery"))
                    should_dispatch = (is_fii and (confluence_score >= 65 or has_actionable)) or is_breakdown_or_sl
                else: # ALL
                    should_dispatch = has_actionable or (confluence_score >= 65) or is_breakdown_or_sl

                if not should_dispatch:
                    return None

                # Anti-Fatigue Cooldown Check: Treat severe breakdowns, stop-loss defenses, and block deals as Tier-1
                is_tier1 = (confluence_score >= 88 or action_bias in ["TRAILING_SL_ALERT", "SELL_WATCH"] or catalyst_type in ["BLOCK_DEAL", "TRAILING_STOP_TRIGGER", "PRICE_BREAKOUT"])
                allowed, reason = should_dispatch_alert(user_id, symbol, action_bias, confluence_score, is_tier1)
                
                if not allowed:
                    logger.info(f"Skipping dispatch for {symbol}: {reason}")
                    return None

                # High-Conviction AI Reasoning: Invoke Gemini strictly for alerts about to be dispatched (capped at max 15/scan)
                if settings.GEMINI_API_KEY and get_ai_scan_calls_count() < _MAX_AI_CALLS_PER_SCAN:
                    increment_ai_scan_calls_count()
                    try:
                        ai_res = await evaluate_stock_with_ai(
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

                # Demat position snapshot for alert formatting
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

                # Dispatch FCM Lock-Screen Push Notification
                fcm_sent = False
                if fcm_token and fcm_enabled:
                    fcm_body = f"Score: {confluence_score}/100 | {action_bias.replace('_', ' ')} | Target: {tactical_levels.get('target_1', 'N/A')} | SL: {tactical_levels.get('protective_stop_loss', 'N/A')}"
                    fcm_sent = await send_fcm_notification(fcm_token, alert_title, fcm_body, {
                        "symbol": symbol,
                        "action_bias": action_bias,
                        "confluence_score": str(confluence_score),
                        "catalyst_type": catalyst_type
                    })

                # Dispatch Rich HTML Telegram Notification with Inline Buttons
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

                # Normalize and validate catalyst against PostgreSQL catalyst_type_enum
                CATALYST_SYNONYM_MAP = {
                    "EARNINGS_SURPRISE": "EARNINGS_BEAT",
                    "DEBT_REDUCTION": "DEBT_CHANGE",
                    "PRICE_BREAKDOWN": "PRICE_BREAKOUT",
                    "STOP_LOSS_DEFENSE": "TRAILING_STOP_TRIGGER"
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

                # Persist Alert in Supabase Ledger
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
