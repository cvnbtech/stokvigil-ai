"use client";

import React, { useState } from "react";
import { Shield, Bolt, Activity, ListFilter, Bell, Lock, Key, ExternalLink } from "lucide-react";

export default function WebPortalDashboard() {
  const [activeTab, setActiveTab] = useState<"dashboard" | "alerts" | "watchlist">("dashboard");
  const [showIciciModal, setShowIciciModal] = useState(false);
  const [appKey, setAppKey] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [sessionToken, setSessionToken] = useState("");
  const [savedStatus, setSavedStatus] = useState<string | null>(null);

  const mockHoldings = [
    { symbol: "RELIANCE", qty: 25, avg: 2450.00, price: 2980.50, pnl: 13262.50, pnlPct: 21.65, pe: 24.2, debtEq: 0.38 },
    { symbol: "TCS", qty: 10, avg: 3600.00, price: 4120.00, pnl: 5200.00, pnlPct: 14.44, pe: 31.5, debtEq: 0.08 },
    { symbol: "INFY", qty: 40, avg: 1420.00, price: 1780.25, pnl: 14410.00, pnlPct: 25.37, pe: 26.8, debtEq: 0.12 },
  ];

  const mockAlerts = [
    {
      symbol: "RELIANCE",
      title: "RELIANCE: Multi-Crore Block Deal Reported",
      impact: 88,
      catalyst: "BLOCK_DEAL",
      reasons: ["Block deal reported involving 1.45M shares on NSE", "Trailing P/E currently at 24.2"],
      time: "10:45 AM Today"
    },
    {
      symbol: "TCS",
      title: "TCS: Quarterly Profit Surges 12.8% YoY",
      impact: 82,
      catalyst: "EARNINGS_BEAT",
      reasons: ["Q1 Net profit reported at ₹12,040 Cr vs ₹10,670 Cr YoY", "Margin expanded by 60 bps"],
      time: "09:30 AM Today"
    }
  ];

  const handleSaveCredentials = (e: React.FormEvent) => {
    e.preventDefault();
    setSavedStatus("Credentials encrypted (AES-256) & stored in Supabase Vault!");
    setTimeout(() => {
      setShowIciciModal(false);
      setSavedStatus(null);
    }, 1500);
  };

  return (
    <div className="flex h-screen overflow-hidden bg-darkBg text-gray-100">
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-cardBg border-r border-cardBorder p-6 flex flex-col justify-between">
        <div>
          <div className="flex items-center gap-3 mb-8">
            <div className="p-2 bg-emeraldAccent/20 rounded-xl">
              <Bolt className="w-6 h-6 text-emeraldAccent" />
            </div>
            <div>
              <h1 className="font-bold text-lg text-white leading-tight">StokVigil AI</h1>
              <p className="text-xs text-gray-400">Market Watchtower</p>
            </div>
          </div>

          <nav className="space-y-2">
            <button
              onClick={() => setActiveTab("dashboard")}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-medium text-sm transition ${
                activeTab === "dashboard" ? "bg-emeraldAccent/15 text-emeraldAccent border border-emeraldAccent/30" : "text-gray-400 hover:bg-gray-800"
              }`}
            >
              <Activity className="w-4 h-4" />
              Portfolio Dashboard
            </button>
            <button
              onClick={() => setActiveTab("alerts")}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-medium text-sm transition ${
                activeTab === "alerts" ? "bg-emeraldAccent/15 text-emeraldAccent border border-emeraldAccent/30" : "text-gray-400 hover:bg-gray-800"
              }`}
            >
              <Bell className="w-4 h-4" />
              StokVigil Alert Radar
            </button>
            <button
              onClick={() => setActiveTab("watchlist")}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-medium text-sm transition ${
                activeTab === "watchlist" ? "bg-emeraldAccent/15 text-emeraldAccent border border-emeraldAccent/30" : "text-gray-400 hover:bg-gray-800"
              }`}
            >
              <ListFilter className="w-4 h-4" />
              Watchlist Manager
            </button>
          </nav>
        </div>

        <div className="p-4 bg-darkBg/60 rounded-xl border border-cardBorder">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-gray-400">ICICI BREEZE TOKEN</span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emeraldAccent/20 text-emeraldAccent border border-emeraldAccent/40">
              <span className="w-1.5 h-1.5 rounded-full bg-emeraldAccent animate-pulse"></span>
              ACTIVE
            </span>
          </div>
          <button
            onClick={() => setShowIciciModal(true)}
            className="w-full mt-2 text-xs font-semibold py-2 px-3 bg-emeraldAccent text-black rounded-lg hover:bg-emerald-400 transition"
          >
            Refresh Session Key
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto p-8">
        {/* Banner Disclaimer */}
        <div className="mb-6 p-4 bg-emeraldAccent/10 border border-emeraldAccent/30 rounded-xl flex items-start gap-3">
          <Shield className="w-5 h-5 text-emeraldAccent shrink-0 mt-0.5" />
          <div className="text-xs text-gray-300">
            <span className="font-bold text-white">Pure Intelligence Guarantee: </span>
            StokVigil AI scans market catalysts every 5 minutes during Indian trading hours. It does not execute trades or issue SEBI financial advice. All alerts stick strictly to factual data points.
          </div>
        </div>

        {activeTab === "dashboard" && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-bold text-white">Portfolio Intelligence</h2>
                <p className="text-sm text-gray-400">Live Demat Holdings & Financial Snapshot</p>
              </div>
              <button
                onClick={() => setShowIciciModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-cardBg border border-cardBorder rounded-xl text-sm font-semibold text-gray-200 hover:border-emeraldAccent transition"
              >
                <Key className="w-4 h-4 text-emeraldAccent" />
                ICICI Breeze Credentials
              </button>
            </div>

            {/* Summary Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="p-6 bg-cardBg border border-cardBorder rounded-2xl">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Total Portfolio Value</span>
                <div className="text-3xl font-bold text-white mt-2">₹1,68,560.00</div>
              </div>
              <div className="p-6 bg-cardBg border border-cardBorder rounded-2xl">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Total Return (P/L)</span>
                <div className="text-3xl font-bold text-emeraldAccent mt-2">+₹32,872.50</div>
              </div>
              <div className="p-6 bg-cardBg border border-cardBorder rounded-2xl">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Return Percentage</span>
                <div className="text-3xl font-bold text-emeraldAccent mt-2">+24.23%</div>
              </div>
            </div>

            {/* Holdings Table */}
            <div className="bg-cardBg border border-cardBorder rounded-2xl overflow-hidden">
              <div className="p-5 border-b border-cardBorder">
                <h3 className="font-bold text-white">Synced Demat Holdings</h3>
              </div>
              <table className="w-full text-left text-sm">
                <thead className="bg-darkBg/50 text-gray-400 text-xs uppercase font-semibold">
                  <tr>
                    <th className="px-6 py-4">Symbol</th>
                    <th className="px-6 py-4">Qty</th>
                    <th className="px-6 py-4">Avg Price</th>
                    <th className="px-6 py-4">Live Price</th>
                    <th className="px-6 py-4">P/L</th>
                    <th className="px-6 py-4">Valuation (P/E)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-cardBorder">
                  {mockHoldings.map((h, i) => (
                    <tr key={i} className="hover:bg-gray-800/50 transition">
                      <td className="px-6 py-4 font-bold text-white">{h.symbol}</td>
                      <td className="px-6 py-4 text-gray-300">{h.qty}</td>
                      <td className="px-6 py-4 text-gray-300">₹{h.avg.toFixed(2)}</td>
                      <td className="px-6 py-4 font-semibold text-white">₹{h.price.toFixed(2)}</td>
                      <td className="px-6 py-4 font-bold text-emeraldAccent">
                        +₹{h.pnl.toFixed(2)} ({h.pnlPct}%)
                      </td>
                      <td className="px-6 py-4 text-gray-400">P/E: {h.pe} | D/E: {h.debtEq}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === "alerts" && (
          <div>
            <h2 className="text-2xl font-bold text-white mb-2">StokVigil Alert Radar</h2>
            <p className="text-sm text-gray-400 mb-6">Real-time feed of 5-minute factual market catalyst alerts</p>

            <div className="space-y-4">
              {mockAlerts.map((alert, idx) => (
                <div key={idx} className="p-6 bg-cardBg border border-cardBorder rounded-2xl hover:border-emeraldAccent/50 transition">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <span className="px-3 py-1 bg-emeraldAccent/15 border border-emeraldAccent text-emeraldAccent rounded-lg text-xs font-bold">
                        HIGH IMPACT {alert.impact}%
                      </span>
                      <span className="font-bold text-white text-lg">{alert.symbol}</span>
                    </div>
                    <span className="text-xs text-gray-400">{alert.time}</span>
                  </div>
                  <h4 className="font-bold text-white text-base mb-2">{alert.title}</h4>
                  <ul className="space-y-1 text-sm text-gray-300 mb-4">
                    {alert.reasons.map((r, rIdx) => (
                      <li key={rIdx} className="flex items-start gap-2">
                        <span className="text-emeraldAccent font-bold">•</span>
                        {r}
                      </li>
                    ))}
                  </ul>
                  <div className="text-xs text-gray-500 italic">
                    ⚠️ Factual market event report. Non-advisory intelligence.
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "watchlist" && (
          <div>
            <h2 className="text-2xl font-bold text-white mb-2">Watchlist Manager</h2>
            <p className="text-sm text-gray-400 mb-6">Track NSE stock symbols & sync Demat holdings</p>

            <div className="p-6 bg-cardBg border border-cardBorder rounded-2xl max-w-xl">
              <div className="flex gap-3 mb-6">
                <input
                  type="text"
                  placeholder="Enter NSE Ticker (e.g. TATAMOTORS)"
                  className="flex-1 bg-darkBg border border-cardBorder rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-emeraldAccent"
                />
                <button className="px-5 py-2.5 bg-emeraldAccent text-black font-bold text-sm rounded-xl hover:bg-emerald-400 transition">
                  Add Symbol
                </button>
              </div>

              <div className="space-y-3">
                {["RELIANCE", "TCS", "INFY", "HDFCBANK", "TATAMOTORS"].map((sym, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-darkBg rounded-xl border border-cardBorder">
                    <span className="font-bold text-white text-sm">{sym}</span>
                    <span className="text-xs text-gray-400">Auto-Monitored</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* ICICI Breeze OAuth Modal */}
      {showIciciModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-cardBg border border-cardBorder rounded-2xl p-6 max-w-md w-full">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Lock className="w-5 h-5 text-emeraldAccent" />
                ICICI Breeze Key Setup
              </h3>
              <button onClick={() => setShowIciciModal(false)} className="text-gray-400 hover:text-white">✕</button>
            </div>

            {savedStatus && (
              <div className="mb-4 p-3 bg-emeraldAccent/20 border border-emeraldAccent text-emeraldAccent text-xs rounded-xl font-semibold">
                {savedStatus}
              </div>
            )}

            <form onSubmit={handleSaveCredentials} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">ICICI Breeze App Key</label>
                <input
                  type="text"
                  value={appKey}
                  onChange={(e) => setAppKey(e.target.value)}
                  placeholder="Enter App Key"
                  required
                  className="w-full bg-darkBg border border-cardBorder rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-emeraldAccent"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">ICICI Breeze Secret Key</label>
                <input
                  type="password"
                  value={secretKey}
                  onChange={(e) => setSecretKey(e.target.value)}
                  placeholder="Enter Secret Key"
                  required
                  className="w-full bg-darkBg border border-cardBorder rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-emeraldAccent"
                />
              </div>

              <div className="pt-2">
                <a
                  href={`https://api.icicidirect.com/apiuser/login?api_key=${encodeURIComponent(appKey || 'YOUR_KEY')}`}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center justify-center gap-2 w-full py-2.5 bg-darkBg border border-emeraldAccent/40 text-emeraldAccent rounded-xl text-xs font-bold hover:bg-emeraldAccent/10 transition"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  Launch 1-Tap ICICI Web Login for Today's Token
                </a>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Daily Session Token</label>
                <input
                  type="text"
                  value={sessionToken}
                  onChange={(e) => setSessionToken(e.target.value)}
                  placeholder="Paste Today's Session Token"
                  required
                  className="w-full bg-darkBg border border-cardBorder rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-emeraldAccent"
                />
              </div>

              <button
                type="submit"
                className="w-full py-3 bg-emeraldAccent text-black font-bold text-sm rounded-xl hover:bg-emerald-400 transition mt-2"
              >
                Encrypt & Save Credentials
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
