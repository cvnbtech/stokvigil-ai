import logging
import yfinance as yf
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

logger = logging.getLogger("stokvigil.technical_engine")

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculates Relative Strength Index (RSI) using Wilder's Smoothing."""
    if len(series) < period + 1:
        return pd.Series([50.0] * len(series), index=series.index)
        
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)

def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
    """Calculates Moving Average Convergence Divergence (MACD)."""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return {
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram
    }

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculates Average True Range (ATR) for volatility and stop-loss sizing."""
    if len(df) < period + 1:
        return pd.Series([0.0] * len(df), index=df.index)
        
    high = df['High']
    low = df['Low']
    close_prev = df['Close'].shift(1)
    
    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    return atr.fillna(0.0)

def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """Calculates Volume Weighted Average Price (VWAP) for intraday data."""
    if 'Volume' not in df.columns or df['Volume'].sum() == 0:
        return df['Close']
    
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    tp_vol = typical_price * df['Volume']
    cum_tp_vol = tp_vol.cumsum()
    cum_vol = df['Volume'].cumsum()
    vwap = cum_tp_vol / cum_vol.replace(0, np.nan)
    return vwap.fillna(df['Close'])

def detect_rsi_divergence(price_series: pd.Series, rsi_series: pd.Series, window: int = 10) -> str:
    """
    Detects regular Bullish and Bearish RSI Divergences.
    Bullish Divergence: Price Lower Low + RSI Higher Low (Strong Reversal Up)
    Bearish Divergence: Price Higher High + RSI Lower High (Strong Reversal Down)
    """
    if len(price_series) < window * 2:
        return "NONE"
        
    recent_price = price_series.iloc[-window:]
    prev_price = price_series.iloc[-window*2:-window]
    
    recent_rsi = rsi_series.iloc[-window:]
    prev_rsi = rsi_series.iloc[-window*2:-window]
    
    # Regular Bullish Divergence
    if recent_price.min() < prev_price.min() and recent_rsi.min() > prev_rsi.min() and recent_rsi.iloc[-1] < 45:
        return "BULLISH_REGULAR_DIVERGENCE"
        
    # Regular Bearish Divergence
    if recent_price.max() > prev_price.max() and recent_rsi.max() < prev_rsi.max() and recent_rsi.iloc[-1] > 55:
        return "BEARISH_REGULAR_DIVERGENCE"
        
    return "NONE"

def fetch_multi_timeframe_technicals(symbol: str) -> Dict[str, Any]:
    """
    Fetches real-time multi-timeframe intraday (5m, 15m) and daily (1D) OHLCV data.
    Computes RSI, MACD, VWAP, ATR, EMAs, Volume surges, and Divergences.
    """
    ticker_sym = symbol if symbol.endswith(".NS") or symbol.endswith(".BO") else f"{symbol}.NS"
    
    default_res = {
        "symbol": symbol,
        "current_price": 0.0,
        "rsi_5m": 50.0,
        "rsi_15m": 50.0,
        "rsi_daily": 50.0,
        "rsi_divergence": "NONE",
        "macd_line": 0.0,
        "macd_signal": 0.0,
        "macd_histogram": 0.0,
        "macd_trend": "NEUTRAL",
        "vwap": 0.0,
        "price_vs_vwap_pct": 0.0,
        "ema_20": 0.0,
        "ema_50": 0.0,
        "ema_200": 0.0,
        "ma_trend": "NEUTRAL",
        "atr_14": 0.0,
        "volume_multiple": 1.0,
        "is_volume_surge": False,
        "technical_score": 50
    }

    try:
        ticker = yf.Ticker(ticker_sym)
        
        # 1. Fetch 5-Minute Intraday Data (Last 5 days)
        df_5m = ticker.history(period="5d", interval="5m")
        # 2. Fetch Daily Data (Last 1 year for 200 EMA & Daily RSI)
        df_daily = ticker.history(period="1y", interval="1d")
        
        if df_5m.empty:
            logger.warning(f"No 5m intraday data returned for {symbol}")
            return default_res
            
        current_price = round(float(df_5m['Close'].iloc[-1]), 2)
        
        # Calculate 5m Technicals
        rsi_5m_series = calculate_rsi(df_5m['Close'], 14)
        rsi_5m = round(float(rsi_5m_series.iloc[-1]), 2)
        
        macd_dict_5m = calculate_macd(df_5m['Close'], 12, 26, 9)
        macd_line = round(float(macd_dict_5m['macd'].iloc[-1]), 2)
        macd_signal = round(float(macd_dict_5m['signal'].iloc[-1]), 2)
        macd_hist = round(float(macd_dict_5m['histogram'].iloc[-1]), 2)
        prev_hist = float(macd_dict_5m['histogram'].iloc[-2]) if len(macd_dict_5m['histogram']) > 1 else macd_hist
        
        if macd_hist > 0 and prev_hist <= 0:
            macd_trend = "BULLISH_CROSSOVER"
        elif macd_hist < 0 and prev_hist >= 0:
            macd_trend = "BEARISH_CROSSOVER"
        elif macd_hist > 0 and macd_hist > prev_hist:
            macd_trend = "EXPANDING_BULLISH_MOMENTUM"
        elif macd_hist < 0 and macd_hist < prev_hist:
            macd_trend = "EXPANDING_BEARISH_MOMENTUM"
        else:
            macd_trend = "NEUTRAL"
            
        vwap_series = calculate_vwap(df_5m)
        vwap_val = round(float(vwap_series.iloc[-1]), 2)
        price_vs_vwap_pct = round(((current_price - vwap_val) / vwap_val) * 100, 2) if vwap_val > 0 else 0.0
        
        atr_series = calculate_atr(df_5m, 14)
        atr_val = round(float(atr_series.iloc[-1]), 2)
        if atr_val == 0.0:
            atr_val = round(current_price * 0.015, 2)
            
        # Volume Surge Check (vs 20-period Volume MA on 5m)
        vol_ma_20 = df_5m['Volume'].rolling(20).mean().iloc[-1]
        recent_vol = df_5m['Volume'].iloc[-1]
        volume_mult = round(float(recent_vol / vol_ma_20), 2) if vol_ma_20 > 0 else 1.0
        is_volume_surge = volume_mult >= 2.0
        
        # 15m Resampling for Multi-Timeframe Confirmation
        df_15m = df_5m.resample('15min').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        rsi_15m_series = calculate_rsi(df_15m['Close'], 14) if len(df_15m) >= 15 else rsi_5m_series
        rsi_15m = round(float(rsi_15m_series.iloc[-1]), 2)
        
        # RSI Divergence on 15m
        rsi_divergence = detect_rsi_divergence(df_15m['Close'], rsi_15m_series)
        
        # Daily Technicals (EMAs & Daily RSI)
        rsi_daily = 50.0
        ema_20 = current_price
        ema_50 = current_price
        ema_200 = current_price
        ma_trend = "NEUTRAL"
        
        if not df_daily.empty and len(df_daily) >= 50:
            rsi_d_series = calculate_rsi(df_daily['Close'], 14)
            rsi_daily = round(float(rsi_d_series.iloc[-1]), 2)
            
            ema_20 = round(float(df_daily['Close'].ewm(span=20, adjust=False).mean().iloc[-1]), 2)
            ema_50 = round(float(df_daily['Close'].ewm(span=50, adjust=False).mean().iloc[-1]), 2)
            if len(df_daily) >= 200:
                ema_200 = round(float(df_daily['Close'].ewm(span=200, adjust=False).mean().iloc[-1]), 2)
            else:
                ema_200 = ema_50
                
            if current_price > ema_20 and ema_20 > ema_50 and ema_50 > ema_200:
                ma_trend = "STRONG_BULLISH_ALIGNMENT"
            elif current_price < ema_20 and ema_20 < ema_50:
                ma_trend = "STRONG_BEARISH_ALIGNMENT"
            elif current_price > ema_200:
                ma_trend = "ABOVE_200_EMA"
            else:
                ma_trend = "BELOW_200_EMA"

        # Calculate Quantitative Technical Score (0 - 100)
        tech_score = 50
        if current_price > vwap_val:
            tech_score += 10
        else:
            tech_score -= 10
            
        if macd_trend in ["BULLISH_CROSSOVER", "EXPANDING_BULLISH_MOMENTUM"]:
            tech_score += 15
        elif macd_trend in ["BEARISH_CROSSOVER", "EXPANDING_BEARISH_MOMENTUM"]:
            tech_score -= 15
            
        if 50 <= rsi_15m <= 70:
            tech_score += 10
        elif rsi_15m > 75:
            tech_score -= 5 # Overbought caution
        elif rsi_15m < 30:
            tech_score -= 10
            
        if rsi_divergence == "BULLISH_REGULAR_DIVERGENCE":
            tech_score += 15
        elif rsi_divergence == "BEARISH_REGULAR_DIVERGENCE":
            tech_score -= 15
            
        if is_volume_surge and current_price > df_5m['Open'].iloc[-1]:
            tech_score += 15
            
        tech_score = max(5, min(95, tech_score))

        return {
            "symbol": symbol,
            "current_price": current_price,
            "rsi_5m": rsi_5m,
            "rsi_15m": rsi_15m,
            "rsi_daily": rsi_daily,
            "rsi_divergence": rsi_divergence,
            "macd_line": macd_line,
            "macd_signal": macd_signal,
            "macd_histogram": macd_hist,
            "macd_trend": macd_trend,
            "vwap": vwap_val,
            "price_vs_vwap_pct": price_vs_vwap_pct,
            "ema_20": ema_20,
            "ema_50": ema_50,
            "ema_200": ema_200,
            "ma_trend": ma_trend,
            "atr_14": atr_val,
            "volume_multiple": volume_mult,
            "is_volume_surge": is_volume_surge,
            "technical_score": tech_score
        }

    except Exception as e:
        logger.error(f"Error computing technical indicators for {symbol}: {e}")
        return default_res
