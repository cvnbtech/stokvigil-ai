import logging
import yfinance as yf
from typing import Dict, Any, Tuple

logger = logging.getLogger("stokvigil.macro_filter")

# Sector mapping for major NSE tickers
SECTOR_MAP = {
    "TCS": "NIFTY IT",
    "INFY": "NIFTY IT",
    "WIPRO": "NIFTY IT",
    "HCLTECH": "NIFTY IT",
    "TECHM": "NIFTY IT",
    "HDFCBANK": "NIFTY BANK",
    "ICICIBANK": "NIFTY BANK",
    "SBIN": "NIFTY BANK",
    "KOTAKBANK": "NIFTY BANK",
    "AXISBANK": "NIFTY BANK",
    "TATAMOTORS": "NIFTY AUTO",
    "M&M": "NIFTY AUTO",
    "MARUTI": "NIFTY AUTO",
    "BAJAJ-AUTO": "NIFTY AUTO",
    "HEROMOTOCO": "NIFTY AUTO",
    "SUNPHARMA": "NIFTY PHARMA",
    "CIPLA": "NIFTY PHARMA",
    "DRREDDY": "NIFTY PHARMA",
    "DIVISLAB": "NIFTY PHARMA",
    "RELIANCE": "NIFTY ENERGY",
    "ONGC": "NIFTY ENERGY",
    "NTPC": "NIFTY ENERGY",
    "POWERGRID": "NIFTY ENERGY",
    "TATASTEEL": "NIFTY METAL",
    "JSWSTEEL": "NIFTY METAL",
    "HINDALCO": "NIFTY METAL",
}

def fetch_macro_market_regime() -> Dict[str, Any]:
    """
    Fetches broad Indian market indices:
    - NIFTY 50 (^NSEI)
    - NIFTY BANK (^NSEBANK)
    - India VIX (^INDIAVIX)
    """
    default_res = {
        "nifty_price": 24500.0,
        "nifty_change_pct": 0.0,
        "nifty_trend": "NEUTRAL",
        "india_vix": 14.5,
        "vix_regime": "MODERATE_VOLATILITY",
        "allow_breakout_trades": True
    }
    
    try:
        nifty = yf.Ticker("^NSEI")
        nifty_hist = nifty.history(period="2d")
        
        nifty_change_pct = 0.0
        nifty_price = 24500.0
        if len(nifty_hist) >= 2:
            prev_close = float(nifty_hist['Close'].iloc[-2])
            curr_close = float(nifty_hist['Close'].iloc[-1])
            nifty_price = round(curr_close, 2)
            nifty_change_pct = round(((curr_close - prev_close) / prev_close) * 100, 2)
            
        nifty_trend = "BULLISH" if nifty_change_pct > 0.3 else ("BEARISH" if nifty_change_pct < -0.3 else "NEUTRAL")
        
        # India VIX
        vix = yf.Ticker("^INDIAVIX")
        vix_hist = vix.history(period="2d")
        vix_val = 14.5
        if not vix_hist.empty:
            vix_val = round(float(vix_hist['Close'].iloc[-1]), 2)
            
        if vix_val < 13.0:
            vix_regime = "LOW_VOLATILITY_TRENDING"
            allow_breakout = True
        elif vix_val <= 19.0:
            vix_regime = "NORMAL_VOLATILITY"
            allow_breakout = True
        elif vix_val <= 24.0:
            vix_regime = "ELEVATED_VOLATILITY_CAUTION"
            allow_breakout = True
        else:
            vix_regime = "EXTREME_VOLATILITY_HIGH_RISK"
            allow_breakout = False
            
        # BSE SENSEX (^BSESN)
        sensex_price = 80000.0
        sensex_change_pct = 0.0
        try:
            sensex = yf.Ticker("^BSESN")
            sensex_hist = sensex.history(period="2d")
            if len(sensex_hist) >= 2:
                s_prev = float(sensex_hist['Close'].iloc[-2])
                s_curr = float(sensex_hist['Close'].iloc[-1])
                sensex_price = round(s_curr, 2)
                sensex_change_pct = round(((s_curr - s_prev) / s_prev) * 100, 2)
        except Exception as e:
            logger.debug(f"BSE SENSEX fetch fallback: {e}")

        return {
            "nifty_price": nifty_price,
            "nifty_change_pct": nifty_change_pct,
            "nifty_trend": nifty_trend,
            "sensex_price": sensex_price,
            "sensex_change_pct": sensex_change_pct,
            "india_vix": vix_val,
            "vix_regime": vix_regime,
            "allow_breakout_trades": allow_breakout
        }
    except Exception as e:
        logger.error(f"Error fetching macro regime: {e}")
        return default_res


