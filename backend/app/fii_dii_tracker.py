"""
StokVigil AI: Institutional FII & DII Flow Tracker
Fetches official daily Net Foreign Institutional (FII) & Domestic Institutional (DII)
cash market activity from the National Stock Exchange of India (NSE).

Includes multi-tier fallback (Live NSE -> Database Cache -> Market Proxy) and
sentiment classification for institutional accumulation vs distribution.
"""

import logging
import time
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
import urllib.request
import json

logger = logging.getLogger("stokvigil.fii_dii_tracker")

# In-memory cache for FII/DII daily data (TTL: 30 minutes)
_FII_DII_CACHE: Dict[str, Any] = {}
_CACHE_TIMESTAMP: float = 0.0
_CACHE_TTL_SECONDS: float = 1800.0  # 30 mins


def classify_institutional_sentiment(fii_net: float, dii_net: float) -> str:
    """
    Classifies overall market institutional sentiment based on combined net flows in ₹ Crores.
    """
    combined = fii_net + dii_net
    if fii_net > 1000 and dii_net > 0:
        return "STRONG_ACCUMULATION"
    elif combined > 500:
        return "BULLISH_INFLOW"
    elif combined < -1500:
        return "HEAVY_DISTRIBUTION"
    elif combined < -300:
        return "BEARISH_OUTFLOW"
    elif fii_net > 0 and dii_net < 0:
        return "FII_ABSORBING_DII_PROFIT_BOOKING"
    elif dii_net > 0 and fii_net < 0:
        return "DOMESTIC_DII_SUPPORT_DEFENDING"
    return "NEUTRAL_BALANCED"


def _fetch_from_nse_direct() -> Optional[Dict[str, Any]]:
    """
    Attempts to fetch official FII/DII daily trade report from NSE.
    """
    url = "https://www.nseindia.com/api/fiidiiTradeReact"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/reports/fii-dii",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                raw = json.loads(response.read().decode("utf-8"))
                if isinstance(raw, list) and len(raw) >= 2:
                    # Format: [{'category': 'FII/FPI *', 'date': '05-Sep-2026', 'buyValue': '14230.5', 'sellValue': '12110.2', 'netValue': '2120.3'}, ...]
                    fii_entry = next((item for item in raw if "FII" in item.get("category", "")), None)
                    dii_entry = next((item for item in raw if "DII" in item.get("category", "")), None)
                    if fii_entry and dii_entry:
                        f_buy = float(str(fii_entry.get("buyValue", 0)).replace(",", ""))
                        f_sell = float(str(fii_entry.get("sellValue", 0)).replace(",", ""))
                        f_net = float(str(fii_entry.get("netValue", 0)).replace(",", ""))
                        d_buy = float(str(dii_entry.get("buyValue", 0)).replace(",", ""))
                        d_sell = float(str(dii_entry.get("sellValue", 0)).replace(",", ""))
                        d_net = float(str(dii_entry.get("netValue", 0)).replace(",", ""))
                        t_date = fii_entry.get("date", datetime.now().strftime("%d-%b-%Y"))

                        return {
                            "date": t_date,
                            "fii": {"buy": f_buy, "sell": f_sell, "net": f_net},
                            "dii": {"buy": d_buy, "sell": d_sell, "net": d_net},
                            "combined_net": round(f_net + d_net, 2),
                            "sentiment": classify_institutional_sentiment(f_net, d_net),
                            "source": "NSE_LIVE"
                        }
    except Exception as e:
        logger.debug(f"Direct NSE FII/DII live fetch skipped/unavailable: {e}")
    return None


def _get_unavailable_institutional_payload() -> Dict[str, Any]:
    """
    ZERO-DEFAULT POLICY: Returns a clean unpopulated payload when exchange and DB sources are unavailable.
    Never fabricates synthetic institutional volume figures.
    """
    today_str = date.today().isoformat()
    return {
        "date": today_str,
        "status": "DATA_UNAVAILABLE",
        "fii": None,
        "dii": None,
        "combined_net": None,
        "sentiment": "DATA_UNAVAILABLE",
        "source": "DATA_UNAVAILABLE",
        "history": []
    }


def fetch_daily_fii_dii_flows(db=None) -> Dict[str, Any]:
    """
    Returns latest FII/DII net flows with 30-minute caching.
    Attempts live NSE query, falls back to Supabase historical table, and finally to DATA_UNAVAILABLE state.
    """
    global _FII_DII_CACHE, _CACHE_TIMESTAMP

    now = time.time()
    if _FII_DII_CACHE and (now - _CACHE_TIMESTAMP) < _CACHE_TTL_SECONDS:
        return _FII_DII_CACHE

    # 1. Try Live NSE
    data = _fetch_from_nse_direct()

    # 2. Try Supabase Cache Table if DB available
    # 2. Try Supabase Cache Table if DB available (to fetch or enrich with multi-day history)
    if db is not None:
        try:
            res = db.table("fii_dii_flows").select("*").order("trade_date", desc=True).limit(5).execute()
            if res.data and len(res.data) > 0:
                history_list = [
                    {
                        "date": str(row.get("trade_date")),
                        "fii_net": float(row.get("fii_net_cr", 0)),
                        "dii_net": float(row.get("dii_net_cr", 0)),
                        "combined_net": float(row.get("combined_net_cr", 0)),
                        "sentiment": row.get("sentiment_bias", "NEUTRAL")
                    }
                    for row in res.data
                ]
                if not data:
                    latest = res.data[0]
                    f_net = float(latest.get("fii_net_cr", 0))
                    d_net = float(latest.get("dii_net_cr", 0))
                    data = {
                        "date": str(latest.get("trade_date")),
                        "fii": {
                            "buy": float(latest.get("fii_buy_cr", 0)),
                            "sell": float(latest.get("fii_sell_cr", 0)),
                            "net": f_net
                        },
                        "dii": {
                            "buy": float(latest.get("dii_buy_cr", 0)),
                            "sell": float(latest.get("dii_sell_cr", 0)),
                            "net": d_net
                        },
                        "combined_net": float(latest.get("combined_net_cr", round(f_net + d_net, 2))),
                        "sentiment": latest.get("sentiment_bias", classify_institutional_sentiment(f_net, d_net)),
                        "source": "SUPABASE_STORED",
                        "history": history_list
                    }
                else:
                    data["history"] = history_list
        except Exception as e:
            logger.debug(f"Supabase FII/DII table lookup skipped: {e}")

    # 3. Fallback to Data Unavailable State (ZERO-DEFAULT POLICY)
    if not data:
        data = _get_unavailable_institutional_payload()
        return data

    if "history" not in data or data["history"] is None:
        if data.get("fii") and data.get("dii"):
            data["history"] = [{
                "date": data["date"],
                "fii_net": data["fii"]["net"],
                "dii_net": data["dii"]["net"],
                "combined_net": data["combined_net"],
                "sentiment": data["sentiment"]
            }]
        else:
            data["history"] = []

    # Cache authentic result
    _FII_DII_CACHE = data
    _CACHE_TIMESTAMP = now
    return data
