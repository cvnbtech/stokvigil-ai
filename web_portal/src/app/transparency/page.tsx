"use client";

import React from "react";
import Link from "next/link";
import AuditLedgerView from "../../components/AuditLedgerView";

export default function TransparencyPage() {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#030712",
        color: "#f8fafc",
        fontFamily: "Inter, system-ui, sans-serif",
        padding: "32px 20px 80px 20px",
      }}
    >
      <div style={{ maxWidth: 1100, margin: "0 auto", display: "flex", flexDirection: "column", gap: 32 }}>
        {/* Navigation Bar */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderBottom: "1px solid rgba(255,255,255,0.08)",
            paddingBottom: 20,
          }}
        >
          <Link href="/" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none" }}>
            <div
              style={{
                width: 38,
                height: 38,
                borderRadius: 12,
                background: "linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 18,
                fontWeight: 900,
                color: "#030712",
              }}
            >
              ⚡
            </div>
            <div>
              <div style={{ fontSize: 18, fontWeight: 900, color: "#ffffff" }}>STOKVIGIL AI</div>
              <div style={{ fontSize: 10, color: "#06b6d4", fontWeight: 700, letterSpacing: "0.08em" }}>
                TRANSPARENCY & AUDIT LEDGER
              </div>
            </div>
          </Link>

          <Link
            href="/"
            style={{
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
              gap: 6,
            }}
          >
            ← Back to Terminal
          </Link>
        </div>

        {/* Reusable Audit Ledger View Component */}
        <AuditLedgerView />
      </div>
    </div>
  );
}
