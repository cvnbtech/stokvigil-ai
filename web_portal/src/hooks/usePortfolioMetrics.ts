"use client";
import { useState, useEffect, useCallback } from "react";
import { HoldingItem, BACKEND_URL, supabase } from "../components/ui/DesignTokens";

interface UsePortfolioMetricsProps {
  getAuthHeaders: () => Promise<Record<string, string>>;
  userId?: string;
  onDematSynced?: (uid: string) => void;
}

export function usePortfolioMetrics({ getAuthHeaders, userId, onDematSynced }: UsePortfolioMetricsProps) {
  const [holdings, setHoldings] = useState<HoldingItem[]>([]);
  const [totalValue, setTotalValue] = useState(0);
  const [totalInvested, setTotalInvested] = useState(0);
  const [totalPnl, setTotalPnl] = useState(0);
  const [totalPnlPct, setTotalPnlPct] = useState(0);
  const [isPortfolioVisible, setIsPortfolioVisible] = useState(false);

  const [hasCredentials, setHasCredentials] = useState(false);
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [selectedBroker, setSelectedBroker] = useState<string>("icici");
  const [brokerLoginUrl, setBrokerLoginUrl] = useState<string>("");
  const [sessionTok, setSessionTok] = useState("");
  const [keySaved, setKeySaved] = useState(false);
  const [keySaving, setKeySaving] = useState(false);

  const [dematAutoSync, setDematAutoSync] = useState(false);
  const [fcmEnabled, setFcmEnabled] = useState(false);
  const [telegramChatId, setTelegramChatId] = useState("");
  const [telegramEnabled, setTelegramEnabled] = useState(true);
  const [telegramSaved, setTelegramSaved] = useState(false);
  const [alertSensitivity, setAlertSensitivity] = useState<"HIGH" | "ALL" | "FII">("HIGH");
  const [executionMode, setExecutionMode] = useState<"INSTANT" | "CONFIRM">("INSTANT");

  const loadPortfolioData = useCallback(async (uid: string) => {
    const todayStr = new Date().toISOString().split("T")[0];
    let portfolioLoaded = false;
    try {
      const headers = await getAuthHeaders();
      const credRes = await fetch(`/api/user/credentials?user_id=${uid}`, { headers });
      if (credRes.ok) {
        const credData = await credRes.json();
        if (credData.has_credentials) {
          const isTokenValidToday = Boolean(credData.token_date === todayStr);
          if (isTokenValidToday) setHasCredentials(true);
        }
        if (credData.login_url) {
          setBrokerLoginUrl(credData.login_url);
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
          setHoldings(data.holdings.map((h: any) => {
            const cleanSym = (h.clean_symbol || h.symbol || "").replace(/\.(BO|NS)$/i, "").trim().toUpperCase();
            const exch = h.exchange || ((h.full_symbol || h.symbol || "").toUpperCase().endsWith(".BO") ? "BSE" : "NSE");
            const displayName = h.name && h.name !== h.symbol && !h.name.endsWith(".BO") ? h.name : cleanSym;
            return {
              symbol: cleanSym,
              clean_symbol: cleanSym,
              full_symbol: h.full_symbol || h.symbol,
              name: displayName,
              exchange: exch,
              qty: h.quantity,
              avg: h.avg_price,
              price: h.current_price,
              pnl: h.pnl,
              pnlPct: h.pnl_percent,
              changePct: h.change_pct != null ? h.change_pct : null,
              dayHigh: h.day_high != null ? h.day_high : null,
              dayLow: h.day_low != null ? h.day_low : null,
              high52: h.high_52 != null ? h.high_52 : null,
              sector: `${exch} Equity`,
              signal: h.signal || null,
              signalType: h.signal_type || null,
              target: h.target ? (String(h.target).startsWith("₹") ? h.target : `₹${h.target}`) : "--",
              sl: h.stop_loss ? (String(h.stop_loss).startsWith("₹") ? h.stop_loss : `₹${h.stop_loss}`) : "--",
            };
          }));
          portfolioLoaded = true;

          // Auto-sync Demat holdings into user_watchlists table (Universal Canonical Suffix Rule)
          if (supabase && uid) {
            try {
              for (const h of data.holdings) {
                const rawSym = (h.symbol || h.clean_symbol || "").trim().toUpperCase();
                if (!rawSym) continue;
                const isBse = rawSym.endsWith(".BO") || (h.exchange && String(h.exchange).toUpperCase() === "BSE") || (/^\d{6}$/.test(rawSym));
                let cleanS = rawSym;
                if (cleanS.endsWith(".NS")) {
                  cleanS = cleanS.replace(/\.NS$/i, "").trim();
                }
                if (isBse && !cleanS.endsWith(".BO") && !/^\d{6}$/.test(cleanS)) {
                  cleanS = `${cleanS}.BO`;
                }
                if (cleanS) {
                  await supabase.from('user_watchlists').upsert({
                    user_id: uid,
                    symbol: cleanS,
                    is_auto_synced: true,
                  }, { onConflict: 'user_id,symbol' });
                }
              }
              if (onDematSynced) {
                onDematSynced(uid);
              }
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
  }, [getAuthHeaders, onDematSynced]);

  const loadProfileData = useCallback(async (uid: string) => {
    try {
      const headers = await getAuthHeaders();
      const res = await fetch(`/api/user/profile?user_id=${uid}`, { headers });
      if (res.ok) {
        const d = await res.json();
        const p = d.profile || {};
        if (p.telegram_chat_id) setTelegramChatId(p.telegram_chat_id);
        if (p.telegram_enabled !== undefined) setTelegramEnabled(p.telegram_enabled);
        if (p.alert_sensitivity) setAlertSensitivity(p.alert_sensitivity);
        if (p.execution_mode) setExecutionMode(p.execution_mode);
        if (p.demat_auto_sync !== undefined) setDematAutoSync(p.demat_auto_sync);
        if (p.fcm_enabled !== undefined) setFcmEnabled(p.fcm_enabled);
      }
    } catch (e) {
      console.warn("Could not load user profile:", e);
    }
  }, [getAuthHeaders]);

  const updatePreference = async (key: string, val: any) => {
    if (!userId) return;
    if (supabase) {
      try {
        await supabase.from('profiles').update({ [key]: val, updated_at: new Date().toISOString() }).eq('id', userId);
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
          user_id: userId,
          [key]: val,
        })
      });
    } catch (e) {
      console.warn("Update profile preference via API error:", e);
    }
  };

  const toggleDematAutoSync = async (val: boolean) => {
    setDematAutoSync(val);
    if (typeof window !== "undefined") {
      localStorage.setItem("stokvigil_demat_auto_sync", String(val));
    }
    await updatePreference("demat_auto_sync", val);
    if (val && userId) {
      loadPortfolioData(userId);
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

  const openKeyModal = useCallback(async () => {
    setShowKeyModal(true);
    let uid = userId;
    if (!uid && supabase) {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        uid = session?.user?.id;
      } catch (_) {}
    }
    if (uid) {
      loadPortfolioData(uid);
    }
    try {
      const headers = await getAuthHeaders();
      const base = BACKEND_URL ? BACKEND_URL.replace(/\/+$/, '') : '';
      let res = await fetch(`${base}/api/broker/icici/login-url`, { headers });
      if (!res.ok && base) {
        res = await fetch(`/api/broker/icici/login-url`, { headers });
      }
      if (res.ok) {
        const d = await res.json();
        if (d.login_url) setBrokerLoginUrl(d.login_url);
      }
    } catch (err) {
      console.warn("Could not load broker login URL:", err);
    }
  }, [userId, loadPortfolioData, getAuthHeaders]);

  const saveKey = async () => {
    setKeySaving(true);
    const cleanSessionTok = sessionTok.trim();

    let currentUserId = userId;
    if (!currentUserId && supabase) {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        currentUserId = session?.user?.id;
      } catch (_) {}
    }

    if (currentUserId) {
      try {
        const headers = await getAuthHeaders();
        const res = await fetch(`/api/user/credentials`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            user_id: currentUserId,
            session_token: cleanSessionTok,
            broker: selectedBroker || "icici"
          })
        });
        if (res.ok) {
          setHasCredentials(true);
        }
      } catch (e) {
        console.warn("Backend save key error:", e);
      }

      if (supabase) {
        try {
          await supabase.from("user_credentials").upsert({
            user_id: currentUserId,
            encrypted_session_token: cleanSessionTok,
            broker_id: selectedBroker || "icici",
            token_date: new Date().toISOString().split("T")[0],
            updated_at: new Date().toISOString()
          }, { onConflict: "user_id" });
          setHasCredentials(true);
        } catch (supaErr) {
          console.warn("Supabase credentials save error:", supaErr);
        }
      }

      setKeySaving(false);
      setKeySaved(true);
      setShowKeyModal(false);
      setSessionTok("");
      loadPortfolioData(currentUserId);
      setTimeout(() => setKeySaved(false), 3000);
    } else {
      setKeySaving(false);
    }
  };

  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedAutoSync = localStorage.getItem("stokvigil_demat_auto_sync");
      if (savedAutoSync !== null) setDematAutoSync(savedAutoSync === "true");
    }
  }, []);

  return {
    holdings, setHoldings,
    totalValue, setTotalValue,
    totalInvested, setTotalInvested,
    totalPnl, setTotalPnl,
    totalPnlPct, setTotalPnlPct,
    isPortfolioVisible, setIsPortfolioVisible,
    hasCredentials, setHasCredentials,
    showKeyModal, setShowKeyModal,
    selectedBroker, setSelectedBroker,
    brokerLoginUrl, setBrokerLoginUrl,
    sessionTok, setSessionTok,
    keySaved, setKeySaved,
    keySaving, setKeySaving,
    dematAutoSync, setDematAutoSync,
    fcmEnabled, setFcmEnabled,
    telegramChatId, setTelegramChatId,
    telegramEnabled, setTelegramEnabled,
    telegramSaved, setTelegramSaved,
    alertSensitivity, setAlertSensitivity,
    executionMode, setExecutionMode,
    loadPortfolioData,
    loadProfileData,
    updatePreference,
    toggleDematAutoSync,
    toggleFcm,
    openKeyModal,
    saveKey
  };
}
