"use client";
import React, { useState, useRef, useEffect, useCallback } from "react";
import { C, HoldingItem, SUPABASE_URL, SUPABASE_ANON_KEY, BACKEND_URL, isSupabaseConfigured, supabase } from "../components/ui/DesignTokens";
import { TradingAILogo, DraggableVerticalCanvas, decodeSafeBase64, encodeSafeBase64 } from "../components/ui/UiAtoms";
import AuthScreen from "../components/auth/AuthScreen";
import HomeTab from "../components/tabs/HomeTab";
import AlertsTab from "../components/tabs/AlertsTab";
import WatchlistTab from "../components/tabs/WatchlistTab";
import SettingsTab from "../components/tabs/SettingsTab";
import AuditLedgerView from "../components/AuditLedgerView";
import TradeOrderModal from "../components/modals/TradeOrderModal";
import StockDetailModal from "../components/modals/StockDetailModal";
import IciciKeyModal from "../components/modals/IciciKeyModal";
import PasswordModal from "../components/modals/PasswordModal";
import DeleteAccountModal from "../components/modals/DeleteAccountModal";
import ShareAlphaCardModal, { AlphaCardData } from "../components/ShareAlphaCardModal";
import LightweightCandleChart from "../components/LightweightCandleChart";

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

  const [tab, setTab]     = useState<"home" | "alerts" | "watchlist" | "settings" | "ledger">("home");
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
  const lastLoadedUidRef          = useRef<string | null>(null);
  const [alertFilter, setAlertFilter] = useState<string>("all");
  const [selectedStock, setSelectedStock] = useState<HoldingItem | null>(null);
  const [showTradeModal, setShowTradeModal] = useState(false);
  const [tradeData, setTradeData] = useState<{ symbol: string; price: number; type: "BUY" | "SELL"; target: string; sl: string } | null>(null);
  const [orderQty, setOrderQty] = useState(10);
  const [orderType, setOrderType] = useState<"MARKET" | "LIMIT">("MARKET");
  const [orderSent, setOrderSent] = useState(false);
  const [orderSending, setOrderSending] = useState(false);
  const [limitPrice, setLimitPrice] = useState<string>("");
  const [targetPriceInput, setTargetPriceInput] = useState<string>("");
  const [stopLossPriceInput, setStopLossPriceInput] = useState<string>("");
  const [executionMode, setExecutionMode] = useState<"INSTANT" | "CONFIRM">("INSTANT");
  const [alertSensitivity, setAlertSensitivity] = useState<"HIGH" | "ALL" | "FII">("HIGH");
  const [fcmEnabled, setFcmEnabled] = useState<boolean>(false);
  const [telegramChatId, setTelegramChatId] = useState<string>("");
  const [telegramEnabled, setTelegramEnabled] = useState<boolean>(true);
  const [telegramSaved, setTelegramSaved] = useState<boolean>(false);
  const [dematAutoSync, setDematAutoSync] = useState<boolean>(false);
  const [isPortfolioVisible, setIsPortfolioVisible] = useState<boolean>(false);
  const [sharingAlert, setSharingAlert] = useState<AlphaCardData | null>(null);
  const [chartingSymbol, setChartingSymbol] = useState<string | null>(null);
  const [isChartMaximized, setIsChartMaximized] = useState<boolean>(false);
  const [fiiDiiFlows, setFiiDiiFlows] = useState<any | null>(null);
  const [expandedRadarId, setExpandedRadarId] = useState<string | null>(null);

  useEffect(() => {
    const fetchFiiDii = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/market/fii-dii-flows`);
        if (res.ok) {
          const data = await res.json();
          setFiiDiiFlows(data);
        }
      } catch (e) {
        console.debug("FII/DII fetch error", e);
      }
    };
    fetchFiiDii();
  }, []);

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
            dayHigh: h.day_high != null ? h.day_high : null,
            dayLow: h.day_low != null ? h.day_low : null,
            high52: h.high_52 != null ? h.high_52 : null,
            sector: "Equity",
            signal: h.signal || "MONITORING",
            signalType: h.signal_type || "monitoring",
            target: h.target ? (String(h.target).startsWith("₹") ? h.target : `₹${h.target}`) : "--",
            sl: h.stop_loss ? (String(h.stop_loss).startsWith("₹") ? h.stop_loss : `₹${h.stop_loss}`) : "--",
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
            const flowData = rawSnap.flow_data || {};
            const technicals = rawSnap.technicals || {};
            const macroData = rawSnap.macro_data || {};
            const dematPos = rawSnap.demat_position || null;

            let livePrice = technicals.current_price || rawSnap.current_price || rawSnap.price || (rawSnap.financials && rawSnap.financials.price) || 0;
            if (!livePrice && dematPos && dematPos.average_buy_price) {
              livePrice = dematPos.average_buy_price;
            }

            let dematSanitized = null;
            if (dematPos && dematPos.is_in_portfolio) {
              const avgP = dematPos.average_buy_price || 0;
              let pnlPct = dematPos.unrealized_pnl_pct != null ? Number(dematPos.unrealized_pnl_pct) : 0;
              if (pnlPct <= -99.0) {
                if (livePrice > 0 && avgP > 0) {
                  pnlPct = Number((((livePrice - avgP) / avgP) * 100).toFixed(1));
                } else {
                  pnlPct = 0.0;
                }
              }
              dematSanitized = {
                quantity: dematPos.quantity || 0,
                average_buy_price: avgP,
                unrealized_pnl_pct: pnlPct
              };
            }

            const bias = rawSnap.action_bias || "HOLD_NEUTRAL";
            let tPrice = rawSnap.tactical_levels?.target_1;
            let sLoss = rawSnap.tactical_levels?.protective_stop_loss;

            const isDummy100 = (tPrice === "₹100.00" || tPrice === "100.0" || tPrice === "100") &&
                               (sLoss === "₹100.00" || sLoss === "100.0" || sLoss === "100");

            if (isDummy100 || !tPrice) {
              tPrice = "-";
            }
            if (isDummy100 || !sLoss) {
              sLoss = "-";
            }

            const deliveryVal = flowData.delivery_pct != null ? `${flowData.delivery_pct}%` : (rawSnap.delivery_pct != null ? `${rawSnap.delivery_pct}%` : "-");
            const rsiVal = technicals.rsi_15m != null ? `${technicals.rsi_15m}` : (rawSnap.rsi_15m != null ? `${rawSnap.rsi_15m}` : "-");
            const vwapVal = technicals.vwap && technicals.vwap > 0 ? `₹${technicals.vwap}` : (rawSnap.vwap && rawSnap.vwap > 0 ? `₹${rawSnap.vwap}` : "-");
            const oiVal = (flowData.fo_oi_status || flowData.flow_bias || rawSnap.fo_oi_status || rawSnap.flow_bias)
              ? String(flowData.fo_oi_status || flowData.flow_bias || rawSnap.fo_oi_status || rawSnap.flow_bias).replace(/_/g, ' ')
              : "-";
            const vsaNote = flowData.vsa_note || flowData.vsa_regime || rawSnap.vsa_regime || "";
            const vixVal = macroData.india_vix || rawSnap.india_vix || null;

            let sigType = "buy";
            if (bias.includes("SELL")) sigType = "sell";
            else if (bias.includes("TRAILING")) sigType = "med";
            else if ((a.impact_score || 0) >= 80) sigType = "strong_buy";

            const hasRealFactors = rawSnap.factor_breakdown &&
              typeof rawSnap.factor_breakdown === 'object' &&
              rawSnap.factor_breakdown.technicals != null;

            const resolvedFactors = hasRealFactors ? {
              technicals: Number(rawSnap.factor_breakdown.technicals),
              flow: Number(rawSnap.factor_breakdown.flow),
              forensics: Number(rawSnap.factor_breakdown.forensics),
              catalysts: Number(rawSnap.factor_breakdown.catalysts)
            } : null;

            return {
              id: a.id,
              symbol: a.symbol,
              impact: a.impact_score != null ? a.impact_score : (a.confluence_score != null ? a.confluence_score : "-"),
              impactColor: (a.impact_score || 0) >= 80 ? "emerald" : "amber",
              catalyst: a.catalyst_type || "CATALYST",
              category: a.catalyst_type?.toLowerCase() || "high",
              signal: bias.replace(/_/g, " "),
              signalType: sigType,
              targetPrice: tPrice,
              stopLoss: sLoss,
              title: a.alert_title,
              reasons: a.factual_reasons || [],
              metrics: {
                delivery: deliveryVal,
                rsi: rsiVal,
                vwap: vwapVal,
                flow: oiVal
              },
              vsaNote: vsaNote ? String(vsaNote).replace(/_/g, ' ') : "",
              vix: vixVal,
              dematPosition: dematSanitized,
              factors: resolvedFactors,
              entryRange: rawSnap.tactical_levels?.entry_range || "-",
              riskReward: rawSnap.tactical_levels?.risk_reward_ratio || "-",
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
            const signal = q.signal || "MONITORING";
            const signalType = q.signal_type || "monitoring";
            const target = q.target ? (String(q.target).startsWith("₹") ? q.target : `₹${q.target}`) : "--";
            const sl = q.stop_loss ? (String(q.stop_loss).startsWith("₹") ? q.stop_loss : `₹${q.stop_loss}`) : "--";

            return {
              id: w.id,
              symbol: sym,
              name,
              auto: w.is_auto_synced || false,
              price,
              chg: price > 0 ? (isPos ? `+${chgPct.toFixed(2)}%` : `${chgPct.toFixed(2)}%`) : "--",
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
          if (data.telegram_chat_id) setTelegramChatId(data.telegram_chat_id);
          if (data.telegram_enabled !== undefined) setTelegramEnabled(Boolean(data.telegram_enabled));
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

    const handleSession = (session: any) => {
      if (session?.user) {
        const u = {
          id: session.user.id,
          name: session.user.user_metadata?.full_name || session.user.email?.split("@")[0] || "Investor",
          email: session.user.email || ""
        };
        setUser(u);
        setScreen("app");

        if (lastLoadedUidRef.current !== session.user.id) {
          lastLoadedUidRef.current = session.user.id;
          loadPortfolioData(session.user.id);
          loadAlertsData(session.user.id);
          loadWatchlistData(session.user.id);
          loadProfileData(session.user.id);
        }
      } else {
        lastLoadedUidRef.current = null;
        setUser(null);
        setScreen("auth");
      }
    };

    supabase.auth.getSession().then(({ data: { session } }) => {
      handleSession(session);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      handleSession(session);
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

    let currentUserId = user?.id;
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
          chg: livePrice > 0 ? "+0.00%" : "--",
          isPositive: true,
          signal: "MONITORING",
          signalType: "monitoring",
          target: "--",
          sl: "--"
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
        const idempotencyKey = `${user.id}-${tradeData.symbol}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
        await fetch(`${BACKEND_URL}/api/v1/orders/place`, {
          method: "POST",
          headers: {
            ...headers,
            "X-Idempotency-Key": idempotencyKey
          },
          body: JSON.stringify({
            user_id: user.id,
            symbol: tradeData.symbol,
            action: tradeData.type,
            order_type: orderType,
            quantity: orderQty,
            price: orderType === "LIMIT" ? parseFloat(limitPrice) || 0.0 : 0.0,
            idempotency_key: idempotencyKey
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

  const handlePlaceOrderFromStock = (stock: HoldingItem) => {
    const isSell = stock.signalType === "sell";
    const cleanTarget = (stock.target && stock.target !== "--") ? stock.target.replace(/[^\d.]/g, "") : "";
    const cleanSl = (stock.sl && stock.sl !== "--") ? stock.sl.replace(/[^\d.]/g, "") : "";
    setTradeData({
      symbol: stock.symbol,
      price: stock.price,
      type: isSell ? "SELL" : "BUY",
      target: stock.target && stock.target !== "--" ? stock.target : "--",
      sl: stock.sl && stock.sl !== "--" ? stock.sl : "--",
    });
    setTargetPriceInput(cleanTarget);
    setStopLossPriceInput(cleanSl);
    setOrderQty(stock.qty || 10);
    setLimitPrice(stock.price > 0 ? stock.price.toFixed(2) : "0");
    setShowTradeModal(true);
    setSelectedStock(null);
  };

  const handleOpenTradeModalFromWatchlist = (stock: { symbol: string; price: number; type: "BUY" | "SELL"; target: string; sl: string; qty?: number }) => {
    const cleanTarget = (stock.target && stock.target !== "--") ? stock.target.replace(/[^\d.]/g, "") : "";
    const cleanSl = (stock.sl && stock.sl !== "--") ? stock.sl.replace(/[^\d.]/g, "") : "";
    setTradeData({
      symbol: stock.symbol,
      price: stock.price,
      type: stock.type,
      target: stock.target && stock.target !== "--" ? stock.target : "--",
      sl: stock.sl && stock.sl !== "--" ? stock.sl : "--",
    });
    setTargetPriceInput(cleanTarget);
    setStopLossPriceInput(cleanSl);
    setOrderQty(stock.qty || 10);
    setLimitPrice(stock.price > 0 ? stock.price.toFixed(2) : "0");
    setShowTradeModal(true);
  };

  // ─────────────────────────────────────────────
  // AUTHENTICATION SCREEN
  // ─────────────────────────────────────────────
  if (screen === "auth") {
    return (
      <AuthScreen
        authTab={authTab}
        setAuthTab={setAuthTab}
        doGoogleOAuth={doGoogleOAuth}
        name={name}
        setName={setName}
        email={email}
        setEmail={setEmail}
        password={password}
        setPassword={setPassword}
        showAuthPassword={showAuthPassword}
        setShowAuthPassword={setShowAuthPassword}
        setShowForgotModal={setShowForgotModal}
        tncAccepted={tncAccepted}
        setTncAccepted={setTncAccepted}
        showTnc={showTnc}
        setShowTnc={setShowTnc}
        authError={authError}
        authSuccess={authSuccess}
        doAuth={doAuth}
        loading={loading}
      />
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
            <button
              onClick={() => setTab(tab === "ledger" ? "home" : "ledger")}
              style={{
                background: tab === "ledger" ? "rgba(16,185,129,0.25)" : "rgba(16,185,129,0.12)",
                border: `1px solid ${tab === "ledger" ? C.emerald : "rgba(16,185,129,0.35)"}`,
                borderRadius: 10, padding: "6px 10px", color: C.emerald, fontSize: 11, fontWeight: 800,
                cursor: "pointer", display: "flex", alignItems: "center", gap: 5,
              }}
            >
              🛡️ Audit Ledger
            </button>
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
            <HomeTab
              user={user}
              fiiDiiFlows={fiiDiiFlows}
              isPortfolioVisible={isPortfolioVisible}
              setIsPortfolioVisible={setIsPortfolioVisible}
              totalValue={totalValue}
              totalInvested={totalInvested}
              totalPnl={totalPnl}
              totalPnlPct={totalPnlPct}
              hasCredentials={hasCredentials}
              holdings={holdings}
              openKeyModal={openKeyModal}
              setSelectedStock={setSelectedStock}
            />
          )}

          {/* ALERTS TAB WITH FILTER PILLS */}
          {tab === "alerts" && (
            <AlertsTab
              alerts={alerts}
              alertFilter={alertFilter}
              setAlertFilter={setAlertFilter}
              setTab={setTab}
              expandedRadarId={expandedRadarId}
              setExpandedRadarId={setExpandedRadarId}
              setChartingSymbol={setChartingSymbol}
              setSharingAlert={setSharingAlert}
            />
          )}

          {/* WATCHLIST TAB */}
          {tab === "watchlist" && (
            <WatchlistTab
              watchlist={watchlist}
              holdings={holdings}
              dematAutoSync={dematAutoSync}
              toggleDematAutoSync={toggleDematAutoSync}
              ticker={ticker}
              handleStockChange={handleStockChange}
              tickerSuggestions={tickerSuggestions}
              setTickerSuggestions={setTickerSuggestions}
              addStock={addStock}
              removeTicker={removeTicker}
              onOpenTradeModal={handleOpenTradeModalFromWatchlist}
            />
          )}

          {/* SETTINGS TAB */}
          {tab === "settings" && (
            <SettingsTab
              user={user}
              openKeyModal={openKeyModal}
              executionMode={executionMode}
              setExecutionMode={setExecutionMode}
              updatePreference={updatePreference}
              telegramChatId={telegramChatId}
              setTelegramChatId={setTelegramChatId}
              telegramSaved={telegramSaved}
              setTelegramSaved={setTelegramSaved}
              setTelegramEnabled={setTelegramEnabled}
              alertSensitivity={alertSensitivity}
              setAlertSensitivity={setAlertSensitivity}
              fcmEnabled={fcmEnabled}
              toggleFcm={toggleFcm}
              setForgotEmail={setForgotEmail}
              setShowForgotModal={setShowForgotModal}
              setDeleteConfirmText={setDeleteConfirmText}
              setShowDeleteModal={setShowDeleteModal}
              doSignOut={doSignOut}
            />
          )}

          {/* AUDIT LEDGER TAB */}
          {tab === "ledger" && (
            <div className="anim-fadeup" style={{ paddingBottom: 24 }}>
              <AuditLedgerView onBack={() => setTab("home")} />
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
          <StockDetailModal
            selectedStock={selectedStock}
            onClose={() => setSelectedStock(null)}
            onPlaceOrder={handlePlaceOrderFromStock}
          />
        )}

        {/* ICICI Key Setup Modal */}
        {showKeyModal && (
          <IciciKeyModal
            onClose={() => setShowKeyModal(false)}
            appKey={appKey}
            setAppKey={setAppKey}
            secretKey={secretKey}
            setSecretKey={setSecretKey}
            sessionTok={sessionTok}
            setSessionTok={setSessionTok}
            showAppKey={showAppKey}
            setShowAppKey={setShowAppKey}
            showSecretKey={showSecretKey}
            setShowSecretKey={setShowSecretKey}
            keySaved={keySaved}
            keySaving={keySaving}
            saveKey={saveKey}
          />
        )}

        {/* INTERACTIVE TRADE ORDER PLACEMENT MODAL */}
        {showTradeModal && tradeData && (
          <TradeOrderModal
            tradeData={tradeData}
            orderQty={orderQty}
            setOrderQty={setOrderQty}
            orderType={orderType}
            setOrderType={setOrderType}
            limitPrice={limitPrice}
            setLimitPrice={setLimitPrice}
            targetPriceInput={targetPriceInput}
            setTargetPriceInput={setTargetPriceInput}
            stopLossPriceInput={stopLossPriceInput}
            setStopLossPriceInput={setStopLossPriceInput}
            orderSending={orderSending}
            orderSent={orderSent}
            onClose={() => { setShowTradeModal(false); setOrderSent(false); }}
            onExecute={executeTrade}
          />
        )}

        {/* GLOBAL FORGOT / CHANGE PASSWORD MODAL */}
        {showForgotModal && (
          <PasswordModal
            user={user}
            onClose={() => {
              setShowForgotModal(false);
              setForgotSent(false);
              setNewPasswordDone(false);
              setNewPassword("");
              setNewPasswordError(null);
            }}
            forgotEmail={forgotEmail}
            setForgotEmail={setForgotEmail}
            forgotSent={forgotSent}
            setForgotSent={setForgotSent}
            forgotLoading={forgotLoading}
            setForgotLoading={setForgotLoading}
            newPassword={newPassword}
            setNewPassword={setNewPassword}
            newPasswordDone={newPasswordDone}
            setNewPasswordDone={setNewPasswordDone}
            newPasswordLoading={newPasswordLoading}
            setNewPasswordLoading={setNewPasswordLoading}
            newPasswordError={newPasswordError}
            setNewPasswordError={setNewPasswordError}
            showNewPassword={showNewPassword}
            setShowNewPassword={setShowNewPassword}
          />
        )}

        {/* GLOBAL DELETE ACCOUNT MODAL */}
        {showDeleteModal && (
          <DeleteAccountModal
            onClose={() => setShowDeleteModal(false)}
            deleteConfirmText={deleteConfirmText}
            setDeleteConfirmText={setDeleteConfirmText}
            doDeleteAccount={doDeleteAccount}
            isDeletingAccount={isDeletingAccount}
          />
        )}

        {/* PHASE 1: 1-TAP SHAREABLE ALPHA CARD MODAL */}
        {sharingAlert && (
          <ShareAlphaCardModal
            alert={sharingAlert}
            onClose={() => setSharingAlert(null)}
          />
        )}

        {/* PHASE 2: IN-APP LIGHTWEIGHT CANDLESTICK CHART MODAL */}
        {chartingSymbol && (
          <div style={{
            position: "fixed",
            inset: 0,
            background: "rgba(3, 7, 18, 0.88)",
            backdropFilter: "blur(14px)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: isChartMaximized ? 10 : 16,
          }}>
            <div style={{
              maxWidth: isChartMaximized ? "96vw" : 780,
              width: "100%",
              transition: "all 0.25s ease",
            }}>
              <LightweightCandleChart
                symbol={chartingSymbol}
                backendUrl={BACKEND_URL}
                isMaximized={isChartMaximized}
                onToggleMaximize={() => setIsChartMaximized(!isChartMaximized)}
                onClose={() => {
                  setChartingSymbol(null);
                  setIsChartMaximized(false);
                }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
