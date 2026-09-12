"use client";
import React from "react";
import { C, HoldingItem } from "../ui/DesignTokens";
import { SignalBadge } from "../ui/UiAtoms";

interface WatchlistTabProps {
  watchlist: any[];
  holdings: HoldingItem[];
  dematAutoSync: boolean;
  toggleDematAutoSync: (enabled: boolean) => void;
  ticker: string;
  handleStockChange: (val: string) => void;
  tickerSuggestions: any[];
  setTickerSuggestions: React.Dispatch<React.SetStateAction<any[]>>;
  addStock: (symbolToAdd?: string, nameToAdd?: string) => void;
  removeTicker: (id: string) => void;
  onOpenTradeModal: (stock: { symbol: string; price: number; type: "BUY" | "SELL"; target: string; sl: string; qty?: number }) => void;
}

export default function WatchlistTab({
  watchlist,
  holdings,
  dematAutoSync,
  toggleDematAutoSync,
  ticker,
  handleStockChange,
  tickerSuggestions,
  setTickerSuggestions,
  addStock,
  removeTicker,
  onOpenTradeModal,
}: WatchlistTabProps) {
  return (
    <div className="anim-fadeup" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* Header Info */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 900, color: C.white, display: "flex", alignItems: "center", gap: 8 }}>
            <span>Watchlist</span>
            <span style={{
              background: "rgba(6,182,212,0.12)", border: `1px solid ${C.borderCyan}`,
              color: C.cyan, borderRadius: 20, padding: "2px 8px", fontSize: 10, fontWeight: 800
            }}>
              {watchlist.length} Stocks
            </span>
          </div>
          <div style={{ fontSize: 10.5, color: C.gray2, marginTop: 2 }}>
            Real-time market feed • Auto-synced with ICICI Demat
          </div>
        </div>
      </div>

      {/* Enhanced Ticker Search & Add Bar */}
      <div style={{ position: "relative" }}>
        <div style={{ display: "flex", gap: 8 }}>
          <div style={{
            flex: 1, position: "relative", display: "flex", alignItems: "center",
            background: C.bgCard, border: `1.5px solid ${C.borderCyan}`, borderRadius: 14,
            boxShadow: "0 4px 12px rgba(6,182,212,0.06)"
          }}>
            <span style={{ position: "absolute", left: 12, fontSize: 14, color: C.cyan }}>🔍</span>
            <input
              value={ticker}
              onChange={e => handleStockChange(e.target.value)}
              onKeyDown={e => e.key === "Enter" && addStock()}
              placeholder="Search NSE stock (e.g. TATA, RELIANCE, HDFCBANK)"
              style={{
                width: "100%", background: "none", border: "none",
                padding: "11px 14px 11px 36px", fontSize: 12.5, fontWeight: 700,
                color: C.white, outline: "none", fontFamily: "Inter, sans-serif",
                textTransform: "uppercase",
              }}
            />
          </div>
          <button
            onClick={() => addStock()}
            style={{
              background: `linear-gradient(135deg, ${C.cyan}, ${C.violet})`,
              border: "none", borderRadius: 14, padding: "0 18px",
              color: "#fff", fontSize: 12.5, cursor: "pointer", fontWeight: 800,
              display: "flex", alignItems: "center", gap: 6,
              boxShadow: "0 4px 14px rgba(6,182,212,0.3)",
              whiteSpace: "nowrap"
            }}
          >
            <span style={{ fontSize: 16 }}>+</span>
            <span>Add Stock</span>
          </button>
        </div>

        {/* 3-Option Suggestion Dropdown */}
        {tickerSuggestions.length > 0 && ticker.trim().length > 0 && (
          <div style={{
            marginTop: 8,
            background: "#0D111E",
            border: `1.5px solid ${C.borderCyan}`,
            borderRadius: 14,
            padding: "8px 10px",
            boxShadow: "0 10px 25px rgba(6,182,212,0.18)",
            display: "flex",
            flexDirection: "column",
            gap: 4
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "2px 6px 6px" }}>
              <span style={{ fontSize: 10, fontWeight: 800, color: C.cyan, letterSpacing: "0.5px" }}>
                SUGGESTED STOCKS (CLICK TO ADD)
              </span>
              <button
                onClick={() => setTickerSuggestions([])}
                style={{ background: "none", border: "none", color: C.gray2, cursor: "pointer", fontSize: 12 }}
              >
                ✕
              </button>
            </div>
            {tickerSuggestions.map((sug) => (
              <div
                key={sug.symbol}
                onClick={() => addStock(sug.symbol, sug.name)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "7px 10px",
                  borderRadius: 10,
                  background: "rgba(255,255,255,0.03)",
                  cursor: "pointer",
                  transition: "background 0.2s ease"
                }}
                onMouseEnter={e => e.currentTarget.style.background = "rgba(6,182,212,0.1)"}
                onMouseLeave={e => e.currentTarget.style.background = "rgba(255,255,255,0.03)"}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{
                    background: "rgba(6,182,212,0.15)",
                    border: `1px solid ${C.borderCyan}`,
                    borderRadius: 6,
                    padding: "2px 7px",
                    fontSize: 11.5,
                    fontWeight: 900,
                    color: C.white
                  }}>
                    {sug.symbol}
                  </span>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: C.white }}>{sug.name}</div>
                    <div style={{ fontSize: 10, color: C.gray2 }}>{sug.sector}</div>
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    addStock(sug.symbol, sug.name);
                  }}
                  style={{
                    background: `linear-gradient(135deg, ${C.cyan}, ${C.violet})`,
                    border: "none",
                    borderRadius: 8,
                    padding: "4px 10px",
                    color: "#fff",
                    fontSize: 11,
                    fontWeight: 800,
                    cursor: "pointer"
                  }}
                >
                  + Add
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* DEMAT AUTO-SYNC WATCHLIST CARD */}
      <div style={{
        background: "linear-gradient(135deg, rgba(6,182,212,0.08) 0%, rgba(13,17,30,0.95) 100%)",
        border: "1px solid rgba(6,182,212,0.25)",
        borderRadius: 16,
        padding: "14px 18px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        boxShadow: "0 4px 20px rgba(0,0,0,0.3)"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: "rgba(6,182,212,0.12)", border: "1px solid rgba(6,182,212,0.3)",
            display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18
          }}>
            📊
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 900, color: C.white }}>Demat Auto-Sync Watchlist</div>
            <div style={{ fontSize: 11, color: C.gray2, marginTop: 2 }}>Automatically import & monitor active demat stocks</div>
          </div>
        </div>
        <label style={{ position: "relative", display: "inline-block", width: 44, height: 24, cursor: "pointer", flexShrink: 0 }}>
          <input
            type="checkbox"
            checked={dematAutoSync}
            onChange={(e) => toggleDematAutoSync(e.target.checked)}
            style={{ opacity: 0, width: 0, height: 0 }}
          />
          <span style={{
            position: "absolute", cursor: "pointer", top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: dematAutoSync ? C.cyan : "rgba(255,255,255,0.12)",
            borderRadius: 24, transition: "0.25s",
            border: `1px solid ${dematAutoSync ? C.cyan : C.border}`
          }}>
            <span style={{
              position: "absolute", content: '""', height: 18, width: 18, left: dematAutoSync ? 22 : 3, bottom: 2,
              backgroundColor: "#fff", borderRadius: "50%", transition: "0.25s",
              boxShadow: "0 2px 4px rgba(0,0,0,0.3)"
            }} />
          </span>
        </label>
      </div>

      {/* Watchlist Cards Stack */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {(() => {
          const holdingItems: any[] = holdings.map(h => ({
            id: `demat-${h.symbol}`,
            symbol: h.symbol,
            name: `${h.symbol} (Demat Holding)`,
            auto: true,
            price: h.price || 0,
            chg: (h.price && h.price > 0) ? (h.pnlPct >= 0 ? `+${h.pnlPct.toFixed(2)}%` : `${h.pnlPct.toFixed(2)}%`) : "--",
            isPositive: h.pnlPct >= 0,
            signal: h.signal || "MONITORING",
            signalType: h.signalType || "monitoring",
            target: h.target || "--",
            sl: h.sl || "--"
          }));

          const combinedList = [...watchlist];
          if (dematAutoSync) {
            for (const dh of holdingItems) {
              if (!combinedList.some(w => w.symbol.toUpperCase() === dh.symbol.toUpperCase())) {
                combinedList.push(dh);
              }
            }
          }

          const displayedWatchlist = dematAutoSync
            ? combinedList
            : combinedList.filter(item => !item.auto);

          if (displayedWatchlist.length === 0) {
            return (
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
                  📌
                </div>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 800, color: C.white }}>No Stocks in Watchlist</div>
                  <div style={{ fontSize: 11.5, color: C.gray1, marginTop: 4, lineHeight: 1.4, maxWidth: 300 }}>
                    {dematAutoSync
                      ? "Search and add any NSE stock symbol above to monitor high-impact catalysts and automated signals."
                      : "Demat auto-sync is paused. Add custom stocks above or enable auto-sync to view demat holdings."}
                  </div>
                </div>
              </div>
            );
          }

          return displayedWatchlist.map(item => (
            <div key={item.id} style={{
              background: "linear-gradient(145deg, #0D111E 0%, #12172A 100%)",
              border: `1px solid ${C.border}`,
              borderRadius: 16, padding: "14px 16px",
              display: "flex", flexDirection: "column", gap: 10,
              boxShadow: "0 4px 16px rgba(0,0,0,0.3)",
              transition: "all 0.2s ease"
            }}>
              {/* Top Symbol Row */}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{
                    width: 38, height: 38, borderRadius: 11,
                    background: item.isPositive ? "rgba(16,185,129,0.12)" : "rgba(239,68,68,0.12)",
                    border: `1.5px solid ${item.isPositive ? "rgba(16,185,129,0.35)" : "rgba(239,68,68,0.35)"}`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 11, fontWeight: 900, color: item.isPositive ? C.emerald : C.rose,
                  }}>
                    {item.symbol.slice(0, 2)}
                  </div>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <span style={{ fontSize: 14, fontWeight: 900, color: C.white }}>{item.symbol}</span>
                      <span style={{
                        fontSize: 9.5, fontWeight: 700,
                        color: item.auto ? C.cyan : C.gray2,
                        background: item.auto ? "rgba(6,182,212,0.1)" : "rgba(255,255,255,0.05)",
                        borderRadius: 4, padding: "1px 5px", border: `1px solid ${item.auto ? "rgba(6,182,212,0.25)" : C.border}`
                      }}>
                        {item.auto ? "📊 Demat Auto-Sync" : "📌 Custom"}
                      </span>
                    </div>
                    <div style={{ fontSize: 10.5, color: C.gray2, marginTop: 2 }}>{item.name || item.symbol}</div>
                  </div>
                </div>

                {/* Price & Change Pill */}
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: 14, fontWeight: 900, color: C.white }}>
                    {item.price > 0 ? `₹${item.price.toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : "--"}
                  </div>
                  <div style={{
                    fontSize: 10.5, fontWeight: 800,
                    color: item.price > 0 ? (item.isPositive ? C.emerald : C.rose) : C.gray2,
                    display: "inline-flex", alignItems: "center", gap: 3, marginTop: 2
                  }}>
                    {item.price > 0 ? `${item.isPositive ? "▲" : "▼"} ${item.chg}` : "--"}
                  </div>
                </div>
              </div>

              {/* Bottom Action & Signal Ribbon */}
              <div style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                paddingTop: 8, borderTop: `1px solid ${C.border}`, marginTop: 2
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <SignalBadge signal={item.signal || "MONITORING"} type={item.signalType || "monitoring"} />
                  <span style={{ fontSize: 10, color: C.gray2 }}>
                    Target: <b style={{ color: item.target && item.target !== "--" ? C.emerald : C.gray2 }}>{item.target || "--"}</b>
                  </span>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <button
                    onClick={() => onOpenTradeModal({
                      symbol: item.symbol,
                      price: item.price,
                      type: item.signalType === "sell" ? "SELL" : "BUY",
                      target: item.target && item.target !== "--" ? item.target : "--",
                      sl: item.sl && item.sl !== "--" ? item.sl : "--",
                      qty: 10
                    })}
                    style={{
                      background: item.signalType === "sell" ? "rgba(239,68,68,0.12)" : "rgba(16,185,129,0.12)",
                      border: `1px solid ${item.signalType === "sell" ? C.rose : C.emerald}`,
                      borderRadius: 8, padding: "5px 10px",
                      fontSize: 11, fontWeight: 800,
                      color: item.signalType === "sell" ? C.rose : C.emerald,
                      cursor: "pointer"
                    }}
                  >
                    ⚡ Trade Order
                  </button>

                  <button
                    onClick={() => removeTicker(item.id)}
                    title="Remove stock from watchlist"
                    style={{
                      background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)",
                      borderRadius: 8, width: 30, height: 30, color: C.rose, cursor: "pointer",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      transition: "all 0.2s ease"
                    }}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                      <path d="M3 6H5H21" stroke={C.rose} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <path d="M8 6V4C8 3.46957 8.21071 2.96086 8.58579 2.58579C8.96086 2.21071 9.46957 2 10 2H14C14.5304 2 15.0391 2.21071 15.4142 2.58579C15.7893 2.96086 16 3.46957 16 4V6M19 6V20C19 20.5304 18.7893 21.0391 18.4142 21.4142C18.0391 21.7893 17.5304 22 17 22H7C6.46957 22 5.96086 21.7893 5.58579 21.4142C5.21071 21.0391 5 20.5304 5 20V6H19Z" stroke={C.rose} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          ));
        })()}
      </div>
    </div>
  );
}
