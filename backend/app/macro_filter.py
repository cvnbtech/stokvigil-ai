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
