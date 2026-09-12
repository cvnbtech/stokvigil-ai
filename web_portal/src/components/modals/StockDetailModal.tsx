"use client";
import React from "react";
import { C, HoldingItem } from "../ui/DesignTokens";
import { Btn, SignalBadge } from "../ui/UiAtoms";

interface StockDetailModalProps {
  selectedStock: HoldingItem;
  onClose: () => void;
  onPlaceOrder: (stock: HoldingItem) => void;
}

export default function StockDetailModal({
  selectedStock,
  onClose,
  onPlaceOrder,
}: StockDetailModalProps) {
  return (
    <div style={{
      position: "fixed", inset: 0,
      background: "rgba(6,8,18,0.92)", backdropFilter: "blur(16px)",
      display: "flex", alignItems: "center", justifyContent: "center",
      padding: 20, zIndex: 50,
    }}>
      <div className="anim-fadeup" style={{
        width: "100%", maxWidth: 380, background: C.bgCard,
        border: `1.5px solid ${C.borderCyan}`, borderRadius: 22, padding: 20,
      }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ fontSize: 16, fontWeight: 900, color: C.white }}>
                {selectedStock.name && selectedStock.name !== selectedStock.symbol && !selectedStock.name.endsWith('.BO')
                  ? selectedStock.name
                  : (selectedStock.clean_symbol || selectedStock.symbol.replace(/\.(BO|NS)$/i, ''))}
              </div>
              <SignalBadge signal={selectedStock.signal} type={selectedStock.signalType} />
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 3 }}>
              <span style={{ fontSize: 12, fontWeight: 800, color: C.cyan }}>
                {(selectedStock.clean_symbol || selectedStock.symbol).replace(/\.(BO|NS)$/i, '')}
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
            </div>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", color: C.gray1, fontSize: 18, cursor: "pointer" }}>✕</button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 16 }}>
          <div style={{ background: "#080B16", border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }}>
            <div style={{ fontSize: 10, color: C.gray2, textTransform: "uppercase", fontWeight: 700 }}>Current Price</div>
            <div style={{ fontSize: 16, fontWeight: 900, color: C.white, marginTop: 2 }}>₹{selectedStock.price.toFixed(2)}</div>
            <div style={{ fontSize: 11, color: C.emerald, fontWeight: 800, marginTop: 2 }}>+{selectedStock.pnlPct}%</div>
          </div>

          <div style={{ background: "#080B16", border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }}>
            <div style={{ fontSize: 10, color: C.gray2, textTransform: "uppercase", fontWeight: 700 }}>Total P&L</div>
            <div style={{ fontSize: 16, fontWeight: 900, color: C.emerald, marginTop: 2 }}>+₹{selectedStock.pnl.toLocaleString()}</div>
            <div style={{ fontSize: 11, color: C.gray1, marginTop: 2 }}>Qty {selectedStock.qty}</div>
          </div>

          <div style={{ background: "#080B16", border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }}>
            <div style={{ fontSize: 10, color: C.gray2, textTransform: "uppercase", fontWeight: 700 }}>Day Range</div>
            <div style={{ fontSize: 11, fontWeight: 800, color: C.white, marginTop: 2 }}>
              {selectedStock.dayLow != null && selectedStock.dayHigh != null
                ? `₹${selectedStock.dayLow} – ₹${selectedStock.dayHigh}`
                : "--"}
            </div>
          </div>

          <div style={{ background: "#080B16", border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }}>
            <div style={{ fontSize: 10, color: C.gray2, textTransform: "uppercase", fontWeight: 700 }}>52-Wk High</div>
            <div style={{ fontSize: 11, fontWeight: 800, color: C.cyan, marginTop: 2 }}>
              {selectedStock.high52 != null ? `₹${selectedStock.high52}` : "--"}
            </div>
          </div>
        </div>

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
          <Btn variant="ghost" onClick={onClose}>
            Close
          </Btn>
        </div>
      </div>
    </div>
  );
}
