"use client";

import React, { useState, useEffect } from "react";

export interface BacktestTrade {
  entry_date: string;
  exit_date: string;
  type: string;
  entry_price: number;
  exit_price: number;
  quantity: number;
  pnl: number;
  return_pct: number;
  exit_reason: string;
  bars_held: number;
}

export interface BacktestEquityPoint {
  date: string;
  equity: number;
}

export interface BacktestResult {
  status: string;
  symbol: string;
  resolved_ticker: string;
  period: string;
  interval: string;
  strategy: string;
  initial_capital: number;
  final_capital: number;
  total_pnl: number;
  total_return_pct: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate_pct: number;
  target_1_hit_rate_pct: number;
  profit_factor: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  average_trade_return_pct: number;
  average_holding_period_bars: number;
  recent_trades: BacktestTrade[];
  equity_curve: BacktestEquityPoint[];
  disclaimer: string;
}

interface BacktestViewProps {
  backendUrl?: string;
  initialSymbol?: string;
  onBack?: () => void;
}

const C = {
  bg: "#04060E",
  card: "#080B16",
  cardHover: "#0C1022",
  cyan: "#06B6D4",
  borderCyan: "rgba(6,182,212,0.3)",
  emerald: "#10B981",
  borderEmerald: "rgba(16,185,129,0.3)",
  rose: "#EF4444",
  borderRose: "rgba(239,68,68,0.3)",
  amber: "#F59E0B",
  violet: "#8B5CF6",
  white: "#FFFFFF",
  gray1: "#94A3B8",
  gray2: "#64748B",
  border: "rgba(255,255,255,0.08)",
};

const PRESET_SYMBOLS = [
  { label: "RELIANCE", ticker: "RELIANCE.NS" },
  { label: "TCS", ticker: "TCS.NS" },
  { label: "HDFCBANK", ticker: "HDFCBANK.NS" },
  { label: "INFY", ticker: "INFY.NS" },
  { label: "BSE: RIL (500325)", ticker: "500325.BO" },
  { label: "BSE: TCS (532540)", ticker: "532540.BO" },
];

