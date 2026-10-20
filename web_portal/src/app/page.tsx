"use client";
import React, { useState, useRef, useEffect } from "react";
import { C, HoldingItem, BACKEND_URL } from "../components/ui/DesignTokens";
import { TradingAILogo, DraggableVerticalCanvas } from "../components/ui/UiAtoms";
import AuthScreen from "../components/auth/AuthScreen";
import HomeTab from "../components/tabs/HomeTab";
import AlertsTab from "../components/tabs/AlertsTab";
import WatchlistTab from "../components/tabs/WatchlistTab";
import SettingsTab from "../components/tabs/SettingsTab";
import dynamic from "next/dynamic";

import { useAuthSession } from "../hooks/useAuthSession";
import { usePortfolioMetrics } from "../hooks/usePortfolioMetrics";
import { useWatchlistManager } from "../hooks/useWatchlistManager";
import { useAlertsManager } from "../hooks/useAlertsManager";

const LightweightCandleChart = dynamic(
  () => import("../components/LightweightCandleChart"),
  { ssr: false, loading: () => <div className="h-64 flex items-center justify-center text-slate-500 font-mono text-xs">Loading Chart Engine...</div> }
);
const BacktestView = dynamic(() => import("../components/BacktestView"), { ssr: false });
const AuditLedgerView = dynamic(() => import("../components/AuditLedgerView"), { ssr: false });
const TradeOrderModal = dynamic(() => import("../components/modals/TradeOrderModal"), { ssr: false });
const StockDetailModal = dynamic(() => import("../components/modals/StockDetailModal"), { ssr: false });
const IciciKeyModal = dynamic(() => import("../components/modals/IciciKeyModal"), { ssr: false });
const PasswordModal = dynamic(() => import("../components/modals/PasswordModal"), { ssr: false });
const DeleteAccountModal = dynamic(() => import("../components/modals/DeleteAccountModal"), { ssr: false });
const ShareAlphaCardModal = dynamic(() => import("../components/ShareAlphaCardModal"), { ssr: false });

