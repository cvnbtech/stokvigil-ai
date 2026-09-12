"use client";
import React from "react";
import { C } from "../ui/DesignTokens";

interface DeleteAccountModalProps {
  onClose: () => void;
  deleteConfirmText: string;
  setDeleteConfirmText: (val: string) => void;
  doDeleteAccount: () => void;
  isDeletingAccount: boolean;
}

export default function DeleteAccountModal({
  onClose,
  deleteConfirmText,
  setDeleteConfirmText,
  doDeleteAccount,
  isDeletingAccount,
}: DeleteAccountModalProps) {
  return (
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
          <button onClick={onClose} style={{ background: "none", border: "none", color: C.gray1, fontSize: 18, cursor: "pointer" }}>✕</button>
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
              onClick={onClose}
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
  );
}
