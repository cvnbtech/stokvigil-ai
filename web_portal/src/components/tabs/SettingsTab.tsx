"use client";
import React from "react";
import { C } from "../ui/DesignTokens";

interface SettingsTabProps {
  user: { id?: string; name: string; email: string } | null;
  openKeyModal: () => void;
  executionMode: "INSTANT" | "CONFIRM";
  setExecutionMode: (m: "INSTANT" | "CONFIRM") => void;
  updatePreference: (key: string, val: any) => Promise<void>;
  telegramChatId: string;
  setTelegramChatId: (id: string) => void;
  telegramSaved: boolean;
  setTelegramSaved: (s: boolean) => void;
  setTelegramEnabled: (e: boolean) => void;
  alertSensitivity: "HIGH" | "ALL" | "FII";
  setAlertSensitivity: (s: "HIGH" | "ALL" | "FII") => void;
  fcmEnabled: boolean;
  toggleFcm: (enabled: boolean) => void;
  setForgotEmail: (email: string) => void;
  setShowForgotModal: (show: boolean) => void;
  setDeleteConfirmText: (text: string) => void;
  setShowDeleteModal: (show: boolean) => void;
  doSignOut: () => void;
}

export default function SettingsTab({
  user,
  openKeyModal,
  executionMode,
  setExecutionMode,
  updatePreference,
  telegramChatId,
  setTelegramChatId,
  telegramSaved,
  setTelegramSaved,
  setTelegramEnabled,
  alertSensitivity,
  setAlertSensitivity,
  fcmEnabled,
  toggleFcm,
  setForgotEmail,
  setShowForgotModal,
  setDeleteConfirmText,
  setShowDeleteModal,
  doSignOut,
}: SettingsTabProps) {
  return (
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
                display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16
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

          {/* Manual Telegram Chat ID Input */}
          <div style={{ background: C.bgCard2, borderRadius: 10, padding: "10px 12px", border: `1px solid ${C.border}` }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: C.white }}>Telegram Chat ID</div>
              <span style={{ fontSize: 10, color: C.gray2 }}>Get from @userinfobot</span>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                type="text"
                placeholder="e.g. 1084729182"
                value={telegramChatId}
                onChange={e => {
                  setTelegramChatId(e.target.value);
                  setTelegramSaved(false);
                }}
                style={{
                  flex: 1, background: C.bgCard, border: `1px solid ${C.border}`,
                  borderRadius: 8, padding: "6px 10px", fontSize: 11.5, color: C.white, outline: "none"
                }}
              />
              <button
                onClick={async () => {
                  if (!telegramChatId.trim()) return;
                  await updatePreference("telegram_chat_id", telegramChatId.trim());
                  await updatePreference("telegram_enabled", true);
                  setTelegramEnabled(true);
                  setTelegramSaved(true);
                  setTimeout(() => setTelegramSaved(false), 3000);
                }}
                style={{
                  background: telegramSaved ? "rgba(16,185,129,0.15)" : "rgba(6,182,212,0.15)",
                  border: `1px solid ${telegramSaved ? C.emerald : C.cyan}`,
                  borderRadius: 8, padding: "6px 12px", color: telegramSaved ? C.emerald : C.cyan,
                  fontSize: 11, fontWeight: 800, cursor: "pointer"
                }}
              >
                {telegramSaved ? "Saved ✓" : "Save ID"}
              </button>
            </div>
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
  );
}
