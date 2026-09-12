"use client";
import React from "react";
import { C } from "../ui/DesignTokens";
import { Input, Btn, VisibilityOutlinedIcon, VisibilityOffOutlinedIcon } from "../ui/UiAtoms";

interface IciciKeyModalProps {
  onClose: () => void;
  appKey: string;
  setAppKey: (val: string) => void;
  secretKey: string;
  setSecretKey: (val: string) => void;
  sessionTok: string;
  setSessionTok: (val: string) => void;
  showAppKey: boolean;
  setShowAppKey: React.Dispatch<React.SetStateAction<boolean>>;
  showSecretKey: boolean;
  setShowSecretKey: React.Dispatch<React.SetStateAction<boolean>>;
  keySaved: boolean;
  keySaving: boolean;
  saveKey: () => void;
}

export default function IciciKeyModal({
  onClose,
  appKey,
  setAppKey,
  secretKey,
  setSecretKey,
  sessionTok,
  setSessionTok,
  showAppKey,
  setShowAppKey,
  showSecretKey,
  setShowSecretKey,
  keySaved,
  keySaving,
  saveKey,
}: IciciKeyModalProps) {
  return (
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
          <button onClick={onClose} style={{ background: "none", border: "none", color: C.gray1, fontSize: 18, cursor: "pointer" }}>✕</button>
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
  );
}
