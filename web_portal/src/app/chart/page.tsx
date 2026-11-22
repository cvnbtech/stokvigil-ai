"use client";

import React, { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import { BACKEND_URL } from "../../components/ui/DesignTokens";

const LightweightCandleChart = dynamic(
  () => import("../../components/LightweightCandleChart"),
  {
    ssr: false,
    loading: () => (
      <div
        style={{
          height: "60vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#64748b",
          fontFamily: "monospace",
          fontSize: 13,
        }}
      >
        ⚡ Initializing High-Speed Candlestick Engine...
      </div>
    ),
  }
);

function ChartContent() {
  const searchParams = useSearchParams();
  const rawSymbol = searchParams.get("symbol") || "RELIANCE";
  const exchange = searchParams.get("exchange") || "NSE";
  const cleanSymbol = rawSymbol.replace(".NS", "").replace(".BO", "").trim().toUpperCase();

  const exchangeUrl =
    exchange === "BSE"
      ? `https://www.bseindia.com/stock-share-price/${cleanSymbol}/`
      : `https://www.nseindia.com/get-quotes/equity?symbol=${cleanSymbol}`;

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#030712",
        color: "#f8fafc",
        fontFamily: "Inter, system-ui, sans-serif",
        padding: "16px 14px 40px 14px",
      }}
    >
      <div style={{ maxWidth: 1200, margin: "0 auto", display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Top Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 12,
            borderBottom: "1px solid rgba(255,255,255,0.08)",
            paddingBottom: 14,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Link
              href="/"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "6px 12px",
                borderRadius: 8,
                background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.1)",
                color: "#94a3b8",
                textDecoration: "none",
                fontSize: 12,
                fontWeight: 700,
              }}
            >
              ← Back to App
            </Link>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 20, fontWeight: 900, color: "#ffffff", letterSpacing: "0.03em" }}>
                  {cleanSymbol}
                </span>
                <span
                  style={{
                    fontSize: 11,
                    padding: "2px 7px",
                    borderRadius: 6,
                    background: "rgba(6, 182, 212, 0.15)",
                    border: "1px solid #06b6d4",
                    color: "#06b6d4",
                    fontWeight: 800,
                  }}
                >
                  {exchange}
                </span>
              </div>
              <div style={{ fontSize: 10, color: "#64748b", fontWeight: 600 }}>
                StokVigil AI Surveillance & Technical Chart
              </div>
            </div>
          </div>

          {/* Quick Action Outlinks */}
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <a
              href={exchangeUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                padding: "6px 12px",
                borderRadius: 8,
                background: "rgba(16, 185, 129, 0.15)",
                border: "1px solid rgba(16, 185, 129, 0.4)",
                color: "#34d399",
                textDecoration: "none",
                fontSize: 11,
                fontWeight: 700,
              }}
            >
              ↗ {exchange} Official
            </a>
          </div>
        </div>

        {/* Interactive Lightweight Candlestick Chart */}
        <div
          style={{
            background: "#080b16",
            borderRadius: 16,
            border: "1px solid rgba(6, 182, 212, 0.2)",
            boxShadow: "0 8px 32px rgba(0, 0, 0, 0.4)",
            overflow: "hidden",
            padding: 8,
          }}
        >
          <LightweightCandleChart
            symbol={cleanSymbol}
            backendUrl={BACKEND_URL}
            isMaximized={true}
          />
        </div>
      </div>
    </div>
  );
}

export default function ChartPage() {
  return (
    <Suspense
      fallback={
        <div
          style={{
            minHeight: "100vh",
            background: "#030712",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#64748b",
            fontFamily: "monospace",
          }}
        >
          Loading chart...
        </div>
      }
    >
      <ChartContent />
    </Suspense>
  );
}
