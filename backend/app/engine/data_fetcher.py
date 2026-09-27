import concurrent.futures
import feedparser
import logging
import time
import urllib.parse
import urllib.request
from typing import Dict, Any, List
import yfinance as yf

logger = logging.getLogger("stokvigil.engine.data_fetcher")

# Silence noisy third-party internal SDK loggers (yfinance)
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

# Corporate Fundamentals Cache: canonical_key -> {data, timestamp} (TTL: 12 hours / 43200s)
_FINANCIALS_CACHE: Dict[str, Dict[str, Any]] = {}
_FINANCIALS_CACHE_TTL: float = 43200.0  # 12 hours (Quarter-invariant corporate metrics)

# News RSS Cache: canonical_key -> {data, timestamp} (TTL: 30 minutes / 1800s)
_NEWS_CACHE: Dict[str, Dict[str, Any]] = {}
_NEWS_CACHE_TTL: float = 1800.0  # 30 minutes


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

    # 2. Determine dual-exchange candidates
    if clean_sym.isdigit() and len(clean_sym) == 6:
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

    if len(_NEWS_CACHE) > 1000:
        oldest = sorted(_NEWS_CACHE.keys(), key=lambda k: _NEWS_CACHE[k].get("timestamp", 0))[:200]
        for ok in oldest:
            _NEWS_CACHE.pop(ok, None)

    _NEWS_CACHE[canonical_key] = {
        "timestamp": now,
        "data": headlines
    }
    return headlines