export default function BacktestView({
  backendUrl,
  initialSymbol = "RELIANCE.NS",
  onBack,
}: BacktestViewProps) {
  const [symbol, setSymbol] = useState(initialSymbol);
  const [strategy, setStrategy] = useState("camarilla_breakout");
  const [period, setPeriod] = useState("1y");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BacktestResult | null>(null);

  const resolvedBackend =
    backendUrl ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    "https://stokvigil-ai.onrender.com";

  const runBacktest = async (symToRun = symbol, stratToRun = strategy, periodToRun = period) => {
    if (!symToRun.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const cleanSym = symToRun.trim().toUpperCase();
      const res = await fetch(
        `${resolvedBackend}/api/market/backtest?symbol=${encodeURIComponent(
          cleanSym
        )}&period=${periodToRun}&strategy=${stratToRun}&capital=200000&risk_budget=2000`
      );

      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.detail || `Backtest failed with status ${res.status}`);
      }

      const data: BacktestResult = await res.json();
      setResult(data);
    } catch (e: any) {
      console.error("Backtest execution error:", e);
      setError(e.message || "Failed to execute backtest. Historical exchange data unavailable.");
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runBacktest(initialSymbol, strategy, period);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Compute SVG coordinates for Equity Curve
  const renderEquityChart = () => {
    if (!result?.equity_curve || result.equity_curve.length < 2) return null;
    const curve = result.equity_curve;
    const equities = curve.map((p) => p.equity);
    const minEq = Math.min(...equities);
    const maxEq = Math.max(...equities);
    const range = maxEq - minEq || 1;

    const width = 600;
    const height = 180;
    const padding = 20;

    const points = curve.map((pt, i) => {
      const x = padding + (i / (curve.length - 1)) * (width - 2 * padding);
      const y = height - padding - ((pt.equity - minEq) / range) * (height - 2 * padding);
      return { x, y, eq: pt.equity, date: pt.date };
    });

    const pathD = points.reduce((acc, p, i) => `${acc} ${i === 0 ? "M" : "L"} ${p.x},${p.y}`, "");
    const areaD = `${pathD} L ${points[points.length - 1].x},${height - padding} L ${points[0].x},${height - padding} Z`;
    const isProfit = (result.total_pnl ?? 0) >= 0;
    const strokeColor = isProfit ? C.emerald : C.rose;

    return (
      <div style={{ width: "100%", overflowX: "auto" }}>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          style={{ width: "100%", height: 180, display: "block" }}
        >
          <defs>
            <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={strokeColor} stopOpacity="0.3" />
              <stop offset="100%" stopColor={strokeColor} stopOpacity="0.0" />
            </linearGradient>
          </defs>
          {/* Baseline */}
          <line
            x1={padding}
            y1={height - padding}
            x2={width - padding}
            y2={height - padding}
            stroke="rgba(255,255,255,0.1)"
            strokeDasharray="4 4"
          />
          {/* Fill Area */}
          <path d={areaD} fill="url(#eqGrad)" />
          {/* Line */}
          <path
            d={pathD}
            fill="none"
            stroke={strokeColor}
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {/* Start and End nodes */}
          {points.length > 0 && (
            <>
              <circle cx={points[0].x} cy={points[0].y} r="4" fill={strokeColor} />
              <circle
                cx={points[points.length - 1].x}
                cy={points[points.length - 1].y}
                r="5"
                fill={strokeColor}
                stroke="#fff"
                strokeWidth="1.5"
              />
            </>
          )}
        </svg>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: 10,
            color: C.gray2,
            marginTop: 4,
            padding: "0 8px",
          }}
        >
          <span>Start: ₹{result.initial_capital?.toLocaleString("en-IN")}</span>
          <span>End: ₹{result.final_capital?.toLocaleString("en-IN")}</span>
        </div>
      </div>
    );
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18, width: "100%" }}>
      {/* Header Banner */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 10,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {onBack && (
            <button
              onClick={onBack}
              style={{
                background: "rgba(255,255,255,0.06)",
                border: `1px solid ${C.border}`,
                color: C.white,
                borderRadius: 8,
                padding: "6px 12px",
                fontSize: 11,
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              ← Back
            </button>
          )}
          <div>
            <div style={{ fontSize: 16, fontWeight: 900, color: C.white, display: "flex", alignItems: "center", gap: 6 }}>
              <span>🧪 Strategy Backtester</span>
              <span
                style={{
                  fontSize: 9,
                  background: "rgba(6,182,212,0.15)",
                  color: C.cyan,
                  padding: "2px 6px",
                  borderRadius: 6,
                  fontWeight: 800,
                  border: `1px solid ${C.borderCyan}`,
                }}
              >
                NSE & BSE REPLAY
              </span>
            </div>
            <div style={{ fontSize: 11, color: C.gray1, marginTop: 2 }}>
              Institutional mathematical backtesting on historical exchange bars with 1% capital risk sizing.
            </div>
          </div>
        </div>
      </div>

      {/* Control Panel */}
      <div
        style={{
          background: C.card,
          border: `1px solid ${C.border}`,
          borderRadius: 14,
          padding: 14,
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        {/* Symbol Input & Popular Presets */}
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label style={{ fontSize: 10, color: C.gray2, fontWeight: 800, letterSpacing: "0.05em" }}>
            TICKER SYMBOL OR BSE SCRIP (E.G. RELIANCE, TCS, 500325)
          </label>
          <div style={{ display: "flex", gap: 8 }}>
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              placeholder="Enter symbol (e.g. RELIANCE, 500325)"
              style={{
                flex: 1,
                background: "#04060E",
                border: `1px solid ${C.borderCyan}`,
                borderRadius: 10,
                padding: "9px 12px",
                color: C.white,
                fontSize: 13,
                fontWeight: 700,
                outline: "none",
              }}
            />
            <button
              onClick={() => runBacktest(symbol, strategy, period)}
              disabled={loading}
              style={{
                background: loading ? "rgba(6,182,212,0.2)" : "rgba(6,182,212,0.9)",
                border: "none",
                borderRadius: 10,
                padding: "0 18px",
                color: loading ? C.gray1 : "#000",
                fontSize: 12,
                fontWeight: 900,
                cursor: loading ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              {loading ? "Replaying..." : "⚡ Run Replay"}
            </button>
          </div>

          {/* Preset Chips */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 }}>
            {PRESET_SYMBOLS.map((p) => (
              <button
                key={p.ticker}
                onClick={() => {
                  setSymbol(p.ticker);
                  runBacktest(p.ticker, strategy, period);
                }}
                style={{
                  background: symbol.toUpperCase() === p.ticker ? "rgba(6,182,212,0.18)" : "rgba(255,255,255,0.04)",
                  border: `1px solid ${symbol.toUpperCase() === p.ticker ? C.cyan : C.border}`,
                  color: symbol.toUpperCase() === p.ticker ? C.cyan : C.gray1,
                  borderRadius: 8,
                  padding: "4px 8px",
                  fontSize: 10.5,
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Strategy & Timeframe Selectors */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <div>
            <label style={{ fontSize: 10, color: C.gray2, fontWeight: 800, letterSpacing: "0.05em", display: "block", marginBottom: 4 }}>
              ALGORITHMIC STRATEGY
            </label>
            <select
              value={strategy}
              onChange={(e) => {
                setStrategy(e.target.value);
                runBacktest(symbol, e.target.value, period);
              }}
              style={{
                width: "100%",
                background: "#04060E",
                border: `1px solid ${C.border}`,
                borderRadius: 8,
                padding: "8px 10px",
                color: C.white,
                fontSize: 11,
                fontWeight: 700,
                outline: "none",
                cursor: "pointer",
              }}
            >
              <option value="camarilla_breakout">Camarilla H4/L4 Breakout</option>
              <option value="confluence_trend">Multi-TF Confluence Trend</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: 10, color: C.gray2, fontWeight: 800, letterSpacing: "0.05em", display: "block", marginBottom: 4 }}>
              HISTORICAL TIMEFRAME
            </label>
            <select
              value={period}
              onChange={(e) => {
                setPeriod(e.target.value);
                runBacktest(symbol, strategy, e.target.value);
              }}
              style={{
                width: "100%",
                background: "#04060E",
                border: `1px solid ${C.border}`,
                borderRadius: 8,
                padding: "8px 10px",
                color: C.white,
                fontSize: 11,
                fontWeight: 700,
                outline: "none",
                cursor: "pointer",
              }}
            >
              <option value="3mo">Last 3 Months</option>
              <option value="6mo">Last 6 Months</option>
              <option value="1y">Last 1 Year (Recommended)</option>
              <option value="2y">Last 2 Years</option>
              <option value="5y">Last 5 Years</option>
            </select>
          </div>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div
          style={{
            background: "rgba(239,68,68,0.1)",
            border: `1px solid ${C.borderRose}`,
            borderRadius: 12,
            padding: "12px 16px",
            color: C.rose,
            fontSize: 12,
            lineHeight: 1.5,
          }}
        >
          <b>⚠️ Backtest Data Notice:</b> {error}
          <div style={{ fontSize: 10.5, color: C.gray1, marginTop: 4 }}>
            In accordance with our strict Zero-Default policy, we never generate synthetic mock trades. Verify the symbol or try another ticker with active historical liquidity.
          </div>
        </div>
      )}

      {/* Results View */}
      {result && result.status === "success" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {/* Resolved Ticker Header */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              background: "rgba(6,182,212,0.06)",
              border: `1px solid ${C.borderCyan}`,
              borderRadius: 12,
              padding: "10px 14px",
            }}
          >
            <div>
              <span style={{ fontSize: 12, fontWeight: 900, color: C.white }}>
                {result.resolved_ticker}
              </span>
              <span style={{ fontSize: 10, color: C.gray1, marginLeft: 8 }}>
                Replay: {result.period} ({result.interval}) • Strategy: {result.strategy === "camarilla_breakout" ? "Camarilla H4/L4 Breakout" : "Confluence Trend"}
              </span>
            </div>
            <div
              style={{
                fontSize: 11,
                fontWeight: 900,
                color: (result.total_pnl ?? 0) >= 0 ? C.emerald : C.rose,
              }}
            >
              {(result.total_pnl ?? 0) >= 0 ? "+" : ""}₹{result.total_pnl?.toLocaleString("en-IN")} ({result.total_return_pct}%)
            </div>
          </div>

          {/* Primary Metric KPI Cards */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
              gap: 10,
            }}
          >
            {/* Win Rate */}
            <div
              style={{
                background: C.card,
                border: `1px solid ${C.border}`,
                borderRadius: 12,
                padding: "12px",
                display: "flex",
                flexDirection: "column",
                gap: 4,
              }}
            >
              <span style={{ fontSize: 10, color: C.gray2, fontWeight: 800 }}>WIN RATE</span>
              <div style={{ fontSize: 18, fontWeight: 900, color: result.win_rate_pct >= 50 ? C.emerald : C.amber }}>
                {result.win_rate_pct}%
              </div>
              <span style={{ fontSize: 9.5, color: C.gray1 }}>
                {result.winning_trades} Wins / {result.losing_trades} Losses
              </span>
            </div>

            {/* Profit Factor */}
            <div
              style={{
                background: C.card,
                border: `1px solid ${C.border}`,
                borderRadius: 12,
                padding: "12px",
                display: "flex",
                flexDirection: "column",
                gap: 4,
              }}
            >
              <span style={{ fontSize: 10, color: C.gray2, fontWeight: 800 }}>PROFIT FACTOR</span>
              <div style={{ fontSize: 18, fontWeight: 900, color: result.profit_factor >= 1.5 ? C.emerald : C.cyan }}>
                {result.profit_factor}x
              </div>
              <span style={{ fontSize: 9.5, color: C.gray1 }}>Institutional &gt; 1.50</span>
            </div>

            {/* Max Drawdown */}
            <div
              style={{
                background: C.card,
                border: `1px solid ${C.border}`,
                borderRadius: 12,
                padding: "12px",
                display: "flex",
                flexDirection: "column",
                gap: 4,
              }}
            >
              <span style={{ fontSize: 10, color: C.gray2, fontWeight: 800 }}>MAX DRAWDOWN</span>
              <div style={{ fontSize: 18, fontWeight: 900, color: result.max_drawdown_pct <= 10 ? C.emerald : C.rose }}>
                {result.max_drawdown_pct}%
              </div>
              <span style={{ fontSize: 9.5, color: C.gray1 }}>Strict Risk Guard</span>
            </div>

            {/* Target 1 Hit Rate */}
            <div
              style={{
                background: C.card,
                border: `1px solid ${C.border}`,
                borderRadius: 12,
                padding: "12px",
                display: "flex",
                flexDirection: "column",
                gap: 4,
              }}
            >
              <span style={{ fontSize: 10, color: C.gray2, fontWeight: 800 }}>TARGET 1 REACHED</span>
              <div style={{ fontSize: 18, fontWeight: 900, color: C.emerald }}>
                {result.target_1_hit_rate_pct}%
              </div>
              <span style={{ fontSize: 9.5, color: C.gray1 }}>Tactical Exits</span>
            </div>

            {/* Sharpe Ratio */}
            <div
              style={{
                background: C.card,
                border: `1px solid ${C.border}`,
                borderRadius: 12,
                padding: "12px",
                display: "flex",
                flexDirection: "column",
                gap: 4,
              }}
            >
              <span style={{ fontSize: 10, color: C.gray2, fontWeight: 800 }}>SHARPE RATIO</span>
              <div style={{ fontSize: 18, fontWeight: 900, color: C.violet }}>
                {result.sharpe_ratio}
              </div>
              <span style={{ fontSize: 9.5, color: C.gray1 }}>Risk-adjusted alpha</span>
            </div>

            {/* Total Trades */}
            <div
              style={{
                background: C.card,
                border: `1px solid ${C.border}`,
                borderRadius: 12,
                padding: "12px",
                display: "flex",
                flexDirection: "column",
                gap: 4,
              }}
            >
              <span style={{ fontSize: 10, color: C.gray2, fontWeight: 800 }}>SAMPLE TRADES</span>
              <div style={{ fontSize: 18, fontWeight: 900, color: C.white }}>
                {result.total_trades}
              </div>
              <span style={{ fontSize: 9.5, color: C.gray1 }}>Avg Hold: {result.average_holding_period_bars} bars</span>
            </div>
          </div>

          {/* Visual Equity Curve Chart */}
          <div
            style={{
              background: C.card,
              border: `1px solid ${C.border}`,
              borderRadius: 14,
              padding: 16,
              display: "flex",
              flexDirection: "column",
              gap: 10,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontSize: 12, fontWeight: 800, color: C.white }}>
                📈 Simulated Demat Equity Curve
              </span>
              <span style={{ fontSize: 10, color: C.cyan, fontWeight: 700 }}>
                1% Position Risk Budget (₹2,000 max/trade)
              </span>
            </div>
            {renderEquityChart()}
          </div>

          {/* Recent Trades Table */}
          {result.recent_trades && result.recent_trades.length > 0 && (
            <div
              style={{
                background: C.card,
                border: `1px solid ${C.border}`,
                borderRadius: 14,
                padding: 16,
                display: "flex",
                flexDirection: "column",
                gap: 10,
              }}
            >
              <div style={{ fontSize: 12, fontWeight: 800, color: C.white }}>
                📋 Execution Log (Last {result.recent_trades.length} Backtested Trades)
              </div>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
                  <thead>
                    <tr style={{ borderBottom: `1px solid ${C.border}`, color: C.gray2, textAlign: "left" }}>
                      <th style={{ padding: "6px 8px" }}>Entry</th>
                      <th style={{ padding: "6px 8px" }}>Exit</th>
                      <th style={{ padding: "6px 8px" }}>Side</th>
                      <th style={{ padding: "6px 8px" }}>Entry Price</th>
                      <th style={{ padding: "6px 8px" }}>Exit Price</th>
                      <th style={{ padding: "6px 8px" }}>Qty</th>
                      <th style={{ padding: "6px 8px" }}>PnL (₹)</th>
                      <th style={{ padding: "6px 8px" }}>Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.recent_trades.map((t, idx) => {
                      const isWin = t.pnl >= 0;
                      return (
                        <tr
                          key={idx}
                          style={{
                            borderBottom: "1px solid rgba(255,255,255,0.04)",
                            color: C.white,
                          }}
                        >
                          <td style={{ padding: "8px", fontSize: 10.5, color: C.gray1 }}>{t.entry_date}</td>
                          <td style={{ padding: "8px", fontSize: 10.5, color: C.gray1 }}>{t.exit_date}</td>
                          <td style={{ padding: "8px" }}>
                            <span
                              style={{
                                background: t.type === "BUY" ? "rgba(16,185,129,0.15)" : "rgba(239,68,68,0.15)",
                                color: t.type === "BUY" ? C.emerald : C.rose,
                                padding: "2px 6px",
                                borderRadius: 4,
                                fontSize: 9.5,
                                fontWeight: 800,
                              }}
                            >
                              {t.type}
                            </span>
                          </td>
                          <td style={{ padding: "8px" }}>₹{t.entry_price?.toFixed(2)}</td>
                          <td style={{ padding: "8px" }}>₹{t.exit_price?.toFixed(2)}</td>
                          <td style={{ padding: "8px" }}>{t.quantity}</td>
                          <td
                            style={{
                              padding: "8px",
                              fontWeight: 800,
                              color: isWin ? C.emerald : C.rose,
                            }}
                          >
                            {isWin ? "+" : ""}₹{t.pnl?.toFixed(2)} ({t.return_pct}%)
                          </td>
                          <td style={{ padding: "8px", fontSize: 10, color: C.gray1 }}>
                            {t.exit_reason?.replace(/_/g, " ")}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* SEBI / Algorithmic Disclaimer */}
          <div
            style={{
              padding: "10px 14px",
              background: "rgba(255,255,255,0.02)",
              border: `1px solid ${C.border}`,
              borderRadius: 10,
              fontSize: 10,
              color: C.gray2,
              lineHeight: 1.5,
            }}
          >
            🛡️ <b>Quantitative Audit Notice:</b> {result.disclaimer} Simulations incorporate slippage buffer and strict mathematical 1% account risk sizing.
          </div>
        </div>
      )}
    </div>
  );
}
