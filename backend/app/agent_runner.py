import json
import logging
import urllib.parse
import feedparser
import yfinance as yf
from typing import List, Dict, Any
from app.config import settings
from app.vault import vault
from app.notifications import send_fcm_notification, send_telegram_notification, format_telegram_alert

logger = logging.getLogger("stokvigil.agent_runner")

# ==========================================
# 1. AGENT TOOL INTEGRATIONS
# ==========================================

def fetch_user_portfolio(app_key: str, secret_key: str, session_token: str) -> List[Dict[str, Any]]:
    """
    Fetches real-time portfolio holdings from user's ICICI Demat account using breeze-connect SDK.
    Falls back gracefully if token is expired or mock testing.
    """
    if not app_key or not secret_key or not session_token:
        logger.warning("Incomplete Breeze credentials provided.")
        return []
        
    try:
        from breeze_connect import BreezeConnect
        breeze = BreezeConnect(api_key=app_key)
        breeze.generate_session(api_secret=secret_key, session_token=session_token)
        
        portfolio_res = breeze.get_portfolio_holdings()
        if portfolio_res and portfolio_res.get('status') == 200:
            holdings = portfolio_res.get('Success', [])
            result = []
            for item in holdings:
                result.append({
                    "symbol": item.get('stock_code', '').upper(),
                    "quantity": float(item.get('quantity', 0)),
                    "average_price": float(item.get('average_price', 0)),
                    "current_market_price": float(item.get('current_market_price', 0)),
                })
            return result
        else:
            logger.warning(f"Breeze API returned non-200 status: {portfolio_res}")
            return []
    except Exception as e:
        logger.error(f"Error fetching ICICI Breeze portfolio: {e}")
        return []


def fetch_stock_financials(symbol: str) -> Dict[str, Any]:
    """
    Fetches comprehensive financial metrics, valuation data, debt ratios, quarterly growth,
    and 52-week position from Yahoo Finance for an NSE ticker.
    """
    ticker_name = symbol if symbol.endswith(".NS") or symbol.endswith(".BO") else f"{symbol}.NS"
    try:
        ticker = yf.Ticker(ticker_name)
        info = ticker.info or {}
        
        current_price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose') or 0.0
        pe_ratio = info.get('trailingPE')
        forward_pe = info.get('forwardPE')
        debt_to_equity = info.get('debtToEquity')
        revenue_growth = info.get('revenueGrowth')
        earnings_growth = info.get('earningsQuarterlyGrowth')
        profit_margins = info.get('profitMargins')
        return_on_equity = info.get('returnOnEquity')
        
        return {
            "symbol": symbol,
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
        logger.error(f"Error fetching yfinance financials for {symbol}: {e}")
        return {"symbol": symbol, "price": 0.0}


def fetch_stock_news(symbol: str) -> List[Dict[str, str]]:
    """
    Parses real-time Google News RSS feeds targeting block/bulk deals, orders,
    quarterly results, revenue, debt changes, and promoter activity.
    """
    query_str = f'"{symbol}" AND (block deal OR bulk deal OR quarterly results OR Q1 OR Q2 OR Q3 OR Q4 OR revenue OR profit OR order OR debt OR expansion)'
    encoded_symbol = urllib.parse.quote(query_str)
    rss_url = f"https://news.google.com/rss/search?q={encoded_symbol}&hl=en-IN&gl=IN&ceid=IN:en"
    
    headlines = []
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:8]: # Top 8 latest headlines
            headlines.append({
                "title": entry.title,
                "link": entry.link,
                "published": entry.published,
            })
    except Exception as e:
        logger.error(f"Error fetching real-time news RSS for {symbol}: {e}")
        
    return headlines


# ==========================================
# 2. ANTIGRAVITY / GEMINI AI EVALUATION ENGINE
# ==========================================

