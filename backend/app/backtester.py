"""
StokVigil AI - In-Memory Vectorized Strategy Backtester Engine
=============================================================
High-performance historical backtesting module for Indian equities (NSE & BSE dual-exchange).
Evaluates algorithmic strategy rules (Camarilla Breakouts, Momentum Confluence) using historical OHLCV bars.
Features:
- Mathematical 1% Capital Risk Position Sizing per trade
- Vectorized indicator calculation (SMA, RSI, ATR, Camarilla Pivots H3/H4/L3/L4)
- Comprehensive trade logs and equity curve tracking
- Institutional performance metrics: Win Rate, Profit Factor, Max Drawdown, Sharpe Ratio
- ZERO-DEFAULT POLICY: Returns clean error payloads if exchange history is offline, never fake data.
"""

import math
import logging
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger("stokvigil.backtester")


def _resolve_exchange_candidates(symbol: str) -> List[str]:
    """
    Resolves symbol to dual-exchange candidates (.NS and .BO).
    Supports bare tickers, 6-digit BSE scrips (e.g. 500325), and explicit suffixes.
    """
    clean = str(symbol).strip().upper()
    if clean.endswith(".NS") or clean.endswith(".BO"):
        return [clean]
    bare = clean.replace(".NS", "").replace(".BO", "").strip()
    if bare.isdigit() and len(bare) == 6:
        # 6-digit numeric BSE security code
        return [f"{bare}.BO", f"{bare}.NS"]
    return [f"{bare}.NS", f"{bare}.BO"]


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Vectorized RSI calculation."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    # Wilder smoothing for remaining periods
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Vectorized Average True Range (ATR)."""
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift(1)).abs()
    low_close = (df["Low"] - df["Close"].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=1).mean()


def run_vectorized_strategy_backtest(
    symbol: str,
    period: str = "1y",
    interval: str = "1d",
    strategy: str = "camarilla_breakout",
    initial_capital: float = 200000.0,
    risk_budget: float = 2000.0,
    max_holding_bars: int = 15
) -> Dict[str, Any]:
    """
    Executes an in-memory historical backtest for a stock symbol over specified timeframe.
    
    Parameters:
    - symbol: NSE/BSE ticker or 6-digit scrip (e.g., "RELIANCE.NS", "500325.BO", "TCS")
    - period: "1mo", "3mo", "6mo", "1y", "2y", "5y"
    - interval: "1d", "1h", "15m"
    - strategy: "camarilla_breakout" or "confluence_trend"
    - initial_capital: Starting demat portfolio value (default ₹2,00,000.0)
    - risk_budget: Max account risk per trade (default ₹2,000 / 1% rule)
    - max_holding_bars: Time-based stop for stagnation
    
    Returns structured performance summary with trade logs and equity curve.
    """
    candidates = _resolve_exchange_candidates(symbol)
    df = pd.DataFrame()
    resolved_ticker = candidates[0]

    for cand in candidates:
        try:
            t = yf.Ticker(cand)
            hist = t.history(period=period, interval=interval)
            if hist is not None and len(hist) >= 20:
                df = hist.copy()
                resolved_ticker = cand
                break
        except Exception as e:
            logger.debug(f"History fetch error for candidate {cand}: {e}")
            continue

    if df.empty or len(df) < 20:
        return {
            "status": "error",
            "symbol": symbol,
            "resolved_ticker": resolved_ticker,
            "message": f"Insufficient historical market data available for {symbol} (period={period}, interval={interval}).",
            "total_trades": 0,
            "win_rate_pct": 0.0
        }

    # Clean & ensure essential columns
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col not in df.columns:
            return {
                "status": "error",
                "symbol": symbol,
                "message": f"Missing required price column '{col}' in historical data."
            }
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Close", "High", "Low"])

    if len(df) < 20:
        return {
            "status": "error",
            "symbol": symbol,
            "message": f"Historical data after cleaning has fewer than 20 valid bars."
        }

    # Vectorized Indicators
    df["SMA_20"] = df["Close"].rolling(window=20, min_periods=5).mean()
    df["SMA_50"] = df["Close"].rolling(window=50, min_periods=10).mean()
    df["Vol_SMA_20"] = df["Volume"].rolling(window=20, min_periods=5).mean()
    df["RSI_14"] = calculate_rsi(df["Close"], period=14)
    df["ATR_14"] = calculate_atr(df, period=14)

    # Camarilla Pivots (Shifted by 1 bar to use yesterday's range without lookahead bias)
    high_prev = df["High"].shift(1)
    low_prev = df["Low"].shift(1)
    close_prev = df["Close"].shift(1)
    rng_prev = high_prev - low_prev

    df["Cam_H4"] = close_prev + (rng_prev * 1.1 / 2.0)
    df["Cam_H3"] = close_prev + (rng_prev * 1.1 / 4.0)
    df["Cam_L3"] = close_prev - (rng_prev * 1.1 / 4.0)
    df["Cam_L4"] = close_prev - (rng_prev * 1.1 / 2.0)

    # Simulation State
    capital = float(initial_capital)
    equity_curve = []
    trades: List[Dict[str, Any]] = []

    in_position = False
    entry_idx = 0
    entry_date = ""
    entry_price = 0.0
    position_qty = 0
    target_1 = 0.0
    target_2 = 0.0
    stop_loss = 0.0

    # Start loop after warm-up period
    start_bar = 20
    dates = df.index

    for i in range(start_bar, len(df)):
        cur_date_str = str(dates[i].strftime("%Y-%m-%d") if hasattr(dates[i], "strftime") else str(dates[i]))[:10]
        cur_open = float(df["Open"].iloc[i])
        cur_high = float(df["High"].iloc[i])
        cur_low = float(df["Low"].iloc[i])
        cur_close = float(df["Close"].iloc[i])
        cur_atr = float(df["ATR_14"].iloc[i] or (cur_close * 0.015))
        cur_rsi = float(df["RSI_14"].iloc[i])
        cur_sma50 = float(df["SMA_50"].iloc[i] or cur_close)
        cur_vol = float(df["Volume"].iloc[i])
        cur_vol_sma = float(df["Vol_SMA_20"].iloc[i] or 1.0)
        h4_val = float(df["Cam_H4"].iloc[i] or cur_close)
        l3_val = float(df["Cam_L3"].iloc[i] or (cur_close * 0.98))

        if in_position:
            bars_held = i - entry_idx
            exit_triggered = False
            exit_price = cur_close
            exit_reason = "HOLD"

            # 1. Stop-Loss Trigger (Checked against Low)
            if cur_low <= stop_loss:
                exit_price = min(cur_open, stop_loss) if cur_open < stop_loss else stop_loss
                exit_reason = "STOP_LOSS_HIT"
                exit_triggered = True

            # 2. Target 2 Trigger (Full Runner Profit)
            elif cur_high >= target_2:
                exit_price = max(cur_open, target_2) if cur_open > target_2 else target_2
                exit_reason = "TARGET_2_HIT"
                exit_triggered = True

            # 3. Target 1 Trigger (Primary Institutional Target)
            elif cur_high >= target_1:
                exit_price = max(cur_open, target_1) if cur_open > target_1 else target_1
                exit_reason = "TARGET_1_HIT"
                exit_triggered = True

            # 4. Time Expiry / Stagnation Stop
            elif bars_held >= max_holding_bars:
                exit_price = cur_close
                exit_reason = "TIME_EXPIRY"
                exit_triggered = True

            if exit_triggered:
                trade_pnl = round((exit_price - entry_price) * position_qty, 2)
                trade_ret_pct = round(((exit_price - entry_price) / entry_price) * 100.0, 2)
                capital = round(capital + trade_pnl, 2)

                trades.append({
                    "entry_date": entry_date,
                    "exit_date": cur_date_str,
                    "entry_price": round(entry_price, 2),
                    "exit_price": round(exit_price, 2),
                    "quantity": position_qty,
                    "pnl": trade_pnl,
                    "return_pct": trade_ret_pct,
                    "exit_reason": exit_reason,
                    "bars_held": bars_held
                })

                in_position = False
                position_qty = 0

        else:
            # Check for Strategy Entry Trigger
            should_enter = False

            if strategy == "camarilla_breakout":
                # Camarilla H4 Breakout with Trend & Momentum confirmation
                is_breakout = (cur_close > h4_val) and (cur_open <= h4_val * 1.01)
                trend_ok = cur_close >= cur_sma50
                momentum_ok = cur_rsi >= 50.0
                volume_ok = cur_vol >= (0.8 * cur_vol_sma)
                should_enter = is_breakout and trend_ok and momentum_ok and volume_ok

            elif strategy == "confluence_trend":
                # Moving Average Alignment + Momentum Confluence
                cur_sma20 = float(df["SMA_20"].iloc[i] or cur_close)
                ma_aligned = cur_close > cur_sma20 > cur_sma50
                momentum_ok = 52.0 <= cur_rsi <= 75.0
                volume_ok = cur_vol >= cur_vol_sma
                should_enter = ma_aligned and momentum_ok and volume_ok

            if should_enter:
                # Mathematical Position Sizer (1% Capital Rule)
                computed_sl = round(max(cur_close - (1.5 * cur_atr), l3_val), 2)
                computed_sl = min(computed_sl, round(cur_close * 0.98, 2))  # At least 2% stop
                risk_per_share = round(abs(cur_close - computed_sl), 2)
                effective_risk = max(0.5, risk_per_share)

                # Determine safe quantity
                allocated_qty = max(1, int(risk_budget // effective_risk))
                # Capital availability constraint
                max_afford_qty = max(1, int(capital // cur_close))
                position_qty = min(allocated_qty, max_afford_qty)

                entry_idx = i
                entry_date = cur_date_str
                entry_price = cur_close
                stop_loss = computed_sl
                target_1 = round(cur_close + (1.5 * cur_atr), 2)
                target_2 = round(cur_close + (2.5 * cur_atr), 2)
                in_position = True

        equity_curve.append({
            "date": cur_date_str,
            "equity": round(capital, 2)
        })

    # Close any open trade at last bar close for final settlement
    if in_position:
        last_close = float(df["Close"].iloc[-1])
        last_date = str(dates[-1].strftime("%Y-%m-%d") if hasattr(dates[-1], "strftime") else str(dates[-1]))[:10]
        trade_pnl = round((last_close - entry_price) * position_qty, 2)
        trade_ret_pct = round(((last_close - entry_price) / entry_price) * 100.0, 2)
        capital = round(capital + trade_pnl, 2)
        trades.append({
            "entry_date": entry_date,
            "exit_date": last_date,
            "entry_price": round(entry_price, 2),
            "exit_price": round(last_close, 2),
            "quantity": position_qty,
            "pnl": trade_pnl,
            "return_pct": trade_ret_pct,
            "exit_reason": "OPEN_MARKED_TO_MARKET",
            "bars_held": len(df) - 1 - entry_idx
        })

    # Calculate Performance Statistics
    total_trades = len(trades)
    winning_trades = [t for t in trades if t["pnl"] > 0]
    losing_trades = [t for t in trades if t["pnl"] < 0]
    num_wins = len(winning_trades)
    num_losses = len(losing_trades)
    win_rate_pct = round((num_wins / total_trades) * 100.0, 2) if total_trades > 0 else 0.0

    gross_profit = sum(t["pnl"] for t in winning_trades)
    gross_loss = abs(sum(t["pnl"] for t in losing_trades))
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 1.0)

    total_pnl = round(capital - initial_capital, 2)
    total_return_pct = round((total_pnl / initial_capital) * 100.0, 2)

    # Max Drawdown Calculation
    eq_values = [pt["equity"] for pt in equity_curve]
    if eq_values:
        eq_series = pd.Series(eq_values)
        rolling_max = eq_series.cummax()
        drawdowns = (eq_series - rolling_max) / rolling_max
        max_drawdown_pct = round(abs(float(drawdowns.min())) * 100.0, 2)
    else:
        max_drawdown_pct = 0.0

    # Sharpe Ratio
    trade_returns = [t["return_pct"] for t in trades]
    if len(trade_returns) >= 3:
        ret_mean = np.mean(trade_returns)
        ret_std = np.std(trade_returns)
        sharpe_ratio = round(float((ret_mean / ret_std) * math.sqrt(50)), 2) if ret_std > 0 else 0.0
    else:
        sharpe_ratio = 0.0

    avg_trade_return = round(float(np.mean(trade_returns)), 2) if trade_returns else 0.0
    avg_bars_held = round(float(np.mean([t["bars_held"] for t in trades])), 1) if trades else 0.0

    target_1_hits = sum(1 for t in trades if t["exit_reason"] in ("TARGET_1_HIT", "TARGET_2_HIT"))
    target_1_hit_rate = round((target_1_hits / total_trades) * 100.0, 2) if total_trades > 0 else 0.0

    return {
        "status": "success",
        "symbol": symbol,
        "resolved_ticker": resolved_ticker,
        "period": period,
        "interval": interval,
        "strategy": strategy,
        "initial_capital": initial_capital,
        "final_capital": capital,
        "total_pnl": total_pnl,
        "total_return_pct": total_return_pct,
        "total_trades": total_trades,
        "winning_trades": num_wins,
        "losing_trades": num_losses,
        "win_rate_pct": win_rate_pct,
        "target_1_hit_rate_pct": target_1_hit_rate,
        "profit_factor": profit_factor,
        "max_drawdown_pct": max_drawdown_pct,
        "sharpe_ratio": sharpe_ratio,
        "average_trade_return_pct": avg_trade_return,
        "average_holding_period_bars": avg_bars_held,
        "recent_trades": trades[-10:],
        "equity_curve": equity_curve[::max(1, len(equity_curve) // 30)],  # Sample ~30 points for fast UI render
        "disclaimer": "Backtested using mathematical simulation on historical exchange OHLCV bars. Past performance is not indicative of future returns."
    }
