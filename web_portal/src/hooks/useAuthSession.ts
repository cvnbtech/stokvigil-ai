"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { BACKEND_URL, supabase } from "../components/ui/DesignTokens";

export interface AuthUser {
  id?: string;
  name: string;
  email: string;
}

interface UseAuthSessionProps {
  onSessionLoaded?: (uid: string) => void;
  onSignedOut?: () => void;
}

export function useAuthSession({ onSessionLoaded, onSignedOut }: UseAuthSessionProps = {}) {
  const [screen, setScreen] = useState<"auth" | "app">("auth");
  const [authTab, setAuthTab] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showAuthPassword, setShowAuthPassword] = useState(false);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authSuccess, setAuthSuccess] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authToken, setAuthToken] = useState<string>("");

  const [tncAccepted, setTncAccepted] = useState(false);
  const [showTnc, setShowTnc] = useState(false);
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotSent, setForgotSent] = useState(false);
  const [forgotLoading, setForgotLoading] = useState(false);

  const [newPassword, setNewPassword] = useState("");
  const [newPasswordDone, setNewPasswordDone] = useState(false);
  const [newPasswordLoading, setNewPasswordLoading] = useState(false);
  const [newPasswordError, setNewPasswordError] = useState<string | null>(null);
  const [showNewPassword, setShowNewPassword] = useState(false);

  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);

  const lastLoadedUidRef = useRef<string | null>(null);

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

  const handleSession = useCallback((session: any) => {
    if (session?.user) {
      setAuthToken(session?.access_token || "");
      const u: AuthUser = {
        id: session.user.id,
        name: session.user.user_metadata?.full_name || session.user.email?.split("@")[0] || "Investor",
        email: session.user.email || ""
      };
      setUser(u);
      setScreen("app");

      if (lastLoadedUidRef.current !== session.user.id) {
        lastLoadedUidRef.current = session.user.id;
        if (onSessionLoaded) {
          onSessionLoaded(session.user.id);
        }
      }
    } else {
      setAuthToken("");
      lastLoadedUidRef.current = null;
      setUser(null);
      setScreen("auth");
      if (onSignedOut) {
        onSignedOut();
      }
    }
  }, [onSessionLoaded, onSignedOut]);

  useEffect(() => {
    if (!supabase) return;

    supabase.auth.getSession().then(({ data: { session } }) => {
      handleSession(session);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      handleSession(session);
    });

    return () => subscription.unsubscribe();
  }, [handleSession]);

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
      if (onSessionLoaded) onSessionLoaded(fallbackId);
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
      if (onSessionLoaded) onSessionLoaded(fallbackId);
    }, 900);
  };

  const doSignOut = async () => {
    if (supabase) {
      await supabase.auth.signOut();
    }
    setUser(null);
    setScreen("auth");
    if (onSignedOut) onSignedOut();
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
        await supabase.from("profiles").delete().eq("id", user.id);
        await supabase.from("user_credentials").delete().eq("user_id", user.id);
        await supabase.from("user_watchlists").delete().eq("user_id", user.id);
        await supabase.from("stok_alerts").delete().eq("user_id", user.id);
        await supabase.auth.signOut();
      }
      setShowDeleteModal(false);
      setUser(null);
      setScreen("auth");
      alert("Account and all associated credentials have been securely wiped.");
    } catch (e: any) {
      console.warn("Delete account error:", e);
      alert(`Error deleting account: ${e.message || "Failed"}`);
    } finally {
      setIsDeletingAccount(false);
    }
  };

  return {
    screen, setScreen,
    authTab, setAuthTab,
    email, setEmail,
    password, setPassword,
    showAuthPassword, setShowAuthPassword,
    name, setName,
    loading, authError, authSuccess,
    user, setUser,
    authToken, setAuthToken,
    tncAccepted, setTncAccepted,
    showTnc, setShowTnc,
    showForgotModal, setShowForgotModal,
    forgotEmail, setForgotEmail,
    forgotSent, setForgotSent,
    forgotLoading, setForgotLoading,
    newPassword, setNewPassword,
    newPasswordDone, setNewPasswordDone,
    newPasswordLoading, setNewPasswordLoading,
    newPasswordError, setNewPasswordError,
    showNewPassword, setShowNewPassword,
    showDeleteModal, setShowDeleteModal,
    deleteConfirmText, setDeleteConfirmText,
    isDeletingAccount,
    getAuthHeaders,
    doAuth,
    doGoogleOAuth,
    doSignOut,
    doDeleteAccount
  };
}
