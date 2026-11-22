<div align="center">

# ⚡ StokVigil AI
### Institutional Quantitative Equity Surveillance & Automated Demat Risk Engine

**Stop gambling on speculative tips. Trade alongside institutional order flow with mathematical certainty.**

[![Architecture](https://img.shields.io/badge/Architecture-4--Pillar%20Confluence-00E5FF?style=for-the-badge&logo=diagramsdotnet&logoColor=white)](#-full-stack-system-architecture)
[![Streaming](https://img.shields.io/badge/Real--Time-SSE%20%3C50ms-FF6D00?style=for-the-badge&logo=fastapi&logoColor=white)](#7--real-time-native-streaming-architecture-50ms-latency)
[![Backend](https://img.shields.io/badge/FastAPI-Python%203.11+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](#-tech-stack)
[![Web](https://img.shields.io/badge/Next.js%2016-App%20Router-black?style=for-the-badge&logo=next.js&logoColor=white)](#-tech-stack)
[![Mobile](https://img.shields.io/badge/Flutter-Dart%203.3+-02569B?style=for-the-badge&logo=flutter&logoColor=white)](#-tech-stack)
[![Database](https://img.shields.io/badge/Supabase-PostgreSQL%2015+-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](#-tech-stack)
[![Compliance](https://img.shields.io/badge/SEBI-Non--Advisory%20Mandate-2E7D32?style=for-the-badge&logo=checkmarx&logoColor=white)](#-regulatory-disclaimer)

[Explore Features](#-key-features) • [Real-Time Streaming](#7--real-time-native-streaming-architecture-50ms-latency) • [Full-Stack Architecture](#-full-stack-system-architecture) • [Live Flow](#-sequence-diagram) • [Quickstart Guide](#-installation-steps) • [Audit Ledger](#-100-transparent-audited-accuracy-ledger)

</div>

---

## 🎯 Purpose & Goal: Why StokVigil AI?

> According to SEBI's official study on Indian capital markets, **over 93% of active retail intraday traders and derivative market participants suffer consistent net losses**.

The retail market is plagued by three fatal pitfalls:
1. **Unverified Stock "Tips" & Social Hype:** Retail capital gets lured into chasing speculative rumors and unverified Telegram signals right when institutional operators are offloading inventory.
2. **The "Averaging Down" Trap:** When a trade goes into loss, emotional retail investors buy more shares of falling stocks, magnifying drawdowns until their Demat accounts are devastated.
3. **Execution Traps & Liquidity Fakeouts:** Midday liquidity lulls (11:30–13:30 IST) are notorious for false breakouts. Furthermore, using Stop-Loss Market (SL-M) orders exposes traders to violent freak-trade slippage.

### 🛡️ The StokVigil Edge: Institutional Mathematics Over Emotions

**StokVigil AI (`com.app.stokvigil`)** levels the playing field. It transforms retail Demat accounts into institutional trading desks using pure mathematical determinism, real-time delivery order flow, and automated risk enforcement:

| Retail Trader Reality | The StokVigil Institutional Superpower |
| :--- | :--- |
| **Guesses support and resistance** using subjective trendlines. | **Calculates static horizontal Camarilla Pivots ($H_4/H_3/L_3/L_4$)** and Volume-Weighted Average Price (VWAP) statistical bands. |
| **Averages down** on losing positions, compounding capital erosion. | **Enforces the 5-State Portfolio Lifecycle:** Strictly cuts risk at $L_4$ breakdown and allows pyramiding only on winning positions (`ACCUMULATE_WATCH`). |
| **Gets trapped in false midday breakouts** during institutional lunch lulls. | **Activates the 11:30–13:30 IST Lunch-Hour Trap Blocker:** Demands an extraordinary 3.0x RVOL hurdle to confirm valid momentum. |
| **Blind to big-money operations** and institutional distribution. | **Scrapes official NSE security-wise delivery bhavcopies & option chains:** Analyzes Wyckoff Close Location Quotient (CLQ), PCR, and Delta-OI velocity. |
| **Vulnerable to broker API leaks & developer key hassles.** | **Pure Master App Publisher Model:** Zero developer account setup for users. Authenticate securely via daily broker OAuth/OTP. |

---

## 🌟 Key Features

### 1. 📐 Mathematical Surveillance Engine
* **Full Camarilla Equation Expansion ($H1 \dots H5$ & $L1 \dots L5$):** Mathematical volatility boundaries derived from prior completed True Range. Features $H5$ Expansion (`#A855F7`), $H4$ Breakout (`#EC4899`), $H3$ Mean Reversion, $L3$ Floor, $L4$ Hard Stop, and $L5$ Capitulation (`#DC2626`).
* **Multi-Timeframe (MTF) Pivot Clustering:** Mathematically checks alignment between Daily and Weekly pivots within $\pm 0.35\%$ to unlock high-conviction institutional breakouts.
* **5-Type Camarilla Opening Engine:** Classifies opening dynamics into `OPEN_INSIDE_VALUE`, `OPEN_ABOVE_H4_BREAKOUT`, `OPEN_BELOW_L4_BREAKDOWN`, `OPEN_IN_UPPER_TRAP_ZONE`, or `OPEN_IN_LOWER_TRAP_ZONE`.
* **Location-Anchored Candlestick Morphology & Wick Rejection:** Detects Hammers, Inverted Hammers, Engulfing, Inside Bars, and NR7 volatility compression. Strictly validates that patterns anchor to institutional zones (VWAP, $L3/L4$, 200 EMA) and vetoes breakout traps showing $> 40\%$ upper wick rejection.
* **VWAP Statistical Dispersion Bands:** Identifies overbought exhaustion ($+2\sigma$) and deep value value zones ($-2\sigma$) dynamically anchored to volume.
* **John Carter's TTM Squeeze:** Captures explosive directional thrusts by tracking Bollinger Band (20, 2.0) compression inside Keltner Channels (20, 1.5 ATR).
* **Midday-Hardened RVOL Engine:** Automatically detects liquidity troughs between 11:30 and 13:30 IST, rejecting false breakouts lacking 3.0x volume confirmation.
* **Wyckoff Volume Spread Analysis (VSA):** Compares Close Location Quotient ($CLQ = \frac{Close - Low}{High - Low}$) against delivery bhavcopy percentages to separate genuine smart-money accumulation from operator churn.

### 2. 📊 Institutional Derivatives & Microstructure Engine
* **4-Quadrant Open Interest (OI) Dynamics:** Classifies underlying stock futures flow:
  - `LONG_BUILDUP` ($\Delta \text{Price} > 0, \Delta \text{OI} > 0$): High institutional accumulation conviction (+10 pts).
  - `SHORT_COVERING` ($\Delta \text{Price} > 0, \Delta \text{OI} < 0$): Fragile short squeeze (+3 pts, tight trailing stop).
  - `SHORT_BUILDUP` ($\Delta \text{Price} < 0, \Delta \text{OI} > 0$): Aggressive short positioning (-12 pts, hard BUY veto).
  - `LONG_UNWINDING` ($\Delta \text{Price} < 0, \Delta \text{OI} < 0$): Panic liquidation (-10 pts, Demat defense alert).
* **Real-Time Option Chain Analytics:** Evaluates Put-Call Ratio (PCR), Max Pain strikes, and major call/put resistance and support strike walls.

### 3. 🌐 Macro Gatekeeper & Event Risk Shields
* **Top-Down Sector Gatekeeper:** Inspects parent sectoral index alignment (e.g. NIFTY IT, NIFTY BANK). If the sector is in severe drag ($< -0.40\%$ vs Nifty), individual stock breakouts are strictly vetoed.
* **Forward Corporate Earnings 48-Hour Lockout Shield:** Cross-references quarterly financial result calendars, enforcing an automatic trade veto within 48 hours of earnings to eliminate binary overnight gap risk.
* **Brent Crude Oil Commodity Shock Veto:** Detects overnight crude oil surges ($\ge 3\%$), automatically vetoing long trades on margin-sensitive sectors (Paints, Auto, OMCs, Aviation).
* **Adaptive Market Regime Switcher:** Automatically switches between **Breakout Hunting Mode** (expanding trend, $\text{ADX} \ge 25$) and **Mean-Reversion Mode** ($L3$ bounce / $H3$ fade, $\text{ADX} < 20, \text{VIX} < 14.5$).

### 4. 💼 5-State Demat Portfolio Risk Lifecycle
Your connected Demat holdings (ICICI Direct, Dhan, Angel One) are continuously guarded by an asymmetric risk manager:
* 🔴 **`CAPITAL_PRESERVATION_EXIT`:** Immediate alert when price breaches $L_4$ breakdown or drops $>8\%$ below your average buy price.
* 🟡 **`DEFENSIVE_TRIM_ALERT`:** Recommends banking 50% profit at Target 1 ($H_4$) and moving your protective stop-loss to cost basis.
* 🟢 **`TRAILING_SL_ALERT`:** Chandelier ATR trailing stops automatically ratchet upwards as the stock advances into profit.
* 🔵 **`ACCUMULATE_WATCH`:** Permits pyramiding strictly on winning positions displaying institutional delivery absorption.
* ⚪ **`HOLD_STEADY`:** Healthy trend progression within normal volatility bounds.

### 5. ⚖️ SEBI-Compliant Execution Guardrails
* **Mandatory Stop-Loss Limit (SL-L) Routing:** In accordance with SEBI risk circulars, Stop-Loss Market (SL-M) orders are completely barred to eliminate freak-trade execution slippage.
* **Dynamic Exchange Tick Snapping:** Automatically rounds prices and trigger limits to exchange rules (₹0.05 for stocks $\ge ₹250$; ₹0.01 for stocks $< ₹250$).
* **Pre-Trade Circuit Freeze Rejections:** Halts BUY orders on Upper Circuit freeze and SELL orders on Lower Circuit freeze before broker routing.
* **Dynamic CNC vs. MIS Short Detection:** If you sell a stock not present in your Demat holdings, StokVigil routes the order as Intraday Margin (MIS) and issues a statutory warning regarding 03:15 PM IST square-off and potential 20% auction penalty risks.
* **Financial-Grade Idempotency Debouncing:** Bounded in-memory lock prevents accidental double-tap orders via custom `X-Idempotency-Key` or automatic request fingerprinting.

### 6. 📜 100% Transparent Audited Accuracy Ledger
Unlike platforms that delete bad calls, StokVigil AI permanently writes every emitted signal to an immutable ledger (`/api/market/accuracy-ledger`). Subsequent market candles are evaluated to independently measure Target 1 hit rates, trailing stop exits, and overnight gap slippage.

### 7. ⚡ Real-Time Native Streaming Architecture (<50ms Latency)
* **FastAPI Native Server-Sent Events (SSE) & WebSockets:** Direct low-latency tick distribution via `GET /api/stocks/stream` and `WS /ws/quotes`.
* **Zero Third-Party Middleware Fees:** Eliminates recurring costs from external pub/sub services (Pusher, PubNub, Redis Enterprise) by using an in-memory asynchronous `TickerBroadcaster` queue fanout.
* **Instant Client Synchronization:** Dispatches live prices, Camarilla status, and risk flags to Next.js Edge streaming proxy (`/api/stream`) and Flutter Mobile app under 50ms, falling back to SWR during connection re-negotiation.

### 8. 🛡️ Institutional Accuracy Engine & Overnight VaR
* **Veto Filter #6 (Bid-Ask Spread & Illiquidity Gatekeeper):** Automatically evaluates exchange turnover and bid-ask spread before confirming buy setups:
  - Minimum Daily Turnover: **₹5.0 Crore** (NSE) / **₹2.0 Crore** (BSE).
  - Maximum Bid-Ask Spread: **0.25%** (NSE) / **0.40%** (BSE).
  - High-momentum setups failing liquidity checks are vetoed (`BUY_WATCH` $\to$ `HOLD_NEUTRAL`), shielding retail capital from high-slippage execution traps in illiquid scrips.
* **1-Day 95% Parametric Overnight Value-at-Risk (VaR) Engine:**
  - Automatically triggered when market volatility elevates (**India VIX $\ge 17.50$**).
  - Calculates single-session maximum probable gap-down loss on Demat holdings:
    $$\text{Overnight VaR (₹)} = \text{Position Value} \times 1.65 \times \beta \times \frac{\text{VIX}}{\sqrt{252}}$$
  - Surfaced directly on holdings cards as an explicit risk percentage and rupee value to prevent overnight gap shock.

### 9. 🔄 Demat Sold Stock Auto-Reconciliation
* **Automatic Holding Lifecycle Purge:** When a user completely liquidates an equity (`quantity == 0` or position absent from broker Demat tradebook), StokVigil instantly purges it from auto-synced watchlists (`user_watchlists` with `is_auto_synced = TRUE`).
* **Zero Ghost Surveillance:** Prevents obsolete alerts on exited positions while preserving user-curated discretionary watchlist symbols (`is_auto_synced = FALSE`).

### 10. 🔰 Beginner Parity Layer: Dual View Mode (`[⚡ Prop Desk | 🔰 Beginner]`)
* **Single-Click Segmented View Mode Toggle:** Integrated into both Next.js Web Portal and Flutter Mobile App with persistent user preference storage.
* **⚡ Prop Desk Mode:** Full quantitative institutional telemetry—Camarilla $H_4/H_5/L_3/L_4$, Anchored VWAP $\pm 2\sigma$, Wyckoff CLQ, RVOL, Chandelier ATR trailing stop, and 1D 95% VaR.
* **🔰 Beginner Mode (Plain English):** Translates quant jargon into clear, actionable terms:
  - `Target 1 (H4 Breakout)` $\to$ `Profit Goal (Target 1 Reached - Consider booking gains)`
  - `Capital Preservation Exit (L4 Breakdown)` $\to$ `Safety Exit (Cut Loss Immediately)`
  - `Hold Steady` $\to$ `Hold (Stable Trend)`
  - `Target:` $\to$ `Profit Goal:`, `Stop Loss:` $\to$ `Safety Exit:`, `Trailing SL:` $\to$ `Profit Lock:`
  - Highlights illiquidity warnings (`⚠️ Hard to Sell (Thin Liquidity)`) and overnight gap risks (`⚠️ High Overnight Risk: ~X% gap potential`).

### 11. ⚖️ Mandatory SEBI Compliance & Transparency Disclosures
* Embedded regulatory disclosure banners across Watchlist and Portfolio interfaces complying with SEBI (Research Analysts) Regulations, 2014 & SEBI (Investment Advisers) Regulations, 2013.
* Explicitly certifies that all levels and alerts are purely algorithmic mathematical volatility benchmarks, upholding zero-advisory standards.

---

## 🏗️ Full-Stack System Architecture

StokVigil AI is structured as a decoupled, multi-tiered full-stack architecture engineered for sub-millisecond execution, zero developer credential leakage, and 100% free-tier cloud viability.

> [!TIP]
> **Interactive Architecture Visualizer**: Open [`stokvigil_architecture.html`](stokvigil_architecture.html) in your browser to interactively explore and toggle between the Full-Stack Market Engine and Multi-User Notification views with live laser animations and device mockups.

### 1. Full-Stack End-to-End Market Engine

<p align="center">
  <img src="./docs/assets/stokvigil_fullstack_engine.svg" alt="StokVigil AI Full-Stack Market Engine Architecture" width="100%" />
</p>

### 2. Multi-User Notification Architecture

<p align="center">
  <img src="./docs/assets/stokvigil_notification_architecture.svg" alt="StokVigil AI Multi-User Notification Architecture" width="100%" />
</p>

### 3. Six-Tier Layered Topology Specification

The architecture follows a strict 6-tier unidirectional flow with sub-millisecond decoupled state, zero-trust security barriers, and cryptographic boundaries:

```mermaid
flowchart TD
    %% Global Styling
    classDef client fill:#0C1E38,stroke:#38BDF8,stroke-width:2px,color:#E2E8F0;
    classDef gateway fill:#131B2E,stroke:#818CF8,stroke-width:2px,color:#E2E8F0;
    classDef app fill:#0A1E24,stroke:#00F5FF,stroke-width:2px,color:#E2E8F0;
    classDef quant fill:#042618,stroke:#00FF88,stroke-width:2px,color:#E2E8F0;
    classDef state fill:#261404,stroke:#FFB800,stroke-width:2px,color:#E2E8F0;
    classDef exec fill:#2A0A18,stroke:#FB7185,stroke-width:2px,color:#E2E8F0;

    subgraph TIER1 ["Tier 1: Presentation & Client Applications"]
        WEB["Next.js 16 Web Portal<br/>(React 19, Tailwind CSS, TypeScript)<br/>TradingView Lightweight Charts (H5-L5) | Confluence Radar"]:::client
        MOBILE["Flutter Mobile App (iOS / Android)<br/>(Dart 3.3+, Provider, Biometrics)<br/>Live Watchlist | Demat Risk Badges | Push Alerts"]:::client
    end

    subgraph TIER2 ["Tier 2: Ingress, Security & Cryptographic Vault"]
        INGRESS["Cloudflare CDN & Cloud Run Ingress<br/>(HTTPS / WSS Termination & Proxy Verification)"]:::gateway
        AUTH_GUARD["Security Middleware & Zero-Trust IDOR Guard<br/>(JWT Bearer Auth & verify_user_access)"]:::gateway
        RATE_LIMIT["Memory-Bounded Token Bucket Rate Limiter<br/>(Burst Protection & IP-Based Throttling)"]:::gateway
        VAULT["Fernet AES-256-CBC Cryptographic Vault<br/>(PBKDF2HMAC SHA-256 Key Derivation + Salt)"]:::gateway
    end

    subgraph TIER3 ["Tier 3: FastAPI Backend & Daemon Orchestration"]
        FASTAPI["FastAPI Async ASGI Application<br/>Lifespan Context Manager | Defensive Security Headers"]:::app
        ROUTERS["REST API Routers<br/>/stocks | /orders | /market | /auth | /cron"]:::app
        SCANNER["5-Min Multi-Tenant Surveillance Scanner<br/>(Deduplicated Scans & Portfolio Evaluator)"]:::app
        TICK_WORKER["worker.py Real-Time Tick Daemon<br/>(2.0s Dual-Tier RAM Synchronization & Re-Auth)"]:::app
    end

    subgraph TIER4 ["Tier 4: Quantitative Confluence & Sovereign AI"]
        MATH_CORE["Vectorized Quantitative Technical Engine<br/>Camarilla Pivots (H1-H5 / L1-L5) | VWAP ±1σ/±2σ Bands<br/>Location-Anchored Candlesticks | TTM Squeeze | Midday RVOL (3.0x)"]:::quant
        VETO_GATE["🛑 Hard Institutional Vetoes<br/>Lunch Trap | 200 EMA | Sector Drag | Earnings Lockout<br/>Crude Shock | Derivatives Short Buildup | Wick Rejection"]:::quant
        DEMAT_GUARDIAN["🛡️ 5-State Demat Portfolio Risk Guardian<br/>CAPITAL_PRESERVATION | DEFENSIVE_TRIM | TRAILING_SL<br/>ACCUMULATE_WATCH | HOLD_STEADY"]:::quant
        GEMINI_AI["Gemini 3.5 Flash Lite Qualitative AI Engine<br/>Strict Mathematical Sovereignty (Numbers 100% Locked by Python)<br/>&lt;untrusted_external_news&gt; Injection Defense | 15 Calls Limit"]:::quant
    end

    subgraph TIER5 ["Tier 5: Ultra-Low Latency State & Persistence"]
        RAM_CACHE["Tier-1 Process RAM Cache<br/>(&lt;0.01 ms Latency | LRU Bounded 2,000 Symbols)"]:::state
        UNLOGGED_DB["Tier-2 Supabase UNLOGGED Table<br/>(market_memory_cache | &lt;0.80 ms DB Access | Zero Redis)"]:::state
        PGBOUNCER["PgBouncer Pool (Port 6543, Transaction Mode)<br/>statement_cache_size=0 | Advisory Locks (987654321)"]:::state
        SUPABASE_PG["Supabase PostgreSQL 15+ Core Store<br/>InitPlan (SELECT auth.uid()) Optimized RLS<br/>profiles | user_credentials | watchlists | stok_alerts"]:::state
    end

    subgraph TIER6 ["Tier 6: Multi-Broker Execution & Dispatch"]
        SEBI_ENGINE["SEBI Pre-Trade Safety Validator<br/>Mandatory SL-Limit Only | Dynamic Tick Snap (₹0.05/₹0.01)<br/>Pre-Trade Circuit Freeze Check | Idempotency Debounce"]:::exec
        BROKER_APIS["Multi-Broker API Adapters<br/>ICICI Breeze Connect | Dhan HQ v2 | Angel One SmartAPI<br/>Pure Master App Publisher (Zero Developer Keys on Server)"]:::exec
        DISPATCH_ENGINE["High-Priority Async Dispatch Engine<br/>Telegram HTTP/2 Client (25 msg/s Leaky Bucket)<br/>Firebase Cloud Messaging (FCM Mobile Lock-Screen)"]:::exec
        EXCHANGES["🏛️ Indian Capital Market Infrastructure<br/>NSE & BSE Matching Engines | NSDL & CDSL Depositories"]:::exec
    end

    %% Client to Ingress
    WEB & MOBILE -->|"HTTPS / WSS"| INGRESS
    INGRESS --> AUTH_GUARD
    AUTH_GUARD --> RATE_LIMIT
    RATE_LIMIT --> FASTAPI

    %% App Server Wiring
    FASTAPI --> ROUTERS
    ROUTERS --> VAULT
    ROUTERS --> SCANNER
    SCANNER --> MATH_CORE
    TICK_WORKER <-->|"IPC &lt;0.01ms"| RAM_CACHE
    RAM_CACHE <-->|"Periodic Sync"| UNLOGGED_DB

    %% Quantitative & AI Confluence Wiring
    MATH_CORE --> VETO_GATE
    VETO_GATE --> DEMAT_GUARDIAN
    DEMAT_GUARDIAN -- "High-Conviction Catalysts Only" --> GEMINI_AI
    DEMAT_GUARDIAN --> DISPATCH_ENGINE
    GEMINI_AI -- "Qualitative Rationale" --> DISPATCH_ENGINE

    %% State & Persistence Wiring
    ROUTERS & SCANNER <-->|"Port 6543"| PGBOUNCER
    PGBOUNCER <--> SUPABASE_PG

    %% Execution Wiring
    ROUTERS -->|"1-Click Order"| SEBI_ENGINE
    SEBI_ENGINE --> BROKER_APIS
    BROKER_APIS -->|"FIX / Open API"| EXCHANGES
    DISPATCH_ENGINE -->|"Telegram Bot & FCM Push"| WEB & MOBILE
```

---

### 4. Full-Stack Layer Responsibility & Latency SLA Matrix

| Full-Stack Tier | Components & Technologies | Protocols & Ports | Latency SLA | Key Architectural Guarantees |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1: Presentation Tier** | **Next.js 16 App Router** (React 19, Tailwind CSS, TypeScript)<br/>**Flutter SDK 3.19+** (Dart 3.3+, Provider, Biometrics) | HTTPS (443), WSS | &lt; 50 ms SSE render | Interactive TradingView Lightweight charts (H5-L5), **[⚡ Prop Desk | 🔰 Beginner]** Dual View Mode, 4-pillar radars, native SSE streaming client, 1-click SL-L order dialogs, and instant push alert rendering. |
| **Tier 2: Ingress & Security** | **FastAPI Middleware**, Pydantic v2 Settings, **Fernet AES-256 Vault**, JWT Bearer Auth | HTTPS (443) | &lt; 2 ms overhead | Client-side IDOR validation (`verify_user_access`), memory-bounded token bucket rate limiting, HTTP security headers (HSTS, CSP), and PBKDF2HMAC credential protection. |
| **Tier 3: App Server & Daemons** | **FastAPI Async Engine**, Uvicorn ASGI, Lifespan Context Manager, **PgBouncer Pool** | HTTP, IPC, SSE | &lt; 15 ms internal API / &lt; 50 ms SSE | High-throughput in-memory **TickerBroadcaster** (FastAPI SSE `/api/stocks/stream` & WebSocket `/ws/quotes`), multi-tenant 5-minute automated scanning loop, 2-second market-hours tick worker (`worker.py`), persistent thread pools, and non-blocking I/O. |
| **Tier 4: Quantitative Math & AI** | **Vectorized NumPy & Pandas Engine**, SciPy, **Gemini 3.5 Flash Lite** (`google-genai` SDK) | In-Memory / Vectorized, HTTPS | &lt; 5 ms math / &lt; 1.2s AI | Expanded Camarilla pivots ($H_1 \dots H_5 / L_1 \dots L_5$), Location-Anchored Candlesticks, 4-Quadrant F&O Derivatives OI, **Veto Filter #6 (Illiquidity & Bid-Ask Gatekeeper)**, **1-Day 95% Parametric Overnight VaR Engine**, **Demat Sold Stock Auto-Reconciliation**, and Gemini AI qualitative synthesis under strict mathematical sovereignty. |
| **Tier 5: State & Persistence** | **Dual-Tier Cache** (Process RAM + Supabase `UNLOGGED` Table), **Supabase PostgreSQL 15+** | PostgreSQL Wire Protocol (Port 6543) | **&lt; 0.01 ms** (RAM)<br/>**&lt; 0.80 ms** (DB) | Sub-millisecond market state bypassing WAL disk I/O, PgBouncer transaction-mode pooling with `statement_cache_size=0`, Postgres advisory locking (`pg_try_advisory_lock`), and `(SELECT auth.uid())` InitPlan RLS. |
| **Tier 6: Execution & Dispatch** | **Broker Adapters** (ICICI Breeze, Dhan HQ, Angel One), **Telegram HTTP/2 Client**, FCM | HTTP/2, REST APIs, WebSockets | &lt; 250 ms order dispatch | Mandatory SEBI Stop-Loss Limit (SL-L) orders, dynamic tick snapping (₹0.05 / ₹0.01), pre-trade circuit freeze rejections, dynamic CNC/MIS short detection, and 25 msg/s leaky-bucket Telegram alert dispatch. |

---

### 5. Architectural Dataflow Trajectories

The system executes three synchronized, non-blocking operational dataflow loops:

1. **Real-Time Native Streaming & Tick Broadcasting (<50ms Loop)**:
   > `Broker WebSockets / Yahoo Pool` ➔ **Live Ticks** ➔ `TickerBroadcaster (Process RAM <0.01ms)` ➔ **FastAPI Native SSE (/api/stocks/stream) & WebSocket (/ws/quotes)** ➔ `Next.js Edge Proxy & Flutter Subscribers (<50ms)` ➔ **Tier-2 UNLOGGED DB Flush (2.0s)**

2. **5-Minute Quantitative Surveillance & Alerting Trajectory**:
   > `Cron Trigger / Market Event` ➔ **Deduplicated Scrip Set** ➔ `Vectorized Technical Engine` ➔ **4-Pillar Confluence (≥75%)** ➔ `6 Hard Institutional Vetoes (Lunch Trap, Breadth, 200 EMA, Sector Drag, Earnings, Illiquidity Gatekeeper)` + `1-Day 95% Overnight VaR` ➔ **Gemini 3.5 AI Rationale** ➔ `Telegram & FCM Lock Screen Push`

3. **1-Click SEBI-Compliant Broker Execution Trajectory**:
   > `User Click` ➔ **Signed JWT + Idempotency Key** ➔ `Pre-Trade Circuit & Dynamic Tick Snap` ➔ **SL-Limit Order Enforcement** ➔ `Multi-Broker Adapter` ➔ `NSE / BSE Clearing & Settlement`

---

## ⚡ Sequence Diagram

The following sequence illustrates how StokVigil AI autonomously scans the market, enforces institutional vetoes, and dispatches high-conviction alerts to users:

```mermaid
sequenceDiagram
    autonumber
    participant Cron as Cloud Scheduler (Every 5 Mins)
    participant Agent as Agent Runner (FastAPI)
    participant Cache as Dual-Tier Cache (RAM + UNLOGGED)
    participant Tech as Technical Engine (1,400+ LOC)
    participant Flow as Flow & Options Tracker
    participant Confluence as 4-Pillar Confluence Engine
    participant Gemini as Gemini 3.5 Flash Lite
    participant DB as Supabase PostgreSQL
    participant Notif as Telegram / FCM Dispatcher
    participant Client as Next.js Web / Flutter App
    participant Broker as Broker Gateway (Breeze/Dhan)

    Cron->>Agent: POST /api/cron/multi-user-scan (Bearer Secret)
    activate Agent
    Agent->>DB: Query Active Watchlists & Demat Portfolios
    DB-->>Agent: Monitored Symbols (ISIN Deduplicated)

    rect rgb(20, 30, 45)
        note over Agent,Tech: Step 1: Pre-compute Deduplicated Universe
        Agent->>Cache: Lookup Process RAM & UNLOGGED Table
        Cache-->>Agent: Sub-millisecond Indicators & Live Ticks
        Agent->>Tech: Batch Vectorized Indicators (50-Stock Chunks)
        Tech-->>Agent: Camarilla H4/L4, VWAP ±2σ, TTM Squeeze, RVOL
        Agent->>Flow: Fetch NSE Delivery Bhavcopy & Option Chain
        Flow-->>Agent: Wyckoff Delivery % & Max Pain Strike
    end

    rect rgb(30, 45, 30)
        note over Agent,Confluence: Step 2: User Portfolio & Veto Evaluation
        Agent->>Confluence: Check 6 Hard Vetoes (Lunch Trap, Breadth, 200 EMA)
        Confluence-->>Agent: 5-State Portfolio Lifecycle Verdict
    end

    alt Active Tier-1 Catalyst Detected (Breakout > H4 or Volume Surge)
        Agent->>Gemini: Synthesize Catalyst Narrative (System Quota <= 15 calls)
        Gemini-->>Agent: Qualitative Rationale (Numbers Hard-Locked by Python)
    else Quiet or Normal Fluctuation
        Agent->>Agent: Generate Deterministic Fact-Based Template
    end

    Agent->>DB: Persist Snapshot to public.stok_alerts
    Agent->>Notif: Dispatch Alert (45-Minute Anti-Fatigue Filtered)
    Notif->>Client: Telegram Rich HTML / FCM Push Alert
    deactivate Agent

    opt Trader Executes Approved Order
        Client->>Agent: POST /api/v1/orders/place (X-Idempotency-Key)
        activate Agent
        Agent->>Agent: Verify Circuit Lock & SEBI SL-M Prohibitions
        Agent->>Agent: Auto-Detect CNC vs MIS & Snap Tick (₹0.05/₹0.01)
        Agent->>Broker: Place Order (ICICI Breeze / Dhan API v2)
        Broker-->>Agent: Order Reference ID / Execution Status
        Agent-->>Client: Instant Order Confirmation & Audit Proof
        deactivate Agent
    end
```

---

## 💻 Tech Stack

| Layer | Technologies | Role in StokVigil AI |
| :--- | :--- | :--- |
| **Backend Runtime** | **Python 3.11+, FastAPI, Uvicorn** | High-concurrency async service handling API requests, market pipelines, and mathematical models. |
| **Database & Auth** | **Supabase (PostgreSQL 15+), pgvector** | Managed database with Row Level Security (RLS) optimized via `(SELECT auth.uid())` InitPlan query caching. |
| **Connection Pooling** | **PgBouncer (Port 6543, Transaction Mode)** | Zero prepared-statement collisions (`statement_cache_size=0`) and Postgres advisory locking. |
| **Market Memory Cache**| **Dual-Tier Cache (Process RAM + UNLOGGED Table)**| Sub-millisecond cross-container state without paid Redis clusters by bypassing WAL disk I/O. |
| **Data Encryption** | **Fernet AES-256 CryptoVault** | PBKDF2HMAC SHA-256 key derivation with per-record 16-byte random salts protecting broker tokens. |
| **Quantitative Math** | **NumPy, Pandas, SciPy** | Vectorized financial indicator calculations across multi-timeframe OHLCV data. |
| **AI Tier** | **Google Gemini 3.5 Flash Lite** | Official modern `google-genai` SDK with fallback chain and quota limiting (Qualitative Rationale only). |
| **Notification Engine** | **Telegram Bot API (HTTP/2) & FCM** | Persistent connection with a 25 msg/s leaky bucket rate limiter and Firebase Cloud Messaging. |
| **Web Portal** | **Next.js 16 (App Router), Tailwind CSS** | TradingView Lightweight Charts (H5-L5), Confluence Radar, interactive backtester, and Demat sync dashboard. |
| **Mobile Application** | **Flutter SDK 3.19+ (Dart 3.3+)** | Cross-platform (Android & iOS) app featuring a terminal dark palette, biometric access, and live charts. |
| **Broker Gateways** | **Breeze Connect, Dhan v2, SmartAPI** | Unified Broker Adapter abstraction pattern supporting automated Demat order execution. |

---

## 📂 Repository Directory Structure

```
stokvigil-ai/
├── backend/                                # FastAPI Backend Service
│   ├── app/
│   │   ├── brokers/                        # Broker Adapters (Breeze, Dhan HQ, SmartAPI)
│   │   │   ├── base.py                     # BrokerAdapter Abstract Base Class
│   │   │   ├── icici.py                    # ICICI Direct Breeze Connect Integration
│   │   │   └── dhan.py                     # Dhan HQ Open API v2 Integration
│   │   ├── core/                           # Application Core Utilities
│   │   │   ├── dependencies.py             # Database injection, market hour checkers
│   │   │   └── rate_limiter.py             # Memory-bounded token bucket rate limiter
│   │   ├── engine/                         # Quantitative Strategy & Data Engines
│   │   │   ├── deterministic.py            # 4-Pillar Confluence, Vetoes, VaR & Regime Switcher
│   │   │   ├── gemini_ai.py                # Gemini SDK pipeline with quota management
│   │   │   ├── portfolio_sync.py           # Demat holding, cost-basis & sold stock auto-reconciliation
│   │   │   ├── security_master.py          # O(1) RAM ISIN & Scrip Code Resolver
│   │   │   └── ticker_stream.py            # Real-time SSE & WebSocket ticker broadcaster (<50ms)
│   │   ├── routers/                        # API Endpoints
│   │   │   ├── auth.py                     # Profiles, credentials & Demat holdings
│   │   │   ├── cron.py                     # Scheduled scanning & briefing pipelines
│   │   │   ├── market.py                   # Backtesting, FII/DII, accuracy ledger
│   │   │   ├── orders.py                   # Idempotent broker trade routing
│   │   │   └── stocks.py                   # Quotes, searches, SSE stream, candles (H5-L5)
│   │   ├── schemas/                        # Pydantic v2 Models & Tick Snapping
│   │   ├── accuracy_verifier.py            # Historical OHLCV alert performance verifier
│   │   ├── agent_runner.py                 # Multi-tenant 5-minute scanning engine
│   │   ├── alert_limiter.py                # 45-minute anti-fatigue cooldown manager
│   │   ├── auth.py                         # JWT verification & IDOR security guards
│   │   ├── backtester.py                   # Vectorized historical backtest engine
│   │   ├── config.py                       # Pydantic BaseSettings environment loader
│   │   ├── corporate_calendar.py           # Forward Corporate Earnings 48-Hour Lockout Shield
│   │   ├── db_pool.py                      # PgBouncer async connection pool manager
│   │   ├── derivatives_tracker.py          # NSE Derivatives 4-Quadrant Open Interest (OI) Engine
│   │   ├── fii_dii_tracker.py              # NSE FII/DII cash turnover scraper
│   │   ├── flow_tracker.py                 # NSE delivery bhavcopy & option chain parser
│   │   ├── macro_filter.py                 # Top-Down Sector Gatekeeper, Crude Shock & Gift Nifty
│   │   ├── market_cache.py                 # Dual-Tier RAM / UNLOGGED Table Manager
│   │   ├── notifications.py                # Telegram HTTP/2 (25 msg/s) & FCM Notifier
│   │   ├── patterns.py                     # Location-Anchored Candlesticks & Wick Rejection Engine
│   │   ├── technical_engine.py             # 1,672-line vectorized indicator engine (H1-H5 / L1-L5)
│   │   ├── vault.py                        # Fernet AES-256 cryptographic vault
│   │   └── worker.py                       # Standalone 2-second market hours tick worker
│   ├── tests/                              # Comprehensive Pytest Suite (43 test files, 309 tests, 100% pass rate)
│   ├── requirements.txt                    # Python runtime dependencies
│   └── Dockerfile                          # Cloud Run container definition
├── supabase/                               # Database Schemas & Migrations
│   └── migrations/                         # SQL migration history (August - November 2026)
├── web_portal/                             # Next.js 16 Web Portal
│   ├── src/
│   │   ├── app/                            # App Router (Pages, Transparency Ledger)
│   │   ├── components/                     # TradingView Charts, Confluence Radar, Modals
│   │   └── hooks/                          # Auth, Portfolio, Watchlist & Alerts Hooks
│   ├── package.json                        # Node dependencies
│   └── tailwind.config.js                  # Custom dark-theme styling configuration
├── mobile_app/                             # Flutter Cross-Platform Mobile Client
│   ├── lib/
│   │   ├── config/                         # Terminal-inspired theme definitions
│   │   ├── models/                         # Strong-typed Dart financial data models
│   │   ├── providers/                      # Provider state managers
│   │   ├── screens/                        # Dashboard, Watchlist, Alerts, Chart Screens
│   │   ├── services/                       # ApiService, SupabaseService, FcmService
│   │   └── widgets/                        # Broker icons, modals, and metric cards
│   └── pubspec.yaml                        # Flutter package configuration
├── architecture_blueprint.md               # Master System Architecture Specification
├── STOKVIGIL_MASTER_PROMPT.md              # Authoritative System Prompt Specification
└── README.md                               # Project Documentation (This File)
```

---

## 📋 Prerequisites

Ensure you have the following installed on your local workstation:

| Tool | Version | Purpose |
| :--- | :--- | :--- |
| **Python** | `3.11.x` or `3.12.x` | Backend runtime & vectorized mathematical computation. |
| **Node.js** | `18.18+` or `20.x` | Next.js 14 Web Portal runtime. |
| **Flutter SDK** | `3.19.x+` (Dart 3.3+) | Cross-platform mobile development for Android & iOS. |
| **Supabase Account**| PostgreSQL 15+ | Cloud PostgreSQL database instance. |
| **Git** | `2.40+` | Source code version control. |

---

## 🚀 Installation Steps

### Step 1: Clone the Repository
```bash
git clone https://github.com/your-org/stokvigil-ai.git
cd stokvigil-ai
```

### Step 2: Initialize the Database (Supabase)
1. Go to your **Supabase Dashboard &rarr; SQL Editor**.
2. Run the consolidated bootstrap script located at [backend/supabase_rls_setup.sql](file:///g:/stokvigil-ai/backend/supabase_rls_setup.sql), or apply the versioned migrations in [supabase/migrations/](file:///g:/stokvigil-ai/supabase/migrations/) sequentially.

### Step 3: Configure and Install the Backend
```bash
cd backend

# Create and activate Python virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create environment configuration
cp .env.example .env
```

Populate your `backend/.env` with your credentials:
```ini
ENVIRONMENT=development
PORT=8000

# Supabase Credentials
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOi...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOi...
DATABASE_URL=postgresql://postgres.your-project:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres

# Cryptographic Master Key (Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
CREDENTIALS_ENCRYPTION_KEY=your-generated-base64-key

# AI Context Synthesis
GEMINI_API_KEY=AIzaSy...

# Notifications
TELEGRAM_BOT_TOKEN=123456789:ABCdef...
TELEGRAM_CHAT_ID=-100123456789

# Security Secrets
CRON_SECRET_KEY=stokvigil-cron-super-secret-key-2026
ADMIN_SECRET_KEY=stokvigil-admin-super-secret-key-2026

# Broker Master Credentials (Publisher Model)
ICICI_MASTER_APP_KEY=your-icici-master-app-key
ICICI_MASTER_SECRET_KEY=your-icici-master-secret-key
```

### Step 4: Configure and Install the Web Portal
```bash
cd ../web_portal
npm install
cp .env.example .env.local
```

Set `web_portal/.env.local`:
```ini
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOi...
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

### Step 5: Configure the Mobile Application
```bash
cd ../mobile_app
flutter pub get
```

---

## 🏃 Running the Application

### 1. Start the FastAPI Backend
```bash
cd backend
# Make sure .venv is active
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
* **Swagger API Documentation:** `http://localhost:8000/docs`
* **Health Check:** `http://localhost:8000/api/health`

### 2. Start the Real-Time Market Tick Worker
```bash
cd backend
python -m app.worker
```
*Streams live ticks and syncs process RAM to the Supabase UNLOGGED table every 2 seconds during market hours (09:14–15:31 IST).*

### 3. Launch the Next.js Web Portal
```bash
cd web_portal
npm run dev
```
*Access the portal at `http://localhost:3000`.*

### 4. Launch the Flutter Mobile App
```bash
cd mobile_app
flutter devices
flutter run
```

### 5. Simulate Scheduled Cron Surveillance Pipelines
```bash
# Trigger 09:00 AM IST Pre-Market War Room Briefing
curl -X POST "http://localhost:8000/api/cron/pre-market-briefing" \
  -H "X-Cron-Secret: stokvigil-cron-super-secret-key-2026"

# Trigger 5-Minute Multi-Tenant Surveillance Scan
curl -X POST "http://localhost:8000/api/cron/multi-user-scan" \
  -H "X-Cron-Secret: stokvigil-cron-super-secret-key-2026"

# Trigger 03:35 PM IST Post-Market Summary
curl -X POST "http://localhost:8000/api/cron/post-market-summary" \
  -H "X-Cron-Secret: stokvigil-cron-super-secret-key-2026"
```

---

## 🧪 Testing

StokVigil AI maintains an institutional test suite covering financial math, RLS policies, broker order routing, and circuit limit edge cases:

```bash
cd backend

# 1. Run all unit and integration tests
pytest

# 2. Test the 1,417-line Technical Engine & Camarilla Formulas
pytest tests/test_institutional_engine.py

# 3. Test 4-Pillar Confluence Engine & Defensive Veto Gatekeepers
pytest tests/test_gatekeeper_and_vsa.py

# 4. Test Broker Adapters, Tick Snapping & SEBI SL-M Prohibitions
pytest tests/test_broker_adapters.py tests/test_financial_trade_flaws.py

# 5. Test Institutional Accuracy Upgrades (Veto #6 Illiquidity Gatekeeper & 1D Overnight VaR)
pytest tests/test_institutional_parity_upgrades.py

# 6. Test Demat Sold Stock Auto-Reconciliation Lifecycle
pytest tests/test_sold_stock_lifecycle.py

# 7. Test Native FastAPI Real-Time SSE & WebSocket Streaming (<50ms)
pytest tests/test_realtime_streaming.py

# 8. Test Dual-Tier UNLOGGED Cache Performance
pytest tests/test_unlogged_cache.py

# 9. Generate Complete Test Coverage Report
pytest --cov=app tests/ --cov-report=term-missing
```

### Client Validations
```bash
# Web Portal TypeScript & Build Validation
cd web_portal
npx tsc --noEmit
npm run build

# Mobile Application Static Analysis
cd ../mobile_app
flutter analyze
```

---

## 🤝 Contributor Guidelines

We welcome contributions from quantitative developers, backend engineers, and financial analysts!

### Engineering Mandates
1. **Mathematical Sovereignty Rule:** LLMs must **NEVER** calculate prices, stop losses, position sizes, or numerical scores. All math must be 100% deterministic and vectorized via NumPy/Pandas.
2. **Zero-Default Policy:** Never insert arbitrary default prices (e.g., `₹0` or `100.0`) when data is unavailable. Always return `None` or `DATA_UNAVAILABLE`.
3. **InitPlan RLS Enforcement:** Supabase Row Level Security SQL policies must ALWAYS use `(SELECT auth.uid()) = user_id` to guarantee InitPlan query caching.
4. **Documentation Integrity:** Preserve all existing comments, docstrings, and financial formulas across all source files.
5. **Defensive Asynchrony:** Offload CPU-heavy mathematical computations (backtesting, multi-stock indicators) with `asyncio.to_thread` or persistent ThreadPoolExecutors.

### Git & PR Workflow
```bash
# 1. Create a feature branch
git checkout -b feature/order-flow-absorption-tuning

# 2. Commit using Conventional Commits
git commit -m "feat(flow): tune Wyckoff CLQ threshold for high-beta stocks"

# 3. Verify all tests pass
pytest tests/

# 4. Push and create a Pull Request
git push origin feature/order-flow-absorption-tuning
```

---

## ⚖️ Regulatory Disclaimer

> [!WARNING]
> **SEBI Non-Advisory Regulatory Disclosure:**  
> StokVigil AI (`com.app.stokvigil`) is a quantitative financial technology research and surveillance engine. It is **NOT** a registered Investment Adviser (IA) or Research Analyst (RA) with the Securities and Exchange Board of India (SEBI).  
> 
> * **No Financial Advice:** The information, alerts, technical calculations, and Camarilla pivot levels surfaced by this application are algorithmic volatility benchmarks based on publicly available market information and mathematical formulas. They do not constitute investment advice, financial recommendations, or price guarantees.
> * **Risk of Capital Loss:** Equities and derivative products are subject to market risks. Past backtested performance is no guarantee of future results. Users are advised to exercise independent discretion and consult certified financial planners before deploying capital.

---

<div align="center">
Built with precision for the Indian Financial Markets 🇮🇳
</div>
