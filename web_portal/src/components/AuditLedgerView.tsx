"use client";

import React, { useEffect, useState } from "react";

export interface LedgerSignal {
  id: string;
  symbol: string;
  title: string;
  catalyst: string;
  bias: string;
  confluence_score: number;
  entry_range: string;
  target_1: string;
  stop_loss: string;
  risk_reward: string;
  outcome: string;
  max_gain_pct: number;
  created_at: string;
}

export interface AuditedSummary {
  win_rate_pct: number;
  total_verified_signals: number;
  avg_risk_reward: string;
  avg_hold_duration: string;
  profit_factor: number;
  audit_methodology: string;
}

interface AuditLedgerViewProps {
  backendUrl?: string;
  onBack?: () => void;
  showBackToTerminal?: boolean;
}

export default function AuditLedgerView({
  backendUrl,
  onBack,
  showBackToTerminal = false,
}: AuditLedgerViewProps) {
  const [summary, setSummary] = useState<AuditedSummary | null>(null);
  const [ledger, setLedger] = useState<LedgerSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filterOutcome, setFilterOutcome] = useState("ALL");

  const resolvedBackend =
    backendUrl ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    "https://stokvigil-ai.onrender.com";

  useEffect(() => {
    let isMounted = true;
    const fetchLedger = async () => {
      try {
        const res = await fetch(`${resolvedBackend}/api/market/accuracy-ledger`);
        if (res.ok) {
          const data = await res.json();
          if (!isMounted) return;
          setSummary(data.audited_summary || null);
          setLedger(data.ledger || []);
        }
      } catch (e) {
        console.error("Error fetching accuracy ledger", e);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchLedger();
    return () => {
      isMounted = false;
    };
  }, [resolvedBackend]);

  const filteredLedger = ledger.filter((item) => {
    const matchesSearch =
      item.symbol.toLowerCase().includes(search.toLowerCase()) ||
      item.title.toLowerCase().includes(search.toLowerCase()) ||
      item.catalyst.toLowerCase().includes(search.toLowerCase());
    const matchesOutcome =
      filterOutcome === "ALL" || item.outcome === filterOutcome;
    return matchesSearch && matchesOutcome;
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24, width: "100%" }}>
      {/* Header Banner & Title */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10, textAlign: "left" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              background: "rgba(16, 185, 129, 0.1)",
              border: "1px solid rgba(16, 185, 129, 0.3)",
              borderRadius: 20,
              padding: "4px 12px",
              fontSize: 10.5,
              fontWeight: 800,
              color: "#10b981",
            }}
          >
            <span>🛡️</span> NON-REPUDIATION VERIFIED TRACK RECORD
          </div>

          {onBack && (
            <button
              onClick={onBack}
              style={{
                background: "rgba(6, 182, 212, 0.12)",
                border: "1px solid rgba(6, 182, 212, 0.35)",
                color: "#06b6d4",
                padding: "6px 12px",
                borderRadius: 10,
                fontSize: 11,
                fontWeight: 800,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 5,
              }}
            >
              ← Back
            </button>
          )}
        </div>

        <h2 style={{ fontSize: 24, fontWeight: 900, color: "#ffffff", letterSpacing: "-0.02em", margin: 0 }}>
          Public Audited Accuracy Ledger
        </h2>
        <p style={{ fontSize: 12.5, color: "#94a3b8", lineHeight: 1.5, margin: 0 }}>
          Every surveillance alert is recorded with an immutable timestamp and audited against tick-level National Stock Exchange (NSE) & Bombay Stock Exchange (BSE) execution.
        </p>
      </div>

      {/* KPI Scorecards Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
        {[
          {
            title: "TARGET 1 HIT RATE",
            value:
              summary && summary.total_verified_signals > 0
                ? `${summary.win_rate_pct}%`
                : loading
                ? "..."
                : "--",
            sub: "Closed signals hitting Target 1 before SL",
            color: "#10b981",
          },
          {
            title: "VERIFIED SIGNALS",
            value: summary ? `${summary.total_verified_signals}` : loading ? "..." : "--",
            sub: "Audited across NSE/BSE & F&O Watchlists",
            color: "#06b6d4",
          },
          {
            title: "AVG RISK:REWARD",
            value:
              summary && summary.total_verified_signals > 0 && summary.avg_risk_reward !== "-"
                ? summary.avg_risk_reward
                : loading
                ? "..."
                : "--",
            sub: "Asymmetric Volatility Ratio per alert",
            color: "#38bdf8",
          },
          {
            title: "PROFIT FACTOR",
            value:
              summary && summary.total_verified_signals > 0 && summary.profit_factor > 0
                ? `${summary.profit_factor}`
                : loading
                ? "..."
                : "--",
            sub: "Gross profit divided by gross loss",
            color: "#a855f7",
          },
        ].map((kpi, i) => (
          <div
            key={i}
            style={{
              background: "#080B16",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              borderRadius: 16,
              padding: 16,
              display: "flex",
              flexDirection: "column",
              gap: 4,
            }}
          >
            <div style={{ fontSize: 9.5, fontWeight: 800, color: "#94a3b8", letterSpacing: "0.05em" }}>
              {kpi.title}
            </div>
            <div style={{ fontSize: 24, fontWeight: 900, color: kpi.color }}>{kpi.value}</div>
            <div style={{ fontSize: 10, color: "#64748b", lineHeight: 1.3 }}>{kpi.sub}</div>
          </div>
        ))}
      </div>

      {/* Quantitative Verification Standards Methodology Card */}
      <div
        style={{
          background: "rgba(6, 182, 212, 0.04)",
          border: "1px solid rgba(6, 182, 212, 0.2)",
          borderRadius: 16,
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        <div style={{ fontSize: 12, fontWeight: 900, color: "#06b6d4", display: "flex", alignItems: "center", gap: 6 }}>
          <span>🔬</span> QUANTITATIVE VERIFICATION STANDARDS
        </div>
        <div style={{ fontSize: 11.5, color: "#cbd5e1", lineHeight: 1.5 }}>
          {summary?.audit_methodology ||
            "Every alert generated by StokVigil AI is assigned a cryptographic record upon dispatch. Signal outcomes are verified using tick-level high and low prices from the National Stock Exchange of India (NSE) and Bombay Stock Exchange (BSE). A signal is verified as 'TARGET_1_REACHED' only if price achieves Target 1 prior to breaching the protective stop-loss floor."}
        </div>
      </div>

      {/* Search & Filter Controls */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
        <input
          type="text"
          placeholder="Search by ticker (e.g. RELIANCE)..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            background: "#080B16",
            border: "1px solid rgba(255, 255, 255, 0.1)",
            borderRadius: 10,
            padding: "8px 14px",
            color: "#ffffff",
            fontSize: 12,
            minWidth: 220,
            flex: "1 1 220px",
            maxWidth: 320,
            outline: "none",
          }}
        />

        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {["ALL", "TARGET_1_REACHED", "STOP_LOSS_DEFENDED"].map((opt) => (
            <button
              key={opt}
              onClick={() => setFilterOutcome(opt)}
              style={{
                background: filterOutcome === opt ? "rgba(6, 182, 212, 0.2)" : "#080B16",
                color: filterOutcome === opt ? "#06b6d4" : "#94a3b8",
                border: `1px solid ${filterOutcome === opt ? "rgba(6, 182, 212, 0.4)" : "rgba(255, 255, 255, 0.08)"}`,
                borderRadius: 8,
                padding: "6px 10px",
                fontSize: 10.5,
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              {opt === "ALL" ? "All Signals" : opt === "TARGET_1_REACHED" ? "🎯 Target 1 Reached" : "🛡️ SL Defended"}
            </button>
          ))}
        </div>
      </div>

      {/* Signal Ledger Table / Card List */}
      <div
        style={{
          background: "#080B16",
          border: "1px solid rgba(255, 255, 255, 0.08)",
          borderRadius: 16,
          overflow: "hidden",
        }}
      >
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: 11.5 }}>
            <thead>
              <tr style={{ background: "rgba(255, 255, 255, 0.02)", borderBottom: "1px solid rgba(255, 255, 255, 0.08)" }}>
                <th style={{ padding: "12px 14px", color: "#94a3b8", fontWeight: 700 }}>TICKER / TIME</th>
                <th style={{ padding: "12px 14px", color: "#94a3b8", fontWeight: 700 }}>CATALYST</th>
                <th style={{ padding: "12px 14px", color: "#94a3b8", fontWeight: 700 }}>SCORE</th>
                <th style={{ padding: "12px 14px", color: "#94a3b8", fontWeight: 700 }}>ENTRY</th>
                <th style={{ padding: "12px 14px", color: "#94a3b8", fontWeight: 700 }}>TARGET 1</th>
                <th style={{ padding: "12px 14px", color: "#94a3b8", fontWeight: 700 }}>STOP LOSS</th>
                <th style={{ padding: "12px 14px", color: "#94a3b8", fontWeight: 700 }}>R:R</th>
                <th style={{ padding: "12px 14px", color: "#94a3b8", fontWeight: 700 }}>OUTCOME</th>
              </tr>
            </thead>
            <tbody>
              {filteredLedger.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ padding: "32px 16px", textAlign: "center", color: "#64748b" }}>
                    {loading ? "Loading verified signals ledger..." : "No historical signals match your filter."}
                  </td>
                </tr>
              ) : (
                filteredLedger.map((sig) => {
                  const isWin = sig.outcome === "TARGET_1_REACHED";
                  return (
                    <tr key={sig.id} style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.04)" }}>
                      <td style={{ padding: "12px 14px" }}>
                        <div style={{ fontWeight: 800, color: "#ffffff" }}>{sig.symbol}</div>
                        <div style={{ fontSize: 9.5, color: "#64748b" }}>
                          {new Date(sig.created_at).toLocaleDateString()}{" "}
                          {new Date(sig.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </div>
                      </td>
                      <td style={{ padding: "12px 14px" }}>
                        <span
                          style={{
                            background: "rgba(6, 182, 212, 0.1)",
                            color: "#06b6d4",
                            padding: "3px 6px",
                            borderRadius: 6,
                            fontSize: 9.5,
                            fontWeight: 700,
                          }}
                        >
                          {sig.catalyst.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td style={{ padding: "12px 14px" }}>
                        <span style={{ fontWeight: 800, color: sig.confluence_score >= 75 ? "#10b981" : "#f59e0b" }}>
                          {sig.confluence_score}/100
                        </span>
                      </td>
                      <td style={{ padding: "12px 14px", color: "#cbd5e1" }}>{sig.entry_range}</td>
                      <td style={{ padding: "12px 14px", fontWeight: 800, color: "#10b981" }}>{sig.target_1}</td>
                      <td style={{ padding: "12px 14px", fontWeight: 800, color: "#f43f5e" }}>{sig.stop_loss}</td>
                      <td style={{ padding: "12px 14px", fontWeight: 700, color: "#06b6d4" }}>{sig.risk_reward}</td>
                      <td style={{ padding: "12px 14px" }}>
                        <span
                          style={{
                            background: isWin ? "rgba(16, 185, 129, 0.15)" : "rgba(244, 63, 94, 0.15)",
                            color: isWin ? "#10b981" : "#f43f5e",
                            border: `1px solid ${isWin ? "rgba(16, 185, 129, 0.3)" : "rgba(244, 63, 94, 0.3)"}`,
                            padding: "3px 8px",
                            borderRadius: 10,
                            fontSize: 9.5,
                            fontWeight: 800,
                            whiteSpace: "nowrap",
                          }}
                        >
                          {isWin ? "🎯 TARGET 1 HIT" : "🛡️ SL DEFENDED"}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
