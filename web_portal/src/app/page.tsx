"use client";
import React, { useState, useRef, useEffect, useCallback } from "react";
import { createClient, SupabaseClient } from "@supabase/supabase-js";

const SUPABASE_URL = process.env.SUPABASE_URL || "https://your-supabase-project.supabase.co";
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY || "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.dummy";
const BACKEND_URL = "";

function decodeSafeBase64(str: string): string {
  if (!str) return "";
  const trimmed = str.trim();
  if (trimmed.startsWith("gAAAAA") && trimmed.length > 50) {
    return "";
  }
  try {
    let base64 = trimmed.replace(/-/g, '+').replace(/_/g, '/');
    while (base64.length % 4 !== 0) {
      base64 += '=';
    }
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    const decoded = new TextDecoder().decode(bytes);
    if (/^[\x20-\x7E\s]+$/.test(decoded) && !decoded.startsWith("gAAAAA")) {
      return decoded;
    }
    if (/^[a-zA-Z0-9_\-~^@#*!]+$/.test(trimmed) && trimmed.length <= 64 && !trimmed.startsWith("gAAAAA")) {
      return trimmed;
    }
    return "";
  } catch {
    if (/^[a-zA-Z0-9_\-~^@#*!]+$/.test(trimmed) && trimmed.length <= 64 && !trimmed.startsWith("gAAAAA")) {
      return trimmed;
    }
    return "";
  }
}

function encodeSafeBase64(str: string): string {
  if (!str) return "";
  try {
    const bytes = new TextEncoder().encode(str);
    let binary = "";
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  } catch {
    return str;
  }
}

const isSupabaseConfigured = Boolean(
  SUPABASE_URL &&
  !SUPABASE_URL.includes("your-supabase-project") &&
  SUPABASE_ANON_KEY &&
  !SUPABASE_ANON_KEY.includes("dummy")
);

const supabase: SupabaseClient | null = isSupabaseConfigured
  ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
  : null;

// ─────────────────────────────────────────────
// DESIGN TOKENS (Vibrant Cyan-Violet Theme)
// ─────────────────────────────────────────────
const C = {
  bg:          "#070913",
  bgCard:      "#0D111E",
  bgCard2:     "#12172A",
  border:      "rgba(255,255,255,0.08)",
  borderCyan:  "rgba(6,182,212,0.35)",
  borderViolet:"rgba(139,92,246,0.35)",
  cyan:        "#06B6D4",
  violet:      "#8B5CF6",
  emerald:     "#10B981",
  rose:        "#EF4444",
  amber:       "#F59E0B",
  white:       "#F8FAFC",
  gray1:       "#94A3B8",
  gray2:       "#64748B",
  gray3:       "#1E293B",
};

// ─────────────────────────────────────────────
// OFFICIAL STOKVIGIL AI LOGO
// ─────────────────────────────────────────────
function TradingAILogo({ size = 48 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 52 52" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="c2_bg" x1="0" y1="0" x2="52" y2="52" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#0D111E" />
          <stop offset="100%" stopColor="#080B16" />
        </linearGradient>
        <linearGradient id="c2_line" x1="4" y1="44" x2="48" y2="6" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#06B6D4" />
          <stop offset="50%" stopColor="#38BDF8" />
          <stop offset="100%" stopColor="#8B5CF6" />
        </linearGradient>
        <filter id="c2_glow" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="1.8" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      <rect x="0" y="0" width="52" height="52" rx="14" fill="url(#c2_bg)" />
      <rect x="0.75" y="0.75" width="50.5" height="50.5" rx="13.2"
            fill="none" stroke="rgba(6,182,212,0.25)" strokeWidth="1.5" />

      {/* Candlesticks Underneath */}
      <line x1="14" y1="18" x2="14" y2="38" stroke="#10B981" strokeWidth="1.2" opacity="0.6" />
      <rect x="12" y="22" width="4" height="12" rx="1" fill="#10B981" opacity="0.85" />

      <line x1="24" y1="24" x2="24" y2="40" stroke="#EF4444" strokeWidth="1.2" opacity="0.6" />
      <rect x="22" y="27" width="4" height="8" rx="1" fill="#EF4444" opacity="0.85" />

      <line x1="34" y1="10" x2="34" y2="36" stroke="#06B6D4" strokeWidth="1.2" opacity="0.6" />
      <rect x="32" y="14" width="4" height="18" rx="1" fill="#06B6D4" opacity="0.9" />

      {/* Overlaid Up-Down-Up Breakout Arrow */}
      <path
        d="M 6,38 L 14,22 L 24,31 L 38,11"
        stroke="url(#c2_line)"
        strokeWidth="3.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        filter="url(#c2_glow)"
      />
      <path
        d="M 44 6 L 32 11 L 38 19 Z"
        fill="url(#c2_line)"
        filter="url(#c2_glow)"
      />
    </svg>
  );
}

function VisibilityOutlinedIcon({ size = 15, color = "currentColor" }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 4.5C7 4.5 2.73 7.61 1 12C2.73 16.39 7 19.5 12 19.5C17 19.5 21.27 16.39 23 12C21.27 7.61 17 4.5 12 4.5ZM12 17C9.24 17 7 14.76 7 12C7 9.24 9.24 7 12 7C14.76 7 17 9.24 17 12C17 14.76 14.76 17 12 17ZM12 9C10.34 9 9 10.34 9 12C9 13.66 10.34 15 12 15C13.66 15 15 13.66 15 12C15 10.34 13.66 9 12 9Z" fill={color}/>
    </svg>
  );
}

function VisibilityOffOutlinedIcon({ size = 15, color = "currentColor" }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 7C14.76 7 17 9.24 17 12C17 12.65 16.87 13.26 16.64 13.83L19.56 16.75C21.07 15.49 22.26 13.86 23 12C21.27 7.61 17 4.5 12 4.5C10.6 4.5 9.26 4.75 8.02 5.2L10.18 7.36C10.74 7.13 11.35 7 12 7ZM2 4.27L4.28 6.55L4.74 7.01C3.08 8.3 1.78 10.02 1 12C2.73 16.39 7 19.5 12 19.5C13.55 19.5 15.03 19.2 16.38 18.66L16.8 19.08L19.73 22L21 20.73L3.27 3L2 4.27ZM7.53 9.8L9.08 11.35C9.03 11.56 9 11.78 9 12C9 13.66 10.34 15 12 15C12.22 15 12.44 14.97 12.65 14.92L14.2 16.47C13.53 16.8 12.79 17 12 17C9.24 17 7 14.76 7 12C7 11.21 7.2 10.47 7.53 9.8ZM11.84 9.02L14.99 12.17C14.98 12.01 15 11.85 15 11.7C15 10.04 13.66 8.7 12 8.7C11.85 8.7 11.69 8.72 11.53 8.73L11.84 9.02Z" fill={color}/>
    </svg>
  );
}

// ─────────────────────────────────────────────
// REUSABLE COMPONENTS
// ─────────────────────────────────────────────
function Card({ children, style, onClick }: { children: React.ReactNode; style?: React.CSSProperties; onClick?: () => void }) {
  return (
    <div
      onClick={onClick}
      style={{
        background: C.bgCard,
        border: `1px solid ${C.border}`,
        borderRadius: 20,
        padding: 16,
        boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
        cursor: onClick ? "pointer" : "default",
        ...style,
      }}
    >
      {children}
    </div>
  );
}

function Btn({
  children, onClick, disabled = false, variant = "primary", style
}: {
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  style?: React.CSSProperties;
}) {
  const base: React.CSSProperties = {
    width: "100%", borderRadius: 14, padding: "13px 16px",
    fontSize: 13, fontWeight: 800, cursor: disabled ? "not-allowed" : "pointer",
    border: "none", outline: "none", transition: "all .2s cubic-bezier(0.16,1,0.3,1)",
    display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
    opacity: disabled ? 0.45 : 1,
  };
  const variants: Record<string, React.CSSProperties> = {
    primary:   { background: `linear-gradient(135deg, ${C.cyan}, #3B82F6, ${C.violet})`, color: "#fff", boxShadow: `0 8px 24px rgba(6,182,212,0.35)` },
    secondary: { background: "rgba(6,182,212,0.08)", color: C.cyan, border: `1.5px solid ${C.borderCyan}` },
    ghost:     { background: C.bgCard2, color: C.gray1, border: `1px solid ${C.border}` },
    danger:    { background: "rgba(239,68,68,0.12)", color: C.rose, border: `1.5px solid rgba(239,68,68,0.3)` },
  };
  return <button style={{ ...base, ...variants[variant], ...style }} onClick={onClick} disabled={disabled}>{children}</button>;
}

function Input({ label, type = "text", value, onChange, placeholder = "", rightAction }: {
  label: string; type?: string; value: string;
  onChange: (v: string) => void; placeholder?: string;
  rightAction?: React.ReactNode;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: C.gray1, textTransform: "uppercase", letterSpacing: "0.08em" }}>{label}</span>
        {rightAction}
      </div>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        style={{
          background: "#080B16", border: `1.5px solid ${C.border}`, borderRadius: 12,
          padding: "12px 14px", fontSize: 13, color: C.white, outline: "none",
          transition: "border-color 0.2s", fontFamily: "Inter, sans-serif",
        }}
        onFocus={e => (e.target.style.borderColor = C.cyan)}
        onBlur={e => (e.target.style.borderColor = C.border)}
      />
    </div>
  );
}

function Badge({ label, color = "cyan" }: { label: string; color?: "cyan" | "emerald" | "rose" | "amber" | "violet" }) {
  const map: Record<string, { bg: string; text: string; border: string }> = {
    cyan:    { bg: "rgba(6,182,212,0.12)",  text: C.cyan,    border: "rgba(6,182,212,0.3)" },
    emerald: { bg: "rgba(16,185,129,0.12)", text: C.emerald, border: "rgba(16,185,129,0.3)" },
    rose:    { bg: "rgba(239,68,68,0.12)",  text: C.rose,    border: "rgba(239,68,68,0.3)" },
    amber:   { bg: "rgba(245,158,11,0.12)", text: C.amber,   border: "rgba(245,158,11,0.3)" },
    violet:  { bg: "rgba(139,92,246,0.12)", text: C.violet,  border: "rgba(139,92,246,0.3)" },
  };
  const m = map[color];
  return (
    <span style={{
      background: m.bg, color: m.text, border: `1px solid ${m.border}`,
      borderRadius: 8, padding: "3px 9px", fontSize: 10, fontWeight: 800,
      letterSpacing: "0.06em", whiteSpace: "nowrap",
    }}>{label}</span>
  );
}

function SignalBadge({ signal, type }: { signal: string; type?: "strong_buy" | "buy" | "sell" | "hold" | "neutral" | string }) {
  const isStrong = type === "strong_buy";
  const isBuy = type === "buy";
  const isSell = type === "sell";
  const isHold = type === "hold" || type === "neutral";

  const bg = isStrong
    ? "linear-gradient(135deg, rgba(16,185,129,0.25), rgba(6,182,212,0.25))"
    : isBuy
      ? "rgba(6,182,212,0.18)"
      : isSell
        ? "rgba(245,158,11,0.18)"
        : "rgba(234,179,8,0.18)";

  const border = isStrong
    ? "rgba(16,185,129,0.5)"
    : isBuy
      ? "rgba(6,182,212,0.4)"
      : isSell
        ? "rgba(245,158,11,0.4)"
        : "rgba(234,179,8,0.4)";

  const color = isStrong ? C.emerald : isBuy ? C.cyan : isSell ? C.amber : "#EAB308";

  return (
    <div style={{
      background: bg, border: `1.5px solid ${border}`,
      borderRadius: 10, padding: "3px 9px",
      display: "inline-flex", alignItems: "center", gap: 5,
      boxShadow: isStrong ? "0 0 10px rgba(16,185,129,0.3)" : "none",
    }}>
      <div style={{
        width: 6, height: 6, borderRadius: "50%",
        background: color,
        boxShadow: `0 0 6px ${color}`,
      }} className={isStrong ? "pulse-live" : ""} />
      <span style={{ fontSize: 10.5, fontWeight: 900, color, letterSpacing: "0.04em" }}>
        {signal}
      </span>
    </div>
  );
}

function Divider({ label }: { label?: string }) {
  if (!label) return <div style={{ height: 1, background: C.border, margin: "4px 0" }} />;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "4px 0" }}>
      <div style={{ flex: 1, height: 1, background: C.border }} />
      <span style={{ fontSize: 11, color: C.gray2, fontWeight: 600 }}>{label}</span>
      <div style={{ flex: 1, height: 1, background: C.border }} />
    </div>
  );
}

