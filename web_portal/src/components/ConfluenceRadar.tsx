"use client";

import React from "react";

export interface FactorBreakdown {
  technicals: number;
  flow: number;
  forensics: number;
  catalysts: number;
}

interface ConfluenceRadarProps {
  factors: FactorBreakdown;
  size?: number;
  showLabels?: boolean;
}

export default function ConfluenceRadar({
  factors,
  size = 200,
  showLabels = true
}: ConfluenceRadarProps) {
  if (!factors) return null;

  const t = Math.max(0, Math.min(100, Number(factors.technicals != null ? factors.technicals : 0)));
  const fl = Math.max(0, Math.min(100, Number(factors.flow != null ? factors.flow : 0)));
  const fo = Math.max(0, Math.min(100, Number(factors.forensics != null ? factors.forensics : 0)));
  const c = Math.max(0, Math.min(100, Number(factors.catalysts != null ? factors.catalysts : 0)));

  const center = size / 2;
  const radius = size * 0.36;

  // 4 Axis Points: 0: Top (Technicals), 1: Right (Flow), 2: Bottom (Forensics), 3: Left (Catalysts)
  const pTop = { x: center, y: center - radius * (t / 100) };
  const pRight = { x: center + radius * (fl / 100), y: center };
  const pBottom = { x: center, y: center + radius * (fo / 100) };
  const pLeft = { x: center - radius * (c / 100), y: center };

  const polygonPoints = `${pTop.x},${pTop.y} ${pRight.x},${pRight.y} ${pBottom.x},${pBottom.y} ${pLeft.x},${pLeft.y}`;

  // Grid levels at 25%, 50%, 75%, 100%
  const gridLevels = [0.25, 0.5, 0.75, 1.0];

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", position: "relative" }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Background Grid Rings */}
        {gridLevels.map((lvl) => {
          const r = radius * lvl;
          const pts = `${center},${center - r} ${center + r},${center} ${center},${center + r} ${center - r},${center}`;
          return (
            <polygon
              key={lvl}
              points={pts}
              fill="none"
              stroke="rgba(255, 255, 255, 0.08)"
              strokeWidth="1"
              strokeDasharray={lvl === 1.0 ? "none" : "2,2"}
            />
          );
        })}

        {/* Axis Crosshairs */}
        <line x1={center} y1={center - radius} x2={center} y2={center + radius} stroke="rgba(255, 255, 255, 0.1)" strokeWidth="1" />
        <line x1={center - radius} y1={center} x2={center + radius} y2={center} stroke="rgba(255, 255, 255, 0.1)" strokeWidth="1" />

        {/* Shaded Confluence Area */}
        <polygon
          points={polygonPoints}
          fill="rgba(6, 182, 212, 0.25)"
          stroke="#06b6d4"
          strokeWidth="2"
          strokeLinejoin="round"
          style={{ filter: "drop-shadow(0 0 6px rgba(6, 182, 212, 0.4))" }}
        />

        {/* Vertex Dots */}
        {[pTop, pRight, pBottom, pLeft].map((pt, i) => (
          <circle
            key={i}
            cx={pt.x}
            cy={pt.y}
            r="3.5"
            fill="#06b6d4"
            stroke="#080B16"
            strokeWidth="1.5"
          />
        ))}

        {/* Center Point */}
        <circle cx={center} cy={center} r="2" fill="rgba(255, 255, 255, 0.3)" />
      </svg>

      {/* Outer Labels */}
      {showLabels && (
        <div style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "6px 16px",
          width: "100%",
          maxWidth: size + 60,
          marginTop: 4,
          fontSize: 10,
          fontWeight: 700
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 4, color: "#94a3b8" }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#06b6d4" }}></span>
            <span>Technicals:</span>
            <span style={{ color: "#fff", marginLeft: "auto" }}>{factors.technicals != null ? `${t}/100` : "-"}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 4, color: "#94a3b8" }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#10b981" }}></span>
            <span>Flow:</span>
            <span style={{ color: "#fff", marginLeft: "auto" }}>{factors.flow != null ? `${fl}/100` : "-"}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 4, color: "#94a3b8" }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#3b82f6" }}></span>
            <span>Forensics:</span>
            <span style={{ color: "#fff", marginLeft: "auto" }}>{factors.forensics != null ? `${fo}/100` : "-"}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 4, color: "#94a3b8" }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#f59e0b" }}></span>
            <span>Catalyst:</span>
            <span style={{ color: "#fff", marginLeft: "auto" }}>{factors.catalysts != null ? `${c}/100` : "-"}</span>
          </div>
        </div>
      )}
    </div>
  );
}