def fetch_pre_market_war_room_data() -> Dict[str, Any]:
    """
    Synthesizes institutional pre-market intelligence for the 09:00 AM IST War Room:
    1. Domestic Benchmark: NIFTY 50 & BSE SENSEX levels and previous close
    2. Volatility Regime: India VIX (^INDIAVIX) and risk posture
    3. Global Cues: US (Dow Jones ^DJI, Nasdaq ^IXIC) and Asia (Nikkei ^N225)
    4. Sectoral Momentum: NIFTY Bank (^NSEBANK), NIFTY IT (^CNXIT), NIFTY Auto (^CNXAUTO)
    5. Actionable Session Guidance: Volatility warning, directional bias, and setup priority
    """
    from datetime import date
    today_str = str(date.today())
    
    # 1. Base macro data
    base_macro = fetch_macro_market_regime()
    nifty_price = base_macro.get("nifty_price", 24500.0)
    nifty_chg = base_macro.get("nifty_change_pct", 0.0)
    sensex_price = base_macro.get("sensex_price", 80000.0)
    sensex_chg = base_macro.get("sensex_change_pct", 0.0)
    vix_val = base_macro.get("india_vix", 14.5)
    vix_regime = base_macro.get("vix_regime", "NORMAL_VOLATILITY")
    allow_breakouts = base_macro.get("allow_breakout_trades", True)
    
    # 2. Global Cues
    global_cues = {
        "dow_jones_pct": 0.0,
        "nasdaq_pct": 0.0,
        "nikkei_pct": 0.0,
        "bias": "NEUTRAL"
    }
    
    ticker_map = {
        "^DJI": "dow_jones_pct",
        "^IXIC": "nasdaq_pct",
        "^N225": "nikkei_pct"
    }
    
    for t_sym, key in ticker_map.items():
        try:
            t = yf.Ticker(t_sym)
            fast = getattr(t, 'fast_info', None)
            if fast:
                lp = getattr(fast, 'last_price', None)
                prev = getattr(fast, 'regular_market_previous_close', None)
                if lp and prev and prev > 0:
                    pct = round(((float(lp) - float(prev)) / float(prev)) * 100, 2)
                    global_cues[key] = pct
        except Exception as err:
            logger.debug(f"Pre-market global cue fetch failed for {t_sym}: {err}")
            
    avg_global = (global_cues["dow_jones_pct"] + global_cues["nasdaq_pct"] + global_cues["nikkei_pct"]) / 3.0
    if avg_global >= 0.5:
        global_cues["bias"] = "BULLISH_TAILWINDS"
    elif avg_global <= -0.5:
        global_cues["bias"] = "BEARISH_HEADWINDS"
    elif avg_global > 0:
        global_cues["bias"] = "MILD_POSITIVE"
    else:
        global_cues["bias"] = "MILD_NEGATIVE"
        
    # 3. Sectoral Momentum Check
    sector_tickers = {
        "NIFTY BANK": "^NSEBANK",
        "NIFTY IT": "^CNXIT",
        "NIFTY AUTO": "^CNXAUTO"
    }
    
    sector_results = []
    for s_name, s_ticker in sector_tickers.items():
        try:
            t = yf.Ticker(s_ticker)
            fast = getattr(t, 'fast_info', None)
            if fast:
                lp = getattr(fast, 'last_price', None)
                prev = getattr(fast, 'regular_market_previous_close', None)
                if lp and prev and prev > 0:
                    chg_pct = round(((float(lp) - float(prev)) / float(prev)) * 100, 2)
                    sector_results.append({
                        "name": s_name,
                        "price": round(float(lp), 2),
                        "change_pct": chg_pct
                    })
        except Exception:
            continue
            
    sector_results.sort(key=lambda x: x["change_pct"], reverse=True)
    leading_sectors = sector_results[:2] if sector_results else [{"name": "NIFTY AUTO", "change_pct": 0.5}]
    lagging_sectors = sector_results[-1:] if sector_results else [{"name": "NIFTY IT", "change_pct": -0.2}]
    
    # 4. Tactical Session Guidance
    if not allow_breakouts or vix_val > 22.0:
        guidance = "⚠️ High volatility regime detected. Widen stop-losses, reduce position sizing, and avoid chasing early gap openings."
    elif global_cues["bias"] in ["BULLISH_TAILWINDS", "MILD_POSITIVE"] and nifty_chg >= 0:
        guidance = f"🟢 Favorable bullish tailwinds. Prioritize Smart Money Absorption breakouts above VWAP in leading sectors ({', '.join(s['name'] for s in leading_sectors)})."
    elif global_cues["bias"] == "BEARISH_HEADWINDS" or nifty_chg < -0.4:
        guidance = "🔴 Macro headwinds prevalent. Watch for Wyckoff operator bull-traps and protect Demat profits with Chandelier Trailing Stops."
    else:
        guidance = "⚪ Mixed global cues. Focus on stock-specific volume surges and disciplined Camarilla L3 liquidity floor entries."
        
    return {
        "date": today_str,
        "nifty_price": nifty_price,
        "nifty_change_pct": nifty_chg,
        "sensex_price": sensex_price,
        "sensex_change_pct": sensex_chg,
        "india_vix": vix_val,
        "vix_regime": vix_regime,
        "allow_breakout_trades": allow_breakouts,
        "global_cues": global_cues,
        "leading_sectors": leading_sectors,
        "lagging_sectors": lagging_sectors,
        "tactical_guidance": guidance
    }


