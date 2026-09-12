"use client";
import React from "react";
import { C } from "../ui/DesignTokens";
import { Btn } from "../ui/UiAtoms";

export interface TradeModalData {
  symbol: string;
  price: number;
  type: "BUY" | "SELL";
  target: string;
  sl: string;
}

interface TradeOrderModalProps {
  tradeData: TradeModalData;
  orderQty: number;
  setOrderQty: React.Dispatch<React.SetStateAction<number>>;
  orderType: "MARKET" | "LIMIT";
  setOrderType: (t: "MARKET" | "LIMIT") => void;
  limitPrice: string;
  setLimitPrice: (p: string) => void;
  targetPriceInput: string;
  setTargetPriceInput: (p: string) => void;
  stopLossPriceInput: string;
  setStopLossPriceInput: (p: string) => void;
  orderSending: boolean;
  orderSent: boolean;
  onClose: () => void;
  onExecute: () => void;
}

export default function TradeOrderModal({
  tradeData,
  orderQty,
  setOrderQty,
  orderType,
  setOrderType,
  limitPrice,
  setLimitPrice,
  targetPriceInput,
  setTargetPriceInput,
  stopLossPriceInput,
  setStopLossPriceInput,
  orderSending,
  orderSent,
  onClose,
  onExecute,
}: TradeOrderModalProps) {
  return (
    <div style={{
      position: "fixed", inset: 0,
      background: "rgba(6,8,18,0.92)", backdropFilter: "blur(16px)",
      display: "flex", alignItems: "center", justifyContent: "center",
      padding: 20, zIndex: 60,
    }}>
      <div className="anim-fadeup" style={{
        width: "100%", maxWidth: 390, background: C.bgCard,
        border: `1.5px solid ${tradeData.type === "BUY" ? "rgba(16,185,129,0.5)" : "rgba(239,68,68,0.5)"}`,
        borderRadius: 22, padding: 22,
        boxShadow: "0 20px 50px rgba(0,0,0,0.8)",
      }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{
              background: tradeData.type === "BUY" ? "rgba(16,185,129,0.2)" : "rgba(239,68,68,0.2)",
              color: tradeData.type === "BUY" ? C.emerald : C.rose,
              border: `1px solid ${tradeData.type === "BUY" ? C.emerald : C.rose}`,
              borderRadius: 10, padding: "4px 10px", fontSize: 12, fontWeight: 900,
            }}>
              {tradeData.type} ORDER
            </div>
            <div style={{ fontSize: 16, fontWeight: 900, color: C.white }}>{tradeData.symbol}</div>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", color: C.gray1, fontSize: 18, cursor: "pointer" }}>✕</button>
        </div>

        {orderSent ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{
              background: "rgba(16,185,129,0.12)", border: `1px solid rgba(16,185,129,0.4)`,
              borderRadius: 16, padding: 16, textAlign: "center",
            }}>
              <div style={{ fontSize: 28, marginBottom: 6 }}>🎉</div>
              <div style={{ fontSize: 14, fontWeight: 900, color: C.emerald }}>Order Executed via ICICI Breeze!</div>
              <div style={{ fontSize: 11, color: C.gray1, marginTop: 4, lineHeight: 1.5 }}>
                Placed <b>{tradeData.type}</b> order for <b>{orderQty} shares</b> of {tradeData.symbol} at <b>₹{(orderType === "LIMIT" && limitPrice ? parseFloat(limitPrice) || tradeData.price : tradeData.price).toFixed(2)}</b> (Total: ₹{(orderQty * (orderType === "LIMIT" && limitPrice ? parseFloat(limitPrice) || tradeData.price : tradeData.price)).toLocaleString()}).
              </div>
              <div style={{ fontSize: 10, color: C.cyan, fontWeight: 700, marginTop: 8 }}>
                📱 Execution Receipt sent to @StokVigilAi_bot on Telegram
              </div>
            </div>
            <Btn variant="primary" onClick={onClose}>
              Done
            </Btn>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {/* Price & Order Type selector */}
            <div style={{ display: "flex", gap: 8 }}>
              {(["MARKET", "LIMIT"] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setOrderType(t)}
                  style={{
                    flex: 1, padding: "9px 0", borderRadius: 10,
                    fontSize: 11.5, fontWeight: 800, cursor: "pointer",
                    background: orderType === t ? "rgba(6,182,212,0.16)" : "#080B16",
                    color: orderType === t ? C.cyan : C.gray1,
                    border: `1.5px solid ${orderType === t ? C.cyan : C.border}`,
                    transition: "all 0.2s ease",
                  }}
                >
                  {t} ORDER
                </button>
              ))}
            </div>

            {/* Order Type Explanation Cards & Custom Limit Input */}
            {orderType === "LIMIT" ? (
              <div style={{ background: "#080B16", border: `1px solid ${C.borderCyan}`, borderRadius: 14, padding: 14, display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ fontSize: 10, color: C.cyan, textTransform: "uppercase", fontWeight: 800 }}>Custom Limit Price (₹)</span>
                  <span style={{ fontSize: 10, color: C.gray2, fontWeight: 700 }}>LTP: ₹{tradeData.price.toFixed(2)}</span>
                </div>
                <input
                  type="number"
                  step="0.05"
                  value={limitPrice}
                  onChange={e => setLimitPrice(e.target.value)}
                  placeholder={tradeData.price.toFixed(2)}
                  style={{
                    background: "#04060E", border: `1px solid ${C.borderCyan}`, borderRadius: 10,
                    padding: "10px 14px", fontSize: 16, fontWeight: 800, color: C.cyan, outline: "none",
                    width: "100%", fontFamily: "Inter, sans-serif"
                  }}
                />
                <div style={{ fontSize: 10.5, color: C.gray1, lineHeight: 1.45, background: "rgba(6,182,212,0.06)", borderRadius: 8, padding: 8, marginTop: 2 }}>
                  💡 <b>What is a Limit Order?</b> Sets the maximum price (₹{limitPrice || tradeData.price.toFixed(2)}) you are willing to pay. Triggers <b>only if market price reaches or drops below</b> your limit.
                </div>
              </div>
            ) : (
              <div style={{ background: "rgba(6,182,212,0.06)", border: `1px dashed ${C.borderCyan}`, borderRadius: 12, padding: "10px 12px" }}>
                <div style={{ fontSize: 11, fontWeight: 800, color: C.cyan, marginBottom: 2 }}>⚡ What is a Market Order?</div>
                <div style={{ fontSize: 10.5, color: C.gray1, lineHeight: 1.45 }}>
                  Executes immediately at the best available current market price (LTP: <b>₹{tradeData.price.toFixed(2)}</b>). Guarantees instant execution.
                </div>
              </div>
            )}

            {/* Quantity Stepper & Manual Input Control */}
            <div style={{ background: "#080B16", border: `1px solid ${C.border}`, borderRadius: 14, padding: 14 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                <span style={{ fontSize: 10, color: C.gray2, textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.05em" }}>Quantity (Shares)</span>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 8, width: "100%" }}>
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    setOrderQty(prev => Math.max(1, prev - 1));
                  }}
                  style={{
                    width: 40, height: 40, flexShrink: 0, borderRadius: 10,
                    background: "rgba(6,182,212,0.1)", border: `1.5px solid ${C.borderCyan}`,
                    color: C.cyan, fontSize: 22, fontWeight: 900, cursor: "pointer",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    lineHeight: 1, padding: 0
                  }}
                >-</button>

                <input
                  type="number"
                  min="1"
                  value={orderQty}
                  onChange={e => {
                    const val = parseInt(e.target.value, 10);
                    setOrderQty(isNaN(val) ? 1 : Math.max(1, val));
                  }}
                  style={{
                    flex: 1, minWidth: 0, textAlign: "center", background: "#04060E",
                    border: `1.5px solid ${C.borderCyan}`, borderRadius: 10,
                    padding: "8px 0", color: C.white, fontSize: 22, fontWeight: 900, outline: "none",
                    fontFamily: "Inter, sans-serif"
                  }}
                />

                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    setOrderQty(prev => prev + 1);
                  }}
                  style={{
                    width: 40, height: 40, flexShrink: 0, borderRadius: 10,
                    background: "rgba(6,182,212,0.1)", border: `1.5px solid ${C.borderCyan}`,
                    color: C.cyan, fontSize: 22, fontWeight: 900, cursor: "pointer",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    lineHeight: 1, padding: 0
                  }}
                >+</button>
              </div>
            </div>

            {/* Financial Breakdown & Bracket Order Parameters */}
            <div style={{ background: "#080B16", border: `1px solid ${C.border}`, borderRadius: 14, padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11.5 }}>
                <span style={{ color: C.gray1 }}>Execution Price:</span>
                <span style={{ fontWeight: 800, color: C.white }}>₹{orderType === "LIMIT" && limitPrice ? parseFloat(limitPrice).toFixed(2) : tradeData.price.toFixed(2)}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11.5 }}>
                <span style={{ color: C.gray1 }}>Total Order Value:</span>
                <span style={{ fontWeight: 900, color: C.cyan }}>₹{(orderQty * (orderType === "LIMIT" && limitPrice ? parseFloat(limitPrice) || tradeData.price : tradeData.price)).toLocaleString("en-IN", { maximumFractionDigits: 2 })}</span>
              </div>

              <div style={{ height: 1, background: C.border }} />

              {/* Bracket Order (Target & Stop Loss Input) */}
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ fontSize: 10, color: C.gray2, textTransform: "uppercase", fontWeight: 800, letterSpacing: "0.05em" }}>
                  🛡️ Auto Risk Management (Bracket Order)
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                  {/* Target Input */}
                  <div style={{ background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.3)", borderRadius: 10, padding: 8 }}>
                    <div style={{ fontSize: 9.5, color: C.emerald, textTransform: "uppercase", fontWeight: 800, marginBottom: 4 }}>🎯 Target (₹)</div>
                    <input
                      type="number"
                      value={targetPriceInput}
                      onChange={e => setTargetPriceInput(e.target.value)}
                      placeholder="Optional"
                      style={{
                        background: "#04060E", border: "1px solid rgba(16,185,129,0.4)", borderRadius: 6,
                        padding: "4px 8px", fontSize: 13, fontWeight: 800, color: C.emerald, outline: "none",
                        width: "100%", fontFamily: "Inter, sans-serif"
                      }}
                    />
                  </div>

                  {/* Stop Loss Input */}
                  <div style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 10, padding: 8 }}>
                    <div style={{ fontSize: 9.5, color: C.rose, textTransform: "uppercase", fontWeight: 800, marginBottom: 4 }}>🛡️ Stop Loss (₹)</div>
                    <input
                      type="number"
                      value={stopLossPriceInput}
                      onChange={e => setStopLossPriceInput(e.target.value)}
                      placeholder="Optional"
                      style={{
                        background: "#04060E", border: "1px solid rgba(239,68,68,0.4)", borderRadius: 6,
                        padding: "4px 8px", fontSize: 13, fontWeight: 800, color: C.rose, outline: "none",
                        width: "100%", fontFamily: "Inter, sans-serif"
                      }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Submit CTA */}
            <Btn
              variant={tradeData.type === "BUY" ? "primary" : "danger"}
              onClick={onExecute}
              disabled={orderSending}
            >
              {orderSending ? "⚡ Sending Order via Breeze…" : "⚡ Confirm & Send Order via Breeze →"}
            </Btn>
          </div>
        )}
      </div>
    </div>
  );
}
