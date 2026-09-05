"use client";

import React, { useRef, useState } from "react";
import ConfluenceRadar, { FactorBreakdown } from "./ConfluenceRadar";

export interface AlphaCardData {
  symbol: string;
  title: string;
  catalyst: string;
  confluenceScore: number;
  bias: string;
  targetPrice: string;
  stopLoss: string;
  entryRange?: string;
  riskReward?: string;
  reasons: string[];
  factors?: FactorBreakdown;
  time?: string;
}

interface ShareAlphaCardModalProps {
  alert: AlphaCardData;
  onClose: () => void;
}

export default function ShareAlphaCardModal({ alert, onClose }: ShareAlphaCardModalProps) {
  const [downloading, setDownloading] = useState(false);
  const [copied, setCopied] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const factors = alert.factors || null;

  const shareText = `⚡ STOKVIGIL AI ALPHA SIGNAL ⚡\n\n🎯 Symbol: #${alert.symbol} (NSE)\n📈 Confluence Score: ${alert.confluenceScore}/100\n🔥 Catalyst: ${alert.catalyst}\n\n🎯 Target: ${alert.targetPrice || "-"}\n🛡️ Stop Loss: ${alert.stopLoss || "-"}\n⚖️ R:R Ratio: ${alert.riskReward || "-"}\n\nKey Insights:\n${alert.reasons.slice(0, 2).map(r => `• ${r}`).join("\n")}\n\nAutomated surveillance via StokVigil AI 🛡️`;

  const handleCopyText = async () => {
    try {
      await navigator.clipboard.writeText(shareText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch (e) {
      console.error("Failed to copy", e);
    }
  };

  const handleShareTwitter = () => {
    const tweetUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}`;
    window.open(tweetUrl, "_blank", "noopener,noreferrer");
  };

  const handleShareWhatsApp = () => {
    const waUrl = `https://api.whatsapp.com/send?text=${encodeURIComponent(shareText)}`;
    window.open(waUrl, "_blank", "noopener,noreferrer");
  };

  const handleDownloadImage = () => {
    setDownloading(true);
    try {
      const canvas = document.createElement("canvas");
      canvas.width = 1080;
      canvas.height = 1080;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      // Dark background gradient
      const bgGrad = ctx.createLinearGradient(0, 0, 1080, 1080);
      bgGrad.addColorStop(0, "#080B16");
      bgGrad.addColorStop(1, "#0B1120");
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, 1080, 1080);

      // Outer border
      ctx.strokeStyle = "rgba(6, 182, 212, 0.35)";
      ctx.lineWidth = 4;
      ctx.strokeRect(30, 30, 1020, 1020);

      // Top branding banner
      ctx.fillStyle = "#06b6d4";
      ctx.font = "bold 28px Inter, system-ui, sans-serif";
      ctx.fillText("STOKVIGIL AI", 70, 95);

      ctx.fillStyle = "#94a3b8";
      ctx.font = "600 20px Inter, system-ui, sans-serif";
      ctx.fillText("INSTITUTIONAL ALPHA SURVEILLANCE", 270, 95);

      // Divider
      ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(70, 125);
      ctx.lineTo(1010, 125);
      ctx.stroke();

      // Symbol & Score Badge
      ctx.fillStyle = "#ffffff";
      ctx.font = "900 64px Inter, system-ui, sans-serif";
      ctx.fillText(alert.symbol, 70, 215);

      // Confluence Badge Pill
      ctx.fillStyle = "rgba(16, 185, 129, 0.2)";
      ctx.fillRect(70, 245, 340, 56);
      ctx.strokeStyle = "#10b981";
      ctx.lineWidth = 2;
      ctx.strokeRect(70, 245, 340, 56);

      ctx.fillStyle = "#10b981";
      ctx.font = "bold 26px Inter, system-ui, sans-serif";
      ctx.fillText(`CONFLUENCE: ${alert.confluenceScore}/100`, 90, 283);

      // Catalyst title
      ctx.fillStyle = "#38bdf8";
      ctx.font = "bold 28px Inter, system-ui, sans-serif";
      ctx.fillText(`⚡ ${alert.catalyst}`, 70, 345);

      ctx.fillStyle = "#f1f5f9";
      ctx.font = "500 24px Inter, system-ui, sans-serif";
      ctx.fillText(alert.title.length > 55 ? alert.title.substring(0, 52) + "..." : alert.title, 70, 385);

      // Tactical Levels Box
      ctx.fillStyle = "rgba(6, 182, 212, 0.08)";
      ctx.fillRect(70, 430, 940, 140);
      ctx.strokeStyle = "rgba(6, 182, 212, 0.25)";
      ctx.strokeRect(70, 430, 940, 140);

      // Target
      ctx.fillStyle = "#94a3b8";
      ctx.font = "600 20px Inter, system-ui, sans-serif";
      ctx.fillText("TARGET 1", 110, 475);
      ctx.fillStyle = "#10b981";
      ctx.font = "900 36px Inter, system-ui, sans-serif";
      ctx.fillText(alert.targetPrice || "-", 110, 525);

      // Stop Loss
      ctx.fillStyle = "#94a3b8";
      ctx.font = "600 20px Inter, system-ui, sans-serif";
      ctx.fillText("STOP LOSS", 430, 475);
      ctx.fillStyle = "#f43f5e";
      ctx.font = "900 36px Inter, system-ui, sans-serif";
      ctx.fillText(alert.stopLoss || "-", 430, 525);

      // Risk Reward
      ctx.fillStyle = "#94a3b8";
      ctx.font = "600 20px Inter, system-ui, sans-serif";
      ctx.fillText("RISK:REWARD", 750, 475);
      ctx.fillStyle = "#06b6d4";
      ctx.font = "900 36px Inter, system-ui, sans-serif";
      ctx.fillText(alert.riskReward || "-", 750, 525);

      // 4 Pillars Box (Rendered only when real factors exist)
      if (factors) {
        ctx.fillStyle = "rgba(255, 255, 255, 0.03)";
        ctx.fillRect(70, 600, 940, 180);
        ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
        ctx.strokeRect(70, 600, 940, 180);

        ctx.fillStyle = "#cbd5e1";
        ctx.font = "bold 22px Inter, system-ui, sans-serif";
        ctx.fillText("INSTITUTIONAL 4-PILLAR CONFLUENCE BREAKDOWN", 100, 645);

        const pColWidth = 210;
        const pillars = [
          { name: "Technicals", val: factors.technicals, col: "#06b6d4" },
          { name: "Smart Flow", val: factors.flow, col: "#10b981" },
          { name: "Forensics", val: factors.forensics, col: "#3b82f6" },
          { name: "Catalyst", val: factors.catalysts, col: "#f59e0b" },
        ];

        pillars.forEach((p, idx) => {
          const x = 100 + (idx * pColWidth);
          ctx.fillStyle = "#94a3b8";
          ctx.font = "600 18px Inter, system-ui, sans-serif";
          ctx.fillText(p.name, x, 695);

          ctx.fillStyle = p.col;
          ctx.font = "bold 32px Inter, system-ui, sans-serif";
          ctx.fillText(p.val != null ? `${p.val}/100` : "-", x, 740);
        });
      }

      // Key Evidence Bullet Points
      ctx.fillStyle = "#e2e8f0";
      ctx.font = "500 22px Inter, system-ui, sans-serif";
      alert.reasons.slice(0, 2).forEach((r, idx) => {
        ctx.fillText(`• ${r.length > 70 ? r.substring(0, 67) + "..." : r}`, 80, 830 + (idx * 40));
      });

      // Footer
      ctx.fillStyle = "#64748b";
      ctx.font = "500 18px Inter, system-ui, sans-serif";
      ctx.fillText("Audited by StokVigil AI • Non-repudiation verified on NSE • 100% Quantitative", 70, 980);

      ctx.fillStyle = "#38bdf8";
      ctx.font = "bold 20px Inter, system-ui, sans-serif";
      ctx.fillText("stokvigil.ai", 880, 980);

      // Trigger automatic download
      const dataUrl = canvas.toDataURL("image/png");
      const link = document.createElement("a");
      link.download = `stokvigil-alpha-${alert.symbol.toLowerCase()}.png`;
      link.href = dataUrl;
      link.click();
    } catch (e) {
      console.error("Canvas export failed", e);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div style={{
      position: "fixed",
      inset: 0,
      background: "rgba(3, 7, 18, 0.85)",
      backdropFilter: "blur(12px)",
      zIndex: 9999,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: 16,
    }}>
      <div style={{
        background: "#080B16",
        border: "1.5px solid rgba(6, 182, 212, 0.35)",
        borderRadius: 24,
        padding: 24,
        maxWidth: 520,
        width: "100%",
        boxShadow: "0 24px 64px rgba(0, 0, 0, 0.8), 0 0 40px rgba(6, 182, 212, 0.15)",
        display: "flex",
        flexDirection: "column",
        gap: 16,
        maxHeight: "90vh",
        overflowY: "auto"
      }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 800, color: "#06b6d4", textTransform: "uppercase", letterSpacing: "0.08em" }}>
              1-Tap Shareable
            </div>
            <div style={{ fontSize: 18, fontWeight: 900, color: "#ffffff" }}>
              Institutional Alpha Card
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "rgba(255, 255, 255, 0.05)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              borderRadius: 12,
              width: 34,
              height: 34,
              color: "#94a3b8",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 16
            }}
          >
            ✕
          </button>
        </div>

        {/* Card Visual Preview */}
        <div style={{
          background: "linear-gradient(135deg, #0B1120 0%, #030712 100%)",
          border: "1px solid rgba(6, 182, 212, 0.25)",
          borderRadius: 18,
          padding: 18,
          display: "flex",
          flexDirection: "column",
          gap: 12
        }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
              <span style={{ fontSize: 24, fontWeight: 900, color: "#ffffff" }}>{alert.symbol}</span>
              <span style={{ fontSize: 11, fontWeight: 800, color: "#06b6d4" }}>NSE</span>
            </div>
            <div style={{
              background: "rgba(16, 185, 129, 0.15)",
              border: "1px solid rgba(16, 185, 129, 0.4)",
              borderRadius: 20,
              padding: "4px 10px",
              fontSize: 11,
              fontWeight: 800,
              color: "#10b981"
            }}>
              🎯 {alert.confluenceScore}/100 SCORE
            </div>
          </div>

          <div style={{ fontSize: 13, fontWeight: 800, color: "#e2e8f0", lineHeight: 1.4 }}>
            {alert.title}
          </div>

          {/* Tactical Targets Grid */}
          <div style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr 1fr",
            gap: 8,
            background: "rgba(6, 182, 212, 0.06)",
            border: "1px solid rgba(6, 182, 212, 0.2)",
            borderRadius: 12,
            padding: "8px 12px",
            textAlign: "center"
          }}>
            <div>
              <div style={{ fontSize: 9, color: "#94a3b8", fontWeight: 700 }}>TARGET 1</div>
              <div style={{ fontSize: 13, fontWeight: 900, color: "#10b981" }}>{alert.targetPrice}</div>
            </div>
            <div>
              <div style={{ fontSize: 9, color: "#94a3b8", fontWeight: 700 }}>STOP LOSS</div>
              <div style={{ fontSize: 13, fontWeight: 900, color: "#f43f5e" }}>{alert.stopLoss}</div>
            </div>
            <div>
              <div style={{ fontSize: 9, color: "#94a3b8", fontWeight: 700 }}>R:R RATIO</div>
              <div style={{ fontSize: 13, fontWeight: 900, color: "#06b6d4" }}>{alert.riskReward || "-"}</div>
            </div>
          </div>

          {/* Radar Visualization */}
          {factors && (
            <div style={{ display: "flex", justifyContent: "center", padding: "6px 0" }}>
              <ConfluenceRadar factors={factors} size={150} showLabels={true} />
            </div>
          )}

          <div style={{ fontSize: 9.5, color: "#64748b", textAlign: "center" }}>
            Audited by StokVigil AI • Verified Institutional Signal
          </div>
        </div>

        {/* Share Actions Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <button
            onClick={handleShareWhatsApp}
            style={{
              background: "#128C7E",
              color: "#ffffff",
              border: "none",
              borderRadius: 12,
              padding: "10px 14px",
              fontSize: 12,
              fontWeight: 800,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 6
            }}
          >
            <span>💬</span> Share WhatsApp
          </button>

          <button
            onClick={handleShareTwitter}
            style={{
              background: "#1D9BF0",
              color: "#ffffff",
              border: "none",
              borderRadius: 12,
              padding: "10px 14px",
              fontSize: 12,
              fontWeight: 800,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 6
            }}
          >
            <span>🐦</span> Post to X / Twitter
          </button>

          <button
            onClick={handleDownloadImage}
            disabled={downloading}
            style={{
              background: "rgba(6, 182, 212, 0.15)",
              border: "1.5px solid rgba(6, 182, 212, 0.4)",
              color: "#06b6d4",
              borderRadius: 12,
              padding: "10px 14px",
              fontSize: 12,
              fontWeight: 800,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 6
            }}
          >
            <span>📥</span> {downloading ? "Rendering..." : "Download Card (PNG)"}
          </button>

          <button
            onClick={handleCopyText}
            style={{
              background: copied ? "rgba(16, 185, 129, 0.15)" : "rgba(255, 255, 255, 0.05)",
              border: `1.5px solid ${copied ? "rgba(16, 185, 129, 0.4)" : "rgba(255, 255, 255, 0.1)"}`,
              color: copied ? "#10b981" : "#ffffff",
              borderRadius: 12,
              padding: "10px 14px",
              fontSize: 12,
              fontWeight: 800,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 6
            }}
          >
            <span>{copied ? "✅" : "📋"}</span> {copied ? "Copied!" : "Copy Signal Text"}
          </button>
        </div>
      </div>
    </div>
  );
}
