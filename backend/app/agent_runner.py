import asyncio
import json
import logging
import urllib.parse
import concurrent.futures
import feedparser
from datetime import date, datetime
import yfinance as yf
from typing import List, Dict, Any, Optional, Tuple

from app.config import settings
from app.vault import vault
from app.technical_engine import fetch_multi_timeframe_technicals
from app.flow_tracker import fetch_delivery_and_fo_flow, fetch_bulk_and_block_deals
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
                cmp = float(item.get('current_market_price') or item.get('last_price') or avg_p)
            except (ValueError, TypeError):
                cmp = avg_p

            if clean_symbol and qty > 0:
                return {
                    "symbol": clean_symbol,
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

def fetch_stock_financials(symbol: str) -> Dict[str, Any]:
    """
    Fetches comprehensive financial metrics, valuation data, debt ratios, quarterly growth,
    and 52-week position from Yahoo Finance with automatic Dual-Exchange (NSE / BSE) resolution.
    """
    clean_sym = str(symbol).strip().upper()
    if not clean_sym or clean_sym in ["NA", "NONE", "NULL", "0"]:
        return {"symbol": clean_sym, "price": 0.0}

    # Determine candidates to check (NSE first, then BSE)
    if clean_sym.endswith(".NS") or clean_sym.endswith(".BO"):
        candidates = [clean_sym]
    else:
        candidates = [f"{clean_sym}.NS", f"{clean_sym}.BO"]

    info = {}
    current_price = 0.0

    for ticker_name in candidates:
        try:
            ticker = yf.Ticker(ticker_name)
            ticker_info = ticker.info or {}
            price = ticker_info.get('currentPrice') or ticker_info.get('regularMarketPrice') or ticker_info.get('previousClose') or 0.0
            if price > 0:
                info = ticker_info
                current_price = price
                break
        except Exception:
            continue

    if not info and current_price == 0.0:
        return {"symbol": clean_sym, "price": 0.0}

    try:
        pe_ratio = info.get('trailingPE')
        forward_pe = info.get('forwardPE')
        debt_to_equity = info.get('debtToEquity')
        revenue_growth = info.get('revenueGrowth')
        earnings_growth = info.get('earningsQuarterlyGrowth')
        profit_margins = info.get('profitMargins')
        return_on_equity = info.get('returnOnEquity')
        
        return {
            "symbol": clean_sym,
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
    except Exception as e:
        logger.warning(f"Error parsing financial metrics for {clean_sym}: {e}")
        return {"symbol": clean_sym, "price": current_price}


def fetch_stock_news(symbol: str) -> List[Dict[str, str]]:
    """
    Parses real-time Google News RSS feeds targeting block/bulk deals, orders,
    quarterly results, revenue, debt changes, and promoter activity in the last 24 hours.
    """
    query_str = f'"{symbol}" AND (block deal OR bulk deal OR quarterly results OR Q1 OR Q2 OR Q3 OR Q4 OR revenue OR profit OR order OR debt OR expansion)'
    encoded_symbol = urllib.parse.quote(query_str)
    rss_url = f"https://news.google.com/rss/search?q={encoded_symbol}&hl=en-IN&gl=IN&ceid=IN:en"
    
    headlines = []
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:6]:
            headlines.append({
                "title": entry.title,
                "link": entry.link,
                "published": entry.published,
            })
    except Exception as e:
        logger.error(f"Error fetching real-time news RSS for {symbol}: {e}")
        
    return headlines


# ==========================================
# 2. SENIOR TRADING ANALYST AI ENGINE
# ==========================================

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
    current_price = technicals.get("current_price") or financials.get("price") or 100.0
    atr_val = technicals.get("atr_14") or (current_price * 0.015)
    
    # Calculate Demat P&L
    demat_context = {"is_in_portfolio": False, "quantity": 0, "average_buy_price": 0.0, "unrealized_pnl_pct": 0.0}
    if holding_info and holding_info.get("quantity", 0) > 0:
        qty = holding_info.get("quantity", 0)
        avg_price = holding_info.get("average_price", 0.0)
        pnl_pct = round(((current_price - avg_price) / avg_price) * 100, 2) if avg_price > 0 else 0.0
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
============================================================
• Wyckoff VSA Regime: {flow_data.get('vsa_regime')} ({flow_data.get('vsa_note', '')})
• Estimated Delivery Volume: {flow_data.get('delivery_pct')}% (Accumulation: {flow_data.get('is_high_delivery')})
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
        try:
            from google import genai
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            for model_name in ['gemini-3.6-flash', 'gemini-2.5-flash']:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config={"response_mime_type": "application/json"}
                    )
                    parsed = json.loads(response.text)
                    if "factor_breakdown" not in parsed:
                        parsed["factor_breakdown"] = {
                            "technicals": technicals.get("technical_score", 65),
                            "flow": flow_data.get("flow_score", 60),
                            "forensics": forensics.get("forensic_score", 70),
                            "catalysts": min(95, max(40, parsed.get("confluence_score", 75)))
                        }
                    logger.info(f"Successfully evaluated {symbol} using Google GenAI SDK '{model_name}'.")
                    return parsed
                except Exception as model_err:
                    logger.warning(f"GenAI SDK '{model_name}' attempt failed for {symbol}: {model_err}")
                    continue
        except ImportError:
            # Temporary fallback only if google.genai is not yet installed in runtime
            try:
                import google.generativeai as legacy_genai
                legacy_genai.configure(api_key=settings.GEMINI_API_KEY)
                model = legacy_genai.GenerativeModel('gemini-3.6-flash')
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                parsed = json.loads(response.text)
                if "factor_breakdown" not in parsed:
                    parsed["factor_breakdown"] = {
                        "technicals": technicals.get("technical_score", 65),
                        "flow": flow_data.get("flow_score", 60),
                        "forensics": forensics.get("forensic_score", 70),
                        "catalysts": min(95, max(40, parsed.get("confluence_score", 75)))
                    }
                return parsed
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
    Deterministic Quantitative Confluence Engine (Master Prompt Section 3 Formula).
    Evaluates institutional math in 0.001ms with zero API costs:
    Confluence Score = (0.30 * Tech) + (0.25 * Flow) + (0.25 * Forensic) + (0.20 * News)
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

    tech_score = technicals.get("technical_score", 50)
    flow_score = flow_data.get("flow_score", 50)
    forensic_score = forensics.get("forensic_score", 60)
    
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
        confluence_drivers.append(f"Wyckoff VSA: Institutional Delivery Absorption ({flow_data.get('delivery_pct')}%)")
        flow_score = min(95, flow_score + 8)
    elif vsa_regime == "OPERATOR_CHURN_TRAP":
        confluence_drivers.append("Wyckoff VSA Warning: Speculative Operator Churn (Low Delivery %)")
        flow_score = max(20, flow_score - 10)

    # Sector Breadth Integration
    sector_name = forensics.get("sector_name", "BROAD_MARKET")
    if sector_name != "BROAD_MARKET":
        confluence_drivers.append(f"Sector Alignment: {sector_name}")

    # Calculate 4-Pillar Confluence Score (Master Prompt 3.1)
    confluence_score = int(round(
        (tech_score * 0.30) +
        (flow_score * 0.25) +
        (forensic_score * 0.25) +
        (min(95, news_score) * 0.20)
    ))

    # 1. ADX Trend Strength Check (Choppy Sideways Veto / Chop Penalty)
    adx_regime = technicals.get("adx_regime", "MODERATE_TREND")
    adx_val = technicals.get("adx_14", 20.0)
    if adx_regime == "CHOPPY_SIDEWAYS":
        confluence_drivers.append(f"ADX Warning: Low trend strength ({adx_val} < 20). Sideways consolidation risk.")
        confluence_score = max(25, confluence_score - 8)
    elif adx_regime == "STRONG_TREND":
        confluence_drivers.append(f"ADX Confirmation: Strong Institutional Trend ({adx_val} >= 25)")

    # 2. Mansfield Relative Strength vs NIFTY 50
    rs_regime = technicals.get("rs_regime", "IN_LINE")
    rs_rating = technicals.get("rs_rating", 0.0)
    if rs_regime == "OUTPERFORMING_LEADER":
        confluence_drivers.append(f"Market Leadership: Outperforming NIFTY 50 by {rs_rating:+.1f}%")
        confluence_score = min(98, confluence_score + 5)
    elif rs_regime == "UNDERPERFORMING_LAGGARD":
        confluence_drivers.append(f"Relative Strength Warning: Underperforming NIFTY 50 by {rs_rating:+.1f}%")
        confluence_score = max(25, confluence_score - 5)

    # 3. Triple-Timeframe Fractal Harmony (Daily Tide -> 15m Wave -> 5m Trigger)
    daily_bullish = (current_price >= technicals.get("ema_50", current_price)) and (technicals.get("rsi_daily", 50) >= 48)
    m15_bullish = (technicals.get("price_vs_vwap_pct", 0) >= -0.2) and (technicals.get("rsi_divergence") != "BEARISH_REGULAR_DIVERGENCE")
    m5_bullish = technicals.get("is_volume_surge", False) or (technicals.get("macd_trend") in ["BULLISH_CROSSOVER", "EXPANDING_BULLISH_MOMENTUM"])

    if daily_bullish and m15_bullish and m5_bullish:
        confluence_drivers.append("Triple-Timeframe Confluence: Daily Tide + 15m Wave + 5m Trigger aligned Bullish")
        confluence_score = min(98, confluence_score + 8)
    elif not daily_bullish and m5_bullish:
        confluence_drivers.append("Timeframe Divergence: 5m rally conflicting with Daily macro downtrend")
        confluence_score = max(30, confluence_score - 8)

    # 4. F&O Options Chain & Max Pain Integration (₹0 Official Feed)
    if flow_data.get("is_fo_stock"):
        pcr_val = float(flow_data.get("pcr", 1.0) or 1.0)
        max_pain = float(flow_data.get("max_pain_strike", 0.0) or 0.0)
        sup_strike = float(flow_data.get("major_support_strike", 0.0) or 0.0)
        res_strike = float(flow_data.get("major_resistance_strike", 0.0) or 0.0)
        
        if pcr_val >= 1.25:
            confluence_drivers.append(f"Option Chain: Bullish Put-Call Ratio ({pcr_val}) with PE writing support at ₹{sup_strike:,.0f}")
            confluence_score = min(98, confluence_score + 4)
        elif pcr_val <= 0.65:
            confluence_drivers.append(f"Option Chain Warning: Bearish PCR ({pcr_val}) with heavy CE writing at ₹{res_strike:,.0f}")
            confluence_score = max(25, confluence_score - 5)

        if max_pain > 0:
            diff_pct = abs(current_price - max_pain) / max_pain * 100
            if diff_pct <= 0.75:
                confluence_drivers.append(f"F&O Max Pain Pinning: Price ₹{current_price:,.2f} near Max Pain ₹{max_pain:,.0f} ({diff_pct:.1f}% dev)")
            elif current_price > max_pain and pcr_val >= 1.0:
                confluence_drivers.append(f"F&O Bullish Driver: Trading above Max Pain Strike ₹{max_pain:,.0f} (Support ₹{sup_strike:,.0f})")
                confluence_score = min(98, confluence_score + 3)
    elif flow_data.get("fo_oi_status") == "BSE_CASH_DELIVERY":
        confluence_drivers.append(f"BSE Cash Market: Delivery volume accumulation ({flow_data.get('delivery_pct')}%)")

    # Determine Action Bias based on adjusted Confluence Score
    action_bias = "HOLD_NEUTRAL"
    has_actionable_signal = False
    
    # Check Trailing Stop-Loss for User Holding
    if demat_context["is_in_portfolio"] and demat_context["unrealized_pnl_pct"] >= 5.0 and technicals.get("rsi_15m", 50) > 72:
        action_bias = "TRAILING_SL_ALERT"
        has_actionable_signal = True
        catalyst_category = "TRAILING_STOP_TRIGGER"
        alert_title = f"{symbol}: Trailing Stop-Loss Trigger (P&L: +{demat_context['unrealized_pnl_pct']}%)"
        confluence_drivers.insert(0, f"Position gained {demat_context['unrealized_pnl_pct']}%; 15m RSI reached {technicals.get('rsi_15m')} (Overbought zone).")
    elif confluence_score >= 72:
        action_bias = "BUY_WATCH"
        has_actionable_signal = True
    elif confluence_score <= 38:
        action_bias = "SELL_WATCH"
        has_actionable_signal = True

    # Multi-Timeframe & Macro Veto Guardrails (Master Prompt Core Principle #2)
    ema_200_val = technicals.get("ema_200", current_price)
    is_macro_downtrend = (technicals.get("ma_trend") == "BELOW_200_EMA") or (current_price < ema_200_val)
    is_high_vix = not macro_data.get("allow_breakout_trades", True)
    adr_val = float(macro_data.get("adr_ratio", 1.0) or 1.0)
    is_breadth_veto = (adr_val < 0.60)

    if (is_macro_downtrend or is_high_vix or is_breadth_veto) and action_bias == "BUY_WATCH":
        veto_reasons = []
        if is_macro_downtrend:
            veto_reasons.append(f"Below 200 EMA (₹{ema_200_val:,.2f})")
        if is_high_vix:
            veto_reasons.append(f"High VIX ({macro_data.get('india_vix')})")
        if is_breadth_veto:
            veto_reasons.append(f"Market Breadth Distribution (ADR: {adr_val} < 0.60)")
        logger.info(f"Macro / Breadth Veto triggered for {symbol}: {', '.join(veto_reasons)}. Downgrading BUY_WATCH to HOLD_NEUTRAL.")
        action_bias = "HOLD_NEUTRAL"
        has_actionable_signal = False
        confluence_score = min(55, confluence_score - 8)
        if is_breadth_veto:
            confluence_drivers.append(f"Market Breadth Veto: Broad market distribution ({macro_data.get('breadth_regime', 'DISTRIBUTION')}, ADR {adr_val}). Long breakout blocked.")

    # Confluence Driver Highlights
    if technicals.get("macd_trend") == "BULLISH_CROSSOVER":
        confluence_drivers.append(f"15m MACD Bullish Crossover detected (Hist: {technicals.get('macd_histogram')}).")
    if technicals.get("is_volume_surge"):
        confluence_drivers.append(f"5m Volume is {technicals.get('volume_multiple')}x above 20 MA.")
    if flow_data.get("is_high_delivery"):
        confluence_drivers.append(f"Institutional delivery estimated at {flow_data.get('delivery_pct')}%.")
    if technicals.get("price_vs_vwap_pct", 0) > 0:
        confluence_drivers.append(f"Trading above Intraday VWAP (₹{technicals.get('vwap')}).")
    if not confluence_drivers:
        confluence_drivers.append(f"Current price: ₹{current_price} | 15m RSI: {technicals.get('rsi_15m')}")

    # 5. Camarilla Equation Institutional Pivots & Tactical Volatility Envelopes
    camarilla = technicals.get("camarilla_pivots", {})
    h4 = camarilla.get("h4", 0.0)
    h3 = camarilla.get("h3", 0.0)
    l3 = camarilla.get("l3", 0.0)
    l4 = camarilla.get("l4", 0.0)

    if has_real_price:
        if h3 > 0 and l3 > 0:
            entry_min = round(min(current_price * 0.995, l3), 2)
            entry_max = round(max(current_price * 1.005, current_price), 2)
            target_1 = round(max(current_price + (1.5 * atr_val), h3), 2)
            target_2 = round(max(current_price + (2.5 * atr_val), h4), 2)
            stop_loss = round(min(current_price - (1.0 * atr_val), l4), 2)
        else:
            entry_min = round(current_price * 0.995, 2)
            entry_max = round(current_price * 1.005, 2)
            stop_loss = round(current_price - (1.0 * atr_val), 2)
            target_1 = round(current_price + (1.5 * atr_val), 2)
            target_2 = round(current_price + (2.5 * atr_val), 2)

        # Sanity guardrails: Target must always be above current_price, Stop-loss below current_price
        target_1 = max(target_1, round(current_price * 1.02, 2))
        target_2 = max(target_2, round(current_price * 1.05, 2))
        stop_loss = min(stop_loss, round(current_price * 0.98, 2))

        # 6. Dynamic Chandelier Trailing Stop-Loss for Demat Holdings
        holding_guidance = "Track for optimal entry in tactical range."
        if demat_context["is_in_portfolio"]:
            avg_buy = demat_context.get("average_buy_price", current_price)
            chandelier_sl = round(current_price - (2.5 * atr_val), 2)
            base_cost_sl = round(avg_buy * 0.96, 2)
            stop_loss = max(stop_loss, base_cost_sl, chandelier_sl)
            holding_guidance = f"Chandelier Trailing SL active at ₹{stop_loss:,.2f} (Protecting cost basis ₹{avg_buy:,.2f})."

        risk_val = max(1.0, current_price - stop_loss)
        reward_val = max(2.5, target_2 - current_price)
        rr_ratio = round(reward_val / risk_val, 1)

        tactical_dict = {
            "entry_range": f"₹{entry_min:,.2f} - ₹{entry_max:,.2f}",
            "target_1": f"₹{target_1:,.2f}",
            "target_2": f"₹{target_2:,.2f}",
            "protective_stop_loss": f"₹{stop_loss:,.2f}",
            "risk_reward_ratio": f"1:{rr_ratio}"
        }
    else:
        holding_guidance = "Awaiting market open for live execution pricing."
        tactical_dict = {
            "entry_range": "-",
            "target_1": "-",
            "target_2": "-",
            "protective_stop_loss": "-",
            "risk_reward_ratio": "-"
        }

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
        "growth_outlook_summary": f"Long term valuation: P/E {financials.get('pe_ratio', 'N/A')}, D/E {financials.get('debt_to_equity', 'N/A')}.",
        "factor_breakdown": {
            "technicals": tech_score,
            "flow": flow_score,
            "forensics": forensic_score,
            "catalysts": min(95, news_score)
        },
        "derivatives_flow": {
            "is_fo_stock": flow_data.get("is_fo_stock", False),
            "pcr": flow_data.get("pcr", 1.0),
            "max_pain_strike": flow_data.get("max_pain_strike", 0.0),
            "major_support_strike": flow_data.get("major_support_strike", 0.0),
            "major_resistance_strike": flow_data.get("major_resistance_strike", 0.0),
            "fo_status": flow_data.get("fo_oi_status", "NEUTRAL")
        },
        "market_breadth": {
            "adr_ratio": macro_data.get("adr_ratio", 1.0),
            "breadth_regime": macro_data.get("breadth_regime", "BALANCED_BREADTH"),
            "advances": macro_data.get("advances", 25),
            "declines": macro_data.get("declines", 25)
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
        curr_p = technicals.get("current_price", 0.0)
        avg_p = holding_info.get("average_price", 0.0)
        pnl_pct = ((curr_p - avg_p) / avg_p * 100) if avg_p > 0 else 0.0
        rsi = technicals.get("rsi_15m", 50)
        if (pnl_pct >= 5.0 and rsi > 70) or pnl_pct <= -4.0:
            return True, f"Demat Holding Protection Trigger (P&L: {pnl_pct:+.1f}%)"

    # 2. Institutional Volume Surge (>= 1.5x 20-period volume MA)
    vol_mult = technicals.get("volume_multiple") or technicals.get("volume_surge_ratio", 1.0)
    if technicals.get("is_volume_surge") or vol_mult >= 1.5:
        return True, f"Volume Surge ({vol_mult}x 20-MA)"

    # 3. Momentum Extremes or Divergence
    rsi_15m = technicals.get("rsi_15m", 50)
    if rsi_15m >= 68 or rsi_15m <= 32:
        return True, f"15m RSI Momentum Extreme ({rsi_15m})"
    if technicals.get("rsi_divergence") in ["BULLISH_DIVERGENCE", "BEARISH_DIVERGENCE"]:
        return True, f"RSI Divergence: {technicals.get('rsi_divergence')}"

    # 4. MACD Trend Transition
    if technicals.get("macd_trend") == "BULLISH_CROSSOVER":
        return True, "15m MACD Bullish Crossover"

    # 5. Institutional Order Flow / F&O Build-up & Options Extreme
    if flow_data.get("is_high_delivery"):
        return True, f"High Institutional Delivery ({flow_data.get('delivery_pct')}%)"
    if flow_data.get("fo_oi_status") in ["LONG_BUILDUP", "SHORT_BUILDUP"]:
        return True, f"Derivatives Regime: {flow_data.get('fo_oi_status')} (PCR: {flow_data.get('pcr')})"
    if flow_data.get("is_fo_stock"):
        pcr = float(flow_data.get("pcr", 1.0) or 1.0)
        if pcr >= 1.4 or pcr <= 0.6:
            return True, f"Extreme Option PCR Catalyst ({pcr})"

    # 6. Intraday VWAP Breakout
    vwap_pct = abs(technicals.get("price_vs_vwap_pct", 0.0))
    if vwap_pct >= 0.8:
        return True, f"Intraday VWAP Deviation ({vwap_pct:.1f}%)"

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
    holding_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates all institutional dimensions (technicals, macro, F&O flow, forensics, news, AI confluence)
    for a single symbol and caches the analysis into RAM.
    Uses Tier-1 Gatekeeper filtering to call Gemini AI only for active catalyst stocks (preserving free tier quota).
    """
    if macro_data is None:
        macro_data = await asyncio.to_thread(fetch_macro_market_regime)

    # Fetch technicals, financials, and news concurrently across thread pool workers
    technicals, financials, news_items = await asyncio.gather(
        asyncio.to_thread(fetch_multi_timeframe_technicals, symbol),
        asyncio.to_thread(fetch_stock_financials, symbol),
        asyncio.to_thread(fetch_stock_news, symbol)
    )

    flow_data = await asyncio.to_thread(
        fetch_delivery_and_fo_flow, 
        symbol, 
        technicals.get("price_vs_vwap_pct", 0.0)
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

    pack = {
        "symbol": symbol,
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

    market_cache.set_stock(symbol, pack, ttl_seconds=300)
    return pack


async def sync_market_cache_for_all_active_symbols(supabase_client) -> int:
    """
    Pre-computes and caches market state in RAM for all unique symbols across all user watchlists.
    Uses bounded async concurrency (Semaphore=15) with thread-pool I/O to evaluate all stocks rapidly.
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

    logger.info(f"⚡ Pre-computing institutional market state for {len(symbols)} unique symbols into RAM cache (Concurrency: 15)...")
    
    sem = asyncio.Semaphore(15)
    synced_count = 0

    async def _worker(sym: str):
        nonlocal synced_count
        async with sem:
            try:
                if market_cache.is_fresh(sym, max_age_seconds=240):
                    synced_count += 1
                    return
                await evaluate_single_symbol_full(sym, macro_data=macro_data)
                synced_count += 1
            except Exception as e:
                logger.error(f"Error pre-computing market cache for {sym}: {e}")

    await asyncio.gather(*(_worker(s) for s in symbols))
    logger.info(f"✅ Market Cache Sync Complete: {synced_count}/{len(symbols)} unique symbols cached in RAM.")
    return synced_count


async def evaluate_user_portfolio_and_watchlists(user_id: str, supabase_client) -> List[dict]:
    """
    Evaluates all tracked stocks for a user across demat holdings and manual watchlists.
    Uses high-speed In-Memory Market Cache for sub-millisecond per-stock lookups.
    Dispatches FCM Push and rich Telegram notifications for high-conviction catalysts.
    """
    generated_alerts = []
    
    # 1. Fetch user profile & notification settings
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
    watchlist_res = supabase_client.table("user_watchlists").select("symbol").eq("user_id", user_id).execute()
    symbols = set(item['symbol'] for item in (watchlist_res.data or []))
    
    # 3. Check ICICI credentials and sync Demat holdings
    holdings_map = {}
    cred_res = supabase_client.table("user_credentials").select("*").eq("user_id", user_id).execute()
    if cred_res.data:
        cred = cred_res.data[0]
        today_str = str(date.today())
        token_date = str(cred.get("token_date", ""))

        if token_date == today_str:
            app_key = vault.decrypt(cred.get("encrypted_app_key"))
            secret_key = vault.decrypt(cred.get("encrypted_secret_key"))
            session_token = vault.decrypt(cred.get("encrypted_session_token"))
            
            holdings = fetch_user_portfolio(app_key, secret_key, session_token)
            watchlist_upserts = []
            for h in holdings:
                sym = h.get('symbol')
                if sym:
                    symbols.add(sym)
                    holdings_map[sym] = h
                    watchlist_upserts.append({
                        "user_id": user_id,
                        "symbol": sym,
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

    # 4. Evaluate each symbol using high-speed In-Memory Cache (< 0.1ms lookup)
    for symbol in symbols:
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
                    rsi_15m = technicals.get("rsi_15m", 50)
                    
                    if pnl_pct >= 5.0 and rsi_15m > 72:
                        analysis["action_bias"] = "TRAILING_SL_ALERT"
                        analysis["has_actionable_signal"] = True
                        analysis["catalyst_category"] = "TRAILING_STOP_TRIGGER"
                        analysis["alert_title"] = f"{symbol}: Trailing Stop-Loss Trigger (P&L: +{pnl_pct}%)"
                        analysis["holding_guidance"] = f"Position gained +{pnl_pct}%; 15m RSI reached {rsi_15m}. Trailing SL active."
                        drivers = list(analysis.get("confluence_drivers", []))
                        drivers.insert(0, f"Position has gained {pnl_pct}%; 15m RSI reached {rsi_15m} (Overbought zone).")
                        analysis["confluence_drivers"] = drivers
            else:
                # Cache miss fallback
                fresh_pack = await evaluate_single_symbol_full(symbol, macro_data=macro_data, holding_info=holding_info)
                technicals = fresh_pack.get("technicals", {})
                financials = fresh_pack.get("financials", {})
                flow_data = fresh_pack.get("flow_data", {})
                analysis = fresh_pack.get("analysis", {})
            
            confluence_score = analysis.get("confluence_score", 50)
            has_actionable = analysis.get("has_actionable_signal", False)
            action_bias = analysis.get("action_bias", "HOLD_NEUTRAL")
            alert_title = analysis.get("alert_title", f"{symbol} Market Update")
            catalyst_type = analysis.get("catalyst_category", "NEWS_CATALYST")
            confluence_drivers = analysis.get("confluence_drivers", [])
            tactical_levels = analysis.get("tactical_levels", {})
            holding_guidance = analysis.get("holding_guidance")
            
            # Sensitivity Filter
            should_dispatch = False
            if alert_sensitivity == "HIGH":
                should_dispatch = (confluence_score >= 80) or (action_bias == "TRAILING_SL_ALERT")
            elif alert_sensitivity == "FII":
                is_fii = (catalyst_type in ["BLOCK_DEAL", "DEBT_REDUCTION"] or flow_data.get("is_high_delivery"))
                should_dispatch = is_fii and (confluence_score >= 65 or has_actionable)
            else: # ALL
                should_dispatch = has_actionable or (confluence_score >= 65)

            if not should_dispatch:
                continue

            # Anti-Fatigue Cooldown Check
            is_tier1 = (confluence_score >= 88 or action_bias == "TRAILING_SL_ALERT" or catalyst_type == "BLOCK_DEAL")
            allowed, reason = should_dispatch_alert(user_id, symbol, action_bias, confluence_score, is_tier1)
            
            if not allowed:
                logger.info(f"Skipping dispatch for {symbol}: {reason}")
                continue

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
                        "rsi_15m": technicals.get("rsi_15m"),
                        "rsi_5m": technicals.get("rsi_5m"),
                        "vwap": technicals.get("vwap"),
                        "delivery_pct": flow_data.get("delivery_pct"),
                        "vsa_regime": flow_data.get("vsa_regime"),
                        "factor_breakdown": analysis.get("factor_breakdown") or {
                            "technicals": technicals.get("technical_score", 65),
                            "flow": flow_data.get("flow_score", 60),
                            "forensics": forensics.get("forensic_score", 75),
                            "catalysts": min(95, max(40, confluence_score))
                        }
                    },
                    holding_guidance=holding_guidance
                )
                inline_buttons = build_telegram_inline_keyboard(symbol)
                telegram_sent = await send_telegram_notification(telegram_chat_id, formatted_msg, reply_markup=inline_buttons)

            # Normalize and validate catalyst against PostgreSQL catalyst_type_enum
            CATALYST_SYNONYM_MAP = {
                "EARNINGS_SURPRISE": "EARNINGS_BEAT",
                "DEBT_REDUCTION": "DEBT_CHANGE",
            }
            normalized_catalyst = CATALYST_SYNONYM_MAP.get(catalyst_type, catalyst_type)
            VALID_CATALYST_TYPES = {
                "BLOCK_DEAL", "EARNINGS_BEAT", "DEBT_CHANGE", "PRICE_BREAKOUT", 
                "NEWS_CATALYST", "VOLUME_SURGE", "TECHNICAL_BREAKOUT", "TRAILING_STOP_TRIGGER"
            }
            resolved_catalyst = normalized_catalyst if normalized_catalyst in VALID_CATALYST_TYPES else "NEWS_CATALYST"

            # Persist Alert in Supabase Ledger
            alert_record = {
                "user_id": user_id,
                "symbol": symbol,
                "alert_title": alert_title,
                "catalyst_type": resolved_catalyst,
                "impact_score": confluence_score,
                "factual_reasons": confluence_drivers,
                "metrics_snapshot": {
                    "action_bias": action_bias,
                    "tactical_levels": tactical_levels,
                    "technicals": technicals,
                    "flow_data": flow_data,
                    "financials": financials,
                    "macro_data": macro_data,
                    "demat_position": demat_pos,
                    "factor_breakdown": analysis.get("factor_breakdown") or {
                        "technicals": technicals.get("technical_score", 65),
                        "flow": flow_data.get("flow_score", 60),
                        "forensics": forensics.get("forensic_score", 75),
                        "catalysts": min(95, max(40, confluence_score))
                    }
                },
                "sent_via_fcm": fcm_sent,
                "sent_via_telegram": telegram_sent,
            }
            res = supabase_client.table("stok_alerts").insert(alert_record).execute()
            if res.data:
                generated_alerts.append(res.data[0])

        except Exception as stock_err:
            logger.error(f"Error evaluating symbol {symbol} for user {mask_id(user_id)}: {stock_err}")
            continue

    return generated_alerts
