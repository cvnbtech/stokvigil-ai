"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import ConfluenceRadar from "../../components/ConfluenceRadar";

interface LedgerSignal {
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

interface AuditedSummary {
  win_rate_pct: number;
  total_verified_signals: number;
  avg_risk_reward: string;
  avg_hold_duration: string;
  profit_factor: number;
  audit_methodology: string;
}

export default function TransparencyPage() {
  const [summary, setSummary] = useState<AuditedSummary | null>(null);
  const [ledger, setLedger] = useState<LedgerSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filterOutcome, setFilterOutcome] = useState("ALL");

  const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "https://stokvigil-ai.onrender.com";

  useEffect(() => {
    const fetchLedger = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/market/accuracy-ledger`);
        if (res.ok) {
          const data = await res.json();
          setSummary(data.audited_summary || null);
          setLedger(data.ledger || []);
        }
      } catch (e) {
        console.error("Error fetching accuracy ledger", e);
      } finally {
        setLoading(false);
      }
    };
    fetchLedger();
  }, [BACKEND_URL]);

  const filteredLedger = ledger.filter((item) => {
    const matchesSearch = item.symbol.toLowerCase().includes(search.toLowerCase()) ||
                          item.title.toLowerCase().includes(search.toLowerCase()) ||
                          item.catalyst.toLowerCase().includes(search.toLowerCase());
    const matchesOutcome = filterOutcome === "ALL" || item.outcome === filterOutcome;
    return matchesSearch && matchesOutcome;
  });

  return (
    <div style={{
      minHeight: "100vh",
      background: "#030712",
      color: "#f8fafc",
      fontFamily: "Inter, system-ui, sans-serif",
      padding: "32px 20px 80px 20px"
    }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", display: "flex", flexDirection: "column", gap: 32 }}>
        {/* Navigation Bar */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: 20 }}>
          <Link href="/" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none" }}>
            <div style={{
              width: 38,
              height: 38,
              borderRadius: 12,
              background: "linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 18,
              fontWeight: 900,
              color: "#030712"
            }}>
              ⚡
            </div>
            <div>
              <div style={{ fontSize: 18, fontWeight: 900, color: "#ffffff" }}>STOKVIGIL AI</div>
              <div style={{ fontSize: 10, color: "#06b6d4", fontWeight: 700, letterSpacing: "0.08em" }}>TRANSPARENCY & AUDIT LEDGER</div>
            </div>
          </Link>

          <Link href="/" style={{
            background: "rgba(6, 182, 212, 0.12)",
            border: "1px solid rgba(6, 182, 212, 0.35)",
            color: "#06b6d4",
            padding: "8px 16px",
            borderRadius: 12,
            fontSize: 12,
            fontWeight: 800,
            textDecoration: "none",
            display: "flex",
            alignItems: "center",
            gap: 6
          }}>
            ← Back to Terminal
          </Link>
        </div>

        {/* Hero Section */}
        <div style={{ textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
          <div style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            background: "rgba(16, 185, 129, 0.1)",
            border: "1px solid rgba(16, 185, 129, 0.3)",
            borderRadius: 20,
            padding: "6px 14px",
            fontSize: 11,
            fontWeight: 800,
            color: "#10b981"
          }}>
            <span>🛡️</span> NON-REPUDIATION SIGNAL VERIFICATION
          </div>
          <h1 style={{ fontSize: 36, fontWeight: 900, color: "#ffffff", letterSpacing: "-0.02em", margin: 0 }}>
            Public Audited Accuracy Ledger
          </h1>
          <p style={{ fontSize: 14, color: "#94a3b8", maxWidth: 640, lineHeight: 1.6, margin: 0 }}>
            StokVigil AI does not use marketing hype or cherry-picked screenshots. Every surveillance alert is timestamped in an immutable PostgreSQL ledger and tracked against live NSE tick execution.
          </p>
        </div>

        {/* KPI Scorecard */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16 }}>
          {[
            {
              title: "TARGET 1 HIT RATE",
              value: summary && summary.total_verified_signals > 0 ? `${summary.win_rate_pct}%` : (loading ? "..." : "--"),
              sub: "Closed signals hitting Target 1 before Stop Loss",
              color: "#10b981"
            },
            {
              title: "VERIFIED SIGNALS",
              value: summary ? `${summary.total_verified_signals}` : (loading ? "..." : "--"),
              sub: "Audited across NIFTY 50 & F&O Watchlists",
              color: "#06b6d4"
            },
            {
              title: "AVG RISK:REWARD",
              value: summary && summary.total_verified_signals > 0 && summary.avg_risk_reward !== "-" ? summary.avg_risk_reward : (loading ? "..." : "--"),
              sub: "Asymmetric Volatility Ratio per alert",
              color: "#38bdf8"
            },
            {
              title: "PROFIT FACTOR",
              value: summary && summary.total_verified_signals > 0 && summary.profit_factor > 0 ? `${summary.profit_factor}` : (loading ? "..." : "--"),
              sub: "Gross profit divided by gross loss",
              color: "#a855f7"
            }
          ].map((kpi, i) => (
            <div key={i} style={{
              background: "#080B16",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              borderRadius: 18,
              padding: 20,
              display: "flex",
              flexDirection: "column",
              gap: 6
            }}>
              <div style={{ fontSize: 10, fontWeight: 800, color: "#94a3b8", letterSpacing: "0.05em" }}>{kpi.title}</div>
              <div style={{ fontSize: 32, fontWeight: 900, color: kpi.color }}>{kpi.value}</div>
              <div style={{ fontSize: 11, color: "#64748b", lineHeight: 1.4 }}>{kpi.sub}</div>
            </div>
          ))}
        </div>

        {/* Audit Methodology Card */}
        <div style={{
          background: "rgba(6, 182, 212, 0.04)",
          border: "1px solid rgba(6, 182, 212, 0.2)",
          borderRadius: 20,
          padding: 24,
          display: "flex",
          flexDirection: "column",
          gap: 12
        }}>
          <div style={{ fontSize: 14, fontWeight: 900, color: "#06b6d4", display: "flex", alignItems: "center", gap: 8 }}>
            <span>🔬</span> QUANTITATIVE VERIFICATION STANDARDS
          </div>
          <div style={{ fontSize: 12.5, color: "#cbd5e1", lineHeight: 1.6 }}>
            {summary?.audit_methodology ||
              "Every alert generated by StokVigil AI is assigned a cryptographic non-repudiation record upon dispatch. Signal outcomes are verified using tick-level high and low prices from the National Stock Exchange of India. A signal is verified as 'TARGET_1_REACHED' only if price achieves Target 1 prior to breaching the protective stop-loss floor."}
          </div>
        </div>

        {/* Search & Filter Controls */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <input
            type="text"
            placeholder="Search by ticker (e.g. RELIANCE, TCS)..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              background: "#080B16",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              borderRadius: 12,
              padding: "10px 16px",
              color: "#ffffff",
              fontSize: 12,
              width: 320,
              outline: "none"
            }}
          />

          <div style={{ display: "flex", gap: 8 }}>
            {["ALL", "TARGET_1_REACHED", "STOP_LOSS_DEFENDED"].map((opt) => (
              <button
                key={opt}
                onClick={() => setFilterOutcome(opt)}
                style={{
                  background: filterOutcome === opt ? "rgba(6, 182, 212, 0.2)" : "#080B16",
                  color: filterOutcome === opt ? "#06b6d4" : "#94a3b8",
                  border: `1px solid ${filterOutcome === opt ? "rgba(6, 182, 212, 0.4)" : "rgba(255, 255, 255, 0.08)"}`,
                  borderRadius: 10,
                  padding: "8px 14px",
                  fontSize: 11,
                  fontWeight: 700,
                  cursor: "pointer"
                }}
              >
                {opt.replace(/_/g, " ")}
              </button>
            ))}
          </div>
        </div>

        {/* Signal Ledger Table */}
        <div style={{
          background: "#080B16",
          border: "1px solid rgba(255, 255, 255, 0.08)",
          borderRadius: 20,
          overflow: "hidden"
        }}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: 12 }}>
              <thead>
                <tr style={{ background: "rgba(255, 255, 255, 0.02)", borderBottom: "1px solid rgba(255, 255, 255, 0.08)" }}>
                  <th style={{ padding: "14px 18px", color: "#94a3b8", fontWeight: 700 }}>TICKER / TIME</th>
                  <th style={{ padding: "14px 18px", color: "#94a3b8", fontWeight: 700 }}>CATALYST</th>
                  <th style={{ padding: "14px 18px", color: "#94a3b8", fontWeight: 700 }}>SCORE</th>
                  <th style={{ padding: "14px 18px", color: "#94a3b8", fontWeight: 700 }}>ENTRY RANGE</th>
                  <th style={{ padding: "14px 18px", color: "#94a3b8", fontWeight: 700 }}>TARGET 1</th>
                  <th style={{ padding: "14px 18px", color: "#94a3b8", fontWeight: 700 }}>STOP LOSS</th>
                  <th style={{ padding: "14px 18px", color: "#94a3b8", fontWeight: 700 }}>R:R</th>
                  <th style={{ padding: "14px 18px", color: "#94a3b8", fontWeight: 700 }}>OUTCOME</th>
                </tr>
              </thead>
              <tbody>
                {filteredLedger.length === 0 ? (
                  <tr>
                    <td colSpan={8} style={{ padding: "36px 18px", textAlign: "center", color: "#64748b" }}>
                      {loading ? "Loading verified signals ledger..." : "No historical signals match your search."}
                    </td>
                  </tr>
                ) : (
                  filteredLedger.map((sig) => (
                    <tr key={sig.id} style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.04)" }}>
                      <td style={{ padding: "14px 18px" }}>
                        <div style={{ fontWeight: 800, color: "#ffffff" }}>{sig.symbol}</div>
                        <div style={{ fontSize: 10, color: "#64748b" }}>
                          {new Date(sig.created_at).toLocaleDateString()} {new Date(sig.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </td>
                      <td style={{ padding: "14px 18px" }}>
                        <span style={{
                          background: "rgba(6, 182, 212, 0.1)",
                          color: "#06b6d4",
                          padding: "3px 8px",
                          borderRadius: 6,
                          fontSize: 10,
                          fontWeight: 700
                        }}>
                          {sig.catalyst.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td style={{ padding: "14px 18px" }}>
                        <span style={{ fontWeight: 800, color: sig.confluence_score >= 75 ? "#10b981" : "#f59e0b" }}>
                          {sig.confluence_score}/100
                        </span>
                      </td>
                      <td style={{ padding: "14px 18px", color: "#cbd5e1" }}>{sig.entry_range}</td>
                      <td style={{ padding: "14px 18px", fontWeight: 800, color: "#10b981" }}>{sig.target_1}</td>
                      <td style={{ padding: "14px 18px", fontWeight: 800, color: "#f43f5e" }}>{sig.stop_loss}</td>
                      <td style={{ padding: "14px 18px", fontWeight: 700, color: "#06b6d4" }}>{sig.risk_reward}</td>
                      <td style={{ padding: "14px 18px" }}>
                        <span style={{
                          background: sig.outcome === "TARGET_1_REACHED" ? "rgba(16, 185, 129, 0.15)" : "rgba(244, 63, 94, 0.15)",
                          color: sig.outcome === "TARGET_1_REACHED" ? "#10b981" : "#f43f5e",
                          border: `1px solid ${sig.outcome === "TARGET_1_REACHED" ? "rgba(16, 185, 129, 0.3)" : "rgba(244, 63, 94, 0.3)"}`,
                          padding: "4px 10px",
                          borderRadius: 12,
                          fontSize: 10,
                          fontWeight: 800
                        }}>
                          {sig.outcome === "TARGET_1_REACHED" ? "🎯 TARGET 1 HIT" : "🛡️ SL DEFENDED"}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
