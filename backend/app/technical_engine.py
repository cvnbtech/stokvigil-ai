import logging
import concurrent.futures
import yfinance as yf
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

logger = logging.getLogger("stokvigil.technical_engine")

def _fetch_history_frame(sym: str, period: str, interval: str) -> pd.DataFrame:
    """Thread-isolated historical candle fetch using a dedicated yf.Ticker instance."""
    try:
        t = yf.Ticker(sym)
        return t.history(period=period, interval=interval)
    except Exception as e:
        logger.debug(f"Error fetching {period}/{interval} for {sym}: {e}")
        return pd.DataFrame()

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculates Relative Strength Index (RSI) using Wilder's Smoothing. Returns NaN if data is insufficient."""
    if len(series) < period + 1:
        return pd.Series([np.nan] * len(series), index=series.index)
        
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
    """Calculates Moving Average Convergence Divergence (MACD). Returns empty Series if insufficient bars."""
    if len(series) < slow:
        empty = pd.Series([np.nan] * len(series), index=series.index)
        return {"macd": empty, "signal": empty, "histogram": empty}
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
    """Calculates Average True Range (ATR) for volatility and stop-loss sizing. Returns NaN if insufficient bars."""
    if len(df) < period + 1:
        return pd.Series([np.nan] * len(df), index=df.index)
        
    high = df['High']
    low = df['Low']
    close_prev = df['Close'].shift(1)
    
    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    return atr

