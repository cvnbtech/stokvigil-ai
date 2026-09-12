"use client";
import React from "react";
import { C } from "../ui/DesignTokens";
import { Badge, SignalBadge, DraggableChipBar } from "../ui/UiAtoms";
import ConfluenceRadar from "../ConfluenceRadar";
import { AlphaCardData } from "../ShareAlphaCardModal";

interface AlertsTabProps {
  alerts: any[];
  alertFilter: string;
  setAlertFilter: (filter: string) => void;
  setTab: (tab: "home" | "alerts" | "watchlist" | "settings" | "ledger") => void;
  expandedRadarId: string | null;
  setExpandedRadarId: (id: string | null) => void;
  setChartingSymbol: (symbol: string) => void;
  setSharingAlert: (data: AlphaCardData) => void;
}

export default function AlertsTab({
  alerts,
  alertFilter,
  setAlertFilter,
  setTab,
  expandedRadarId,
  setExpandedRadarId,
  setChartingSymbol,
  setSharingAlert,
}: AlertsTabProps) {
  const filteredAlerts = alerts.filter(a => {
    if (alertFilter === "all") return true;
    if (alertFilter === "high") return a.impact >= 80;
    if (alertFilter === "earnings") return a.catalyst?.toLowerCase().includes("earning") || a.title?.toLowerCase().includes("earning");
    if (alertFilter === "breakout") return a.catalyst?.toLowerCase().includes("breakout") || a.title?.toLowerCase().includes("breakout");
    if (alertFilter === "volume") return a.catalyst?.toLowerCase().includes("volume") || a.title?.toLowerCase().includes("volume");
    if (alertFilter === "fii") return a.catalyst?.toLowerCase().includes("block") || a.title?.toLowerCase().includes("fii");
    if (alertFilter === "hold") return a.signal?.toLowerCase().includes("hold") || a.signalType === "hold" || a.signalType === "neutral";
    return true;
  });

  return (
    <div className="anim-fadeup" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ fontSize: 16, fontWeight: 900, color: C.white }}>Alerts</div>
        <Badge label="5-MIN AUTO SCAN" color="emerald" />
      </div>

      {/* Native App Filter Chips with Smooth Drag/Slide */}
      <DraggableChipBar>
        {[
          {
            id: "all",
            label: "All Alerts",
            icon: (c: string) => (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M4 6H20M4 12H20M4 18H20" stroke={c} strokeWidth="2.5" strokeLinecap="round" />
              </svg>
            )
          },
          {
            id: "high",
            label: "High Impact",
            icon: (c: string) => (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M12 2C12 2 4 8 4 14C4 18.4183 7.58172 22 12 22C16.4183 22 20 18.4183 20 14C20 8 12 2 12 2Z" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M12 18C13.6569 18 15 16.6569 15 15C15 13 12 10 12 10C12 10 9 13 9 15C9 16.6569 10.3431 18 12 18Z" fill={c} />
              </svg>
            )
          },
          {
            id: "earnings",
            label: "Earnings",
            icon: (c: string) => (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M18 20V10M12 20V4M6 20V14" stroke={c} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )
          },
          {
            id: "breakout",
            label: "Breakout",
            icon: (c: string) => (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M23 6L13.5 15.5L8.5 10.5L1 18M23 6H17M23 6V12" stroke={c} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )
          },
          {
            id: "volume",
            label: "Volume Surge",
            icon: (c: string) => (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M13 2L3 14H12L11 22L21 10H12L13 2Z" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )
          },
          {
            id: "fii",
            label: "FII Buying",
            icon: (c: string) => (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M3 21H21M5 21V10M9 21V10M13 21V10M17 21V10M2 10L12 3L22 10H2Z" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )
          },
          {
            id: "hold",
            label: "Hold / Neutral",
            icon: (c: string) => (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="9" stroke={c} strokeWidth="2" />
                <line x1="8" y1="12" x2="16" y2="12" stroke={c} strokeWidth="2" strokeLinecap="round" />
              </svg>
            )
          },
        ].map(chip => {
          const isActive = alertFilter === chip.id;
          const chipColor = isActive ? C.cyan : C.gray1;
          return (
            <button
              key={chip.id}
              onClick={() => setAlertFilter(chip.id)}
              style={{
                background: isActive ? "rgba(6,182,212,0.14)" : C.bgCard,
                color: isActive ? C.cyan : C.gray1,
                border: `1.5px solid ${isActive ? "rgba(6,182,212,0.4)" : C.border}`,
                borderRadius: 12,
                padding: "8px 14px",
                fontSize: 11.5,
                fontWeight: isActive ? 800 : 600,
                cursor: "pointer",
                whiteSpace: "nowrap",
                display: "flex",
                alignItems: "center",
                gap: 6,
                boxShadow: isActive ? "0 4px 12px rgba(6,182,212,0.15)" : "none",
                transition: "all 0.2s cubic-bezier(0.16,1,0.3,1)",
                flexShrink: 0,
              }}
            >
              {chip.icon(chipColor)}
              <span>{chip.label}</span>
            </button>
          );
        })}
      </DraggableChipBar>

      {/* Public Audit Ledger Track Record Bar */}
      <div
        onClick={() => setTab("ledger")}
        style={{
          background: "rgba(16,185,129,0.08)",
          border: "1px solid rgba(16,185,129,0.25)",
          borderRadius: 12,
          padding: "8px 14px",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          transition: "all 0.2s ease",
          marginBottom: 6,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 15 }}>🛡️</span>
          <span style={{ fontSize: 11.5, fontWeight: 800, color: C.emerald }}>
            Public Audited Accuracy Ledger & Track Record
          </span>
        </div>
        <span style={{ fontSize: 10.5, fontWeight: 800, color: C.cyan }}>
          View Verified Outcomes →
        </span>
      </div>

      {filteredAlerts.length === 0 ? (
        <div style={{
          background: C.bgCard, border: `1px solid ${C.border}`,
          borderRadius: 18, padding: "36px 20px", textAlign: "center",
          display: "flex", flexDirection: "column", alignItems: "center", gap: 12,
        }}>
          <div style={{
            width: 52, height: 52, borderRadius: 16,
            background: "rgba(6,182,212,0.1)", border: `1px solid ${C.borderCyan}`,
            display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24
          }}>
            ⚡
          </div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 800, color: C.white }}>No High-Impact Catalysts Yet</div>
            <div style={{ fontSize: 11.5, color: C.gray1, marginTop: 4, lineHeight: 1.4, maxWidth: 300 }}>
              StokVigil scans your portfolio every 5 minutes during Indian market hours. Noise is filtered out automatically.
            </div>
          </div>
        </div>
      ) : (
        filteredAlerts.map(a => (
          <div key={a.id} style={{
            background: C.bgCard, border: `1px solid ${C.border}`,
            borderLeft: `3.5px solid ${a.signalType === "strong_buy" ? C.emerald : a.signalType === "sell" ? C.amber : C.cyan}`,
            borderRadius: 18, padding: 16,
            boxShadow: "0 8px 24px rgba(0,0,0,0.3)",
          }}>
            {/* Top Badge & Action Signal Row */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10, flexWrap: "wrap", gap: 6 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <SignalBadge signal={a.signal} type={a.signalType} />
                <Badge label={`${a.impact}% CONFIDENCE`} color={a.impactColor} />
              </div>
              <span style={{ fontSize: 10, color: C.gray2, fontWeight: 600 }}>{a.time}</span>
            </div>

            <div style={{ fontSize: 13.5, fontWeight: 900, color: C.white, marginBottom: 10, lineHeight: 1.4 }}>
              <span style={{
                color: a.exchange === "BSE" || a.symbol?.endsWith(".BO") ? C.amber : C.cyan,
                marginRight: 6
              }}>
                [{(a.symbol || "").replace(/\.(BO|NS)$/i, '')}]
              </span>
              <span style={{
                fontSize: 9.5, fontWeight: 800,
                color: (a.exchange === "BSE" || a.symbol?.endsWith(".BO")) ? C.amber : C.cyan,
                background: (a.exchange === "BSE" || a.symbol?.endsWith(".BO")) ? "rgba(245,158,11,0.12)" : "rgba(6,182,212,0.12)",
                border: `1px solid ${(a.exchange === "BSE" || a.symbol?.endsWith(".BO")) ? "rgba(245,158,11,0.3)" : "rgba(6,182,212,0.3)"}`,
                borderRadius: 4, padding: "1px 5px", marginRight: 8, verticalAlign: "middle"
              }}>
                {a.exchange || (a.symbol?.endsWith(".BO") ? "BSE" : "NSE")}
              </span>
              {a.title}
            </div>

            {/* ICICI Demat Position Banner */}
            {a.dematPosition && (
              <div style={{
                background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.25)",
                borderRadius: 10, padding: "7px 12px", marginBottom: 10, display: "flex", alignItems: "center", gap: 8
              }}>
                <span style={{ fontSize: 13 }}>💼</span>
                <span style={{ fontSize: 11.5, fontWeight: 700, color: C.white }}>
                  ICICI Demat: {a.dematPosition.quantity} Qty @ Avg ₹{Number(a.dematPosition.average_buy_price).toFixed(1)} (P&L: {a.dematPosition.unrealized_pnl_pct >= 0 ? '+' : ''}{a.dematPosition.unrealized_pnl_pct}%)
                </span>
              </div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: 5, marginBottom: 12 }}>
              {a.reasons.map((r: string, i: number) => (
                <div key={i} style={{ display: "flex", gap: 7, fontSize: 11.5, color: C.gray1, lineHeight: 1.5 }}>
                  <span style={{ color: C.cyan, fontWeight: 800 }}>•</span>
                  <span>{r}</span>
                </div>
              ))}
            </div>

            {/* Target & Stop-Loss Action Box */}
            <div style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              background: "rgba(6,182,212,0.06)", border: `1px solid rgba(6,182,212,0.2)`,
              borderRadius: 12, padding: "8px 12px", marginBottom: 10,
            }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: C.gray1 }}>
                🎯 Target: <span style={{ color: C.emerald, fontWeight: 900 }}>{a.targetPrice}</span>
              </div>
              <div style={{ fontSize: 11, fontWeight: 700, color: C.gray1 }}>
                🛡️ Stop Loss: <span style={{ color: C.rose, fontWeight: 900 }}>{a.stopLoss}</span>
              </div>
            </div>

            {/* Institutional Metrics Grid & Wyckoff VSA Insight */}
            <div style={{
              background: "#080B16", borderRadius: 12, padding: "10px 12px",
              border: `1px solid ${C.border}`, display: "flex", flexDirection: "column", gap: 8
            }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 6 }}>
                {Object.entries(a.metrics || {}).map(([k, v]) => (
                  <div key={k} style={{ textAlign: "center" }}>
                    <div style={{ fontSize: 9, color: C.gray2, textTransform: "uppercase", fontWeight: 700, marginBottom: 2 }}>
                      {k === "flow" ? "F&O / OI" : (k === "rsi" ? "RSI (15M)" : k)}
                    </div>
                    <div style={{
                      fontSize: 11, fontWeight: 800,
                      color: k === "delivery" ? C.cyan : (k === "flow" ? C.emerald : C.white),
                      overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap"
                    }}>
                      {String(v)}
                    </div>
                  </div>
                ))}
              </div>

              {a.vsaNote && (
                <div style={{
                  background: "rgba(6,182,212,0.06)", border: `1px solid rgba(6,182,212,0.2)`,
                  borderRadius: 6, padding: "4px 8px", fontSize: 10.5, color: C.cyan,
                  fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "space-between"
                }}>
                  <span>⚡ Wyckoff VSA: {a.vsaNote}</span>
                  {a.vix && <span style={{ color: C.gray2, fontSize: 10 }}>VIX: {a.vix}</span>}
                </div>
              )}
            </div>

            {/* Visual 4-Pillar Confluence Spider / Radar Section */}
            {a.factors && (
              <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 8 }}>
                <button
                  onClick={() => setExpandedRadarId(expandedRadarId === a.id ? null : a.id)}
                  style={{
                    background: expandedRadarId === a.id ? "rgba(6,182,212,0.15)" : "rgba(255,255,255,0.03)",
                    border: `1px solid ${expandedRadarId === a.id ? "rgba(6,182,212,0.4)" : C.border}`,
                    borderRadius: 10,
                    padding: "6px 12px",
                    color: expandedRadarId === a.id ? C.cyan : C.gray1,
                    fontSize: 11,
                    fontWeight: 700,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    width: "100%",
                    transition: "all 0.2s"
                  }}
                >
                  <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span>🕸️</span>
                    <span>4-Pillar Confluence Radar</span>
                  </span>
                  <span>{expandedRadarId === a.id ? "▲ Hide" : "▼ View"}</span>
                </button>

                {expandedRadarId === a.id && (
                  <div style={{
                    background: "#080B16",
                    border: `1px solid ${C.border}`,
                    borderRadius: 14,
                    padding: 12,
                    display: "flex",
                    justifyContent: "center"
                  }}>
                    <ConfluenceRadar factors={a.factors} size={190} showLabels={true} />
                  </div>
                )}
              </div>
            )}

            {/* Phase 1 & 2 Action Buttons: Candlestick Chart + Share Alpha Card */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 10 }}>
              <button
                onClick={() => setChartingSymbol(a.symbol)}
                style={{
                  background: "rgba(6,182,212,0.1)",
                  border: `1px solid rgba(6,182,212,0.3)`,
                  borderRadius: 10,
                  padding: "8px 10px",
                  color: C.cyan,
                  fontSize: 11,
                  fontWeight: 800,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 6,
                  transition: "all 0.2s"
                }}
              >
                <span>📊</span>
                <span>Candles & Camarilla</span>
              </button>

              <button
                onClick={() => setSharingAlert({
                  symbol: a.symbol,
                  title: a.title,
                  catalyst: a.catalyst,
                  confluenceScore: a.impact,
                  bias: a.signal,
                  targetPrice: a.targetPrice,
                  stopLoss: a.stopLoss,
                  entryRange: a.entryRange,
                  riskReward: a.riskReward,
                  reasons: a.reasons,
                  factors: a.factors,
                  time: a.time
                })}
                style={{
                  background: "rgba(16,185,129,0.12)",
                  border: `1px solid rgba(16,185,129,0.35)`,
                  borderRadius: 10,
                  padding: "8px 10px",
                  color: C.emerald,
                  fontSize: 11,
                  fontWeight: 800,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 6,
                  transition: "all 0.2s"
                }}
              >
                <span>⚡</span>
                <span>Share Alpha Card</span>
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
