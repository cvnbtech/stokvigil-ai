"use client";
import React, { useEffect, useState } from "react";
import { C, HoldingItem } from "../ui/DesignTokens";
import { Btn, SignalBadge } from "../ui/UiAtoms";

interface StockDetailModalProps {
  selectedStock: HoldingItem;
  onClose: () => void;
  onPlaceOrder: (stock: HoldingItem) => void;
  onOpenBacktest?: (symbol: string) => void;
}

export default function StockDetailModal({
  selectedStock,
  onClose,
  onPlaceOrder,
  onOpenBacktest,
}: StockDetailModalProps) {
  const [analysisData, setAnalysisData] = useState<any>(null);
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState<boolean>(false);

  const cleanSym = (selectedStock.clean_symbol || selectedStock.symbol).replace(/\.(BO|NS)$/i, "").trim().toUpperCase();

  useEffect(() => {
    let isMounted = true;
    const fetchAnalysis = async () => {
      setIsLoadingAnalysis(true);
      try {
        const res = await fetch(`/api/stocks/${cleanSym}/analysis`);
        if (res.ok) {
          const json = await res.json();
          if (isMounted) setAnalysisData(json);
        }
      } catch (e) {
        console.warn("Failed to fetch detailed stock analysis:", e);
      } finally {
        if (isMounted) setIsLoadingAnalysis(false);
      }
    };

    fetchAnalysis();
    return () => {
      isMounted = false;
    };
  }, [cleanSym]);

  // Combine preloaded and fetched institutional data
  const tech = analysisData?.technicals || {};
  const flow = analysisData?.flow_data || selectedStock.derivatives || {};
  const analysis = analysisData?.analysis || {};

  const camarilla = selectedStock.camarilla_levels || tech.camarilla_pivots || null;
  const camarillaOpen = selectedStock.camarilla_open_type || tech.camarilla_open_type || null;
  const mtfCluster = selectedStock.camarilla_cluster || tech.camarilla_cluster || null;

  const candlePattern = selectedStock.candlestick_patterns || tech.candlestick_patterns || null;
  const derivatives = flow || null;
  const sectorRs = selectedStock.sector_rs || analysis.sector_rs || (tech.sector_rs_regime ? {
    sector_name: tech.sector_name,
    sector_rs_regime: tech.sector_rs_regime,
    sector_rs_rating: tech.sector_rs_rating,
  } : null);
  const eventRisk = selectedStock.event_risk || analysis.event_risk || null;

  const score = selectedStock.confluence_score ?? analysisData?.confluence_score ?? null;

  return (
    <div style={{
      position: "fixed", inset: 0,
      background: "rgba(6,8,18,0.92)", backdropFilter: "blur(16px)",
      display: "flex", alignItems: "center", justifyContent: "center",
      padding: 16, zIndex: 50,
    }}>
      <div className="anim-fadeup" style={{
        width: "100%", maxWidth: 460, maxHeight: "90vh", overflowY: "auto",
        background: C.bgCard, border: `1.5px solid ${C.borderCyan}`,
        borderRadius: 22, padding: 20, boxShadow: "0 10px 40px rgba(0,0,0,0.6)"
      }}>
        {/* Header Bar */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 14 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ fontSize: 17, fontWeight: 900, color: C.white }}>
                {selectedStock.name && selectedStock.name !== selectedStock.symbol && !selectedStock.name.endsWith(".BO")
                  ? selectedStock.name
                  : cleanSym}
              </div>
              <SignalBadge signal={selectedStock.signal} type={selectedStock.signalType} />
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4 }}>
              <span style={{ fontSize: 12, fontWeight: 800, color: C.cyan }}>
                {cleanSym}
              </span>
              <span style={{
                fontSize: 9, fontWeight: 800,
                color: (selectedStock.exchange === "BSE" || selectedStock.symbol.endsWith(".BO")) ? C.amber : C.cyan,
                background: (selectedStock.exchange === "BSE" || selectedStock.symbol.endsWith(".BO")) ? "rgba(245,158,11,0.12)" : "rgba(6,182,212,0.12)",
                border: `1px solid ${(selectedStock.exchange === "BSE" || selectedStock.symbol.endsWith(".BO")) ? "rgba(245,158,11,0.3)" : "rgba(6,182,212,0.3)"}`,
                borderRadius: 4, padding: "1px 5px"
              }}>
                {selectedStock.exchange || (selectedStock.symbol.endsWith(".BO") ? "BSE" : "NSE")}
              </span>
              <span style={{ fontSize: 11, color: C.gray2 }}>· {selectedStock.sector}</span>
              {score != null && (
                <span style={{
                  fontSize: 10, fontWeight: 800,
                  color: score >= 75 ? C.emerald : score >= 50 ? C.cyan : C.rose,
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: 6, padding: "1px 6px"
                }}>
                  Confluence {score}/100
                </span>
              )}
            </div>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", color: C.gray1, fontSize: 18, cursor: "pointer" }}>✕</button>
        </div>

        {/* Binary Event Risk Warning (Earnings Lockout) */}
        {eventRisk?.has_imminent_event_risk && (
          <div style={{
            background: "rgba(245,158,11,0.12)",
            border: "1.5px solid rgba(245,158,11,0.4)",
            borderRadius: 12, padding: "8px 12px", marginBottom: 12,
            display: "flex", alignItems: "center", gap: 8
          }}>
            <span style={{ fontSize: 16 }}>🛡️</span>
            <div>
              <div style={{ fontSize: 11, fontWeight: 800, color: C.amber }}>
                EARNINGS BLACKOUT SHIELD ACTIVE
              </div>
              <div style={{ fontSize: 10.5, color: C.white, marginTop: 1 }}>
                {eventRisk.event_description || "Quarterly Results"} scheduled in {eventRisk.days_to_earnings} day(s). New breakout entries vetoed.
              </div>
            </div>
          </div>
        )}

        {/* Pricing & PnL 4-Card Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 14 }}>
          <div style={{ background: "#080B16", border: `1px solid ${C.border}`, borderRadius: 12, padding: 10 }}>
            <div style={{ fontSize: 9.5, color: C.gray2, textTransform: "uppercase", fontWeight: 700 }}>Current Price</div>
            <div style={{ fontSize: 15, fontWeight: 900, color: C.white, marginTop: 2 }}>
              {selectedStock.price && selectedStock.price > 0 ? `₹${selectedStock.price.toFixed(2)}` : "--"}
            </div>
            <div style={{
              fontSize: 10.5,
              color: selectedStock.price && selectedStock.price > 0 && selectedStock.pnlPct != null
                ? (selectedStock.pnlPct >= 0 ? C.emerald : C.rose)
                : C.gray2,
              fontWeight: 800, marginTop: 1
            }}>
              {selectedStock.price && selectedStock.price > 0 && selectedStock.pnlPct != null
                ? `${selectedStock.pnlPct >= 0 ? "+" : ""}${selectedStock.pnlPct}%`
                : "--"}
            </div>
          </div>

          <div style={{ background: "#080B16", border: `1px solid ${C.border}`, borderRadius: 12, padding: 10 }}>
            <div style={{ fontSize: 9.5, color: C.gray2, textTransform: "uppercase", fontWeight: 700 }}>Total P&L</div>
            <div style={{
              fontSize: 15, fontWeight: 900,
              color: selectedStock.price && selectedStock.price > 0 && selectedStock.pnl != null
                ? (selectedStock.pnl >= 0 ? C.emerald : C.rose)
                : C.gray2,
              marginTop: 2
            }}>
              {selectedStock.price && selectedStock.price > 0 && selectedStock.pnl != null
                ? `${selectedStock.pnl >= 0 ? "+" : "-"}₹${Math.abs(selectedStock.pnl).toLocaleString()}`
                : "--"}
            </div>
            <div style={{ fontSize: 10, color: C.gray1, marginTop: 1 }}>Qty {selectedStock.qty}</div>
          </div>

          <div style={{ background: "#080B16", border: `1px solid ${C.border}`, borderRadius: 12, padding: 10 }}>
            <div style={{ fontSize: 9.5, color: C.gray2, textTransform: "uppercase", fontWeight: 700 }}>Day Range</div>
            <div style={{ fontSize: 11, fontWeight: 800, color: C.white, marginTop: 3 }}>
              {selectedStock.dayLow != null && selectedStock.dayHigh != null
                ? `₹${selectedStock.dayLow} – ₹${selectedStock.dayHigh}`
                : "--"}
            </div>
          </div>

          <div style={{ background: "#080B16", border: `1px solid ${C.border}`, borderRadius: 12, padding: 10 }}>
            <div style={{ fontSize: 9.5, color: C.gray2, textTransform: "uppercase", fontWeight: 700 }}>52-Wk High</div>
            <div style={{ fontSize: 11, fontWeight: 800, color: C.cyan, marginTop: 3 }}>
              {selectedStock.high52 != null ? `₹${selectedStock.high52}` : "--"}
            </div>
          </div>
        </div>

        {/* Institutional Microstructure: Camarilla Equation Levels (H5 -> L5) */}
        {camarilla && (camarilla.h4 != null || camarilla.l4 != null) && (
          <div style={{
            background: "#080B16", border: `1px solid ${C.border}`,
            borderRadius: 14, padding: "12px 14px", marginBottom: 14
          }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
              <div style={{ fontSize: 10.5, fontWeight: 800, color: C.white, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                📐 Camarilla Equation Levels (D-1 Session)
              </div>
              {camarillaOpen && camarillaOpen !== "DATA_INSUFFICIENT" && (
                <span style={{
                  fontSize: 9, fontWeight: 800,
                  color: camarillaOpen.includes("ABOVE_H4") ? "#a855f7" : camarillaOpen.includes("BELOW_L4") ? C.rose : C.cyan,
                  background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: 6, padding: "1px 6px"
                }}>
                  {camarillaOpen.replace(/_/g, " ")}
                </span>
              )}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 6, textAlign: "center" }}>
              <div style={{ background: "rgba(168,85,247,0.08)", border: "1px solid rgba(168,85,247,0.25)", borderRadius: 8, padding: "5px 4px" }}>
                <div style={{ fontSize: 9, color: "#a855f7", fontWeight: 800 }}>H5 Expansion</div>
                <div style={{ fontSize: 11, fontWeight: 900, color: C.white, marginTop: 1 }}>
                  {camarilla.h5 != null ? `₹${camarilla.h5}` : "--"}
                </div>
              </div>

              <div style={{ background: "rgba(236,72,153,0.08)", border: "1px solid rgba(236,72,153,0.25)", borderRadius: 8, padding: "5px 4px" }}>
                <div style={{ fontSize: 9, color: "#ec4899", fontWeight: 800 }}>H4 Breakout</div>
                <div style={{ fontSize: 11, fontWeight: 900, color: C.white, marginTop: 1 }}>
                  {camarilla.h4 != null ? `₹${camarilla.h4}` : "--"}
                </div>
              </div>

              <div style={{ background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.25)", borderRadius: 8, padding: "5px 4px" }}>
                <div style={{ fontSize: 9, color: C.emerald, fontWeight: 800 }}>H3 Target 1</div>
                <div style={{ fontSize: 11, fontWeight: 900, color: C.white, marginTop: 1 }}>
                  {camarilla.h3 != null ? `₹${camarilla.h3}` : "--"}
                </div>
              </div>

              <div style={{ background: "rgba(6,182,212,0.08)", border: "1px solid rgba(6,182,212,0.25)", borderRadius: 8, padding: "5px 4px" }}>
                <div style={{ fontSize: 9, color: C.cyan, fontWeight: 800 }}>L3 Floor</div>
                <div style={{ fontSize: 11, fontWeight: 900, color: C.white, marginTop: 1 }}>
                  {camarilla.l3 != null ? `₹${camarilla.l3}` : "--"}
                </div>
              </div>

              <div style={{ background: "rgba(244,63,94,0.08)", border: "1px solid rgba(244,63,94,0.25)", borderRadius: 8, padding: "5px 4px" }}>
                <div style={{ fontSize: 9, color: C.rose, fontWeight: 800 }}>L4 Hard SL</div>
                <div style={{ fontSize: 11, fontWeight: 900, color: C.white, marginTop: 1 }}>
                  {camarilla.l4 != null ? `₹${camarilla.l4}` : "--"}
                </div>
              </div>

              <div style={{ background: "rgba(220,38,38,0.08)", border: "1px solid rgba(220,38,38,0.25)", borderRadius: 8, padding: "5px 4px" }}>
                <div style={{ fontSize: 9, color: "#dc2626", fontWeight: 800 }}>L5 Capitulation</div>
                <div style={{ fontSize: 11, fontWeight: 900, color: C.white, marginTop: 1 }}>
                  {camarilla.l5 != null ? `₹${camarilla.l5}` : "--"}
                </div>
              </div>
            </div>

            {mtfCluster?.is_pivot_cluster && (
              <div style={{
                marginTop: 8, padding: "5px 8px", borderRadius: 6,
                background: "rgba(168,85,247,0.1)", border: "1px solid rgba(168,85,247,0.25)",
                fontSize: 10, color: "#c084fc", fontWeight: 700
              }}>
                🎯 {mtfCluster.description}
              </div>
            )}
          </div>
        )}

        {/* Candlestick Morphology & Wick Rejection */}
        {candlePattern && candlePattern.primary_pattern && candlePattern.primary_pattern !== "NONE" && (
          <div style={{
            background: "#080B16", border: `1px solid ${C.border}`,
            borderRadius: 14, padding: "10px 14px", marginBottom: 14
          }}>
            <div style={{ fontSize: 10.5, fontWeight: 800, color: C.white, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 6 }}>
              🕯️ Candlestick Morphology & Wick Anatomy
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
              <span style={{
                fontSize: 10, fontWeight: 800,
                color: candlePattern.primary_pattern.includes("BULLISH") || candlePattern.primary_pattern.includes("HAMMER") ? C.emerald : candlePattern.primary_pattern.includes("BEARISH") || candlePattern.primary_pattern.includes("SHOOTING") ? C.rose : C.cyan,
                background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 6, padding: "2px 8px"
              }}>
                {candlePattern.pattern_label || candlePattern.primary_pattern.replace(/_/g, " ")}
              </span>

              {candlePattern.anchored_level && (
                <span style={{
                  fontSize: 10, fontWeight: 700, color: C.cyan,
                  background: "rgba(6,182,212,0.1)", border: "1px solid rgba(6,182,212,0.25)",
                  borderRadius: 6, padding: "2px 8px"
                }}>
                  Anchored @ {candlePattern.anchored_level}
                </span>
              )}

              {candlePattern.is_upper_wick_rejection && (
                <span style={{
                  fontSize: 10, fontWeight: 800, color: C.rose,
                  background: "rgba(244,63,94,0.12)", border: "1px solid rgba(244,63,94,0.3)",
                  borderRadius: 6, padding: "2px 8px"
                }}>
                  ⚠️ Upper Wick Seller Rejection ({((candlePattern.upper_wick_ratio || 0) * 100).toFixed(0)}%)
                </span>
              )}

              {candlePattern.is_nr7 && (
                <span style={{
                  fontSize: 10, fontWeight: 800, color: C.amber,
                  background: "rgba(245,158,11,0.12)", border: "1px solid rgba(245,158,11,0.3)",
                  borderRadius: 6, padding: "2px 8px"
                }}>
                  ⏳ NR7 Volatility Compression (Breakout Imminent)
                </span>
              )}
            </div>
          </div>
        )}

        {/* Derivatives F&O & Sector Alignment Row */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 14 }}>
          {/* F&O Microstructure */}
          <div style={{ background: "#080B16", border: `1px solid ${C.border}`, borderRadius: 12, padding: 10 }}>
            <div style={{ fontSize: 9.5, color: C.gray2, textTransform: "uppercase", fontWeight: 700 }}>Derivatives OI Status</div>
            <div style={{
              fontSize: 12, fontWeight: 900, marginTop: 3,
              color: derivatives?.fo_oi_status === "LONG_BUILDUP" ? C.emerald
                : derivatives?.fo_oi_status === "SHORT_BUILDUP" ? C.rose
                : derivatives?.fo_oi_status === "SHORT_COVERING" ? C.cyan
                : derivatives?.fo_oi_status === "LONG_UNWINDING" ? C.amber
                : C.gray1
            }}>
              {derivatives?.fo_oi_status ? derivatives.fo_oi_status.replace(/_/g, " ") : "CASH EQUITY"}
            </div>
            {derivatives?.pcr != null && (
              <div style={{ fontSize: 10, color: C.gray1, marginTop: 2 }}>
                PCR: <b>{Number(derivatives.pcr).toFixed(2)}</b>
                {derivatives.max_pain != null ? ` · Max Pain ₹${derivatives.max_pain}` : ""}
              </div>
            )}
          </div>

          {/* Sector Alignment */}
          <div style={{ background: "#080B16", border: `1px solid ${C.border}`, borderRadius: 12, padding: 10 }}>
            <div style={{ fontSize: 9.5, color: C.gray2, textTransform: "uppercase", fontWeight: 700 }}>Sector Relative Strength</div>
            <div style={{
              fontSize: 12, fontWeight: 900, marginTop: 3,
              color: sectorRs?.sector_rs_regime === "SECTOR_LEADER" ? C.emerald
                : sectorRs?.sector_rs_regime === "SECTOR_LAGGARD" ? C.rose
                : C.cyan
            }}>
              {sectorRs?.sector_rs_regime ? sectorRs.sector_rs_regime.replace(/_/g, " ") : "INLINE SECTOR"}
            </div>
            {sectorRs?.sector_rs_rating != null && (
              <div style={{ fontSize: 10, color: C.gray1, marginTop: 2 }}>
                {sectorRs.sector_rs_rating >= 0 ? "+" : ""}{Number(sectorRs.sector_rs_rating).toFixed(1)}% vs Sector
              </div>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <Btn
            variant={selectedStock.signalType === "sell" ? "danger" : "primary"}
            onClick={() => onPlaceOrder(selectedStock)}
          >
            {selectedStock.signalType === "sell"
              ? "⚡ Place Sell Order"
              : selectedStock.signalType === "strong_buy" || selectedStock.signalType === "buy"
                ? "⚡ Place Buy Order"
                : "⚡ Execute Trade Order"
            }
          </Btn>
          {onOpenBacktest && (
            <button
              onClick={() => {
                onClose();
                onOpenBacktest(selectedStock.symbol);
              }}
              style={{
                background: "rgba(6,182,212,0.1)",
                border: `1px solid ${C.borderCyan}`,
                borderRadius: 12,
                padding: "9px 0",
                color: C.cyan,
                fontSize: 12,
                fontWeight: 800,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 6,
              }}
            >
              🧪 Backtest Strategy Replay
            </button>
          )}
          <Btn variant="ghost" onClick={onClose}>
            Close
          </Btn>
        </div>
      </div>
    </div>
  );
}