def calculate_vwap_bands(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculates Volume Weighted Average Price (VWAP) anchored to current trading day's session
    along with Volume-Weighted Standard Deviation Bands (+/- 1σ, +/- 2σ).
    Returns None if volume is zero or session data is unavailable.
    """
    if 'Volume' not in df.columns or df['Volume'].sum() == 0 or df.empty:
        return {
            "vwap": None,
            "vwap_upper_1s": None,
            "vwap_lower_1s": None,
            "vwap_upper_2s": None,
            "vwap_lower_2s": None,
            "vwap_series": pd.Series(dtype=float)
        }
    
    try:
        latest_date = df.index[-1].date()
        df_session = df[df.index.date == latest_date].copy()
        if df_session.empty or df_session['Volume'].sum() == 0:
            df_session = df.copy()
    except Exception:
        df_session = df.copy()

    typical_price = (df_session['High'] + df_session['Low'] + df_session['Close']) / 3.0
    tp_vol = typical_price * df_session['Volume']
    cum_tp_vol = tp_vol.cumsum()
    cum_vol = df_session['Volume'].cumsum()
    vwap_series = cum_tp_vol / cum_vol.replace(0, np.nan)
    
    # Calculate volume-weighted variance & standard deviation
    cum_var_num = (df_session['Volume'] * ((typical_price - vwap_series) ** 2)).cumsum()
    variance = cum_var_num / cum_vol.replace(0, np.nan)
    std_dev = np.sqrt(variance.fillna(0.0))
    
    curr_vwap = round(float(vwap_series.iloc[-1]), 2) if not vwap_series.empty and not pd.isna(vwap_series.iloc[-1]) else None
    curr_sd = round(float(std_dev.iloc[-1]), 2) if not std_dev.empty and not pd.isna(std_dev.iloc[-1]) else 0.0

    if curr_vwap is not None:
        return {
            "vwap": curr_vwap,
            "vwap_upper_1s": round(curr_vwap + curr_sd, 2),
            "vwap_lower_1s": round(max(0.01, curr_vwap - curr_sd), 2),
            "vwap_upper_2s": round(curr_vwap + (2.0 * curr_sd), 2),
            "vwap_lower_2s": round(max(0.01, curr_vwap - (2.0 * curr_sd)), 2),
            "vwap_series": vwap_series,
            "std_dev_series": std_dev
        }
    return {
        "vwap": None,
        "vwap_upper_1s": None,
        "vwap_lower_1s": None,
        "vwap_upper_2s": None,
        "vwap_lower_2s": None,
        "vwap_series": pd.Series(dtype=float),
        "std_dev_series": pd.Series(dtype=float)
    }

def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """Calculates Volume Weighted Average Price (VWAP) Series for backward compatibility."""
    bands = calculate_vwap_bands(df)
    series = bands.get("vwap_series")
    if series is not None and not series.empty:
        return series
    return df['Close'] if 'Close' in df.columns else pd.Series(dtype=float)

def calculate_ttm_squeeze(df: pd.DataFrame, bb_period: int = 20, bb_mult: float = 2.0, kc_period: int = 20, kc_mult: float = 1.5) -> Dict[str, Any]:
    """
    Calculates John Carter's TTM Squeeze indicator using Bollinger Bands and Keltner Channels.
    - Squeeze On: Bollinger Bands compress inside Keltner Channels (explosive volatility buildup).
    - Squeeze Release: Bollinger Bands break out of Keltner Channels.
    - Momentum: Linear regression / detrended momentum of price relative to 20-period midpoint.
    Returns DATA_INSUFFICIENT if bars < 25.
    """
    if len(df) < max(bb_period, kc_period) + 5:
        return {
            "squeeze_on": False,
            "squeeze_release": False,
            "squeeze_status": "DATA_INSUFFICIENT",
            "momentum_hist": None,
            "momentum_trend": None
        }

    try:
        close = df['Close']
        # 1. Bollinger Bands (20-period SMA +/- 2.0 * std)
        bb_basis = close.rolling(window=bb_period).mean()
        bb_std = close.rolling(window=bb_period).std()
        bb_upper = bb_basis + (bb_mult * bb_std)
        bb_lower = bb_basis - (bb_mult * bb_std)

        # 2. Keltner Channels (20-period EMA +/- 1.5 * ATR_14)
        kc_basis = close.ewm(span=kc_period, adjust=False).mean()
        atr_series = calculate_atr(df, 14)
        kc_upper = kc_basis + (kc_mult * atr_series)
        kc_lower = kc_basis - (kc_mult * atr_series)

        # Squeeze Condition: BB inside KC
        squeeze_series = (bb_upper < kc_upper) & (bb_lower > kc_lower)
        curr_squeeze_on = bool(squeeze_series.iloc[-1])
        prev_squeeze_on = bool(squeeze_series.iloc[-2]) if len(squeeze_series) > 1 else curr_squeeze_on
        curr_squeeze_release = bool(prev_squeeze_on and not curr_squeeze_on)

        # Momentum Histogram: Detrended price vs (Donchian Mid + SMA) / 2
        donchian_high = df['High'].rolling(window=kc_period).max()
        donchian_low = df['Low'].rolling(window=kc_period).min()
        midpoint = ((donchian_high + donchian_low) / 2.0 + bb_basis) / 2.0
        delta = close - midpoint
        
        mom_hist = delta.ewm(span=5, adjust=False).mean()
        curr_hist = round(float(mom_hist.iloc[-1]), 2)
        prev_hist = round(float(mom_hist.iloc[-2]), 2) if len(mom_hist) > 1 else curr_hist

        if curr_hist > prev_hist and curr_hist > 0:
            mom_trend = "EXPANDING_BULLISH"
        elif curr_hist <= prev_hist and curr_hist > 0:
            mom_trend = "CONTRACTING_BULLISH"
        elif curr_hist < prev_hist and curr_hist < 0:
            mom_trend = "EXPANDING_BEARISH"
        else:
            mom_trend = "CONTRACTING_BEARISH"

        if curr_squeeze_on:
            status = "SQUEEZE_ON"
        elif curr_squeeze_release:
            status = "SQUEEZE_RELEASE"
        else:
            status = "NO_SQUEEZE"

        return {
            "squeeze_on": curr_squeeze_on,
            "squeeze_release": curr_squeeze_release,
            "squeeze_status": status,
            "momentum_hist": curr_hist,
            "momentum_trend": mom_trend
        }
    except Exception as e:
        logger.warning(f"TTM Squeeze calculation fallback: {e}")
        return {
            "squeeze_on": False,
            "squeeze_release": False,
            "squeeze_status": "DATA_INSUFFICIENT",
            "momentum_hist": None,
            "momentum_trend": None
        }

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

def calculate_adx(df: pd.DataFrame, period: int = 14) -> Dict[str, Any]:
    """
    Calculates 14-period Wilder's Average Directional Index (ADX).
    Quantifies trend strength to eliminate false breakouts in choppy, range-bound markets.
    Returns None if data is insufficient.
    """
    default_adx = {"adx_14": None, "plus_di": None, "minus_di": None, "adx_regime": "DATA_INSUFFICIENT"}
    if len(df) < period + 5:
        return default_adx

    try:
        high = df['High']
        low = df['Low']
        close = df['Close']
        prev_close = close.shift(1)

        # True Range
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Directional Movement
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

        plus_dm_series = pd.Series(plus_dm, index=df.index)
        minus_dm_series = pd.Series(minus_dm, index=df.index)

        # Wilder's Smoothing
        tr_smooth = tr.ewm(alpha=1.0 / period, adjust=False).mean()
        plus_dm_smooth = plus_dm_series.ewm(alpha=1.0 / period, adjust=False).mean()
        minus_dm_smooth = minus_dm_series.ewm(alpha=1.0 / period, adjust=False).mean()

        plus_di = (plus_dm_smooth / tr_smooth.replace(0, np.nan) * 100).fillna(0.0)
        minus_di = (minus_dm_smooth / tr_smooth.replace(0, np.nan) * 100).fillna(0.0)

        di_sum = plus_di + minus_di
        dx = ((plus_di - minus_di).abs() / di_sum.replace(0, np.nan) * 100).fillna(0.0)
        adx = dx.ewm(alpha=1.0 / period, adjust=False).mean()

        adx_val = round(float(adx.iloc[-1]), 2)
        plus_di_val = round(float(plus_di.iloc[-1]), 2)
        minus_di_val = round(float(minus_di.iloc[-1]), 2)

        if adx_val >= 25.0:
            regime = "STRONG_TREND"
        elif adx_val >= 20.0:
            regime = "MODERATE_TREND"
        else:
            regime = "CHOPPY_SIDEWAYS"

        return {
            "adx_14": adx_val,
            "plus_di": plus_di_val,
            "minus_di": minus_di_val,
            "adx_regime": regime
        }
    except Exception as e:
        logger.warning(f"ADX calculation fallback: {e}")
        return default_adx

def calculate_camarilla_pivots(df_daily: pd.DataFrame) -> Dict[str, Optional[float]]:
    """
    Computes Camarilla Equation Institutional Pivots from the prior completed daily session.
    Provides mathematical floors (L3, L4) and ceilings (H3, H4) watched by institutional order books.
    Returns None values if data is unavailable.
    """
    default_pivots = {"h4": None, "h3": None, "l3": None, "l4": None}
    if len(df_daily) < 1:
        return default_pivots

    try:
        ref_row = df_daily.iloc[-2] if len(df_daily) >= 2 else df_daily.iloc[-1]
        h = float(ref_row['High'])
        l = float(ref_row['Low'])
        c = float(ref_row['Close'])
        rng = h - l

        if rng <= 0 or pd.isna(rng):
            return default_pivots

        h4 = round(c + (rng * 1.1 / 2.0), 2)
        h3 = round(c + (rng * 1.1 / 4.0), 2)
        l3 = round(c - (rng * 1.1 / 4.0), 2)
        l4 = round(c - (rng * 1.1 / 2.0), 2)

        return {"h4": h4, "h3": h3, "l3": l3, "l4": l4}
    except Exception as e:
        logger.warning(f"Camarilla pivots calculation fallback: {e}")
        return default_pivots

def calculate_relative_strength(df_daily: pd.DataFrame, nifty_20d_ret: float = 1.0) -> Dict[str, Any]:
    """
    Computes Mansfield Relative Strength (RS vs NIFTY 50) over a 20-trading-day window.
    Returns None if fewer than 20 daily bars exist.
    """
    default_rs = {"rs_rating": None, "rs_regime": "DATA_INSUFFICIENT"}
    if len(df_daily) < 20:
        return default_rs

    try:
        p_now = float(df_daily['Close'].iloc[-1])
        p_20d = float(df_daily['Close'].iloc[-20])
        if p_20d <= 0 or pd.isna(p_now) or pd.isna(p_20d):
            return default_rs

        stock_20d_ret = ((p_now - p_20d) / p_20d) * 100.0
        delta_rs = round(stock_20d_ret - nifty_20d_ret, 2)

        if delta_rs >= 3.0:
            regime = "OUTPERFORMING_LEADER"
        elif delta_rs <= -3.0:
            regime = "UNDERPERFORMING_LAGGARD"
        else:
            regime = "IN_LINE"

        return {"rs_rating": delta_rs, "rs_regime": regime}
    except Exception as e:
        logger.warning(f"Relative Strength calculation fallback: {e}")
        return default_rs

def fetch_multi_timeframe_technicals(symbol: str) -> Dict[str, Any]:
    """
    Fetches real-time multi-timeframe intraday (5m, 15m) and daily (1D) OHLCV data.
    Computes RSI, MACD, VWAP Bands, ATR, TTM Squeeze, EMAs, Volume surges, and Divergences.
    Returns None for any indicator where data cannot be accurately calculated.
    """
    clean_sym = symbol.strip()
    if clean_sym.endswith(".NS") or clean_sym.endswith(".BO"):
        ticker_sym = clean_sym
    elif clean_sym.isdigit() and len(clean_sym) == 6:
        ticker_sym = f"{clean_sym}.BO"
    else:
        ticker_sym = f"{clean_sym}.NS"
    
    default_res = {
        "symbol": symbol,
        "current_price": None,
        "rsi_5m": None,
        "rsi_15m": None,
        "rsi_daily": None,
        "rsi_divergence": "NONE",
        "macd_line": None,
        "macd_signal": None,
        "macd_histogram": None,
        "macd_trend": "NEUTRAL",
        "vwap": None,
        "vwap_upper_1s": None,
        "vwap_lower_1s": None,
        "vwap_upper_2s": None,
        "vwap_lower_2s": None,
        "price_vs_vwap_pct": None,
        "ema_20": None,
        "ema_50": None,
        "ema_200": None,
        "ma_trend": "NEUTRAL",
        "atr_14": None,
        "adx_14": None,
        "adx_regime": "DATA_INSUFFICIENT",
        "camarilla_pivots": {"h4": None, "h3": None, "l3": None, "l4": None},
        "rs_rating": None,
        "rs_regime": "DATA_INSUFFICIENT",
        "ttm_squeeze": {
            "squeeze_on": False,
            "squeeze_release": False,
            "squeeze_status": "DATA_INSUFFICIENT",
            "momentum_hist": None,
            "momentum_trend": None
        },
        "volume_multiple": None,
        "is_volume_surge": False,
        "technical_score": 50
    }

    try:
        # 1 & 2. Concurrently fetch 5-minute intraday and 1-year daily candles in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            fut_5m = executor.submit(_fetch_history_frame, ticker_sym, "5d", "5m")
            fut_daily = executor.submit(_fetch_history_frame, ticker_sym, "1y", "1d")
            df_5m = fut_5m.result()
            df_daily = fut_daily.result()
        
        # Fallback to BSE (.BO) if NSE returned no data and ticker was not already .BO
        if df_5m.empty and not ticker_sym.endswith(".BO"):
            clean_ticker = symbol.replace(".NS", "").strip()
            bse_sym = f"{clean_ticker}.BO"
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    fut_5m_bse = executor.submit(_fetch_history_frame, bse_sym, "5d", "5m")
                    fut_daily_bse = executor.submit(_fetch_history_frame, bse_sym, "1y", "1d")
                    df_5m_bse = fut_5m_bse.result()
                    df_daily_bse = fut_daily_bse.result()
                if not df_5m_bse.empty:
                    df_5m = df_5m_bse
                    df_daily = df_daily_bse
                    ticker_sym = bse_sym
                    logger.info(f"Resolved {symbol} via BSE exchange ({bse_sym})")
            except Exception as e:
                logger.debug(f"BSE fallback failed for {symbol}: {e}")

        if df_5m.empty:
            if not df_daily.empty:
                logger.info(f"No 5m intraday data for {symbol}; synthesizing technical metrics from daily candles ({len(df_daily)} bars)")
                current_price = round(float(df_daily['Close'].iloc[-1]), 2)
                atr_series = calculate_atr(df_daily, 14)
                atr_val = round(float(atr_series.iloc[-1]), 2) if not atr_series.empty and not pd.isna(atr_series.iloc[-1]) else None
                
                rsi_d_series = calculate_rsi(df_daily['Close'], 14)
                rsi_daily = round(float(rsi_d_series.iloc[-1]), 2) if not rsi_d_series.empty and not pd.isna(rsi_d_series.iloc[-1]) else None
                
                ema_20 = round(float(df_daily['Close'].ewm(span=20, adjust=False).mean().iloc[-1]), 2) if len(df_daily) >= 20 else None
                ema_50 = round(float(df_daily['Close'].ewm(span=50, adjust=False).mean().iloc[-1]), 2) if len(df_daily) >= 50 else None
                ema_200 = round(float(df_daily['Close'].ewm(span=200, adjust=False).mean().iloc[-1]), 2) if len(df_daily) >= 200 else None
                
                if ema_20 and ema_50 and ema_200:
                    if current_price > ema_20 and ema_20 > ema_50 and ema_50 > ema_200:
                        ma_trend = "STRONG_BULLISH_ALIGNMENT"
                    elif current_price < ema_20 and ema_20 < ema_50:
                        ma_trend = "STRONG_BEARISH_ALIGNMENT"
                    elif current_price > ema_200:
                        ma_trend = "ABOVE_200_EMA"
                    else:
                        ma_trend = "BELOW_200_EMA"
                else:
                    ma_trend = "NEUTRAL"
                
                camarilla_pivots = calculate_camarilla_pivots(df_daily)
                rs_dict = calculate_relative_strength(df_daily)
                adx_dict = calculate_adx(df_daily, 14)
                ttm_squeeze = calculate_ttm_squeeze(df_daily)
                
                tech_score = 50
                if ema_50:
                    tech_score += 10 if current_price > ema_50 else -10
                if rsi_daily is not None:
                    if 50 <= rsi_daily <= 70:
                        tech_score += 10
                    elif rsi_daily < 35:
                        tech_score -= 10
                if rs_dict.get("rs_regime") == "OUTPERFORMING_LEADER":
                    tech_score += 5
                elif rs_dict.get("rs_regime") == "UNDERPERFORMING_LAGGARD":
                    tech_score -= 5
                tech_score = max(5, min(95, tech_score))
                
                return {
                    "symbol": symbol,
                    "current_price": current_price,
                    "rsi_5m": None,
                    "rsi_15m": None,
                    "rsi_daily": rsi_daily,
                    "rsi_divergence": "NONE",
                    "macd_line": None,
                    "macd_signal": None,
                    "macd_histogram": None,
                    "macd_trend": "NEUTRAL",
                    "vwap": None,
                    "vwap_upper_1s": None,
                    "vwap_lower_1s": None,
                    "vwap_upper_2s": None,
                    "vwap_lower_2s": None,
                    "price_vs_vwap_pct": None,
                    "ema_20": ema_20,
                    "ema_50": ema_50,
                    "ema_200": ema_200,
                    "ma_trend": ma_trend,
                    "atr_14": atr_val,
                    "adx_14": adx_dict.get("adx_14"),
                    "adx_regime": adx_dict.get("adx_regime", "DATA_INSUFFICIENT"),
                    "camarilla_pivots": camarilla_pivots,
                    "rs_rating": rs_dict.get("rs_rating"),
                    "rs_regime": rs_dict.get("rs_regime", "DATA_INSUFFICIENT"),
                    "ttm_squeeze": ttm_squeeze,
                    "volume_multiple": None,
                    "is_volume_surge": False,
                    "technical_score": tech_score
                }
            else:
                logger.warning(f"No 5m intraday or daily data returned for {symbol} (checked NSE & BSE)")
                return default_res
            
        current_price = round(float(df_5m['Close'].iloc[-1]), 2)
        
        # Calculate 5m Technicals
        rsi_5m_series = calculate_rsi(df_5m['Close'], 14)
        rsi_5m = round(float(rsi_5m_series.iloc[-1]), 2) if not rsi_5m_series.empty and not pd.isna(rsi_5m_series.iloc[-1]) else None
        
        macd_dict_5m = calculate_macd(df_5m['Close'], 12, 26, 9)
        macd_line = round(float(macd_dict_5m['macd'].iloc[-1]), 2) if not macd_dict_5m['macd'].empty and not pd.isna(macd_dict_5m['macd'].iloc[-1]) else None
        macd_signal = round(float(macd_dict_5m['signal'].iloc[-1]), 2) if not macd_dict_5m['signal'].empty and not pd.isna(macd_dict_5m['signal'].iloc[-1]) else None
        macd_hist = round(float(macd_dict_5m['histogram'].iloc[-1]), 2) if not macd_dict_5m['histogram'].empty and not pd.isna(macd_dict_5m['histogram'].iloc[-1]) else None
        
        if macd_hist is not None and len(macd_dict_5m['histogram']) > 1:
            prev_hist = float(macd_dict_5m['histogram'].iloc[-2])
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
        else:
            macd_trend = "NEUTRAL"
            
        vwap_bands = calculate_vwap_bands(df_5m)
        vwap_val = vwap_bands.get("vwap")
        vwap_upper_1s = vwap_bands.get("vwap_upper_1s")
        vwap_lower_1s = vwap_bands.get("vwap_lower_1s")
        vwap_upper_2s = vwap_bands.get("vwap_upper_2s")
        vwap_lower_2s = vwap_bands.get("vwap_lower_2s")
        price_vs_vwap_pct = round(((current_price - vwap_val) / vwap_val) * 100, 2) if vwap_val is not None and vwap_val > 0 else None
        
        atr_series = calculate_atr(df_5m, 14)
        atr_val = round(float(atr_series.iloc[-1]), 2) if not atr_series.empty and not pd.isna(atr_series.iloc[-1]) else None
            
        # Volume Surge Check (vs 20-period Volume MA on 5m)
        is_volume_surge = False
        volume_mult = None
        if 'Volume' in df_5m.columns and len(df_5m) >= 20:
            vol_ma_20 = float(df_5m['Volume'].rolling(20).mean().iloc[-1])
            recent_vol = float(df_5m['Volume'].iloc[-1])
            if vol_ma_20 > 0:
                volume_mult = round(recent_vol / vol_ma_20, 2)
                is_volume_surge = (volume_mult >= 2.0)
        
        # 15m Resampling for Multi-Timeframe Confirmation
        df_15m = df_5m.resample('15min').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        
        if len(df_15m) >= 15:
            rsi_15m_series = calculate_rsi(df_15m['Close'], 14)
            rsi_15m = round(float(rsi_15m_series.iloc[-1]), 2) if not rsi_15m_series.empty and not pd.isna(rsi_15m_series.iloc[-1]) else None
            rsi_divergence = detect_rsi_divergence(df_15m['Close'], rsi_15m_series)
        else:
            rsi_15m = rsi_5m
            rsi_divergence = "NONE"
        
        # 14-period Wilder's ADX Trend Strength
        adx_dict = calculate_adx(df_15m if len(df_15m) >= 20 else df_5m, 14)
        adx_14 = adx_dict["adx_14"]
        adx_regime = adx_dict["adx_regime"]

        # TTM Volatility Squeeze Engine
        ttm_squeeze = calculate_ttm_squeeze(df_15m if len(df_15m) >= 25 else df_5m)

        # Daily Technicals (EMAs & Daily RSI)
        rsi_daily = None
        ema_20 = None
        ema_50 = None
        ema_200 = None
        ma_trend = "NEUTRAL"
        
        if not df_daily.empty and len(df_daily) >= 20:
            rsi_d_series = calculate_rsi(df_daily['Close'], 14)
            rsi_daily = round(float(rsi_d_series.iloc[-1]), 2) if not rsi_d_series.empty and not pd.isna(rsi_d_series.iloc[-1]) else None
            
            ema_20 = round(float(df_daily['Close'].ewm(span=20, adjust=False).mean().iloc[-1]), 2)
            if len(df_daily) >= 50:
                ema_50 = round(float(df_daily['Close'].ewm(span=50, adjust=False).mean().iloc[-1]), 2)
            if len(df_daily) >= 200:
                ema_200 = round(float(df_daily['Close'].ewm(span=200, adjust=False).mean().iloc[-1]), 2)
                
            if ema_20 and ema_50 and ema_200:
                if current_price > ema_20 and ema_20 > ema_50 and ema_50 > ema_200:
                    ma_trend = "STRONG_BULLISH_ALIGNMENT"
                elif current_price < ema_20 and ema_20 < ema_50:
                    ma_trend = "STRONG_BEARISH_ALIGNMENT"
                elif current_price > ema_200:
                    ma_trend = "ABOVE_200_EMA"
                else:
                    ma_trend = "BELOW_200_EMA"

        # Camarilla Institutional Pivots & Relative Strength vs NIFTY
        camarilla_pivots = calculate_camarilla_pivots(df_daily)
        rs_dict = calculate_relative_strength(df_daily)
        rs_rating = rs_dict["rs_rating"]
        rs_regime = rs_dict["rs_regime"]

        # Calculate Quantitative Technical Score (0 - 100)
        tech_score = 50
        if vwap_val is not None:
            tech_score += 10 if current_price > vwap_val else -10
            
        if macd_trend in ["BULLISH_CROSSOVER", "EXPANDING_BULLISH_MOMENTUM"]:
            tech_score += 15
        elif macd_trend in ["BEARISH_CROSSOVER", "EXPANDING_BEARISH_MOMENTUM"]:
            tech_score -= 15
            
        if rsi_15m is not None:
            if 50 <= rsi_15m <= 70:
                tech_score += 10
            elif rsi_15m > 75:
                tech_score -= 5
            elif rsi_15m < 30:
                tech_score -= 10
            
        if rsi_divergence == "BULLISH_REGULAR_DIVERGENCE":
            tech_score += 15
        elif rsi_divergence == "BEARISH_REGULAR_DIVERGENCE":
            tech_score -= 15
            
        if is_volume_surge and current_price > df_5m['Open'].iloc[-1]:
            tech_score += 15

        # TTM Squeeze Release bonus / Squeeze compression notice
        if ttm_squeeze.get("squeeze_release") and ttm_squeeze.get("momentum_trend") in ["EXPANDING_BULLISH", "CONTRACTING_BEARISH"]:
            tech_score += 8
        elif ttm_squeeze.get("squeeze_on"):
            tech_score += 3  # Coiling setup

        # ADX Trend Strength bonus / chop penalty
        if adx_regime == "STRONG_TREND":
            tech_score += 5
        elif adx_regime == "CHOPPY_SIDEWAYS":
            tech_score -= 8

        # Relative Strength market leadership bonus / laggard penalty
        if rs_regime == "OUTPERFORMING_LEADER":
            tech_score += 5
        elif rs_regime == "UNDERPERFORMING_LAGGARD":
            tech_score -= 5
            
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
            "vwap_upper_1s": vwap_upper_1s,
            "vwap_lower_1s": vwap_lower_1s,
            "vwap_upper_2s": vwap_upper_2s,
            "vwap_lower_2s": vwap_lower_2s,
            "price_vs_vwap_pct": price_vs_vwap_pct,
            "ema_20": ema_20,
            "ema_50": ema_50,
            "ema_200": ema_200,
            "ma_trend": ma_trend,
            "atr_14": atr_val,
            "adx_14": adx_14,
            "adx_regime": adx_regime,
            "camarilla_pivots": camarilla_pivots,
            "rs_rating": rs_rating,
            "rs_regime": rs_regime,
            "ttm_squeeze": ttm_squeeze,
            "volume_multiple": volume_mult,
            "is_volume_surge": is_volume_surge,
            "technical_score": tech_score
        }

    except Exception as e:
        logger.error(f"Error computing technical indicators for {symbol}: {e}")
        return default_res
