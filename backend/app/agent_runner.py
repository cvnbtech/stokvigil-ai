import json
import logging
import urllib.parse
import concurrent.futures
import feedparser
from datetime import date, datetime
import yfinance as yf
from typing import List, Dict, Any, Optional

from app.config import settings
from app.vault import vault
from app.technical_engine import fetch_multi_timeframe_technicals
from app.flow_tracker import fetch_delivery_and_fo_flow, fetch_bulk_and_block_deals
from app.macro_filter import fetch_macro_market_regime, evaluate_forensic_health
from app.alert_limiter import should_dispatch_alert
from app.notifications import send_fcm_notification, send_telegram_notification, format_telegram_alert, build_telegram_inline_keyboard
from app.market_cache import market_cache

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
    Dynamically resolves any Indian stock ISIN (e.g. INE750C01026) to its official NSE exchange ticker
    using real-time exchange security search. 100% dynamic for all 2,000+ stocks with sub-millisecond RAM caching.
    """
    isin_clean = str(isin).strip().upper()
    fallback = str(fallback_code).strip().upper()
    
    if not isin_clean or not isin_clean.startswith("INE"):
        return fallback

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
                if sym.endswith(".BO") or quote.get("quoteType") == "EQUITY":
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
        max_workers = min(25, max(1, len(raw_holdings)))
        
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
• Volume Multiple: {technicals.get('volume_multiple')}x vs 20 MA (Surge: {technicals.get('is_volume_surge')})

============================================================
3. INSTITUTIONAL FLOW & DERIVATIVES:
============================================================
• Estimated Delivery Volume: {flow_data.get('delivery_pct')}% (Accumulation: {flow_data.get('is_high_delivery')})
• F&O Open Interest: {flow_data.get('fo_oi_status')} ({flow_data.get('flow_bias')})

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
• Sector: {forensics.get('sector_name')}

============================================================
6. 24-HOUR REAL-TIME NEWS & FILINGS:
============================================================
{json.dumps(news_items, indent=2)}

DIRECTIVES:
1. Confluence Score (1-100): Technical (30%), Flow (25%), Fundamentals (25%), News/Catalysts (20%).
2. Action Bias: "BUY_WATCH" (Score >= 75), "SELL_WATCH" (Score <= 35), "TRAILING_SL_ALERT" (User holds stock, profit > 5% & momentum stalling), "HOLD_NEUTRAL".
3. Calculate strict tactical levels: Entry Range, Target 1 (1.5x ATR), Target 2 (2.5x ATR), Stop Loss (1.5x ATR), Risk-Reward Ratio (Min 1:2).

Output ONLY valid JSON matching this exact structure:
{{
  "symbol": "{symbol}",
  "has_actionable_signal": true/false,
  "action_bias": "BUY_WATCH | SELL_WATCH | TRAILING_SL_ALERT | HOLD_NEUTRAL",
  "confluence_score": 85,
  "alert_title": "Descriptive concise headline",
  "catalyst_category": "TECHNICAL_BREAKOUT | BLOCK_DEAL | EARNINGS_SURPRISE | DEBT_REDUCTION | VOLUME_SURGE | TRAILING_STOP_TRIGGER",
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
  "holding_guidance": "Recommended holding / trailing stop guidance for user's Demat position.",
  "growth_outlook_summary": "12-month expansion summary."
}}
"""

    if settings.GEMINI_API_KEY:
        # Try google.genai (Modern SDK) first, then fallback to google.generativeai
        try:
            from google import genai
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            for model_name in ['gemini-2.5-flash', 'gemini-1.5-flash']:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config={"response_mime_type": "application/json"}
                    )
                    parsed = json.loads(response.text)
                    logger.info(f"Successfully evaluated {symbol} using GenAI SDK '{model_name}'.")
                    return parsed
                except Exception as model_err:
                    logger.warning(f"GenAI SDK '{model_name}' attempt failed for {symbol}: {model_err}")
                    continue
        except Exception:
            try:
                import google.generativeai as legacy_genai
                legacy_genai.configure(api_key=settings.GEMINI_API_KEY)
                for model_name in ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']:
                    try:
                        model = legacy_genai.GenerativeModel(model_name)
                        response = model.generate_content(
                            prompt,
                            generation_config={"response_mime_type": "application/json"}
                        )
                        parsed = json.loads(response.text)
                        logger.info(f"Successfully evaluated {symbol} using legacy AI model '{model_name}'.")
                        return parsed
                    except Exception as model_err:
                        logger.warning(f"Legacy model '{model_name}' attempt failed for {symbol}: {model_err}")
                        continue
            except Exception as e:
                logger.error(f"Gemini API execution error: {e}. Falling back to deterministic engine.")

    # ==========================================
    # DETERMINISTIC QUANTITATIVE FALLBACK ENGINE
    # ==========================================
    tech_score = technicals.get("technical_score", 50)
    flow_score = flow_data.get("flow_score", 50)
    forensic_score = forensics.get("forensic_score", 60)
    
    # News Score
    news_score = 50
    catalyst_category = "TECHNICAL_BREAKOUT"
    alert_title = f"{symbol}: Technical & Momentum Update"
    confluence_drivers = []
    
    for item in news_items:
        title_upper = item['title'].upper()
        if "BLOCK DEAL" in title_upper or "BULK DEAL" in title_upper:
            news_score += 35
            catalyst_category = "BLOCK_DEAL"
            alert_title = f"{symbol}: Institutional Block/Bulk Deal Reported"
            confluence_drivers.append(f"Exchange Filing: {item['title']}")
            break
        elif "PROFIT" in title_upper or "REVENUE" in title_upper or "Q1" in title_upper or "Q2" in title_upper or "Q3" in title_upper or "Q4" in title_upper:
            news_score += 30
            catalyst_category = "EARNINGS_SURPRISE"
            alert_title = f"{symbol}: Quarterly Earnings & Financial Catalyst"
            confluence_drivers.append(f"Financial Disclosure: {item['title']}")
            break

    # Calculate Multi-Factor Confluence Score (0-100)
    confluence_score = int(round(
        (tech_score * 0.30) +
        (flow_score * 0.25) +
        (forensic_score * 0.25) +
        (min(95, news_score) * 0.20)
    ))

    # Determine Action Bias
    action_bias = "HOLD_NEUTRAL"
    has_actionable_signal = False
    
    # Check Trailing Stop-Loss for User Holding
    if demat_context["is_in_portfolio"] and demat_context["unrealized_pnl_pct"] >= 5.0 and technicals.get("rsi_15m", 50) > 72:
        action_bias = "TRAILING_SL_ALERT"
        has_actionable_signal = True
        catalyst_category = "TRAILING_STOP_TRIGGER"
        alert_title = f"{symbol}: Trailing Stop-Loss Trigger (P&L: +{demat_context['unrealized_pnl_pct']}%)"
        confluence_drivers.append(f"Position has gained {demat_context['unrealized_pnl_pct']}%; 15m RSI reached {technicals.get('rsi_15m')} (Overbought zone).")
    elif confluence_score >= 72:
        action_bias = "BUY_WATCH"
        has_actionable_signal = True
    elif confluence_score <= 38:
        action_bias = "SELL_WATCH"
        has_actionable_signal = True

    # Multi-Timeframe & Macro Veto Guardrails (Core Principle #2)
    ema_200_val = technicals.get("ema_200", current_price)
    is_macro_downtrend = (technicals.get("ma_trend") == "BELOW_200_EMA") or (current_price < ema_200_val)
    is_high_vix = not macro_data.get("allow_breakout_trades", True)

    if (is_macro_downtrend or is_high_vix) and action_bias == "BUY_WATCH":
        logger.info(f"Multi-Timeframe Veto triggered for {symbol}: Below 200 EMA (₹{ema_200_val}) or High VIX. Downgrading BUY_WATCH to HOLD_NEUTRAL.")
        action_bias = "HOLD_NEUTRAL"
        has_actionable_signal = False
        confluence_score = min(58, confluence_score)

    # Build Confluence Drivers
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

    # Compute Tactical Volatility Envelopes (Strict 1:2.5 Asymmetric R:R)
    entry_min = round(current_price * 0.995, 2)
    entry_max = round(current_price * 1.005, 2)
    stop_loss = round(current_price - (1.0 * atr_val), 2)
    target_1 = round(current_price + (1.5 * atr_val), 2)
    target_2 = round(current_price + (2.5 * atr_val), 2)
    risk_val = current_price - stop_loss
    reward_val = target_2 - current_price
    rr_ratio = round(reward_val / risk_val, 1) if risk_val > 0 else 2.5

    holding_guidance = "Monitor position with trailing SL." if demat_context["is_in_portfolio"] else "Track for optimal entry in tactical range."

    return {
        "symbol": symbol,
        "has_actionable_signal": has_actionable_signal,
        "action_bias": action_bias,
        "confluence_score": confluence_score,
        "alert_title": alert_title,
        "catalyst_category": catalyst_category,
        "confluence_drivers": confluence_drivers,
        "tactical_levels": {
            "entry_range": f"₹{entry_min:,.2f} - ₹{entry_max:,.2f}",
            "target_1": f"₹{target_1:,.2f}",
            "target_2": f"₹{target_2:,.2f}",
            "protective_stop_loss": f"₹{stop_loss:,.2f}",
            "risk_reward_ratio": f"1:{rr_ratio}"
        },
        "holding_guidance": holding_guidance,
        "growth_outlook_summary": f"Long term valuation: P/E {financials.get('pe_ratio', 'N/A')}, D/E {financials.get('debt_to_equity', 'N/A')}."
    }


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
    """
    if macro_data is None:
        macro_data = fetch_macro_market_regime()

    technicals = fetch_multi_timeframe_technicals(symbol)
    financials = fetch_stock_financials(symbol)
    flow_data = fetch_delivery_and_fo_flow(symbol, technicals.get("price_vs_vwap_pct", 0.0))
    forensics = evaluate_forensic_health(symbol, financials)
    news_items = fetch_stock_news(symbol)

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
    Runs once per 5-minute pulse, reducing 50,000 API calls to ~150-200 calls total.
    """
    macro_data = fetch_macro_market_regime()
    w_res = supabase_client.table("user_watchlists").select("symbol").execute()
    symbols = set(item['symbol'].strip().upper() for item in (w_res.data or []) if item.get('symbol'))

    if not symbols:
        logger.info("No active symbols found across user watchlists to pre-compute.")
        return 0

    logger.info(f"⚡ Pre-computing institutional market state for {len(symbols)} unique symbols into RAM cache...")
    synced = 0
    for sym in symbols:
        try:
            if market_cache.is_fresh(sym, max_age_seconds=240):
                synced += 1
                continue
            await evaluate_single_symbol_full(sym, macro_data=macro_data)
            synced += 1
        except Exception as e:
            logger.error(f"Error pre-computing market cache for {sym}: {e}")

    logger.info(f"✅ Market Cache Sync Complete: {synced}/{len(symbols)} unique symbols cached in RAM.")
    return synced


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
        logger.warning(f"Profile not found for user {user_id}")
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
            for h in holdings:
                sym = h['symbol']
                symbols.add(sym)
                holdings_map[sym] = h
                try:
                    supabase_client.table("user_watchlists").upsert({
                        "user_id": user_id,
                        "symbol": sym,
                        "is_auto_synced": True
                    }, on_conflict="user_id,symbol").execute()
                except Exception as e:
                    logger.error(f"Error syncing holding {sym} to watchlist: {e}")
        else:
            logger.info(f"ICICI Session Token for user {user_id} is from {token_date} (expired today {today_str}). Scanning watchlist symbols only.")

    macro_data = fetch_macro_market_regime()

    # 4. Evaluate each symbol using high-speed In-Memory Cache (< 0.1ms lookup)
    for symbol in symbols:
        try:
            cached_pack = market_cache.get_stock(symbol)
            holding_info = holdings_map.get(symbol)

            if cached_pack and not holding_info:
                technicals = cached_pack.get("technicals", {})
                flow_data = cached_pack.get("flow_data", {})
                analysis = cached_pack.get("analysis", {})
            else:
                # Cache miss or holding-specific evaluation
                fresh_pack = await evaluate_single_symbol_full(symbol, macro_data=macro_data, holding_info=holding_info)
                technicals = fresh_pack.get("technicals", {})
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
                curr_p = technicals.get("current_price") or financials.get("price") or 0.0
                avg_p = holding_info.get("average_price", 0.0)
                pnl_pct = round(((curr_p - avg_p) / avg_p) * 100, 2) if avg_p > 0 else 0.0
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
                        "delivery_pct": flow_data.get("delivery_pct")
                    },
                    holding_guidance=holding_guidance
                )
                inline_buttons = build_telegram_inline_keyboard(symbol)
                telegram_sent = await send_telegram_notification(telegram_chat_id, formatted_msg, reply_markup=inline_buttons)

            # Persist Alert in Supabase Ledger
            alert_record = {
                "user_id": user_id,
                "symbol": symbol,
                "alert_title": alert_title,
                "catalyst_type": catalyst_type if catalyst_type in ["BLOCK_DEAL", "EARNINGS_BEAT", "DEBT_CHANGE", "PRICE_BREAKOUT", "NEWS_CATALYST"] else "NEWS_CATALYST",
                "impact_score": confluence_score,
                "factual_reasons": confluence_drivers,
                "metrics_snapshot": {
                    "action_bias": action_bias,
                    "tactical_levels": tactical_levels,
                    "technicals": technicals,
                    "flow_data": flow_data,
                    "financials": financials,
                    "macro_data": macro_data,
                    "demat_position": demat_pos
                },
                "sent_via_fcm": fcm_sent,
                "sent_via_telegram": telegram_sent,
            }
            res = supabase_client.table("stok_alerts").insert(alert_record).execute()
            if res.data:
                generated_alerts.append(res.data[0])

        except Exception as stock_err:
            logger.error(f"Error evaluating symbol {symbol} for user {user_id}: {stock_err}")
            continue

    return generated_alerts
