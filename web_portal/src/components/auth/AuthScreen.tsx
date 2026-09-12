"use client";
import React from "react";
import { C } from "../ui/DesignTokens";
import {
  TradingAILogo,
  Input,
  Btn,
  Divider,
  TncModal,
  VisibilityOutlinedIcon,
  VisibilityOffOutlinedIcon,
} from "../ui/UiAtoms";

interface AuthScreenProps {
  authTab: "signin" | "signup";
  setAuthTab: (tab: "signin" | "signup") => void;
  doGoogleOAuth: () => void;
  name: string;
  setName: (v: string) => void;
  email: string;
  setEmail: (v: string) => void;
  password: string;
  setPassword: (v: string) => void;
  showAuthPassword: boolean;
  setShowAuthPassword: React.Dispatch<React.SetStateAction<boolean>>;
  setShowForgotModal: (show: boolean) => void;
  tncAccepted: boolean;
  setTncAccepted: (accepted: boolean) => void;
  showTnc: boolean;
  setShowTnc: (show: boolean) => void;
  authError: string | null;
  authSuccess: string | null;
  doAuth: () => void;
  loading: boolean;
}

export default function AuthScreen({
  authTab,
  setAuthTab,
  doGoogleOAuth,
  name,
  setName,
  email,
  setEmail,
  password,
  setPassword,
  showAuthPassword,
  setShowAuthPassword,
  setShowForgotModal,
  tncAccepted,
  setTncAccepted,
  showTnc,
  setShowTnc,
  authError,
  authSuccess,
  doAuth,
  loading,
}: AuthScreenProps) {
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
    maxHeight: "920px",
    background: C.bg,
    display: "flex",
    flexDirection: "column",
    boxShadow: "0 25px 60px rgba(0,0,0,0.8), 0 0 40px rgba(6,182,212,0.08)",
    position: "relative",
    overflow: "hidden",
  };

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

      {showTnc && (
        <TncModal
          onAccept={() => { setTncAccepted(true); setShowTnc(false); }}
          onClose={() => setShowTnc(false)}
        />
      )}
    </div>
  );
}