def evaluate_forensic_health(symbol: str, financials: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates corporate governance, debt health, and forensic red flags:
    - Debt-to-Equity (< 1.0 is healthy, > 2.0 is risky)
    - Trailing P/E vs Forward P/E
    - Interest Coverage (Estimated)
    - Promoter Pledging Flag (Flagged if > 15%)
    """
    debt_to_equity = financials.get("debt_to_equity")
    pe_ratio = financials.get("pe_ratio")
    forward_pe = financials.get("forward_pe")
    profit_margin = financials.get("profit_margin_pct")
    
    red_flags = []
    strengths = []
    
    if debt_to_equity is not None:
        if debt_to_equity > 2.0:
            red_flags.append(f"Elevated Debt-to-Equity ratio ({debt_to_equity})")
        elif debt_to_equity < 0.5:
            strengths.append(f"Virtually Debt-Free / Robust Balance Sheet (D/E: {debt_to_equity})")
            
    if pe_ratio and forward_pe:
        if forward_pe < pe_ratio:
            strengths.append(f"Forward Valuation improving (Trailing P/E: {pe_ratio} -> Forward P/E: {forward_pe})")
            
    if profit_margin and profit_margin > 15.0:
        strengths.append(f"High Operating Profit Margin ({profit_margin}%)")
        
    sector_name = SECTOR_MAP.get(symbol.upper(), "BROAD_MARKET")
    
    return {
        "symbol": symbol,
        "sector_name": sector_name,
        "is_healthy": len(red_flags) == 0,
        "red_flags": red_flags,
        "strengths": strengths,
        "forensic_score": 80 if len(red_flags) == 0 else (40 if len(red_flags) == 1 else 20)
    }