// ─────────────────────────────────────────────
// MOCK DATA WITH ENHANCED STATS & ACTION SIGNALS
// ─────────────────────────────────────────────
interface HoldingItem {
  symbol: string;
  qty: number;
  avg: number;
  price: number;
  pnl: number;
  pnlPct: number;
  dayHigh: number;
  dayLow: number;
  high52: number;
  sector: string;
  signal: string;
  signalType: "strong_buy" | "buy" | "sell" | "hold" | "neutral";
}

const HOLDINGS: HoldingItem[] = [];
const ALERTS: any[] = [];
const WATCHLIST_INIT: any[] = [];

// ─────────────────────────────────────────────
// TNC MODAL WITH PROGRESS BAR & GLOW SCROLL
// ─────────────────────────────────────────────
function TncModal({ onAccept, onClose }: { onAccept: () => void; onClose: () => void }) {
  const [hasScrolledToBottom, setHasScrolledToBottom] = useState(false);
  const [scrollProgress, setScrollProgress] = useState(0);
  const bodyRef = useRef<HTMLDivElement>(null);

  const handleScroll = () => {
    const el = bodyRef.current;
    if (!el) return;
    const maxScroll = el.scrollHeight - el.clientHeight;
    const current = el.scrollTop;
    const progress = Math.min(100, Math.round((current / maxScroll) * 100));
    setScrollProgress(progress);

    if (current + el.clientHeight >= el.scrollHeight - 50) {
      setHasScrolledToBottom(true);
    }
  };

  const sections = [
    {
      title: "1. Service Description",
      body: "StokVigil AI is a market intelligence and research watchtower platform. It monitors your ICICI Direct demat holdings every 5 minutes and delivers factual catalyst notifications (block deals, earnings beats, quarterly P&L, debt shifts) during Indian market hours (09:15 AM – 03:30 PM IST, Mon–Fri)."
    },
    {
      title: "2. Zero SEBI Advisory & No Automated Trades",
      body: "StokVigil AI is NOT registered with SEBI as an Investment Advisor. All information provided is strictly 100% factual market data. We do NOT recommend buying, selling, or holding any securities. We do NOT execute automated trades on your behalf. All investment decisions remain 100% in your control."
    },
    {
      title: "3. Credential Security & Vault Storage",
      body: "Your ICICI Breeze API credentials (App Key, Secret Key, Session Token) are encrypted client-side using AES-256 Fernet cipher with SHA-256 PBKDF2 key derivation before vault storage in Supabase PostgreSQL with Row-Level Security (RLS) enabled."
    },
    {
      title: "4. Market Risk Disclaimer",
      body: "Equity market investments carry inherent financial risk. Past performance of any stock, catalyst, or pattern does not guarantee future results. You may lose part or all of your invested capital. Only invest capital you can afford to lose."
    },
    {
      title: "5. Data Privacy Guarantee",
      body: "We do not sell, rent, or share your personal or demat data with third parties. Your credentials are used strictly to retrieve your personal portfolio positions for monitoring."
    },
    {
      title: "6. User Agreement & Account Termination",
      body: "By creating an account, you confirm that you have read, understood, and agreed to these terms. You may delete your account and revoke API access at any time."
    }
  ];

  return (
    <div style={{
      position: "fixed", inset: 0,
      background: "rgba(6,8,18,0.92)",
      backdropFilter: "blur(20px)",
      display: "flex", alignItems: "center", justifyContent: "center",
      zIndex: 100, padding: "20px 16px",
    }}>
      <div className="anim-fadeup" style={{
        width: "100%", maxWidth: 420,
        height: "80vh", maxHeight: "580px",
        background: C.bgCard,
        border: `1.5px solid ${C.borderCyan}`,
        borderRadius: 24,
        display: "flex", flexDirection: "column",
        boxShadow: "0 20px 50px rgba(0,0,0,0.9), 0 0 30px rgba(6,182,212,0.2)",
        overflow: "hidden",
      }}>
        {/* Fixed Header */}
        <div style={{
          padding: "16px 20px 14px",
          borderBottom: `1px solid ${C.border}`,
          display: "flex", alignItems: "center", justifyContent: "space-between",
          background: "#0A0E1A", flexShrink: 0,
        }}>
          <div>
            <div style={{ fontWeight: 900, fontSize: 15, color: C.white, display: "flex", alignItems: "center", gap: 6 }}>
              <span>📄</span> Terms & Conditions
            </div>
            <div style={{ fontSize: 11, color: C.cyan, fontWeight: 600, marginTop: 2 }}>
              StokVigil AI • Updated August 2026
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: C.bgCard2, border: `1px solid ${C.border}`,
              borderRadius: 10, padding: "6px 12px", color: C.gray1,
              cursor: "pointer", fontSize: 13, fontWeight: 700,
            }}
          >
            ✕
          </button>
        </div>

        {/* Scroll Progress Bar */}
        <div style={{ width: "100%", height: 3, background: "#0A0E1A" }}>
          <div style={{
            height: "100%",
            width: `${scrollProgress}%`,
            background: `linear-gradient(90deg, ${C.cyan}, ${C.violet})`,
            transition: "width 0.1s linear",
          }} />
        </div>

        {/* Scrollable Container with Custom Cyan Scrollbar */}
        <div style={{ position: "relative", flex: "1 1 auto", minHeight: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}>
          <div
            ref={bodyRef}
            onScroll={handleScroll}
            className="custom-scroll"
            style={{
              height: "360px",
              maxHeight: "55vh",
              overflowY: "scroll",
              WebkitOverflowScrolling: "touch",
              padding: "16px 20px",
              display: "flex",
              flexDirection: "column",
              gap: 14,
              background: C.bgCard,
            }}
          >
            <div style={{
              fontSize: 11,
              color: hasScrolledToBottom ? C.emerald : C.cyan,
              fontWeight: 700,
              background: hasScrolledToBottom ? "rgba(16,185,129,0.1)" : "rgba(6,182,212,0.1)",
              border: `1px solid ${hasScrolledToBottom ? "rgba(16,185,129,0.3)" : "rgba(6,182,212,0.3)"}`,
              borderRadius: 10, padding: "8px 12px", display: "flex", alignItems: "center", gap: 6,
              flexShrink: 0,
            }}>
              <span>{hasScrolledToBottom ? "✓" : "📜"}</span>
              <span>
                {hasScrolledToBottom
                  ? "You have read all 6 terms! Click Accept below."
                  : `Read progress: ${scrollProgress}% — scroll right bar to finish.`}
              </span>
            </div>

            {sections.map((s, i) => (
              <div key={i} style={{
                background: "#0A0E1A", border: `1px solid ${C.border}`,
                borderRadius: 14, padding: "12px 14px", flexShrink: 0,
              }}>
                <div style={{ fontSize: 12, fontWeight: 800, color: C.cyan, marginBottom: 4 }}>
                  {s.title}
                </div>
                <div style={{ fontSize: 11.5, color: C.gray1, lineHeight: 1.6 }}>
                  {s.body}
                </div>
              </div>
            ))}
            <div style={{ height: 24 }} />
          </div>

          {/* Floating Bouncing Scroll Indicator Icon */}
          {!hasScrolledToBottom && (
            <div className="bounce-indicator" style={{
              position: "absolute",
              bottom: 12,
              left: "50%",
              transform: "translateX(-50%)",
              background: "linear-gradient(135deg, #06B6D4, #8B5CF6)",
              color: "#FFFFFF",
              padding: "6px 14px",
              borderRadius: 20,
              fontSize: 10,
              fontWeight: 800,
              boxShadow: "0 4px 16px rgba(6, 182, 212, 0.5)",
              display: "flex",
              alignItems: "center",
              gap: 6,
              pointerEvents: "none",
              zIndex: 10,
            }}>
              <span>↓ Scroll Down to Read All 6 Terms</span>
            </div>
          )}
        </div>

        {/* Fixed Footer */}
        <div style={{
          padding: "14px 20px 16px",
          borderTop: `1px solid ${C.border}`,
          background: "#0A0E1A",
          display: "flex", flexDirection: "column", gap: 8,
          flexShrink: 0,
        }}>
          <Btn
            variant={hasScrolledToBottom ? "primary" : "ghost"}
            onClick={onAccept}
            disabled={!hasScrolledToBottom}
          >
            <span>{hasScrolledToBottom ? "✓" : "🔒"}</span>
            <span>
              {hasScrolledToBottom
                ? "I Have Read & Accept Terms"
                : "Scroll to Bottom to Accept"}
            </span>
          </Btn>
          <button
            onClick={onClose}
            style={{
              background: "none", border: "none", color: C.gray2,
              fontSize: 11, cursor: "pointer", textAlign: "center", fontWeight: 600
            }}
          >
            Decline & Close
          </button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// DRAGGABLE HORIZONTAL CHIP BAR (NO SCROLLBAR)
// ─────────────────────────────────────────────
function DraggableChipBar({ children }: { children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const isDown = useRef(false);
  const startX = useRef(0);
  const scrollLeft = useRef(0);
  const [dragging, setDragging] = useState(false);

  return (
    <div style={{ position: "relative" }}>
      <div
        ref={ref}
        className="no-scrollbar"
        onMouseDown={e => {
          if (!ref.current) return;
          isDown.current = true;
          setDragging(true);
          startX.current = e.pageX - ref.current.offsetLeft;
          scrollLeft.current = ref.current.scrollLeft;
        }}
        onMouseLeave={() => {
          isDown.current = false;
          setDragging(false);
        }}
        onMouseUp={() => {
          isDown.current = false;
          setDragging(false);
        }}
        onMouseMove={e => {
          if (!isDown.current || !ref.current) return;
          e.preventDefault();
          const x = e.pageX - ref.current.offsetLeft;
          const walk = (x - startX.current) * 1.5;
          ref.current.scrollLeft = scrollLeft.current - walk;
        }}
        style={{
          display: "flex", gap: 8, overflowX: "auto", padding: "2px 0 6px",
          cursor: dragging ? "grabbing" : "grab",
          userSelect: "none",
          WebkitOverflowScrolling: "touch",
        }}
      >
        {children}
      </div>
      <div style={{
        position: "absolute", top: 0, right: 0, bottom: 6, width: 28,
        background: "linear-gradient(to right, transparent, rgba(6,8,18,0.95))",
        pointerEvents: "none", borderRadius: "0 12px 12px 0"
      }} />
    </div>
  );
}

function DraggableVerticalCanvas({ children, className, style }: { children: React.ReactNode; className?: string; style?: React.CSSProperties }) {
  const ref = useRef<HTMLDivElement>(null);
  const isDown = useRef(false);
  const startY = useRef(0);
  const scrollTop = useRef(0);
  const [dragging, setDragging] = useState(false);

  return (
    <div
      ref={ref}
      className={className}
      onMouseDown={e => {
        if (!ref.current) return;
        const target = e.target as HTMLElement;
        if (target.tagName === "BUTTON" || target.tagName === "INPUT" || target.closest("button") || target.closest("input")) return;
        isDown.current = true;
        setDragging(true);
        startY.current = e.pageY - ref.current.offsetTop;
        scrollTop.current = ref.current.scrollTop;
      }}
      onMouseLeave={() => {
        isDown.current = false;
        setDragging(false);
      }}
      onMouseUp={() => {
        isDown.current = false;
        setDragging(false);
      }}
      onMouseMove={e => {
        if (!isDown.current || !ref.current) return;
        e.preventDefault();
        const y = e.pageY - ref.current.offsetTop;
        const walk = (y - startY.current) * 1.4;
        ref.current.scrollTop = scrollTop.current - walk;
      }}
      style={{
        ...style,
        cursor: dragging ? "grabbing" : "grab",
        userSelect: "none",
        WebkitOverflowScrolling: "touch",
        touchAction: "pan-y",
      }}
    >
      {children}
    </div>
  );
}

// ─────────────────────────────────────────────
// MAIN ROOT APP
// ─────────────────────────────────────────────
export default function App() {
  const [screen, setScreen] = useState<"auth" | "app">("auth");
  const [authTab, setAuthTab] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showAuthPassword, setShowAuthPassword] = useState(false);
  const [name, setName]  = useState("");
  const [loading, setLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authSuccess, setAuthSuccess] = useState<string | null>(null);
  const [user, setUser]  = useState<{ id?: string; name: string; email: string } | null>(null);

  const [tncAccepted, setTncAccepted] = useState(false);
  const [showTnc, setShowTnc]         = useState(false);
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotSent, setForgotSent]   = useState(false);
  const [forgotLoading, setForgotLoading] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [newPasswordDone, setNewPasswordDone] = useState(false);
  const [newPasswordLoading, setNewPasswordLoading] = useState(false);
  const [newPasswordError, setNewPasswordError] = useState<string | null>(null);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);

  const [tab, setTab]     = useState<"home" | "alerts" | "watchlist" | "settings">("home");
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [appKey, setAppKey] = useState<string>("");
  const [secretKey, setSecretKey] = useState<string>("");
  const [sessionTok, setSessionTok] = useState("");
  const [showAppKey, setShowAppKey] = useState(false);
  const [showSecretKey, setShowSecretKey] = useState(false);
  const [keySaved, setKeySaved]   = useState(false);
  const [keySaving, setKeySaving] = useState(false);
  const [hasCredentials, setHasCredentials] = useState(false);

  const [holdings, setHoldings]   = useState<HoldingItem[]>([]);
  const [totalValue, setTotalValue] = useState(0);
  const [totalInvested, setTotalInvested] = useState(0);
  const [totalPnl, setTotalPnl]   = useState(0);
  const [totalPnlPct, setTotalPnlPct] = useState(0);

  const [alerts, setAlerts]       = useState<any[]>([]);
  const [watchlist, setWatchlist] = useState<any[]>([]);
  const [ticker, setTicker]       = useState("");
  const [tickerSuggestions, setTickerSuggestions] = useState<any[]>([]);
  const searchTimerRef            = useRef<NodeJS.Timeout | null>(null);
  const [alertFilter, setAlertFilter] = useState<string>("all");
  const [selectedStock, setSelectedStock] = useState<HoldingItem | null>(null);
  const [showTradeModal, setShowTradeModal] = useState(false);
  const [tradeData, setTradeData] = useState<{ symbol: string; price: number; type: "BUY" | "SELL"; target: string; sl: string } | null>(null);
  const [orderQty, setOrderQty] = useState(10);
  const [orderType, setOrderType] = useState<"MARKET" | "LIMIT">("MARKET");
  const [orderSent, setOrderSent] = useState(false);
  const [orderSending, setOrderSending] = useState(false);
  const [limitPrice, setLimitPrice] = useState<string>("0");
  const [targetPriceInput, setTargetPriceInput] = useState<string>("0");
  const [stopLossPriceInput, setStopLossPriceInput] = useState<string>("0");
  const [executionMode, setExecutionMode] = useState<"INSTANT" | "CONFIRM">("INSTANT");
  const [alertSensitivity, setAlertSensitivity] = useState<"HIGH" | "ALL" | "FII">("HIGH");
  const [fcmEnabled, setFcmEnabled] = useState<boolean>(false);
  const [dematAutoSync, setDematAutoSync] = useState<boolean>(false);
  const [isPortfolioVisible, setIsPortfolioVisible] = useState<boolean>(false);

  const getAuthHeaders = useCallback(async () => {
    let token = "";
    if (supabase) {
      const { data } = await supabase.auth.getSession();
      token = data?.session?.access_token || "";
    }
    return {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    };
  }, []);

  const loadPortfolioData = useCallback(async (uid: string) => {
    const todayStr = new Date().toISOString().split("T")[0];
    let portfolioLoaded = false;
    // Backend API Service Call (Backend decrypts Fernet Vault on server safely)
    try {
      const headers = await getAuthHeaders();
      const credRes = await fetch(`/api/user/credentials?user_id=${uid}`, { headers });
      if (credRes.ok) {
        const credData = await credRes.json();
        if (credData.has_credentials) {
          const isTokenValidToday = Boolean(credData.token_date === todayStr);
          if (isTokenValidToday) setHasCredentials(true);
          if (credData.app_key) setAppKey(credData.app_key);
          if (credData.secret_key) setSecretKey(credData.secret_key);
        }
      }

      const res = await fetch(`/api/user/portfolio?user_id=${uid}`, { headers });
      if (res.ok) {
        const data = await res.json();
        const isTokenValidToday = Boolean(data.has_credentials && data.token_date === todayStr);
        if (isTokenValidToday) setHasCredentials(true);
        setTotalValue(data.total_portfolio_value || 0);
        setTotalInvested(data.total_investment_value || 0);
        setTotalPnl(data.total_pnl || 0);
        setTotalPnlPct(data.total_pnl_percent || 0);
        if (data.holdings && data.holdings.length > 0) {
          setHoldings(data.holdings.map((h: any) => ({
            symbol: h.symbol,
            qty: h.quantity,
            avg: h.avg_price,
            price: h.current_price,
            pnl: h.pnl,
            pnlPct: h.pnl_percent,
            dayHigh: h.current_price * 1.02,
            dayLow: h.current_price * 0.98,
            high52: h.current_price * 1.15,
            sector: "Equity",
            signal: h.pnl >= 0 ? "STRONG BUY" : "HOLD",
            signalType: h.pnl >= 0 ? "strong_buy" : "hold",
          })));
          portfolioLoaded = true;

          // Auto-sync Demat holdings into user_watchlists table
          if (supabase && uid) {
            try {
              for (const h of data.holdings) {
                await supabase.from('user_watchlists').upsert({
                  user_id: uid,
                  symbol: h.symbol.toUpperCase(),
                  is_auto_synced: true,
                }, { onConflict: 'user_id,symbol' });
              }
              loadWatchlistData(uid);
            } catch (err) {
              console.warn("Error auto-syncing demat holdings to watchlists:", err);
            }
          }
        }
      }
    } catch (e) {
      console.warn("Portfolio fetch fallback:", e);
    }

    if (!portfolioLoaded) {
      setHoldings([]);
      setTotalValue(0);
      setTotalInvested(0);
      setTotalPnl(0);
      setTotalPnlPct(0);
    }
  }, [getAuthHeaders]);

  const loadAlertsData = useCallback(async (uid: string) => {
    if (supabase) {
      try {
        const { data } = await supabase.from('stok_alerts').select('*').eq('user_id', uid).order('created_at', { ascending: false });
        if (data && data.length > 0) {
          setAlerts(data.map((a: any) => {
            const rawSnap = a.metrics_snapshot || {};
            const livePrice = rawSnap.current_price || rawSnap.price || 0;
            const bias = rawSnap.action_bias || (a.impact_score >= 80 ? "STRONG BUY" : "BUY");
            const tPrice = rawSnap.tactical_levels?.target_1 || (livePrice > 0 ? `₹${(livePrice * 1.12).toFixed(0)}` : "₹0");
            const sLoss = rawSnap.tactical_levels?.protective_stop_loss || (livePrice > 0 ? `₹${(livePrice * 0.94).toFixed(0)}` : "₹0");
            const peVal = rawSnap.financials?.pe_ratio?.toString() || rawSnap.pe_ratio?.toString() || "24.2";
            const debtVal = rawSnap.financials?.debt_to_equity?.toString() || rawSnap.debt_to_equity?.toString() || "0.38";
            const roeVal = rawSnap.financials?.roe_pct ? `${rawSnap.financials.roe_pct}%` : (rawSnap.roe || "18.5%");

            let sigType = "buy";
            if (bias.includes("SELL")) sigType = "sell";
            else if (bias.includes("TRAILING")) sigType = "med";
            else if (a.impact_score >= 80) sigType = "strong_buy";

            return {
              id: a.id,
              symbol: a.symbol,
              impact: a.impact_score || 80,
              impactColor: a.impact_score >= 80 ? "emerald" : "amber",
              catalyst: a.catalyst_type || "CATALYST",
              category: a.catalyst_type?.toLowerCase() || "high",
              signal: bias.replace("_", " "),
              signalType: sigType,
              targetPrice: tPrice,
              stopLoss: sLoss,
              title: a.alert_title,
              reasons: a.factual_reasons || [],
              metrics: {
                price: `₹${livePrice}`,
                pe: peVal,
                debt: debtVal,
                roe: roeVal
              },
              time: new Date(a.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            };
          }));
          return;
        }
      } catch (e) {
        console.warn("Alerts fetch error:", e);
      }
    }
    setAlerts([]);
  }, []);

  const loadWatchlistData = useCallback(async (uid: string) => {
    if (supabase) {
      try {
        const { data } = await supabase.from('user_watchlists').select('*').eq('user_id', uid).order('created_at', { ascending: false });
        if (data && data.length > 0) {
          const symbols = data.map((w: any) => w.symbol.toUpperCase());
          let quotesMap: Record<string, any> = {};

          try {
            const res = await fetch(`${BACKEND_URL}/api/stocks/quotes?symbols=${encodeURIComponent(symbols.join(','))}`, {
              signal: AbortSignal.timeout(30000)
            });
            if (res.ok) {
              const qData = await res.json();
              quotesMap = qData.quotes || {};
            }
          } catch (qErr) {
            console.warn("Error fetching live batch stock quotes:", qErr);
          }

          setWatchlist(data.map((w: any) => {
            const sym = w.symbol.toUpperCase();
            const q = quotesMap[sym] || {};
            const price = q.price !== undefined ? q.price : 0;
            const chgPct = q.change_pct !== undefined ? q.change_pct : 0.0;
            const isPos = q.is_positive !== undefined ? q.is_positive : chgPct >= 0;
            const name = q.name || sym;
            const signal = q.signal || (isPos ? "BUY" : "HOLD");
            const signalType = q.signal_type || (isPos ? "buy" : "hold");
            const target = q.target ? `₹${q.target}` : (price > 0 ? `₹${(price * 1.12).toFixed(0)}` : "₹0");
            const sl = q.stop_loss ? `₹${q.stop_loss}` : (price > 0 ? `₹${(price * 0.94).toFixed(0)}` : "₹0");

            return {
              id: w.id,
              symbol: sym,
              name,
              auto: w.is_auto_synced || false,
              price,
              chg: isPos ? `+${chgPct.toFixed(2)}%` : `${chgPct.toFixed(2)}%`,
              isPositive: isPos,
              signal,
              signalType,
              target,
              sl
            };
          }));
          return;
        }
      } catch (e) {
        console.warn("Watchlist fetch error:", e);
      }
    }
    setWatchlist([]);
  }, []);

  const loadProfileData = useCallback(async (uid: string) => {
    if (supabase) {
      try {
        const { data } = await supabase.from('profiles').select('*').eq('id', uid).maybeSingle();
        if (data) {
          if (data.alert_sensitivity) setAlertSensitivity(data.alert_sensitivity.toUpperCase() as any);
          if (data.execution_mode) setExecutionMode(data.execution_mode.toUpperCase() as any);
          if (data.fcm_enabled !== undefined) setFcmEnabled(Boolean(data.fcm_enabled));
          if (data.demat_auto_sync !== undefined) setDematAutoSync(Boolean(data.demat_auto_sync));
        }
      } catch (e) {
        console.warn("Profile load error:", e);
      }
    }
  }, []);

  const toggleDematAutoSync = async (val: boolean) => {
    setDematAutoSync(val);
    if (typeof window !== "undefined") {
      localStorage.setItem("stokvigil_demat_auto_sync", String(val));
    }
    await updatePreference("demat_auto_sync", val);
    if (val && user?.id) {
      loadPortfolioData(user.id);
    }
  };

  const toggleFcm = async (val: boolean) => {
    setFcmEnabled(val);
    if (val && typeof window !== "undefined" && "Notification" in window) {
      if (Notification.permission === "default") {
        try {
          await Notification.requestPermission();
        } catch (e) {
          console.warn("Notification permission request error:", e);
        }
      }
    }
    await updatePreference("fcm_enabled", val);
  };

  const updatePreference = async (key: string, val: any) => {
    if (!user?.id) return;
    if (supabase) {
      try {
        await supabase.from('profiles').update({ [key]: val, updated_at: new Date().toISOString() }).eq('id', user.id);
      } catch (e) {
        console.warn("Update profile preference in Supabase error:", e);
      }
    }
    try {
      const headers = await getAuthHeaders();
      await fetch(`${BACKEND_URL}/api/auth/register-device`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          user_id: user.id,
          [key]: val,
        })
      });
    } catch (e) {
      console.warn("Update profile preference via API error:", e);
    }
  };

  const openKeyModal = useCallback(async () => {
    setShowKeyModal(true);
    let uid = user?.id;
    if (!uid && supabase) {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        uid = session?.user?.id;
      } catch (_) {}
    }
    if (uid) {
      loadPortfolioData(uid);
    }
  }, [user?.id, loadPortfolioData]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedAutoSync = localStorage.getItem("stokvigil_demat_auto_sync");
      if (savedAutoSync !== null) setDematAutoSync(savedAutoSync === "true");
    }
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const sessionParam = params.get("apisession");
      if (sessionParam) {
        setSessionTok(sessionParam);
        openKeyModal();
      }
    }
  }, [openKeyModal]);

  useEffect(() => {
    if (showKeyModal && user?.id) {
      loadPortfolioData(user.id);
    }
  }, [showKeyModal, user?.id, loadPortfolioData]);

  useEffect(() => {
    if (!supabase) return;

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) {
        const u = {
          id: session.user.id,
          name: session.user.user_metadata?.full_name || session.user.email?.split("@")[0] || "Investor",
          email: session.user.email || ""
        };
        setUser(u);
        setScreen("app");
        loadPortfolioData(session.user.id);
        loadAlertsData(session.user.id);
        loadWatchlistData(session.user.id);
        loadProfileData(session.user.id);
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        const u = {
          id: session.user.id,
          name: session.user.user_metadata?.full_name || session.user.email?.split("@")[0] || "Investor",
          email: session.user.email || ""
        };
        setUser(u);
        setScreen("app");
        loadPortfolioData(session.user.id);
        loadAlertsData(session.user.id);
        loadWatchlistData(session.user.id);
        loadProfileData(session.user.id);
      } else {
        setUser(null);
        setScreen("auth");
      }
    });

    return () => subscription.unsubscribe();
  }, [loadPortfolioData, loadAlertsData, loadWatchlistData, loadProfileData]);

  const doAuth = async () => {
    if (!tncAccepted) { setShowTnc(true); return; }
    setLoading(true);
    setAuthError(null);
    setAuthSuccess(null);

    if (supabase) {
      try {
        if (authTab === "signup") {
          const { data, error } = await supabase.auth.signUp({
            email,
            password,
            options: { data: { full_name: name } }
          });
          if (error) throw error;
          if (data.session) {
            setUser({ id: data.user?.id, name: name || email.split("@")[0], email });
            setScreen("app");
          } else {
            setAuthSuccess("✉️ Verification link sent! Please check your email inbox to activate your account.");
          }
        } else {
          const { data, error } = await supabase.auth.signInWithPassword({ email, password });
          if (error) throw error;
          if (data.user) {
            setUser({
              id: data.user.id,
              name: data.user.user_metadata?.full_name || email.split("@")[0],
              email: data.user.email || email
            });
            setScreen("app");
          }
        }
      } catch (err: any) {
        setAuthError(err.message || "Authentication failed.");
      } finally {
        setLoading(false);
      }
      return;
    }

    setTimeout(() => {
      const fallbackId = "user_" + (email ? email.replace(/[^a-zA-Z0-9]/g, '_') : "investor");
      setUser({ id: fallbackId, name: name || (email.split("@")[0]) || "Investor", email: email || "investor@gmail.com" });
      setScreen("app");
      setLoading(false);
      loadPortfolioData(fallbackId);
    }, 900);
  };

  const doGoogleOAuth = async () => {
    if (!tncAccepted) { setShowTnc(true); return; }
    if (supabase) {
      try {
        await supabase.auth.signInWithOAuth({
          provider: "google",
          options: { redirectTo: window.location.origin }
        });
      } catch (err: any) {
        setAuthError(err.message || "Google OAuth failed.");
      }
      return;
    }
    setLoading(true);
    setTimeout(() => {
      const fallbackId = "user_google_investor";
      setUser({ id: fallbackId, name: "Google Investor", email: "google.user@gmail.com" });
      setScreen("app");
      setLoading(false);
      loadPortfolioData(fallbackId);
    }, 900);
  };

  const saveKey = async () => {
    setKeySaving(true);
    const cleanAppKey = appKey.trim();
    const cleanSecretKey = secretKey.trim();
    const cleanSessionTok = sessionTok.trim();

    // 1. Resolve Active User ID
    let currentUserId = user?.id;
    if (!currentUserId && supabase) {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        currentUserId = session?.user?.id;
      } catch (_) {}
    }

    if (currentUserId) {
      let saved = false;

      // Save securely via Backend Vault (AES-256 Fernet encryption on server)
      try {
        const headers = await getAuthHeaders();
        const res = await fetch(`/api/user/credentials`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            user_id: currentUserId,
            app_key: cleanAppKey,
            secret_key: cleanSecretKey,
            session_token: cleanSessionTok
          })
        });
        if (res.ok) {
          setHasCredentials(true);
        }
      } catch (e) {
        console.warn("Backend save key error:", e);
      }

      loadPortfolioData(currentUserId);
    }

    setKeySaved(true);
    setKeySaving(false);
    setTimeout(() => { setShowKeyModal(false); setKeySaved(false); }, 1200);
  };

  const doDeleteAccount = async () => {
    if (deleteConfirmText.trim() !== "DELETE" || !user?.id) return;
    setIsDeletingAccount(true);
    try {
      const headers = await getAuthHeaders();
      await fetch(`${BACKEND_URL}/api/user/delete-account`, {
        method: "POST",
        headers,
        body: JSON.stringify({ user_id: user.id })
      });
      if (supabase) {
        await supabase.from("user_credentials").delete().eq("user_id", user.id);
        await supabase.from("user_watchlists").delete().eq("user_id", user.id);
        await supabase.from("user_devices").delete().eq("user_id", user.id);
      }
    } catch (e) {
      console.warn("Delete account error:", e);
    }
    await doSignOut();
    setIsDeletingAccount(false);
    setShowDeleteModal(false);
    alert("✅ Your account and all associated data have been permanently deleted.");
  };

  const handleStockChange = (val: string) => {
    setTicker(val);
    const q = val.trim();
    if (!q) {
      if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
      setTickerSuggestions([]);
      return;
    }

    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/stocks/search?q=${encodeURIComponent(q)}`, {
          signal: AbortSignal.timeout(30000)
        });
        if (res.ok) {
          const data = await res.json();
          setTickerSuggestions(data.stocks || []);
        }
      } catch (e) {
        console.warn("Dynamic stock search error:", e);
      }
    }, 300);
  };

  const addStock = async (explicitSym?: string, explicitName?: string) => {
    const raw = (explicitSym || ticker).trim().toUpperCase();
    if (!raw) return;

    let isValid = false;
    let isTimeout = false;
    let stockName = explicitName || raw;
    let exchange = "NSE";

    if (raw.length < 2) {
      alert(`⚠️ '${raw}' is too short. Please enter a valid NSE or BSE stock symbol.`);
      return;
    }

    let livePrice = 0;

    try {
      const res = await fetch(`${BACKEND_URL}/api/stocks/validate?symbol=${encodeURIComponent(raw)}`, {
        signal: AbortSignal.timeout(30000)
      });
      if (res.ok) {
        const valData = await res.json();
        if (valData.is_valid === true) {
          isValid = true;
          exchange = valData.exchange || "NSE";
          if (valData.name) stockName = valData.name;
          if (valData.price) livePrice = Number(valData.price);
        } else if (valData.is_timeout) {
          isTimeout = true;
        }
      }
    } catch (e: any) {
      if (e?.name === 'TimeoutError' || e?.name === 'AbortError') {
        isTimeout = true;
      }
      console.warn("Stock validation error:", e);
      isValid = false;
    }

    if (isTimeout) {
      alert(`⏳ Connection to exchange timed out for '${raw}'. Please check your connection and try again.`);
      return;
    }

    if (!isValid) {
      alert(`⚠️ '${raw}' is not a recognized or actively traded stock on NSE or BSE.\n\nPlease select from the live search suggestions.`);
      return;
    }

    setTickerSuggestions([]);
    setTicker("");

    if (user?.id && supabase) {
      await supabase.from('user_watchlists').upsert({
        user_id: user.id,
        symbol: raw,
        is_auto_synced: false
      }, { onConflict: 'user_id,symbol' });
      loadWatchlistData(user.id);
    } else {
      setWatchlist(prev => [
        {
          id: Date.now().toString(),
          symbol: raw,
          name: stockName,
          auto: false,
          price: livePrice,
          chg: "+0.00%",
          isPositive: true,
          signal: "BUY",
          signalType: "buy",
          target: livePrice > 0 ? `₹${(livePrice * 1.12).toFixed(0)}` : "₹0",
          sl: livePrice > 0 ? `₹${(livePrice * 0.94).toFixed(0)}` : "₹0"
        },
        ...prev.filter(p => p.symbol !== raw)
      ]);
    }
  };

  const removeTicker = async (id: string) => {
    if (user?.id && supabase) {
      await supabase.from('user_watchlists').delete().eq('id', id);
      loadWatchlistData(user.id);
    } else {
      setWatchlist(prev => prev.filter(w => w.id !== id));
    }
  };

  const executeTrade = async () => {
    if (!tradeData) return;
    setOrderSending(true);
    if (user?.id) {
      try {
        const headers = await getAuthHeaders();
        await fetch(`${BACKEND_URL}/api/v1/orders/place`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            user_id: user.id,
            symbol: tradeData.symbol,
            action: tradeData.type,
            order_type: orderType,
            quantity: orderQty,
            price: orderType === "LIMIT" ? parseFloat(limitPrice) || 0.0 : 0.0
          })
        });
      } catch (e) {
        console.warn("Trade order execution:", e);
      }
    }
    setOrderSending(false);
    setOrderSent(true);
  };

  const doSignOut = async () => {
    if (supabase) {
      await supabase.auth.signOut();
    }
    setUser(null);
    setScreen("auth");
  };

  const filteredAlerts = alerts.filter(a => {
    if (alertFilter === "all") return true;
    if (alertFilter === "high") return a.impact >= 80;
    if (alertFilter === "earnings") return a.catalyst?.toLowerCase().includes("earning") || a.title?.toLowerCase().includes("earning");
    if (alertFilter === "breakout") return a.catalyst?.toLowerCase().includes("breakout") || a.title?.toLowerCase().includes("breakout");
    if (alertFilter === "fii") return a.catalyst?.toLowerCase().includes("block") || a.title?.toLowerCase().includes("fii");
    return true;
  });

  const rootStyle: React.CSSProperties = {
    minHeight: "100vh",
    background: "#060812",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "0",
  };

  const phoneStyle: React.CSSProperties = {
    width: "100%",
    maxWidth: 430,
    height: "100vh",
    maxHeight: "100vh",
    background: C.bg,
    display: "flex",
    flexDirection: "column",
    position: "relative",
    overflow: "hidden",
  };

  // ─────────────────────────────────────────────
  // AUTHENTICATION SCREEN
  // ─────────────────────────────────────────────
  if (screen === "auth") {
    return (
      <div style={rootStyle}>
        <div style={phoneStyle}>
          {/* Ambient Radial Lights */}
          <div style={{
            position: "absolute", inset: 0, pointerEvents: "none",
            background: "radial-gradient(ellipse 80% 50% at 50% 100%, rgba(139,92,246,0.18) 0%, transparent 70%), radial-gradient(ellipse 60% 40% at 80% 10%, rgba(6,182,212,0.12) 0%, transparent 60%)",
          }} />


          <div className="anim-fadeup" style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", padding: "16px 24px 32px", gap: 20, position: "relative" }}>

            {/* LOGO & BRAND */}
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <TradingAILogo size={44} />
                <div style={{ fontSize: 26, fontWeight: 900, color: C.white, letterSpacing: "-0.5px" }}>
                  StokVigil <span style={{ background: `linear-gradient(135deg, ${C.cyan}, ${C.violet})`, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>AI</span>
                </div>
              </div>
              <div style={{ fontSize: 12, color: C.cyan, fontWeight: 800, letterSpacing: "0.04em" }}>
                Track Your Stocks. Spot the Signals.
              </div>
            </div>

            {/* AUTH CARD */}
            <div style={{
              background: C.bgCard,
              border: `1px solid ${C.border}`,
              borderRadius: 24, padding: "22px 20px",
              display: "flex", flexDirection: "column", gap: 16,
              boxShadow: "0 16px 40px rgba(0,0,0,0.6)",
            }}>

              {/* Mode Toggle */}
              <div style={{ display: "flex", background: "#080B16", borderRadius: 12, padding: 4, border: `1px solid ${C.border}` }}>
                {(["signin", "signup"] as const).map(t => (
                  <button key={t} onClick={() => setAuthTab(t)} style={{
                    flex: 1, padding: "9px 0", borderRadius: 9, border: "none", cursor: "pointer",
                    fontSize: 12, fontWeight: 800,
                    background: authTab === t ? `linear-gradient(135deg, ${C.cyan}, ${C.violet})` : "transparent",
                    color: authTab === t ? "#fff" : C.gray1,
                    transition: "all 0.2s",
                  }}>
                    {t === "signin" ? "Sign In" : "Create Account"}
                  </button>
                ))}
              </div>

              {/* Google Button */}
              <button onClick={doGoogleOAuth} style={{
                width: "100%", background: "#fff", borderRadius: 14, padding: "12px 16px",
                display: "flex", alignItems: "center", justifyContent: "center", gap: 10,
                border: "none", cursor: "pointer", fontWeight: 800, fontSize: 13, color: "#1a1a1a",
                boxShadow: "0 4px 16px rgba(0,0,0,0.4)",
              }}>
                <svg width="18" height="18" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                </svg>
                Continue with Google
              </button>

              <Divider label="or continue with email" />

              {/* Form Inputs */}
              {authTab === "signup" && (
                <Input label="Full Name" value={name} onChange={setName} placeholder="" />
              )}
              <Input label="Email Address" type="email" value={email} onChange={setEmail} placeholder="" />
              <Input
                label="Password"
                type={showAuthPassword ? "text" : "password"}
                value={password}
                onChange={setPassword}
                placeholder=""
                rightAction={
                  <button
                    type="button"
                    onClick={() => setShowAuthPassword(v => !v)}
                    style={{
                      background: "none", border: "none", color: C.cyan,
                      fontSize: 10.5, fontWeight: 800, cursor: "pointer",
                      display: "flex", alignItems: "center", gap: 4, padding: 0
                    }}
                  >
                    {showAuthPassword
                      ? <VisibilityOffOutlinedIcon size={14} color={C.cyan} />
                      : <VisibilityOutlinedIcon size={14} color={C.cyan} />}
                    <span>{showAuthPassword ? "Hide" : "Show"}</span>
                  </button>
                }
              />
              {authTab === "signin" && (
                <div style={{ display: "flex", justifyContent: "flex-end", marginTop: -6 }}>
                  <button
                    type="button"
                    onClick={() => setShowForgotModal(true)}
                    style={{
                      background: "none", border: "none", color: C.cyan,
                      fontSize: 11.5, fontWeight: 700, cursor: "pointer", padding: 0
                    }}
                  >
                    Forgot Password?
                  </button>
                </div>
              )}

              {/* Checkbox + Read Terms & Conditions Row */}
              <div
                onClick={() => {
                  if (!tncAccepted) {
                    setShowTnc(true);
                  }
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 12,
                  padding: "12px 14px",
                  background: tncAccepted
                    ? "rgba(16,185,129,0.08)"
                    : "rgba(6,182,212,0.06)",
                  border: `1.5px solid ${tncAccepted ? "rgba(16,185,129,0.35)" : C.borderCyan}`,
                  borderRadius: 14,
                  cursor: tncAccepted ? "default" : "pointer",
                  transition: "all 0.2s cubic-bezier(0.16,1,0.3,1)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  {/* Custom Checkbox Box */}
                  <div style={{
                    width: 22,
                    height: 22,
                    borderRadius: 7,
                    border: tncAccepted ? `2px solid ${C.emerald}` : `2px solid ${C.cyan}`,
                    background: tncAccepted ? C.emerald : "transparent",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: tncAccepted ? "#080B16" : "transparent",
                    fontWeight: 900,
                    fontSize: 13,
                    boxShadow: tncAccepted
                      ? "0 0 10px rgba(16,185,129,0.4)"
                      : "0 0 8px rgba(6,182,212,0.2)",
                    flexShrink: 0,
                    transition: "all 0.2s ease",
                  }}>
                    ✓
                  </div>

                  {/* Label with clickable Terms link */}
                  <div style={{ fontSize: 12, color: C.white, fontWeight: 600, lineHeight: 1.3 }}>
                    {tncAccepted ? (
                      <span style={{ color: C.emerald, fontWeight: 700 }}>
                        I have read and accepted the{" "}
                        <span
                          onClick={(e) => { e.stopPropagation(); setShowTnc(true); }}
                          style={{ textDecoration: "underline", cursor: "pointer" }}
                        >
                          Terms & Conditions
                        </span>
                      </span>
                    ) : (
                      <span>
                        I agree to the{" "}
                        <span
                          onClick={(e) => { e.stopPropagation(); setShowTnc(true); }}
                          style={{ color: C.cyan, textDecoration: "underline", fontWeight: 800, cursor: "pointer" }}
                        >
                          Terms & Conditions
                        </span>
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Error and Success Feedback */}
              {authError && (
                <div style={{
                  background: "rgba(239,68,68,0.1)",
                  border: "1px solid rgba(239,68,68,0.35)",
                  borderRadius: 12,
                  padding: "10px 14px",
                  color: C.rose,
                  fontSize: 12,
                  fontWeight: 700,
                  lineHeight: 1.4,
                }}>
                  ⚠️ {authError}
                </div>
              )}
              {authSuccess && (
                <div style={{
                  background: "rgba(16,185,129,0.1)",
                  border: "1px solid rgba(16,185,129,0.35)",
                  borderRadius: 12,
                  padding: "10px 14px",
                  color: C.emerald,
                  fontSize: 12,
                  fontWeight: 700,
                  lineHeight: 1.4,
                }}>
                  {authSuccess}
                </div>
              )}

              {/* Submit CTA */}
              <Btn
                variant="primary"
                onClick={doAuth}
                disabled={loading || !tncAccepted}
              >
                {loading
                  ? "Authenticating…"
                  : !tncAccepted
                    ? authTab === "signin" ? "🔒 Sign In to StokVigil" : "🔒 Create Account"
                    : authTab === "signin"
                      ? "Sign In to StokVigil →"
                      : "Create Account →"
                }
              </Btn>
            </div>

          </div>
        </div>

        {/* FORGOT PASSWORD MODAL */}
        {showForgotModal && (
          <div style={{
            position: "fixed", inset: 0,
            background: "rgba(6,8,18,0.92)", backdropFilter: "blur(16px)",
            display: "flex", alignItems: "center", justifyContent: "center",
            padding: 20, zIndex: 60,
          }}>
            <div className="anim-fadeup" style={{
              width: "100%", maxWidth: 380, background: C.bgCard,
              border: `1.5px solid ${C.borderCyan}`, borderRadius: 22, padding: 20,
            }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                <div style={{ fontSize: 14, fontWeight: 900, color: C.white }}>🔑 Reset Password</div>
                <button onClick={() => { setShowForgotModal(false); setForgotSent(false); }} style={{ background: "none", border: "none", color: C.gray1, fontSize: 18, cursor: "pointer" }}>✕</button>
              </div>

              {forgotSent ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <div style={{ background: "rgba(16,185,129,0.12)", border: `1px solid rgba(16,185,129,0.3)`, borderRadius: 12, padding: "12px 14px", fontSize: 12, color: C.emerald, fontWeight: 800, lineHeight: 1.4 }}>
                    ✅ Password reset link sent to {forgotEmail}! Please check your email inbox and click the link to set your new password.
                  </div>
                  <Btn variant="primary" onClick={() => { setShowForgotModal(false); setForgotSent(false); }}>
                    Done
                  </Btn>
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <div style={{ fontSize: 12, color: C.gray1, lineHeight: 1.5 }}>
                    Enter your registered email address and we'll send you an instant link to reset your password.
                  </div>
                  <Input label="Email Address" type="email" value={forgotEmail} onChange={setForgotEmail} placeholder="" />
                  <Btn
                    variant="primary"
                    disabled={!forgotEmail.trim() || forgotLoading}
                    onClick={async () => {
                      setForgotLoading(true);
                      try {
                        if (supabase) {
                          await supabase.auth.resetPasswordForEmail(forgotEmail, {
                            redirectTo: `${window.location.origin}`,
                          });
                        }
                      } catch (e) {
                        console.error(e);
                      } finally {
                        setForgotLoading(false);
                        setForgotSent(true);
                      }
                    }}
                  >
                    {forgotLoading ? "Sending..." : "Send Reset Link →"}
                  </Btn>
                </div>
              )}
            </div>
          </div>
        )}

        {showTnc && (
          <TncModal
            onAccept={() => { setTncAccepted(true); setShowTnc(false); }}
            onClose={() => setShowTnc(false)}
          />
        )}
      </div>
    );
  }

  // ─────────────────────────────────────────────
  // MAIN AUTHENTICATED APP VIEW
  // ─────────────────────────────────────────────
  const headerH = 60;
  const navH    = 64;

  const NavItem = ({ id, label, icon }: { id: typeof tab; label: string; icon: (active: boolean, color: string) => React.ReactNode }) => {
    const isActive = tab === id;
    const color = isActive ? C.cyan : C.gray2;
    return (
      <button onClick={() => setTab(id)} style={{
        flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 4,
        background: "none", border: "none", cursor: "pointer", padding: "8px 0",
        color: color, transition: "all 0.2s cubic-bezier(0.16,1,0.3,1)",
        position: "relative",
      }}>
        <div style={{
          transform: isActive ? "scale(1.1)" : "scale(1)",
          transition: "transform 0.2s cubic-bezier(0.16,1,0.3,1)",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          {icon(isActive, color)}
        </div>
        <span style={{ fontSize: 10.5, fontWeight: isActive ? 800 : 600, letterSpacing: "0.03em" }}>{label}</span>
        {isActive && (
          <div style={{
            position: "absolute", bottom: 0, width: 24, height: 3, borderRadius: 99,
            background: `linear-gradient(90deg, ${C.cyan}, ${C.violet})`,
            boxShadow: `0 0 10px ${C.cyan}`,
          }} />
        )}
      </button>
    );
  };

  return (
    <div style={rootStyle}>
      <div style={phoneStyle}>
        <div style={{
          position: "absolute", inset: 0, pointerEvents: "none",
          background: "radial-gradient(ellipse 90% 40% at 50% 100%, rgba(139,92,246,0.14) 0%, transparent 70%)",
        }} />


        {/* Main Sticky Header */}
        <div style={{
          position: "sticky", top: 0, zIndex: 40, height: headerH,
          background: "rgba(6,8,18,0.95)", backdropFilter: "blur(20px)",
          borderBottom: `1px solid ${C.border}`,
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "0 18px",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <TradingAILogo size={36} />
            <div>
              <div style={{ fontWeight: 900, fontSize: 15, color: C.white, letterSpacing: "-0.3px" }}>
                StokVigil <span style={{ background: `linear-gradient(135deg, ${C.cyan}, ${C.violet})`, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>AI</span>
              </div>
              <div className="pulse-live" style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 1 }}>
                <div style={{ width: 6, height: 6, borderRadius: "50%", background: C.emerald, boxShadow: `0 0 8px ${C.emerald}` }} />
                <span style={{ fontSize: 10, color: C.emerald, fontWeight: 800, letterSpacing: "0.2px" }}>NSE/BSE LIVE 09:15–15:30</span>
              </div>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <button onClick={openKeyModal} style={{
              background: "rgba(6,182,212,0.12)", border: `1px solid ${C.borderCyan}`,
              borderRadius: 10, padding: "6px 10px", color: C.cyan, fontSize: 11, fontWeight: 800, cursor: "pointer",
              display: "flex", alignItems: "center", gap: 5,
            }}>
              🔑 Key Active
            </button>
            <button
              onClick={() => { setScreen("auth"); setUser(null); setTncAccepted(false); }}
              title="Sign Out"
              style={{
                background: "rgba(239,68,68,0.1)", border: `1px solid rgba(239,68,68,0.25)`,
                borderRadius: 10, padding: "7px 9px", color: C.rose, cursor: "pointer",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
                <path d="M9 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H9" stroke={C.rose} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M16 17L21 12L16 7" stroke={C.rose} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M21 12H9" stroke={C.rose} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>
        </div>

        {/* Main Scrollable App Canvas */}
        <DraggableVerticalCanvas className="no-scrollbar" style={{ flex: 1, overflowY: "auto", padding: "16px 16px 20px" }}>

          {/* HOME PORTFOLIO TAB */}
          {tab === "home" && (
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
          )}

          {/* ALERTS TAB WITH FILTER PILLS */}
          {tab === "alerts" && (
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
                      onClick={() => setAlertFilter(chip.id as any)}
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
                      <span style={{ color: C.cyan, marginRight: 6 }}>[{a.symbol}]</span>
                      {a.title}
                    </div>

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

                    {/* Fundamental Metrics Grid */}
                    <div style={{
                      display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr",
                      gap: 6, background: "#080B16", borderRadius: 12, padding: 10,
                      border: `1px solid ${C.border}`,
                    }}>
                      {Object.entries(a.metrics || {}).map(([k, v]) => (
                        <div key={k} style={{ textAlign: "center" }}>
                          <div style={{ fontSize: 9, color: C.gray2, textTransform: "uppercase", fontWeight: 700, marginBottom: 2 }}>{k}</div>
                          <div style={{ fontSize: 11, fontWeight: 800, color: k === "roe" ? C.emerald : C.white }}>{String(v)}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* WATCHLIST TAB */}
          {tab === "watchlist" && (
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
                    chg: h.pnlPct >= 0 ? `+${h.pnlPct.toFixed(2)}%` : `${h.pnlPct.toFixed(2)}%`,
                    isPositive: h.pnlPct >= 0,
                    signal: h.signal || (h.pnl >= 0 ? "STRONG BUY" : "HOLD"),
                    signalType: h.signalType || (h.pnl >= 0 ? "strong_buy" : "hold"),
                    target: h.price ? `₹${(h.price * 1.12).toFixed(0)}` : "₹0",
                    sl: h.price ? `₹${(h.price * 0.94).toFixed(0)}` : "₹0"
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
                            ₹{item.price.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                          </div>
                          <div style={{
                            fontSize: 10.5, fontWeight: 800,
                            color: item.isPositive ? C.emerald : C.rose,
                            display: "inline-flex", alignItems: "center", gap: 3, marginTop: 2
                          }}>
                            {item.isPositive ? "▲" : "▼"} {item.chg}
                          </div>
                        </div>
                      </div>

                      {/* Bottom Action & Signal Ribbon */}
                      <div style={{
                        display: "flex", alignItems: "center", justifyContent: "space-between",
                        paddingTop: 8, borderTop: `1px solid ${C.border}`, marginTop: 2
                      }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <SignalBadge signal={item.signal || "BUY"} type={item.signalType || "buy"} />
                          <span style={{ fontSize: 10, color: C.gray2 }}>
                            Target: <b style={{ color: C.emerald }}>{item.target || "₹3,250"}</b>
                          </span>
                        </div>

                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <button
                            onClick={() => {
                              setTradeData({
                                symbol: item.symbol,
                                price: item.price,
                                type: item.signalType === "sell" ? "SELL" : "BUY",
                                target: item.target || "₹3,250",
                                sl: item.sl || "₹2,820"
                              });
                              setOrderQty(10);
                              setLimitPrice(item.price.toFixed(2));
                              setShowTradeModal(true);
                            }}
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
          )}

          {/* SETTINGS TAB */}
          {tab === "settings" && (
            <div className="anim-fadeup" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div>
                  <div style={{ fontSize: 16, fontWeight: 900, color: C.white }}>Control Center</div>
                  <div style={{ fontSize: 10.5, color: C.gray2, marginTop: 2 }}>
                    Manage broker API keys, notifications & trading parameters
                  </div>
                </div>
                <span style={{
                  background: "rgba(16,185,129,0.12)", border: `1px solid rgba(16,185,129,0.3)`,
                  color: C.emerald, borderRadius: 20, padding: "3px 10px", fontSize: 10, fontWeight: 800,
                  display: "flex", alignItems: "center", gap: 5
                }}>
                  <span className="pulse-live" style={{ width: 6, height: 6, borderRadius: "50%", background: C.emerald }} />
                  SYSTEM ACTIVE
                </span>
              </div>

              {/* User Profile Card */}
              <div style={{
                background: "linear-gradient(135deg, rgba(13,17,30,0.95) 0%, rgba(18,23,42,0.95) 100%)",
                border: `1.5px solid ${C.borderCyan}`, borderRadius: 20, padding: 18,
                boxShadow: "0 10px 30px rgba(6,182,212,0.08)", position: "relative", overflow: "hidden"
              }}>
                <div style={{
                  position: "absolute", top: -20, right: -20, width: 90, height: 90,
                  background: `radial-gradient(circle, ${C.cyan} 0%, transparent 70%)`, opacity: 0.15, pointerEvents: "none"
                }} />

                <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                  <div style={{
                    width: 52, height: 52, borderRadius: 16,
                    background: `linear-gradient(135deg, ${C.cyan}, ${C.violet})`,
                    border: `2px solid rgba(255,255,255,0.2)`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 20, fontWeight: 900, color: "#fff",
                    boxShadow: "0 6px 18px rgba(6,182,212,0.4)"
                  }}>
                    {(user?.name?.[0] || "I").toUpperCase()}
                  </div>

                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <span style={{ fontWeight: 900, fontSize: 16, color: C.white }}>{user?.name || "Investor Account"}</span>
                      <span style={{
                        background: "linear-gradient(90deg, #06B6D4, #8B5CF6)",
                        color: "#fff", borderRadius: 6, padding: "1px 6px", fontSize: 9, fontWeight: 900
                      }}>PRO TIER</span>
                    </div>
                    <div style={{ fontSize: 11, color: C.cyan, fontWeight: 600, marginTop: 2 }}>{user?.email}</div>
                  </div>
                </div>

                {/* Quick Performance Metrics Strip */}
                <div style={{
                  display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8,
                  marginTop: 14, paddingTop: 12, borderTop: `1px solid ${C.border}`
                }}>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: 9, color: C.gray2, textTransform: "uppercase", fontWeight: 700 }}>Signal Scan</div>
                    <div style={{ fontSize: 12, fontWeight: 900, color: C.emerald, marginTop: 2 }}>5-Min Live</div>
                  </div>
                  <div style={{ textAlign: "center", borderLeft: `1px solid ${C.border}`, borderRight: `1px solid ${C.border}` }}>
                    <div style={{ fontSize: 9, color: C.gray2, textTransform: "uppercase", fontWeight: 700 }}>Order Execution</div>
                    <div style={{ fontSize: 12, fontWeight: 900, color: C.cyan, marginTop: 2 }}>ICICI Breeze</div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: 9, color: C.gray2, textTransform: "uppercase", fontWeight: 700 }}>Risk Shield</div>
                    <div style={{ fontSize: 12, fontWeight: 900, color: C.violet, marginTop: 2 }}>Auto Target</div>
                  </div>
                </div>
              </div>

              {/* Section 1: Broker Integration */}
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ fontSize: 10, color: C.gray2, textTransform: "uppercase", fontWeight: 800, letterSpacing: "0.08em" }}>
                  🔌 Broker Integration & API
                </div>

                <div style={{
                  background: C.bgCard, border: `1px solid ${C.border}`,
                  borderRadius: 16, padding: 14, display: "flex", flexDirection: "column", gap: 12
                }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <div style={{
                        width: 36, height: 36, borderRadius: 10,
                        background: "rgba(6,182,212,0.1)", border: `1px solid ${C.borderCyan}`,
                        display: "center", alignItems: "center", justifyContent: "center", fontSize: 16
                      }}>🔑</div>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 800, color: C.white }}>ICICI Breeze Session Key</div>
                        <div style={{ fontSize: 10.5, color: C.gray2, marginTop: 2 }}>Required daily — expires at midnight IST</div>
                      </div>
                    </div>

                    <button onClick={openKeyModal} style={{
                      background: `rgba(6,182,212,0.12)`, border: `1px solid ${C.borderCyan}`,
                      borderRadius: 10, padding: "7px 12px", color: C.cyan, fontSize: 11, fontWeight: 800, cursor: "pointer",
                    }}>
                      Configure Key →
                    </button>
                  </div>

                  <div style={{ height: 1, background: C.border }} />

                  {/* Execution Mode Selector */}
                  <div>
                    <div style={{ fontSize: 10, color: C.gray2, fontWeight: 700, textTransform: "uppercase", marginBottom: 8 }}>
                      ⚡ Default Execution Workflow
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                      <button
                        onClick={() => {
                          setExecutionMode("INSTANT");
                          updatePreference("execution_mode", "INSTANT");
                        }}
                        style={{
                          background: executionMode === "INSTANT" ? "rgba(6,182,212,0.12)" : C.bgCard2,
                          border: `1.5px solid ${executionMode === "INSTANT" ? C.cyan : C.border}`,
                          borderRadius: 10, padding: "8px 10px", textAlign: "left", cursor: "pointer"
                        }}
                      >
                        <div style={{ fontSize: 11, fontWeight: 800, color: executionMode === "INSTANT" ? C.cyan : C.white }}>⚡ Instant Execution</div>
                        <div style={{ fontSize: 9.5, color: C.gray2, marginTop: 2 }}>1-Tap Direct Breeze Order</div>
                      </button>

                      <button
                        onClick={() => {
                          setExecutionMode("CONFIRM");
                          updatePreference("execution_mode", "CONFIRM");
                        }}
                        style={{
                          background: executionMode === "CONFIRM" ? "rgba(139,92,246,0.12)" : C.bgCard2,
                          border: `1.5px solid ${executionMode === "CONFIRM" ? C.violet : C.border}`,
                          borderRadius: 10, padding: "8px 10px", textAlign: "left", cursor: "pointer"
                        }}
                      >
                        <div style={{ fontSize: 11, fontWeight: 800, color: executionMode === "CONFIRM" ? C.violet : C.white }}>🛡️ Confirm First</div>
                        <div style={{ fontSize: 9.5, color: C.gray2, marginTop: 2 }}>Review parameters first</div>
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Section 2: Notifications Hub */}
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ fontSize: 10, color: C.gray2, textTransform: "uppercase", fontWeight: 800, letterSpacing: "0.08em" }}>
                  🔔 Real-Time Notifications
                </div>

                <div style={{
                  background: C.bgCard, border: `1px solid ${C.border}`,
                  borderRadius: 16, padding: 14, display: "flex", flexDirection: "column", gap: 12
                }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <div style={{
                        width: 36, height: 36, borderRadius: 10,
                        background: "linear-gradient(135deg, #2AABEE 0%, #229ED9 100%)",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        boxShadow: "0 4px 12px rgba(34,158,217,0.35)"
                      }}>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                          <path d="M21.6 3.4L2.6 10.7C1.3 11.2 1.3 12.5 2.4 12.8L7.3 14.3L18.6 7.2C19.1 6.9 19.6 7.1 19.2 7.5L10.1 15.7V19.8C10.5 19.8 10.7 19.6 11 19.3L13.1 17.3L17.5 20.5C18.3 21 18.9 20.6 19.1 19.6L22 4.9C22.3 3.7 21.5 3 21.6 3.4Z" fill="#FFFFFF"/>
                        </svg>
                      </div>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 800, color: C.white }}>Telegram Bot Channel</div>
                        <div style={{ fontSize: 10.5, color: C.gray2, marginTop: 2 }}>Instant catalyst & order receipt alerts</div>
                      </div>
                    </div>

                    <button
                      onClick={() => {
                        const startParam = user?.id || (user?.email ? user.email.replace(/[^a-zA-Z0-9_]/g, '_') : 'user');
                        window.open(`https://t.me/StokVigilAi_bot?start=${startParam}`, "_blank");
                      }}
                      style={{
                        background: "rgba(6,182,212,0.12)", border: `1px solid ${C.borderCyan}`,
                        borderRadius: 10, padding: "7px 12px", color: C.cyan, fontSize: 11, fontWeight: 800, cursor: "pointer"
                      }}
                    >
                      Connect @StokVigilAi_bot
                    </button>
                  </div>

                  <div style={{ height: 1, background: C.border }} />

                  {/* Alert Sensitivity Filter */}
                  <div>
                    <div style={{ fontSize: 10, color: C.gray2, fontWeight: 700, marginBottom: 8 }}>
                      🔥 AI Alert Signal Frequency
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 6 }}>
                      {(["HIGH", "ALL", "FII"] as const).map(mode => (
                        <button
                          key={mode}
                          onClick={() => {
                            setAlertSensitivity(mode);
                            updatePreference("alert_sensitivity", mode);
                          }}
                          style={{
                            background: alertSensitivity === mode ? "rgba(6,182,212,0.12)" : C.bgCard2,
                            border: `1px solid ${alertSensitivity === mode ? C.cyan : C.border}`,
                            borderRadius: 8, padding: "6px 8px", fontSize: 10.5, fontWeight: 800,
                            color: alertSensitivity === mode ? C.cyan : C.gray1, cursor: "pointer",
                            textAlign: "center"
                          }}
                        >
                          {mode === "HIGH" ? "🔥 High Impact" : mode === "ALL" ? "⚡ All Signals" : "📊 FII / Institutional"}
                        </button>
                      ))}
                    </div>

                    <div style={{ height: 1, background: C.border, margin: "6px 0" }} />

                    {/* Push Notification Alerts Toggle (FCM / Web Push) */}
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: 4 }}>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 800, color: C.white }}>Push Notification Alerts (FCM)</div>
                        <div style={{ fontSize: 10.5, color: fcmEnabled ? C.cyan : C.gray2, marginTop: 2 }}>
                          {fcmEnabled ? "Receive 5-min market hours push alerts on browser & device" : "Push notifications paused"}
                        </div>
                      </div>

                      <label style={{ position: "relative", display: "inline-block", width: 44, height: 24, cursor: "pointer" }}>
                        <input
                          type="checkbox"
                          checked={fcmEnabled}
                          onChange={e => toggleFcm(e.target.checked)}
                          style={{ opacity: 0, width: 0, height: 0 }}
                        />
                        <span style={{
                          position: "absolute", inset: 0,
                          background: fcmEnabled ? `linear-gradient(135deg, ${C.cyan}, ${C.violet})` : "rgba(255,255,255,0.12)",
                          borderRadius: 24, transition: "0.25s all ease",
                          border: `1px solid ${fcmEnabled ? C.borderCyan : C.border}`,
                          boxShadow: fcmEnabled ? "0 0 10px rgba(6,182,212,0.4)" : "none"
                        }}>
                          <span style={{
                            position: "absolute", content: '""', height: 18, width: 18, left: fcmEnabled ? 22 : 2, bottom: 2,
                            background: "#FFFFFF", borderRadius: "50%", transition: "0.25s all ease",
                          }} />
                        </span>
                      </label>
                    </div>
                  </div>
                </div>
              </div>

              {/* Section 3: Security & Access */}
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ fontSize: 10, color: C.gray2, textTransform: "uppercase", fontWeight: 800, letterSpacing: "0.08em" }}>
                  🔒 Security & Access
                </div>

                <div style={{
                  background: C.bgCard, border: `1px solid ${C.border}`,
                  borderRadius: 16, padding: 14,
                }}>
                  <button
                    onClick={() => {
                      if (user?.email) setForgotEmail(user.email);
                      setShowForgotModal(true);
                    }}
                    style={{
                      width: "100%",
                      background: C.bgCard2, border: `1px solid ${C.border}`,
                      borderRadius: 10, padding: 12, display: "flex", alignItems: "center", justifyContent: "space-between",
                      color: C.white, cursor: "pointer", fontSize: 12, fontWeight: 700
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span>🔑</span>
                      <span>Change Password</span>
                    </div>
                    <span style={{ color: C.gray2 }}>→</span>
                  </button>
                </div>
              </div>

              {/* Section 4: Danger Zone */}
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ fontSize: 10, color: C.rose, textTransform: "uppercase", fontWeight: 800, letterSpacing: "0.08em" }}>
                  ⚠️ Danger Zone
                </div>

                <div style={{
                  background: C.bgCard, border: `1px solid rgba(239,68,68,0.3)`,
                  borderRadius: 16, padding: 14, display: "flex", flexDirection: "column", gap: 12
                }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 900, color: C.white }}>Delete Account & Data</div>
                    <div style={{ fontSize: 11, color: C.gray1, marginTop: 2 }}>
                      Permanently erase your account, watchlist, and encrypted broker keys.
                    </div>
                  </div>

                  <button
                    onClick={() => {
                      setDeleteConfirmText("");
                      setShowDeleteModal(true);
                    }}
                    style={{
                      background: "rgba(239,68,68,0.12)", border: `1.5px solid rgba(239,68,68,0.5)`,
                      borderRadius: 12, padding: 12, display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
                      color: C.rose, cursor: "pointer", fontSize: 13, fontWeight: 900,
                    }}
                  >
                    <span>🗑️ Delete My Account</span>
                  </button>
                </div>
              </div>

              {/* Bottom Action: Brand Gradient Pill Sign Out Button */}
              <button
                onClick={doSignOut}
                style={{
                  width: "100%",
                  height: 50,
                  borderRadius: 16,
                  border: "none",
                  background: "linear-gradient(90deg, #00B4D8 0%, #0284C7 35%, #6366F1 70%, #8B5CF6 100%)",
                  color: "#FFFFFF",
                  fontSize: 14.5,
                  fontWeight: 900,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                  boxShadow: "0 6px 20px rgba(6,182,212,0.35)",
                  transition: "all 0.2s ease"
                }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                  <path d="M9 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H9" stroke="#FFFFFF" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M16 17L21 12L16 7" stroke="#FFFFFF" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M21 12H9" stroke="#FFFFFF" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                <span>Sign Out</span>
              </button>

              {/* Version Badge */}
              <div style={{ textAlign: "center", fontSize: 10, color: C.gray2, padding: "4px 0" }}>
                StokVigil AI Portal v2.4.0 • Connected to ICICI Breeze API
              </div>
            </div>
          )}
        </DraggableVerticalCanvas>

        {/* Bottom Navigation */}
        <div style={{
          height: navH, background: "rgba(6,8,18,0.97)", backdropFilter: "blur(20px)",
          borderTop: `1px solid ${C.border}`,
          display: "flex", alignItems: "stretch",
          position: "sticky", bottom: 0, zIndex: 40,
        }}>
          <NavItem
            id="home"
            label="Home"
            icon={(active, color) => (
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M4 19V14M9 19V9M14 19V12M19 19V5" stroke={color} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"/>
                <line x1="2" y1="21" x2="22" y2="21" stroke={color} strokeWidth="2" strokeLinecap="round"/>
              </svg>
            )}
          />
          <NavItem
            id="alerts"
            label="Alerts"
            icon={(active, color) => (
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 22C13.1 22 14 21.1 14 20H10C10 21.1 10.9 22 12 22ZM18 16V11C18 7.93 16.37 5.36 13.5 4.68V4C13.5 3.17 12.83 2.5 12 2.5C11.17 2.5 10.5 3.17 10.5 4V4.68C7.64 5.36 6 7.92 6 11V16L4 18V19H20V18L18 16Z" fill={active ? "rgba(6,182,212,0.2)" : "none"} stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                {active && <circle cx="17" cy="5" r="3.5" fill="#06B6D4" />}
              </svg>
            )}
          />
          <NavItem
            id="watchlist"
            label="Watchlist"
            icon={(active, color) => (
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M8 6H21M8 12H21M8 18H21M3 6H3.01M3 12H3.01M3 18H3.01" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            )}
          />
          <NavItem
            id="settings"
            label="Settings"
            icon={(active, color) => (
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12.22 2H11.78C11.13 2 10.6 2.45 10.5 3.09L10.28 4.54C9.69 4.79 9.14 5.12 8.64 5.51L7.22 4.96C6.6 4.72 5.9 4.97 5.58 5.53L5.36 5.91C5.04 6.47 5.17 7.19 5.67 7.6L6.78 8.52C6.66 9.12 6.6 9.74 6.6 10.37C6.6 11 6.66 11.62 6.78 12.22L5.67 13.14C5.17 13.55 5.04 14.27 5.36 14.83L5.58 15.21C5.9 15.77 6.6 16.02 7.22 15.78L8.64 15.23C9.14 15.62 9.69 15.95 10.28 16.2L10.5 17.65C10.6 18.29 11.13 18.74 11.78 18.74H12.22C12.87 18.74 13.4 18.29 13.5 17.65L13.72 16.2C14.31 15.95 14.86 15.62 15.36 15.23L16.78 15.78C17.4 16.02 18.1 15.77 18.42 15.21L18.64 14.83C18.96 14.27 18.83 13.55 18.33 13.14L17.22 12.22C17.34 11.62 17.4 11 17.4 10.37C17.4 9.74 17.34 9.12 17.22 8.52L18.33 7.6C18.83 7.19 18.96 6.47 18.64 5.91L18.42 5.53C18.1 4.97 17.4 4.72 16.78 4.96L15.36 5.51C14.86 5.12 14.31 4.79 13.72 4.54L13.5 3.09C13.4 2.45 12.87 2 12.22 2Z" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                <circle cx="12" cy="10.37" r="3" stroke={color} strokeWidth="1.8"/>
              </svg>
            )}
          />
        </div>

        {/* STOCK DETAIL MODAL */}
        {selectedStock && (
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
                    <div style={{ fontSize: 16, fontWeight: 900, color: C.white }}>{selectedStock.symbol}</div>
                    <SignalBadge signal={selectedStock.signal} type={selectedStock.signalType} />
                  </div>
                  <div style={{ fontSize: 11, color: C.cyan, fontWeight: 700, marginTop: 2 }}>{selectedStock.sector}</div>
                </div>
                <button onClick={() => setSelectedStock(null)} style={{ background: "none", border: "none", color: C.gray1, fontSize: 18, cursor: "pointer" }}>✕</button>
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
                  <div style={{ fontSize: 11, fontWeight: 800, color: C.white, marginTop: 2 }}>₹{selectedStock.dayLow} – ₹{selectedStock.dayHigh}</div>
                </div>

                <div style={{ background: "#080B16", border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }}>
                  <div style={{ fontSize: 10, color: C.gray2, textTransform: "uppercase", fontWeight: 700 }}>52-Wk High</div>
                  <div style={{ fontSize: 11, fontWeight: 800, color: C.cyan, marginTop: 2 }}>₹{selectedStock.high52}</div>
                </div>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <Btn
                  variant={selectedStock.signalType === "sell" ? "danger" : "primary"}
                  onClick={() => {
                    const isSell = selectedStock.signalType === "sell";
                    setTradeData({
                      symbol: selectedStock.symbol,
                      price: selectedStock.price,
                      type: isSell ? "SELL" : "BUY",
                      target: "₹3,250",
                      sl: "₹2,820",
                    });
                    setOrderQty(selectedStock.qty || 10);
                    setLimitPrice(selectedStock.price.toFixed(2));
                    setShowTradeModal(true);
                    setSelectedStock(null);
                  }}
                >
                  {selectedStock.signalType === "sell"
                    ? "⚡ Place Sell Order"
                    : selectedStock.signalType === "strong_buy" || selectedStock.signalType === "buy"
                      ? "⚡ Place Buy Order"
                      : "⚡ Execute Trade Order"
                  }
                </Btn>
                <Btn variant="ghost" onClick={() => setSelectedStock(null)}>
                  Close
                </Btn>
              </div>
            </div>
          </div>
        )}

        {/* ICICI Key Setup Modal */}
        {showKeyModal && (
          <div style={{
            position: "fixed", inset: 0,
            background: "rgba(6,8,18,0.92)", backdropFilter: "blur(16px)",
            display: "flex", alignItems: "center", justifyContent: "center",
            padding: 20, zIndex: 50,
          }}>
            <div className="anim-fadeup" style={{
              width: "100%", maxWidth: 380, background: C.bgCard,
              border: `1px solid ${C.borderCyan}`, borderRadius: 22, padding: 20,
            }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                <div style={{ fontSize: 14, fontWeight: 900, color: C.white }}>🔑 ICICI Breeze Key Setup</div>
                <button onClick={() => setShowKeyModal(false)} style={{ background: "none", border: "none", color: C.gray1, fontSize: 18, cursor: "pointer" }}>✕</button>
              </div>

              {keySaved && (
                <div style={{ background: "rgba(16,185,129,0.12)", border: `1px solid rgba(16,185,129,0.3)`, borderRadius: 12, padding: "10px 14px", fontSize: 12, color: C.emerald, fontWeight: 800, marginBottom: 12 }}>
                  ✅ Credentials encrypted (AES-256) and saved!
                </div>
              )}

              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <Input
                  label="App Key"
                  type={showAppKey ? "text" : "password"}
                  value={appKey}
                  onChange={(val) => setAppKey(val)}
                  placeholder="Enter App Key"
                  rightAction={
                    <button
                      type="button"
                      onClick={() => setShowAppKey(v => !v)}
                      style={{ background: "none", border: "none", color: C.cyan, fontSize: 10.5, fontWeight: 800, cursor: "pointer", display: "flex", alignItems: "center", gap: 4, padding: 0 }}
                    >
                      {showAppKey
                        ? <VisibilityOffOutlinedIcon size={14} color={C.cyan} />
                        : <VisibilityOutlinedIcon size={14} color={C.cyan} />}
                      <span>{showAppKey ? "Hide" : "Show"}</span>
                    </button>
                  }
                />
                <Input
                  label="Secret Key"
                  type={showSecretKey ? "text" : "password"}
                  value={secretKey}
                  onChange={(val) => setSecretKey(val)}
                  placeholder="Enter Secret Key"
                  rightAction={
                    <button
                      type="button"
                      onClick={() => setShowSecretKey(v => !v)}
                      style={{ background: "none", border: "none", color: C.cyan, fontSize: 10.5, fontWeight: 800, cursor: "pointer", display: "flex", alignItems: "center", gap: 4, padding: 0 }}
                    >
                      {showSecretKey
                        ? <VisibilityOffOutlinedIcon size={14} color={C.cyan} />
                        : <VisibilityOutlinedIcon size={14} color={C.cyan} />}
                      <span>{showSecretKey ? "Hide" : "Show"}</span>
                    </button>
                  }
                />

                <button
                  type="button"
                  onClick={() => {
                    if (!appKey.trim()) {
                      alert("Please enter your ICICI App Key above first before opening login.");
                      return;
                    }
                    window.open(`https://api.icicidirect.com/apiuser/login?api_key=${encodeURIComponent(appKey.trim())}`, "_blank");
                  }}
                  style={{
                    background: "rgba(6,182,212,0.08)", border: `1.5px solid ${C.borderCyan}`,
                    borderRadius: 12, padding: "10px 16px", color: C.cyan, fontSize: 12, fontWeight: 800, cursor: "pointer",
                    display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                  }}
                >
                  🌐 1-Tap ICICI Web Login
                </button>

                <Input label="Session Token" value={sessionTok} onChange={setSessionTok} placeholder="Paste session token here" />

                <Btn
                  variant="primary"
                  onClick={saveKey}
                  disabled={!appKey.trim() || !secretKey.trim() || !sessionTok.trim() || keySaving}
                  style={{
                    opacity: (!appKey.trim() || !secretKey.trim() || !sessionTok.trim() || keySaving) ? 0.45 : 1,
                    cursor: (!appKey.trim() || !secretKey.trim() || !sessionTok.trim() || keySaving) ? "not-allowed" : "pointer"
                  }}
                >
                  {keySaving ? "⏳ Encrypting & Saving..." : "🔐 Encrypt & Save Key"}
                </Btn>
              </div>
            </div>
          </div>
        )}

        {/* INTERACTIVE TRADE ORDER PLACEMENT MODAL */}
        {showTradeModal && tradeData && (
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
                <button onClick={() => { setShowTradeModal(false); setOrderSent(false); }} style={{ background: "none", border: "none", color: C.gray1, fontSize: 18, cursor: "pointer" }}>✕</button>
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
                  <Btn variant="primary" onClick={() => { setShowTradeModal(false); setOrderSent(false); }}>
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
                            placeholder="3250"
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
                            placeholder="2820"
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
                    onClick={executeTrade}
                    disabled={orderSending}
                  >
                    {orderSending ? "⚡ Sending Order via Breeze…" : "⚡ Confirm & Send Order via Breeze →"}
                  </Btn>
                </div>
              )}
            </div>
          </div>
        )}

        {/* GLOBAL FORGOT / CHANGE PASSWORD MODAL */}
        {showForgotModal && (
          <div style={{
            position: "fixed", inset: 0,
            background: "rgba(6,8,18,0.92)", backdropFilter: "blur(16px)",
            display: "flex", alignItems: "center", justifyContent: "center",
            padding: 20, zIndex: 60,
          }}>
            <div className="anim-fadeup" style={{
              width: "100%", maxWidth: 380, background: C.bgCard,
              border: `1.5px solid ${C.borderCyan}`, borderRadius: 22, padding: 20,
              boxShadow: "0 20px 50px rgba(0,0,0,0.8)",
            }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                <div style={{ fontSize: 14, fontWeight: 900, color: C.white, display: "flex", alignItems: "center", gap: 6 }}>
                  <span>🔑</span> {user?.id ? "Change Password" : "Reset Password"}
                </div>
                <button
                  onClick={() => {
                    setShowForgotModal(false);
                    setForgotSent(false);
                    setNewPasswordDone(false);
                    setNewPassword("");
                    setNewPasswordError(null);
                  }}
                  style={{ background: "none", border: "none", color: C.gray1, fontSize: 18, cursor: "pointer" }}
                >✕</button>
              </div>

              {/* Case 1: Authenticated in Settings -> Direct Password Update (Matches Mobile) */}
              {user?.id ? (
                newPasswordDone ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                    <div style={{
                      background: "rgba(16,185,129,0.12)", border: `1px solid rgba(16,185,129,0.4)`,
                      borderRadius: 14, padding: 16, textAlign: "center"
                    }}>
                      <div style={{ fontSize: 24, marginBottom: 4 }}>✅</div>
                      <div style={{ fontSize: 13, fontWeight: 900, color: C.emerald }}>Password Changed Successfully!</div>
                      <div style={{ fontSize: 11, color: C.gray1, marginTop: 4, lineHeight: 1.4 }}>
                        Your new password is now active for all future logins.
                      </div>
                    </div>
                    <Btn variant="primary" onClick={() => {
                      setShowForgotModal(false);
                      setNewPasswordDone(false);
                      setNewPassword("");
                    }}>
                      Done
                    </Btn>
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                    <div style={{ fontSize: 11.5, color: C.gray1, lineHeight: 1.5 }}>
                      Please enter your new password below (at least 6 characters):
                    </div>
                    {newPasswordError && (
                      <div style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 10, padding: "8px 12px", color: C.rose, fontSize: 11, fontWeight: 700 }}>
                        {newPasswordError}
                      </div>
                    )}
                    <Input
                      label="New Password"
                      type={showNewPassword ? "text" : "password"}
                      value={newPassword}
                      onChange={setNewPassword}
                      placeholder="Enter at least 6 characters"
                      rightAction={
                        <button
                          type="button"
                          onClick={() => setShowNewPassword(v => !v)}
                          style={{ background: "none", border: "none", color: C.cyan, fontSize: 10.5, fontWeight: 800, cursor: "pointer", display: "flex", alignItems: "center", gap: 4, padding: 0 }}
                        >
                          {showNewPassword
                            ? <VisibilityOffOutlinedIcon size={14} color={C.cyan} />
                            : <VisibilityOutlinedIcon size={14} color={C.cyan} />}
                          <span>{showNewPassword ? "Hide" : "Show"}</span>
                        </button>
                      }
                    />
                    <Btn
                      variant="primary"
                      onClick={async () => {
                        const pass = newPassword.trim();
                        if (pass.length < 6) {
                          setNewPasswordError("Password must be at least 6 characters.");
                          return;
                        }
                        setNewPasswordLoading(true);
                        setNewPasswordError(null);
                        try {
                          if (supabase) {
                            const { error } = await supabase.auth.updateUser({ password: pass });
                            if (error) throw error;
                          }
                          setNewPasswordDone(true);
                        } catch (err: any) {
                          setNewPasswordError(err.message || "Failed to update password.");
                        } finally {
                          setNewPasswordLoading(false);
                        }
                      }}
                      disabled={newPasswordLoading || newPassword.trim().length < 6}
                    >
                      {newPasswordLoading ? "Saving Password…" : "Save New Password →"}
                    </Btn>
                  </div>
                )
              ) : (
                /* Case 2: Unauthenticated on Auth Screen -> Send Reset Link */
                forgotSent ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                    <div style={{
                      background: "rgba(16,185,129,0.12)", border: `1px solid rgba(16,185,129,0.4)`,
                      borderRadius: 14, padding: 16, textAlign: "center"
                    }}>
                      <div style={{ fontSize: 24, marginBottom: 4 }}>🎉</div>
                      <div style={{ fontSize: 13, fontWeight: 900, color: C.emerald }}>Password Reset Link Sent!</div>
                      <div style={{ fontSize: 11, color: C.gray1, marginTop: 4, lineHeight: 1.4 }}>
                        We have sent a secure password reset link to <b>{forgotEmail || "your registered email"}</b>.
                      </div>
                    </div>
                    <Btn variant="primary" onClick={() => { setShowForgotModal(false); setForgotSent(false); }}>
                      Done
                    </Btn>
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                    <div style={{ fontSize: 11.5, color: C.gray1, lineHeight: 1.5 }}>
                      Enter your registered email address to receive an instant secure link to reset your password.
                    </div>
                    <Input label="Registered Email Address" type="email" value={forgotEmail} onChange={setForgotEmail} placeholder="investor@gmail.com" />
                    <Btn
                      variant="primary"
                      onClick={async () => {
                        const target = forgotEmail.trim();
                        if (!target) return;
                        setForgotLoading(true);
                        if (supabase) {
                          try {
                            await supabase.auth.resetPasswordForEmail(target, {
                              redirectTo: window.location.origin
                            });
                          } catch (e) {
                            console.warn("Reset password error:", e);
                          }
                        }
                        setForgotLoading(false);
                        setForgotSent(true);
                      }}
                      disabled={forgotLoading || !forgotEmail.trim()}
                    >
                      {forgotLoading ? "Sending Link…" : "⚡ Send Password Reset Link →"}
                    </Btn>
                  </div>
                )
              )}
            </div>
          </div>
        )}

        {/* GLOBAL DELETE ACCOUNT MODAL */}
        {showDeleteModal && (
          <div style={{
            position: "fixed", inset: 0,
            background: "rgba(6,8,18,0.92)", backdropFilter: "blur(16px)",
            display: "flex", alignItems: "center", justifyContent: "center",
            padding: 20, zIndex: 60,
          }}>
            <div className="anim-fadeup" style={{
              width: "100%", maxWidth: 400, background: C.bgCard,
              border: `1.5px solid rgba(239,68,68,0.5)`, borderRadius: 22, padding: 22,
              boxShadow: "0 20px 50px rgba(0,0,0,0.8), 0 0 30px rgba(239,68,68,0.15)",
            }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                <div style={{ fontSize: 15, fontWeight: 900, color: C.white, display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ color: C.rose }}>⚠️</span> Delete Account Permanently?
                </div>
                <button onClick={() => setShowDeleteModal(false)} style={{ background: "none", border: "none", color: C.gray1, fontSize: 18, cursor: "pointer" }}>✕</button>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <div style={{ fontSize: 12, color: C.gray1, lineHeight: 1.4 }}>
                  This action is permanent and cannot be undone. All of the following will be erased immediately:
                </div>

                <div style={{
                  background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)",
                  borderRadius: 12, padding: 12, fontSize: 11.5, color: C.gray1, display: "flex", flexDirection: "column", gap: 4
                }}>
                  <div>• All personal watchlists and synced stocks</div>
                  <div>• Encrypted ICICI Breeze API & Session keys</div>
                  <div>• Telegram bot bindings & device tokens</div>
                  <div style={{ color: C.rose, fontWeight: 800 }}>• Your login credentials and account identity</div>
                </div>

                <div>
                  <div style={{ fontSize: 12, color: C.gray1, marginBottom: 6 }}>
                    To confirm, please type <b style={{ color: C.rose }}>DELETE</b> below:
                  </div>
                  <input
                    value={deleteConfirmText}
                    onChange={e => setDeleteConfirmText(e.target.value)}
                    placeholder="Type DELETE to confirm"
                    style={{
                      width: "100%", background: "#080B16", border: `1px solid ${C.border}`,
                      borderRadius: 10, padding: "10px 12px", color: C.white, fontSize: 13, fontWeight: 700,
                      outline: "none"
                    }}
                  />
                </div>

                <div style={{ display: "flex", gap: 12, marginTop: 6 }}>
                  <button
                    onClick={() => setShowDeleteModal(false)}
                    style={{
                      flex: 1, height: 44, borderRadius: 12,
                      background: "#131A2B", border: "1.2px solid #2A364F",
                      color: "#94A3B8", fontSize: 13.5, fontWeight: 800, cursor: "pointer",
                      transition: "all 0.2s ease"
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={doDeleteAccount}
                    disabled={deleteConfirmText.trim() !== "DELETE" || isDeletingAccount}
                    style={{
                      flex: 1, height: 44, borderRadius: 12,
                      background: deleteConfirmText.trim() === "DELETE"
                        ? "linear-gradient(135deg, #EF4444 0%, #DC2626 50%, #B91C1C 100%)"
                        : "#201318",
                      border: deleteConfirmText.trim() === "DELETE"
                        ? "1.2px solid #F87171"
                        : "1.2px solid #4A1D24",
                      color: deleteConfirmText.trim() === "DELETE" ? "#FFFFFF" : "#8B3A44",
                      fontSize: 13.5, fontWeight: 900,
                      cursor: deleteConfirmText.trim() === "DELETE" ? "pointer" : "not-allowed",
                      boxShadow: deleteConfirmText.trim() === "DELETE" ? "0 4px 16px rgba(239,68,68,0.4)" : "none",
                      transition: "all 0.2s ease"
                    }}
                  >
                    {isDeletingAccount ? "Deleting…" : "Delete Account"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