export default function App() {
  // Navigation & View State
  const [tab, setTab] = useState<"home" | "alerts" | "watchlist" | "settings" | "ledger" | "backtest">("home");
  const [backtestSymbol, setBacktestSymbol] = useState<string>("");
  const [fiiDiiFlows, setFiiDiiFlows] = useState<any | null>(null);

  // Charting & Modal Interaction State
  const [selectedStock, setSelectedStock] = useState<HoldingItem | null>(null);
  const [chartingSymbol, setChartingSymbol] = useState<string | null>(null);
  const [isChartMaximized, setIsChartMaximized] = useState<boolean>(false);

  // Trade Execution Modal State
  const [showTradeModal, setShowTradeModal] = useState(false);
  const [tradeData, setTradeData] = useState<{ symbol: string; price: number; type: "BUY" | "SELL"; target: string; sl: string } | null>(null);
  const [orderQty, setOrderQty] = useState(10);
  const [orderType, setOrderType] = useState<"MARKET" | "LIMIT">("MARKET");
  const [orderSent, setOrderSent] = useState(false);
  const [orderSending, setOrderSending] = useState(false);
  const [limitPrice, setLimitPrice] = useState<string>("");
  const [targetPriceInput, setTargetPriceInput] = useState<string>("");
  const [stopLossPriceInput, setStopLossPriceInput] = useState<string>("");

  // Upstream callbacks via refs to prevent circular hook closures
  const loadUserDataRef = useRef<(uid: string) => void>(null!);
  const handleSignedOutRef = useRef<() => void>(null!);

  // 1. Auth & User Profile Session
  const auth = useAuthSession({
    onSessionLoaded: (uid) => {
      loadUserDataRef.current?.(uid);
    },
    onSignedOut: () => {
      handleSignedOutRef.current?.();
    }
  });

  // 2. Watchlist Manager
  const watchlist = useWatchlistManager({
    userId: auth.user?.id
  });

  // 3. Alerts Manager
  const alerts = useAlertsManager({
    userId: auth.user?.id
  });

  // 4. Portfolio & Demat Broker Metrics
  const portfolio = usePortfolioMetrics({
    getAuthHeaders: auth.getAuthHeaders,
    userId: auth.user?.id,
    onDematSynced: (uid) => {
      watchlist.loadWatchlistData(uid);
    }
  });

  // Wire callbacks
  loadUserDataRef.current = (uid: string) => {
    portfolio.loadPortfolioData(uid);
    alerts.loadAlertsData(uid);
    watchlist.loadWatchlistData(uid);
    portfolio.loadProfileData(uid);
  };

  handleSignedOutRef.current = () => {
    portfolio.setHoldings([]);
    portfolio.setTotalValue(0);
    portfolio.setTotalInvested(0);
    portfolio.setTotalPnl(0);
    portfolio.setTotalPnlPct(0);
    alerts.setAlerts([]);
    watchlist.setWatchlist([]);
  };

  // Initial Market FII/DII Data
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

  // Trade Execution Handler
  const executeTrade = async () => {
    if (!tradeData) return;
    setOrderSending(true);
    if (auth.user?.id) {
      try {
        const headers = await auth.getAuthHeaders();
        const idempotencyKey = `${auth.user.id}-${tradeData.symbol}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
        const res = await fetch(`${BACKEND_URL}/api/v1/orders/place`, {
          method: "POST",
          headers: {
            ...headers,
            "X-Idempotency-Key": idempotencyKey
          },
          body: JSON.stringify({
            user_id: auth.user.id,
            symbol: tradeData.symbol,
            action: tradeData.type,
            order_type: orderType,
            quantity: orderQty,
            price: orderType === "LIMIT" ? parseFloat(limitPrice) || 0.0 : 0.0,
            idempotency_key: idempotencyKey
          })
        });
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          const errMsg = errData.detail || errData.message || `Order rejected (HTTP ${res.status})`;
          alert(`⚠️ Order Rejection: ${errMsg}`);
          setOrderSending(false);
          return;
        }
      } catch (e: any) {
        console.warn("Trade order execution:", e);
        alert(`❌ Network / Server Error: ${e.message || "Failed to place order."}`);
        setOrderSending(false);
        return;
      }
    }
    setOrderSending(false);
    setOrderSent(true);
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
  if (auth.screen === "auth") {
    return (
      <AuthScreen
        authTab={auth.authTab}
        setAuthTab={auth.setAuthTab}
        doGoogleOAuth={auth.doGoogleOAuth}
        name={auth.name}
        setName={auth.setName}
        email={auth.email}
        setEmail={auth.setEmail}
        password={auth.password}
        setPassword={auth.setPassword}
        showAuthPassword={auth.showAuthPassword}
        setShowAuthPassword={auth.setShowAuthPassword}
        setShowForgotModal={auth.setShowForgotModal}
        tncAccepted={auth.tncAccepted}
        setTncAccepted={auth.setTncAccepted}
        showTnc={auth.showTnc}
        setShowTnc={auth.setShowTnc}
        authError={auth.authError}
        authSuccess={auth.authSuccess}
        doAuth={auth.doAuth}
        loading={auth.loading}
      />
    );
  }

  // ─────────────────────────────────────────────
  // MAIN AUTHENTICATED APP VIEW
  // ─────────────────────────────────────────────
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

  const headerH = 60;
  const navH = 64;

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
            <button onClick={portfolio.openKeyModal} style={{
              background: "rgba(6,182,212,0.12)", border: `1px solid ${C.borderCyan}`,
              borderRadius: 10, padding: "6px 10px", color: C.cyan, fontSize: 11, fontWeight: 800, cursor: "pointer",
              display: "flex", alignItems: "center", gap: 5,
            }}>
              🔑 Key Active
            </button>
            <button
              onClick={() => { auth.setScreen("auth"); auth.setUser(null); auth.setTncAccepted(false); }}
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
              user={auth.user}
              fiiDiiFlows={fiiDiiFlows}
              isPortfolioVisible={portfolio.isPortfolioVisible}
              setIsPortfolioVisible={portfolio.setIsPortfolioVisible}
              totalValue={portfolio.totalValue}
              totalInvested={portfolio.totalInvested}
              totalPnl={portfolio.totalPnl}
              totalPnlPct={portfolio.totalPnlPct}
              hasCredentials={portfolio.hasCredentials}
              holdings={portfolio.holdings}
              openKeyModal={portfolio.openKeyModal}
              setSelectedStock={setSelectedStock}
            />
          )}

          {/* ALERTS TAB WITH FILTER PILLS */}
          {tab === "alerts" && (
            <AlertsTab
              alerts={alerts.alerts}
              alertFilter={alerts.alertFilter}
              setAlertFilter={alerts.setAlertFilter}
              setTab={setTab}
              expandedRadarId={alerts.expandedRadarId}
              setExpandedRadarId={alerts.setExpandedRadarId}
              setChartingSymbol={setChartingSymbol}
              setSharingAlert={alerts.setSharingAlert}
            />
          )}

          {/* WATCHLIST TAB */}
          {tab === "watchlist" && (
            <WatchlistTab
              watchlist={watchlist.watchlist}
              holdings={portfolio.holdings}
              dematAutoSync={portfolio.dematAutoSync}
              toggleDematAutoSync={portfolio.toggleDematAutoSync}
              ticker={watchlist.ticker}
              handleStockChange={watchlist.handleStockChange}
              tickerSuggestions={watchlist.tickerSuggestions}
              setTickerSuggestions={watchlist.setTickerSuggestions}
              addStock={watchlist.addStock}
              removeTicker={watchlist.removeTicker}
              onOpenTradeModal={handleOpenTradeModalFromWatchlist}
              flashMap={watchlist.flashMap}
            />
          )}

          {/* SETTINGS TAB */}
          {tab === "settings" && (
            <SettingsTab
              user={auth.user}
              openKeyModal={portfolio.openKeyModal}
              executionMode={portfolio.executionMode}
              setExecutionMode={portfolio.setExecutionMode}
              updatePreference={portfolio.updatePreference}
              telegramChatId={portfolio.telegramChatId}
              setTelegramChatId={portfolio.setTelegramChatId}
              telegramSaved={portfolio.telegramSaved}
              setTelegramSaved={portfolio.setTelegramSaved}
              setTelegramEnabled={portfolio.setTelegramEnabled}
              alertSensitivity={portfolio.alertSensitivity}
              setAlertSensitivity={portfolio.setAlertSensitivity}
              fcmEnabled={portfolio.fcmEnabled}
              toggleFcm={portfolio.toggleFcm}
              setForgotEmail={auth.setForgotEmail}
              setShowForgotModal={auth.setShowForgotModal}
              setDeleteConfirmText={auth.setDeleteConfirmText}
              setShowDeleteModal={auth.setShowDeleteModal}
              doSignOut={auth.doSignOut}
              onOpenLedger={() => setTab("ledger")}
              onOpenBacktest={() => setTab("backtest")}
            />
          )}

          {/* AUDIT LEDGER TAB */}
          {tab === "ledger" && (
            <div className="anim-fadeup" style={{ paddingBottom: 24 }}>
              <AuditLedgerView onBack={() => setTab("settings")} />
            </div>
          )}

          {/* STRATEGY BACKTESTER TAB */}
          {tab === "backtest" && (
            <div className="anim-fadeup" style={{ paddingBottom: 24 }}>
              <BacktestView initialSymbol={backtestSymbol} onBack={() => setTab("settings")} authToken={auth.authToken} />
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
            onOpenBacktest={(sym) => {
              setBacktestSymbol(sym);
              setTab("backtest");
            }}
          />
        )}

        {/* ICICI Key Setup Modal */}
        {portfolio.showKeyModal && (
          <IciciKeyModal
            onClose={() => portfolio.setShowKeyModal(false)}
            sessionTok={portfolio.sessionTok}
            setSessionTok={portfolio.setSessionTok}
            keySaved={portfolio.keySaved}
            keySaving={portfolio.keySaving}
            saveKey={portfolio.saveKey}
            loginUrl={portfolio.brokerLoginUrl}
            selectedBroker={portfolio.selectedBroker}
            setSelectedBroker={portfolio.setSelectedBroker}
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
        {auth.showForgotModal && (
          <PasswordModal
            user={auth.user}
            onClose={() => {
              auth.setShowForgotModal(false);
              auth.setForgotSent(false);
              auth.setNewPasswordDone(false);
              auth.setNewPassword("");
              auth.setNewPasswordError(null);
            }}
            forgotEmail={auth.forgotEmail}
            setForgotEmail={auth.setForgotEmail}
            forgotSent={auth.forgotSent}
            setForgotSent={auth.setForgotSent}
            forgotLoading={auth.forgotLoading}
            setForgotLoading={auth.setForgotLoading}
            newPassword={auth.newPassword}
            setNewPassword={auth.setNewPassword}
            newPasswordDone={auth.newPasswordDone}
            setNewPasswordDone={auth.setNewPasswordDone}
            newPasswordLoading={auth.newPasswordLoading}
            setNewPasswordLoading={auth.setNewPasswordLoading}
            newPasswordError={auth.newPasswordError}
            setNewPasswordError={auth.setNewPasswordError}
            showNewPassword={auth.showNewPassword}
            setShowNewPassword={auth.setShowNewPassword}
          />
        )}

        {/* GLOBAL DELETE ACCOUNT MODAL */}
        {auth.showDeleteModal && (
          <DeleteAccountModal
            onClose={() => auth.setShowDeleteModal(false)}
            deleteConfirmText={auth.deleteConfirmText}
            setDeleteConfirmText={auth.setDeleteConfirmText}
            doDeleteAccount={auth.doDeleteAccount}
            isDeletingAccount={auth.isDeletingAccount}
          />
        )}

        {/* PHASE 1: 1-TAP SHAREABLE ALPHA CARD MODAL */}
        {alerts.sharingAlert && (
          <ShareAlphaCardModal
            alert={alerts.sharingAlert}
            onClose={() => alerts.setSharingAlert(null)}
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