async def analyze_catalysts_with_gemini(symbol: str, financials: dict, news_items: list, holding_info: dict = None) -> dict:
    """
    Passes 360-degree market data to Gemini 3.6 Flash via Google AI Studio API.
    Evaluates trajectory direction (UPWARD/DOWNWARD), order/deal impact, quarterly results surprise,
    debt & valuation (P/E) shifts, current market context, and 12-month future growth drivers.
    Guarantees non-advisory, pure factual data notifications.
    """
    prompt = f"""
You are an expert financial market catalyst & trajectory analyzer for Indian stock exchange (NSE: {symbol}).
Your task is to analyze real-time data and determine if there is a major price-moving event or trajectory shift.

DEMAT HOLDING POSITION (ICICI DIRECT):
{json.dumps(holding_info or {}, indent=2)}

FACTUAL FINANCIAL & VALUATION SNAPSHOT:
{json.dumps(financials, indent=2)}

REAL-TIME MARKET NEWS HEADLINES:
{json.dumps(news_items, indent=2)}

ANALYSIS CRITERIA:
1. Trajectory Direction: Evaluate if data suggests an UPWARD, DOWNWARD, or NEUTRAL trajectory shift.
2. Catalyst Triggers: Check for institutional Bulk/Block Deals, Large Commercial Orders, Quarterly Earnings (P&L/Revenue surprise), Debt reduction/addition, or Promoter buying/selling.
3. Valuation Check: Compare Trailing P/E vs Forward P/E and Debt-to-Equity shift.
4. Noise Filter: Ignore routine promotional news or minor daily fluctuations.
5. Compliance: Do NOT give buy/sell recommendations or SEBI advice. All bullet points must be 100% factual.

Output ONLY valid JSON matching this exact structure:
{{
  "symbol": "{symbol}",
  "has_catalyst": true/false,
  "trajectory_direction": "EXPECTED_UPWARD | EXPECTED_DOWNWARD | NEUTRAL_WATCH",
  "alert_title": "Short descriptive title (e.g. RELIANCE: Q1 Profit Up 18% & Large Block Deal)",
  "catalyst_type": "BLOCK_DEAL | EARNINGS_BEAT | DEBT_CHANGE | PRICE_BREAKOUT | NEWS_CATALYST",
  "impact_score": 85,
  "factual_reasons": [
    "Fact 1: Q1 revenue grew 18.5% YoY with profit margin expanding to 14.2%",
    "Fact 2: Block deal of 1.25M shares reported at ₹2,950",
    "Fact 3: Debt-to-equity reduced from 0.45 to 0.38"
  ],
  "growth_outlook_summary": "12-month factual expansion & market context summary"
}}
"""

    if settings.GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            
            # Try Gemini 3.6 Flash first (Primary Model), fallback to 2.5 Flash and 1.5 Flash
            for model_name in ['gemini-3.6-flash', 'gemini-2.5-flash', 'gemini-1.5-flash']:
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(
                        prompt,
                        generation_config={"response_mime_type": "application/json"}
                    )
                    parsed = json.loads(response.text)
                    logger.info(f"Successfully evaluated catalyst using model '{model_name}'.")
                    return parsed
                except Exception as model_err:
                    logger.warning(f"Model '{model_name}' execution attempt: {model_err}")
                    continue

        except Exception as e:
            logger.error(f"Gemini AI Studio API analysis failed: {e}. Falling back to deterministic rules.")

    # Rule-Based Fallback Engine if Gemini API Key not set
    has_catalyst = False
    impact_score = 30
    catalyst_type = "NEWS_CATALYST"
    alert_title = f"{symbol} Market Update"
    factual_reasons = []

    for news in news_items:
        title_upper = news['title'].upper()
        if "BLOCK DEAL" in title_upper or "BULK DEAL" in title_upper:
            has_catalyst = True
            impact_score = 88
            catalyst_type = "BLOCK_DEAL"
            alert_title = f"{symbol}: Large Block/Bulk Deal Reported"
            factual_reasons.append(f"Headline: {news['title']}")
            break
        elif "Q1" in title_upper or "Q2" in title_upper or "Q3" in title_upper or "Q4" in title_upper or "PROFIT" in title_upper:
            has_catalyst = True
            impact_score = 82
            catalyst_type = "EARNINGS_BEAT"
            alert_title = f"{symbol}: Quarterly Results & Earnings Update"
            factual_reasons.append(f"Headline: {news['title']}")
            break

    if not factual_reasons and news_items:
        factual_reasons.append(f"Recent headline: {news_items[0]['title']}")

    if financials.get("price"):
        factual_reasons.append(f"Current Market Price: ₹{financials['price']}")

    return {
        "symbol": symbol,
        "has_catalyst": has_catalyst or (impact_score >= 60),
        "alert_title": alert_title,
        "catalyst_type": catalyst_type,
        "impact_score": impact_score,
        "factual_reasons": factual_reasons
    }


