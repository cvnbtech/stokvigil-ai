"use client";
import React from "react";
import { C, HoldingItem } from "../ui/DesignTokens";
import { Card, Badge, SignalBadge, VisibilityOutlinedIcon, VisibilityOffOutlinedIcon } from "../ui/UiAtoms";

interface HomeTabProps {
  user: { id?: string; name: string; email: string } | null;
  fiiDiiFlows: any | null;
  isPortfolioVisible: boolean;
  setIsPortfolioVisible: React.Dispatch<React.SetStateAction<boolean>>;
  totalValue: number;
  totalInvested: number;
  totalPnl: number;
  totalPnlPct: number;
  hasCredentials: boolean;
  holdings: HoldingItem[];
  openKeyModal: () => void;
  setSelectedStock: (stock: HoldingItem) => void;
}

export default function HomeTab({
  user,
  fiiDiiFlows,
  isPortfolioVisible,
  setIsPortfolioVisible,
  totalValue,
  totalInvested,
  totalPnl,
  totalPnlPct,
  hasCredentials,
  holdings,
  openKeyModal,
  setSelectedStock,
}: HomeTabProps) {
  return (
    <div className="anim-fadeup" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div>
        <div style={{ fontSize: 12, color: C.gray1 }}>
          {(() => {
            const h = new Date().getHours();
            if (h < 12) return "Good morning 👋";
            if (h < 17) return "Good afternoon 👋";
            return "Good evening 👋";
          })()}
        </div>
        <div style={{ fontSize: 18, fontWeight: 900, color: C.white, marginTop: 2 }}>{user?.name || "Investor"}</div>
      </div>

      {/* Institutional FII / DII Flow Bar */}
      {fiiDiiFlows && (
        <div style={{
          background: "#080B16",
          border: `1px solid ${C.border}`,
          borderRadius: 16,
          padding: "12px 16px",
          display: "flex",
          flexDirection: "column",
          gap: 8,
          boxShadow: "0 4px 20px rgba(0,0,0,0.3)"
        }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11.5, fontWeight: 800, color: C.white }}>
              <span>🏛️</span>
              <span>Institutional FII / DII Net Flow</span>
              <span style={{ fontSize: 10, color: C.gray2 }}>({fiiDiiFlows.date})</span>
            </div>
            <div style={{
              fontSize: 10,
              fontWeight: 800,
              padding: "3px 8px",
              borderRadius: 8,
              background: fiiDiiFlows.combined_net >= 0 ? "rgba(16,185,129,0.15)" : "rgba(244,63,94,0.15)",
              color: fiiDiiFlows.combined_net >= 0 ? C.emerald : C.rose,
              border: `1px solid ${fiiDiiFlows.combined_net >= 0 ? "rgba(16,185,129,0.3)" : "rgba(244,63,94,0.3)"}`
            }}>
              {String(fiiDiiFlows.sentiment || "BALANCED").replace(/_/g, " ")}
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, textAlign: "center" }}>
            <div style={{ background: "rgba(255,255,255,0.02)", padding: "6px 4px", borderRadius: 8 }}>
              <div style={{ fontSize: 9.5, color: C.gray2, fontWeight: 700 }}>FII NET</div>
              <div style={{ fontSize: 12, fontWeight: 800, color: (fiiDiiFlows.fii?.net || 0) >= 0 ? C.emerald : C.rose }}>
                {(fiiDiiFlows.fii?.net || 0) >= 0 ? "+" : ""}₹{Number(fiiDiiFlows.fii?.net || 0).toLocaleString()} Cr
              </div>
            </div>
            <div style={{ background: "rgba(255,255,255,0.02)", padding: "6px 4px", borderRadius: 8 }}>
              <div style={{ fontSize: 9.5, color: C.gray2, fontWeight: 700 }}>DII NET</div>
              <div style={{ fontSize: 12, fontWeight: 800, color: (fiiDiiFlows.dii?.net || 0) >= 0 ? C.emerald : C.rose }}>
                {(fiiDiiFlows.dii?.net || 0) >= 0 ? "+" : ""}₹{Number(fiiDiiFlows.dii?.net || 0).toLocaleString()} Cr
              </div>
            </div>
            <div style={{ background: "rgba(6,182,212,0.05)", border: `1px solid rgba(6,182,212,0.2)`, padding: "6px 4px", borderRadius: 8 }}>
              <div style={{ fontSize: 9.5, color: C.cyan, fontWeight: 800 }}>COMBINED</div>
              <div style={{ fontSize: 12, fontWeight: 900, color: (fiiDiiFlows.combined_net || 0) >= 0 ? C.cyan : C.rose }}>
                {(fiiDiiFlows.combined_net || 0) >= 0 ? "+" : ""}₹{Number(fiiDiiFlows.combined_net || 0).toLocaleString()} Cr
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Hero Card */}
      <div style={{
        background: "linear-gradient(145deg, #0D111E 0%, #12172A 100%)",
        border: `1px solid rgba(6,182,212,0.25)`,
        borderRadius: 22, padding: 20, position: "relative", overflow: "hidden",
        boxShadow: "0 12px 36px rgba(6,182,212,0.1)",
      }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
          <div style={{ fontSize: 10, fontWeight: 800, color: C.gray1, textTransform: "uppercase", letterSpacing: "0.1em" }}>
            Demat Portfolio Value
          </div>
          <button
            onClick={() => setIsPortfolioVisible(v => !v)}
            style={{
              background: "rgba(255,255,255,0.06)",
              border: `1px solid rgba(255,255,255,0.12)`,
              borderRadius: 12,
              padding: "3px 9px",
              color: "#94A3B8",
              fontSize: 10.5,
              fontWeight: 700,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 4
            }}
          >
            {isPortfolioVisible
              ? <VisibilityOutlinedIcon size={14} color="#94A3B8" />
              : <VisibilityOffOutlinedIcon size={14} color="#94A3B8" />}
            <span>{isPortfolioVisible ? "Hide" : "Show"}</span>
          </button>
        </div>
        <div style={{ fontSize: 34, fontWeight: 900, color: C.white, letterSpacing: isPortfolioVisible ? "-1px" : "2px", lineHeight: 1 }}>
          {isPortfolioVisible
            ? `₹${totalValue.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
            : "₹ • • • • • •"}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10 }}>
          <span style={{ fontSize: 13, fontWeight: 800, color: totalPnl >= 0 ? C.emerald : C.rose }}>
            {isPortfolioVisible
              ? `${totalPnl >= 0 ? "↑ +" : "↓ -"}₹${Math.abs(totalPnl).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              : "••••••"}
          </span>
          <Badge
            label={isPortfolioVisible ? `${totalPnlPct >= 0 ? "+" : ""}${totalPnlPct.toFixed(2)}%` : "••• %"}
            color={totalPnlPct >= 0 ? "emerald" : "rose"}
          />
          <span style={{ fontSize: 11, color: C.gray2 }}>Real-Time Breeze</span>
        </div>

        {/* Sparkline chart */}
        <svg width="100%" height="40" viewBox="0 0 200 40" style={{ marginTop: 14 }}>
          <defs>
            <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={totalPnl >= 0 ? C.emerald : C.rose} stopOpacity="0.35" />
              <stop offset="100%" stopColor={totalPnl >= 0 ? C.emerald : C.rose} stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d="M0,32 L20,28 L45,22 L70,18 L95,14 L120,10 L145,8 L170,5 L200,3" stroke={totalPnl >= 0 ? C.emerald : C.rose} strokeWidth="2.5" fill="none" strokeLinecap="round" />
          <path d="M0,32 L20,28 L45,22 L70,18 L95,14 L120,10 L145,8 L170,5 L200,3 L200,40 L0,40 Z" fill="url(#sparkGrad)" />
        </svg>

        <div style={{ display: "flex", gap: 16, marginTop: 4, paddingTop: 12, borderTop: `1px solid ${C.border}` }}>
          <div>
            <div style={{ fontSize: 10, color: C.gray2 }}>Invested</div>
            <div style={{ fontSize: 13, fontWeight: 800, color: C.white }}>
              {isPortfolioVisible ? `₹${totalInvested.toLocaleString('en-IN')}` : "₹ ••••••"}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: C.gray2 }}>Holdings</div>
            <div style={{ fontSize: 13, fontWeight: 800, color: C.white }}>
              {isPortfolioVisible ? `${holdings.length} Stocks` : "•• Stocks"}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: C.gray2 }}>Broker API</div>
            <div style={{ fontSize: 13, fontWeight: 800, color: hasCredentials ? C.emerald : C.amber }}>
              {hasCredentials ? "Connected" : "Key Needed"}
            </div>
          </div>
        </div>
      </div>

      {/* Active Holdings Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ fontSize: 14, fontWeight: 900, color: C.white }}>Active Demat Holdings</div>
        <span style={{ fontSize: 11, color: C.cyan, fontWeight: 700 }}>{holdings.length} stocks</span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {holdings.length === 0 ? (
          <div style={{
            background: C.bgCard, border: `1px solid ${C.border}`,
            borderRadius: 18, padding: "28px 20px", textAlign: "center",
            display: "flex", flexDirection: "column", alignItems: "center", gap: 12,
          }}>
            <div style={{
              width: 48, height: 48, borderRadius: 14,
              background: "rgba(6,182,212,0.1)", border: `1px solid ${C.borderCyan}`,
              display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22
            }}>
              💼
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 800, color: C.white }}>No Holdings Synced Yet</div>
              <div style={{ fontSize: 11.5, color: C.gray1, marginTop: 4, lineHeight: 1.4 }}>
                {hasCredentials
                  ? "Your ICICI Direct Demat portfolio is empty or sync is in progress."
                  : "Configure your ICICI Direct Breeze API Key to view live portfolio & holdings."}
              </div>
            </div>
            {!hasCredentials && (
              <button
                onClick={openKeyModal}
                style={{
                  background: `linear-gradient(135deg, ${C.cyan}, ${C.violet})`,
                  border: "none", borderRadius: 12, padding: "9px 18px",
                  color: "#fff", fontSize: 12, fontWeight: 800, cursor: "pointer",
                  boxShadow: "0 4px 16px rgba(6,182,212,0.3)"
                }}
              >
                ⚡ Configure Breeze Key
              </button>
            )}
          </div>
        ) : (
          holdings.map(h => (
            <Card
              key={h.symbol}
              onClick={() => setSelectedStock(h)}
              style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                transition: "transform 0.15s ease",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{
                  width: 38, height: 38, borderRadius: 12,
                  background: `linear-gradient(135deg, rgba(6,182,212,0.15), rgba(139,92,246,0.15))`,
                  border: `1px solid ${C.borderCyan}`,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 10, fontWeight: 900, color: C.cyan,
                }}>{h.symbol.slice(0, 2)}</div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 800, color: C.white }}>{h.symbol}</div>
                  <div style={{ fontSize: 11, color: C.gray1 }}>Qty {h.qty} · Avg ₹{h.avg}</div>
                </div>
              </div>
              <div style={{ textAlign: "right", display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 3 }}>
                <div style={{ fontSize: 13, fontWeight: 800, color: C.white }}>₹{h.price.toFixed(2)}</div>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ fontSize: 11, fontWeight: 800, color: h.pnlPct >= 0 ? C.emerald : C.rose }}>
                    {h.pnlPct >= 0 ? "+" : ""}{h.pnlPct.toFixed(2)}%
                  </span>
                  <SignalBadge signal={h.signal} type={h.signalType} />
                </div>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
