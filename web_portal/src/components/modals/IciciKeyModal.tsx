"use client";
import React, { useState } from "react";
import { C } from "../ui/DesignTokens";
import { Input, Btn } from "../ui/UiAtoms";
import { IciciDirectLogo, ZerodhaLogo, AngelOneLogo } from "../ui/BrokerLogos";

interface IciciKeyModalProps {
  onClose: () => void;
  sessionTok: string;
  setSessionTok: (val: string) => void;
  keySaved: boolean;
  keySaving: boolean;
  saveKey: () => void;
  loginUrl?: string;
  selectedBroker?: string;
  setSelectedBroker?: (b: string) => void;
}

export default function IciciKeyModal({
  onClose,
  sessionTok,
  setSessionTok,
  keySaved,
  keySaving,
  saveKey,
  loginUrl,
  selectedBroker = "icici",
  setSelectedBroker,
}: IciciKeyModalProps) {
  const [activeTab, setActiveTab] = useState<string>(selectedBroker || "icici");
  const [copySuccess, setCopySuccess] = useState(false);

  const effectiveLoginUrl = loginUrl || "https://api.icicidirect.com/apiuser/login";

  const handlePasteClipboard = async () => {
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard) {
        const text = await navigator.clipboard.readText();
        if (text) {
          let clean = text.trim();
          if (clean.includes("apisession=")) {
            clean = clean.split("apisession=")[1].split("&")[0];
          }
          setSessionTok(decodeURIComponent(clean));
          setCopySuccess(true);
          setTimeout(() => setCopySuccess(false), 2000);
        }
      }
    } catch (_) {}
  };

  return (
    <div style={{
      position: "fixed", inset: 0,
      background: "rgba(6,8,18,0.92)", backdropFilter: "blur(16px)",
      display: "flex", alignItems: "center", justifyContent: "center",
      padding: 20, zIndex: 50,
    }}>
      <div className="anim-fadeup" style={{
        width: "100%", maxWidth: 440, background: C.bgCard,
        border: `1px solid ${C.borderCyan}`, borderRadius: 24, padding: "24px 22px",
        boxShadow: "0 20px 40px rgba(0,0,0,0.6)",
      }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 900, color: C.white, display: "flex", alignItems: "center", gap: 8 }}>
              <span>⚡ Connect Demat Broker</span>
            </div>
            <div style={{ fontSize: 11, color: C.gray1, marginTop: 3 }}>
              Institutional Master App Model • Zero API Keys Needed
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: "rgba(255,255,255,0.06)", border: "none", color: C.gray1, width: 28, height: 28, borderRadius: 14, fontSize: 14, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}
          >
            ✕
          </button>
        </div>

        {/* Multi-Broker Switcher Tabs */}
        <div style={{ display: "flex", gap: 6, marginBottom: 18, background: "rgba(255,255,255,0.03)", padding: 4, borderRadius: 12 }}>
          <button
            type="button"
            onClick={() => {
              setActiveTab("icici");
              if (setSelectedBroker) setSelectedBroker("icici");
            }}
            style={{
              flex: 1, padding: "8px 10px", borderRadius: 8, border: "none",
              background: activeTab === "icici" ? "rgba(6,182,212,0.15)" : "transparent",
              color: activeTab === "icici" ? C.cyan : C.gray1,
              fontSize: 11, fontWeight: 800, cursor: "pointer",
              display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
            }}
          >
            <IciciDirectLogo size={16} />
            <span>ICICI Direct</span>
            <span style={{ fontSize: 9, background: C.emerald, color: "#000", padding: "1px 5px", borderRadius: 4, fontWeight: 900 }}>ACTIVE</span>
          </button>

          <button
            type="button"
            disabled
            style={{
              flex: 1, padding: "8px 10px", borderRadius: 8, border: "none",
              background: "transparent", color: C.gray1, opacity: 0.5,
              fontSize: 11, fontWeight: 700, cursor: "not-allowed",
              display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
            }}
          >
            <ZerodhaLogo size={16} />
            <span>Zerodha</span>
            <span style={{ fontSize: 9, background: "rgba(255,255,255,0.1)", color: C.gray1, padding: "1px 5px", borderRadius: 4 }}>SOON</span>
          </button>

          <button
            type="button"
            disabled
            style={{
              flex: 1, padding: "8px 10px", borderRadius: 8, border: "none",
              background: "transparent", color: C.gray1, opacity: 0.5,
              fontSize: 11, fontWeight: 700, cursor: "not-allowed",
              display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
            }}
          >
            <AngelOneLogo size={16} />
            <span>Angel One</span>
            <span style={{ fontSize: 9, background: "rgba(255,255,255,0.1)", color: C.gray1, padding: "1px 5px", borderRadius: 4 }}>SOON</span>
          </button>
        </div>

        {keySaved && (
          <div style={{ background: "rgba(16,185,129,0.12)", border: `1px solid rgba(16,185,129,0.3)`, borderRadius: 12, padding: "10px 14px", fontSize: 12, color: C.emerald, fontWeight: 800, marginBottom: 14 }}>
            ✅ Demat Connected & Encrypted (AES-256)! Syncing holdings...
          </div>
        )}

        {/* Step 1: 1-Click Login Card */}
        <div style={{
          background: "rgba(6,182,212,0.04)", border: "1px solid rgba(6,182,212,0.2)",
          borderRadius: 14, padding: "12px 14px", marginBottom: 14,
        }}>
          <div style={{ fontSize: 11, fontWeight: 900, color: C.cyan, textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 4 }}>
            Step 1: Authenticate with ICICI Direct
          </div>
          <div style={{ fontSize: 11, color: C.gray1, lineHeight: 1.4, marginBottom: 10 }}>
            Opens official ICICI login. Sign in with your regular User ID, Password & OTP.
          </div>
          <button
            type="button"
            onClick={() => window.open(effectiveLoginUrl, "_blank")}
            style={{
              width: "100%", background: "rgba(6,182,212,0.12)", border: `1.5px solid ${C.borderCyan}`,
              borderRadius: 10, padding: "10px 14px", color: C.cyan, fontSize: 12, fontWeight: 900, cursor: "pointer",
              display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
            }}
          >
            <IciciDirectLogo size={18} />
            <span>1-Click ICICI Direct Login</span>
            <span style={{ fontSize: 11 }}>↗</span>
          </button>
        </div>

        {/* Step 2: Session Token */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
            <span style={{ fontSize: 11, fontWeight: 900, color: C.white, textTransform: "uppercase" }}>
              Step 2: Session Token
            </span>
            <button
              type="button"
              onClick={handlePasteClipboard}
              style={{ background: "none", border: "none", color: copySuccess ? C.emerald : C.cyan, fontSize: 11, fontWeight: 800, cursor: "pointer", display: "flex", alignItems: "center", gap: 4, padding: 0 }}
            >
              📋 {copySuccess ? "Pasted!" : "Paste from Clipboard"}
            </button>
          </div>
          <Input
            label="Session Token"
            value={sessionTok}
            onChange={setSessionTok}
            placeholder="Paste your session token (apisession) here"
          />
          <div style={{ fontSize: 10, color: C.gray1, marginTop: 4 }}>
            Captured automatically upon redirect or copied from the login redirect URL.
          </div>
        </div>

        {/* Primary CTA Button */}
        <Btn
          variant="primary"
          onClick={saveKey}
          disabled={!sessionTok.trim() || keySaving}
          style={{
            width: "100%", padding: "12px 16px", borderRadius: 12,
            opacity: (!sessionTok.trim() || keySaving) ? 0.45 : 1,
            cursor: (!sessionTok.trim() || keySaving) ? "not-allowed" : "pointer"
          }}
        >
          {keySaving ? "⏳ Connecting & Syncing Demat..." : "🔐 Connect Demat & Sync Holdings"}
        </Btn>

        {/* Compliance Footer */}
        <div style={{ textAlign: "center", fontSize: 10, color: C.gray1, marginTop: 14, lineHeight: 1.4 }}>
          🛡️ 256-Bit Vault Encrypted • SEBI Registered Integration • Zero Plaintext Storage
        </div>
      </div>
    </div>
  );
}
