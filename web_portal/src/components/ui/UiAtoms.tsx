"use client";
import React, { useState, useRef } from "react";
import { C } from "./DesignTokens";

export function decodeSafeBase64(str: string): string {
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

export function encodeSafeBase64(str: string): string {
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

// ─────────────────────────────────────────────
// OFFICIAL STOKVIGIL AI LOGO
// ─────────────────────────────────────────────
export function TradingAILogo({ size = 48 }: { size?: number }) {
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

export function VisibilityOutlinedIcon({ size = 15, color = "currentColor" }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 4.5C7 4.5 2.73 7.61 1 12C2.73 16.39 7 19.5 12 19.5C17 19.5 21.27 16.39 23 12C21.27 7.61 17 4.5 12 4.5ZM12 17C9.24 17 7 14.76 7 12C7 9.24 9.24 7 12 7C14.76 7 17 9.24 17 12C17 14.76 14.76 17 12 17ZM12 9C10.34 9 9 10.34 9 12C9 13.66 10.34 15 12 15C13.66 15 15 13.66 15 12C15 10.34 13.66 9 12 9Z" fill={color}/>
    </svg>
  );
}

export function VisibilityOffOutlinedIcon({ size = 15, color = "currentColor" }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 7C14.76 7 17 9.24 17 12C17 12.65 16.87 13.26 16.64 13.83L19.56 16.75C21.07 15.49 22.26 13.86 23 12C21.27 7.61 17 4.5 12 4.5C10.6 4.5 9.26 4.75 8.02 5.2L10.18 7.36C10.74 7.13 11.35 7 12 7ZM2 4.27L4.28 6.55L4.74 7.01C3.08 8.3 1.78 10.02 1 12C2.73 16.39 7 19.5 12 19.5C13.55 19.5 15.03 19.2 16.38 18.66L16.8 19.08L19.73 22L21 20.73L3.27 3L2 4.27ZM7.53 9.8L9.08 11.35C9.03 11.56 9 11.78 9 12C9 13.66 10.34 15 12 15C12.22 15 12.44 14.97 12.65 14.92L14.2 16.47C13.53 16.8 12.79 17 12 17C9.24 17 7 14.76 7 12C7 11.21 7.2 10.47 7.53 9.8ZM11.84 9.02L14.99 12.17C14.98 12.01 15 11.85 15 11.7C15 10.04 13.66 8.7 12 8.7C11.85 8.7 11.69 8.72 11.53 8.73L11.84 9.02Z" fill={color}/>
    </svg>
  );
}

// ─────────────────────────────────────────────
// REUSABLE COMPONENTS
// ─────────────────────────────────────────────
export function Card({ children, style, onClick }: { children: React.ReactNode; style?: React.CSSProperties; onClick?: () => void }) {
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

export function Btn({
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

export function Input({ label, type = "text", value, onChange, placeholder = "", rightAction }: {
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

export function Badge({ label, color = "cyan" }: { label: string; color?: "cyan" | "emerald" | "rose" | "amber" | "violet" }) {
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

export function SignalBadge({ signal, type }: { signal: string; type?: "strong_buy" | "buy" | "sell" | "hold" | "neutral" | "monitoring" | string }) {
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
        : isHold
          ? "rgba(234,179,8,0.18)"
          : "rgba(148,163,184,0.15)";

  const border = isStrong
    ? "rgba(16,185,129,0.5)"
    : isBuy
      ? "rgba(6,182,212,0.4)"
      : isSell
        ? "rgba(245,158,11,0.4)"
        : isHold
          ? "rgba(234,179,8,0.4)"
          : "rgba(148,163,184,0.3)";

  const color = isStrong ? C.emerald : isBuy ? C.cyan : isSell ? C.amber : isHold ? "#EAB308" : C.gray2;

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

export function Divider({ label }: { label?: string }) {
  if (!label) return <div style={{ height: 1, background: C.border, margin: "4px 0" }} />;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "4px 0" }}>
      <div style={{ flex: 1, height: 1, background: C.border }} />
      <span style={{ fontSize: 11, color: C.gray2, fontWeight: 600 }}>{label}</span>
      <div style={{ flex: 1, height: 1, background: C.border }} />
    </div>
  );
}

export function TncModal({ onAccept, onClose }: { onAccept: () => void; onClose: () => void }) {
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

export function DraggableChipBar({ children }: { children: React.ReactNode }) {
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

export function DraggableVerticalCanvas({ children, className, style }: { children: React.ReactNode; className?: string; style?: React.CSSProperties }) {
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
