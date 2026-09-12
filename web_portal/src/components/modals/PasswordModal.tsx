"use client";
import React from "react";
import { C, supabase } from "../ui/DesignTokens";
import { Input, Btn, VisibilityOutlinedIcon, VisibilityOffOutlinedIcon } from "../ui/UiAtoms";

interface PasswordModalProps {
  user: { id?: string; name: string; email: string } | null;
  onClose: () => void;
  forgotEmail: string;
  setForgotEmail: (val: string) => void;
  forgotSent: boolean;
  setForgotSent: (val: boolean) => void;
  forgotLoading: boolean;
  setForgotLoading: (val: boolean) => void;
  newPassword: string;
  setNewPassword: (val: string) => void;
  newPasswordDone: boolean;
  setNewPasswordDone: (val: boolean) => void;
  newPasswordLoading: boolean;
  setNewPasswordLoading: (val: boolean) => void;
  newPasswordError: string | null;
  setNewPasswordError: (val: string | null) => void;
  showNewPassword: boolean;
  setShowNewPassword: React.Dispatch<React.SetStateAction<boolean>>;
}

export default function PasswordModal({
  user,
  onClose,
  forgotEmail,
  setForgotEmail,
  forgotSent,
  setForgotSent,
  forgotLoading,
  setForgotLoading,
  newPassword,
  setNewPassword,
  newPasswordDone,
  setNewPasswordDone,
  newPasswordLoading,
  setNewPasswordLoading,
  newPasswordError,
  setNewPasswordError,
  showNewPassword,
  setShowNewPassword,
}: PasswordModalProps) {
  return (
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
            onClick={onClose}
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
              <Btn variant="primary" onClick={onClose}>
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
              <Btn variant="primary" onClick={onClose}>
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
  );
}