# ==========================================
# 3. MULTI-USER PORTFOLIO EVALUATION ROUTINE
# ==========================================

async def evaluate_user_portfolio_and_watchlists(user_id: str, supabase_client) -> List[dict]:
    """
    Evaluates all tracked stocks for a user across demat holdings and manual watchlists.
    Dispatches FCM and Telegram notifications for high-impact catalysts (impact_score >= 60).
    """
    generated_alerts = []
    
    # 1. Fetch user profile
    profile_res = supabase_client.table("profiles").select("*").eq("id", user_id).execute()
    if not profile_res.data:
        logger.warning(f"Profile not found for user {user_id}")
        return []
        
    profile = profile_res.data[0]
    fcm_token = profile.get("fcm_device_token")
    telegram_chat_id = profile.get("telegram_chat_id")
    telegram_enabled = profile.get("telegram_enabled", False)
    
    # 2. Fetch user's active watchlist
    watchlist_res = supabase_client.table("user_watchlists").select("symbol").eq("user_id", user_id).execute()
    symbols = set(item['symbol'] for item in (watchlist_res.data or []))
    
    # 3. Check ICICI credentials and sync holdings
    cred_res = supabase_client.table("user_credentials").select("*").eq("user_id", user_id).execute()
    if cred_res.data:
        cred = cred_res.data[0]
        app_key = vault.decrypt(cred.get("encrypted_app_key"))
        secret_key = vault.decrypt(cred.get("encrypted_secret_key"))
        session_token = vault.decrypt(cred.get("encrypted_session_token"))
        
        holdings = fetch_user_portfolio(app_key, secret_key, session_token)
        for h in holdings:
            sym = h['symbol']
            symbols.add(sym)
            # Auto-upsert into user_watchlists
            supabase_client.table("user_watchlists").upsert({
                "user_id": user_id,
                "symbol": sym,
                "is_auto_synced": True
            }, on_conflict="user_id,symbol").execute()

    # Map holdings by symbol for deep position-aware analysis
    holdings_map = {h['symbol']: h for h in holdings} if 'holdings' in locals() else {}

    # 4. Evaluate each symbol
    for symbol in symbols:
        financials = fetch_stock_financials(symbol)
        news_items = fetch_stock_news(symbol)
        holding_info = holdings_map.get(symbol, {})
        
        analysis = await analyze_catalysts_with_gemini(symbol, financials, news_items, holding_info)
        
        impact_score = analysis.get("impact_score", 0)
        has_catalyst = analysis.get("has_catalyst", False)
        
        # Threshold: Dispatches alert if impact score >= 60
        if has_catalyst or impact_score >= 60:
            alert_title = analysis.get("alert_title", f"{symbol} Alert")
            catalyst_type = analysis.get("catalyst_type", "NEWS_CATALYST")
            factual_reasons = analysis.get("factual_reasons", [])
            
            # Dispatch FCM Push Notification
            fcm_sent = False
            if fcm_token:
                fcm_body = f"Impact: {impact_score}/100 | " + " ".join(factual_reasons[:1])
                fcm_sent = await send_fcm_notification(fcm_token, alert_title, fcm_body, {
                    "symbol": symbol,
                    "impact_score": str(impact_score),
                    "catalyst_type": catalyst_type
                })
                
            # Dispatch Telegram Notification
            telegram_sent = False
            if telegram_enabled and telegram_chat_id:
                formatted_msg = format_telegram_alert(
                    symbol=symbol,
                    alert_title=alert_title,
                    catalyst_type=catalyst_type,
                    impact_score=impact_score,
                    factual_reasons=factual_reasons,
                    metrics_snapshot=financials
                )
                telegram_sent = await send_telegram_notification(telegram_chat_id, formatted_msg)
                
            # Save Alert to Supabase Ledger
            alert_record = {
                "user_id": user_id,
                "symbol": symbol,
                "alert_title": alert_title,
                "catalyst_type": catalyst_type,
                "impact_score": impact_score,
                "factual_reasons": factual_reasons,
                "metrics_snapshot": financials,
                "sent_via_fcm": fcm_sent,
                "sent_via_telegram": telegram_sent,
            }
            res = supabase_client.table("stok_alerts").insert(alert_record).execute()
            if res.data:
                generated_alerts.append(res.data[0])

    return generated_alerts
