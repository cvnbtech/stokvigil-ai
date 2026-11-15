<div align="center">

# ⚡ StokVigil AI
### Institutional Quantitative Equity Surveillance & Automated Demat Risk Engine

**Stop gambling on speculative tips. Trade alongside institutional order flow with mathematical certainty.**

[![Architecture](https://img.shields.io/badge/Architecture-4--Pillar%20Confluence-00E5FF?style=for-the-badge&logo=diagramsdotnet&logoColor=white)](#-full-stack-system-architecture)
[![Backend](https://img.shields.io/badge/FastAPI-Python%203.11+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](#-tech-stack)
[![Web](https://img.shields.io/badge/Next.js%2014-App%20Router-black?style=for-the-badge&logo=next.js&logoColor=white)](#-tech-stack)
[![Mobile](https://img.shields.io/badge/Flutter-Dart%203.3+-02569B?style=for-the-badge&logo=flutter&logoColor=white)](#-tech-stack)
[![Database](https://img.shields.io/badge/Supabase-PostgreSQL%2015+-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](#-tech-stack)
[![Compliance](https://img.shields.io/badge/SEBI-Non--Advisory%20Mandate-2E7D32?style=for-the-badge&logo=checkmarx&logoColor=white)](#-regulatory-disclaimer)

[Explore Features](#-key-features) • [Full-Stack Architecture](#-full-stack-system-architecture) • [Live Flow](#-sequence-diagram) • [Quickstart Guide](#-installation-steps) • [Audit Ledger](#-100-transparent-audited-accuracy-ledger)

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
* **Classic Camarilla Breakout Boundaries:** Mathematical intraday volatility benchmarks derived from prior-day True Range ($H_4$ breakout, $H_3$ resistance, $L_3$ support, $L_4$ protective stop).
* **VWAP Statistical Dispersion Bands:** Identifies overbought exhaustion ($+2\sigma$) and deep value value zones ($-2\sigma$) dynamically anchored to volume.
* **John Carter's TTM Squeeze:** Captures explosive directional thrusts by tracking Bollinger Band (20, 2.0) compression inside Keltner Channels (20, 1.5 ATR).
* **Midday-Hardened RVOL Engine:** Automatically detects liquidity troughs between 11:45 and 13:15 IST, rejecting false breakouts lacking 3.0x volume confirmation.
* **Wyckoff Volume Spread Analysis (VSA):** Compares Close Location Quotient ($CLQ = \frac{Close - Low}{High - Low}$) against delivery bhavcopy percentages to separate genuine smart-money accumulation from operator churn.

### 2. 💼 5-State Demat Portfolio Risk Lifecycle
Your connected Demat holdings (ICICI Direct, Dhan, Angel One) are continuously guarded by an asymmetric risk manager:
* 🔴 **`CAPITAL_PRESERVATION_EXIT`:** Immediate alert when price breaches $L_4$ breakdown or drops $>8\%$ below your average buy price.
* 🟡 **`DEFENSIVE_TRIM_ALERT`:** Recommends banking 50% profit at Target 1 ($H_4$) and moving your protective stop-loss to cost basis.
* 🟢 **`TRAILING_SL_ALERT`:** Chandelier ATR trailing stops automatically ratchet upwards as the stock advances into profit.
* 🔵 **`ACCUMULATE_WATCH`:** Permits pyramiding strictly on winning positions displaying institutional delivery absorption.
* ⚪ **`HOLD_STEADY`:** Healthy trend progression within normal volatility bounds.

### 3. ⚖️ SEBI-Compliant Execution Guardrails
* **Mandatory Stop-Loss Limit (SL-L) Routing:** In accordance with SEBI risk circulars, Stop-Loss Market (SL-M) orders are completely barred to eliminate freak-trade execution slippage.
* **Dynamic Exchange Tick Snapping:** Automatically rounds prices and trigger limits to exchange rules (₹0.05 for stocks $\ge ₹250$; ₹0.01 for stocks $< ₹250$).
* **Pre-Trade Circuit Freeze Rejections:** Halts BUY orders on Upper Circuit freeze and SELL orders on Lower Circuit freeze before broker routing.
* **Dynamic CNC vs. MIS Short Detection:** If you sell a stock not present in your Demat holdings, StokVigil routes the order as Intraday Margin (MIS) and issues a statutory warning regarding 03:15 PM IST square-off and potential 20% auction penalty risks.
* **Financial-Grade Idempotency Debouncing:** Bounded in-memory lock prevents accidental double-tap orders via custom `X-Idempotency-Key` or automatic request fingerprinting.

### 4. 📜 100% Transparent Audited Accuracy Ledger
Unlike platforms that delete bad calls, StokVigil AI permanently writes every emitted signal to an immutable ledger (`/api/market/accuracy-ledger`). Subsequent market candles are evaluated to independently measure Target 1 hit rates, trailing stop exits, and overnight gap slippage.

---

## 🏗️ Full-Stack System Architecture

StokVigil AI is structured as a decoupled, multi-tiered full-stack architecture engineered for sub-millisecond execution, zero developer credential leakage, and 100% free-tier cloud viability.

### 1. Full-Stack Layered Topology

```mermaid
flowchart TD
    subgraph ClientLayer ["1. Presentation & Client Tier"]
        WEB["Next.js 14 Web Portal<br/>(React 18, Tailwind CSS, TypeScript)<br/>TradingView Lightweight Charts | Confluence Radar"]
        MOBILE["Flutter Cross-Platform Mobile App<br/>(Dart 3.3+, Android & iOS)<br/>Provider State | Biometric Auth | Push Notifications"]
    end

    subgraph GatewaySecurity ["2. Ingress, Security & Gateway Tier"]
        HTTPS_WSS["HTTPS / WSS (Cloudflare / Cloud Run Ingress)"]
        AUTH_IDOR["JWT Verification & IDOR Access Validation<br/>(verify_user_access & auth.uid enforcement)"]
        RATE_LIMIT["Token Bucket Rate Limiting & Proxy Guards<br/>(check_rate_limit & trusted proxies)"]
        VAULT["Fernet AES-256 Cryptographic Vault<br/>(PBKDF2HMAC SHA-256 Key Derivation + Salt)"]
    end

    subgraph AppServer ["3. FastAPI Backend Application Tier (Python 3.11+)"]
        FASTAPI["FastAPI Lifespan Context Manager<br/>Async Uvicorn Workers | Defensive Security Headers"]
        ROUTERS["REST API Routers<br/>/stocks | /orders | /market | /auth | /cron"]
        AGENT_LOOP["5-Minute Multi-Tenant Agent Runner<br/>Deduplicated Scanning & Portfolio Evaluator"]
        TICK_WORKER["Market Hours Real-Time Tick Worker<br/>(worker.py - 2.0s Dual-Tier Synchronization)"]
    end

    subgraph ComputeEngine ["4. Quantitative Mathematical & AI Processing Tier"]
        TECH_VEC["1,417-Line Vectorized Technical Engine<br/>Camarilla Pivots (H4/H3/L3/L4) | VWAP ±1σ/±2σ Bands<br/>TTM Squeeze | ADX 14 | Midday-Hardened RVOL | Mansfield RS"]
        FLOW_VSA["Derivatives & Order Flow Engine<br/>Wyckoff VSA Absorption (CLQ) | NSE Delivery Bhavcopy<br/>Option Chain PCR & Max Pain Strike | Delta-OI Velocity"]
        CONFLUENCE_VETO["Adaptive 4-Pillar Confluence Engine<br/>Regime Weights | 6 Hard Institutional Vetoes<br/>5-State Demat Portfolio Risk Lifecycle"]
        GEMINI_AI["Gemini 3.5 Flash Lite Qualitative AI Engine<br/>google-genai SDK | 15 Calls/Scan Quota Limiter<br/>Mathematical Sovereignty (Numbers Hard-Locked by Python)"]
    end

    subgraph StateStorage ["5. High-Speed State & Database Tier"]
        RAM_TIER["Tier-1 Process RAM Cache<br/>(&lt;0.01ms Access | FIFO Bounded to 2,000 Symbols)"]
        UNLOGGED_TIER["Tier-2 Supabase UNLOGGED Table<br/>(market_memory_cache | Bypasses WAL Disk I/O | &lt;0.8ms Access)"]
        PGBOUNCER["PgBouncer Pool (Port 6543, Transaction Mode)<br/>statement_cache_size=0 | Advisory Locks (987654321)"]
        SUPABASE_PG["Supabase PostgreSQL 15+ Engine<br/>Row Level Security (RLS) with (SELECT auth.uid()) InitPlan Cache<br/>profiles | user_credentials | user_watchlists | stok_alerts"]
    end

    subgraph ExternalBrokers ["6. External Broker & Market Infrastructure"]
        BROKERS["Multi-Broker Adapter Framework<br/>ICICI Direct Breeze Connect | Dhan HQ v2 | Angel One SmartAPI<br/>SEBI SL-M Order Prohibition | Dynamic Tick Snap (₹0.05/₹0.01)"]
        MARKET_FEEDS["Official Market Feeds & Registries<br/>NSE Security-Wise Bhavcopy | NSE Option Chain | FII/DII Cash<br/>Yahoo Finance Pooled Keep-Alive HTTP | BSE Scrip API"]
        DISPATCH["High-Priority Notification Dispatcher<br/>Persistent HTTP/2 Telegram Client (25 msg/s Leaky Bucket)<br/>Firebase Cloud Messaging (FCM Push)"]
    end

    %% Client to Ingress
    WEB --> HTTPS_WSS
    MOBILE --> HTTPS_WSS
    HTTPS_WSS --> AUTH_IDOR
    AUTH_IDOR --> RATE_LIMIT
    RATE_LIMIT --> FASTAPI

    %% App Server to Engines & State
    FASTAPI --> ROUTERS
    ROUTERS --> AGENT_LOOP
    ROUTERS --> VAULT
    AGENT_LOOP --> TECH_VEC
    AGENT_LOOP --> FLOW_VSA
    TECH_VEC --> CONFLUENCE_VETO
    FLOW_VSA --> CONFLUENCE_VETO
    CONFLUENCE_VETO -- "Tier-1 Active Catalysts" --> GEMINI_AI

    %% State & Persistence
    FASTAPI <--> RAM_TIER
    TICK_WORKER <--> RAM_TIER
    RAM_TIER <--> UNLOGGED_TIER
    ROUTERS <--> PGBOUNCER
    AGENT_LOOP <--> PGBOUNCER
    PGBOUNCER <--> SUPABASE_PG

    %% Execution & External
    ROUTERS --> BROKERS
    AGENT_LOOP --> DISPATCH
    TECH_VEC <--> MARKET_FEEDS
    FLOW_VSA <--> MARKET_FEEDS
    BROKERS <--> MARKET_FEEDS
    DISPATCH --> WEB
    DISPATCH --> MOBILE
```

### 2. Full-Stack Layer Responsibility Matrix

| Full-Stack Tier | Components & Technologies | Key Responsibilities & Guarantees |
| :--- | :--- | :--- |
| **Presentation Tier** | **Next.js 14 App Router** (React 18, Tailwind CSS, TypeScript)<br/>**Flutter SDK 3.19+** (Dart 3.3+, Provider, Biometrics) | Interactive TradingView Lightweight candlestick canvases, 4-pillar confluence radars, transparency audit ledgers, 1-click trade execution modals, Demat holdings synchronization, and real-time push alerts. |
| **Ingress & Security Tier** | **FastAPI Middleware**, Pydantic v2 Settings, **Fernet AES-256 Vault**, JWT Bearer Auth | Enforces zero trust: client-side IDOR access validation (`verify_user_access`), memory-bounded token bucket rate limiting, HTTP security headers (HSTS, CSP, X-Frame-Options), and PBKDF2HMAC encrypted credential storage. |
| **Application Server Tier** | **FastAPI Async Engine**, Uvicorn ASGI, Lifespan Context Manager, **PgBouncer Async Pool** | Multi-tenant 5-minute automated scanning orchestrator, 2-second market-hours tick worker (`worker.py`), persistent thread pools for non-blocking I/O, and REST API routing for quotes, backtests, and broker orders. |
| **Quantitative & AI Tier** | **NumPy & Pandas Vectorized Engine (1,417 LOC)**, SciPy, **Gemini 3.5 Flash Lite** (`google-genai` SDK) | Computes Camarilla equations ($H_4/H_3/L_3/L_4$), VWAP dispersion bands ($\pm 1\sigma, \pm 2\sigma$), TTM Squeeze, Wyckoff VSA delivery absorption, 6 Hard Institutional Vetoes, 5-state portfolio lifecycles, and qualitative AI contextual synthesis under strict mathematical sovereignty. |
| **State & Persistence Tier** | **Dual-Tier Cache** (Process RAM + Supabase `UNLOGGED` Table), **Supabase PostgreSQL 15+** | Sub-millisecond market state (<0.01ms in RAM, <0.8ms in UNLOGGED table bypassing WAL disk I/O), PgBouncer transaction-mode pooling (Port 6543) with `statement_cache_size=0`, Postgres advisory locking (`pg_try_advisory_lock`), and `(SELECT auth.uid())` InitPlan optimized RLS. |
| **External & Execution Tier** | **Broker Adapters** (ICICI Breeze, Dhan HQ, Angel One), **Telegram HTTP/2 Client**, FCM, NSE Feeds | Automated order placement with SEBI Stop-Loss Market (SL-M) order prohibition, dynamic tick snapping (₹0.05 / ₹0.01), pre-trade circuit freeze rejections, dynamic CNC/MIS short detection, and 25 msg/s leaky-bucket Telegram alert dispatch. |

---

### 3. End-to-End Market Data & Execution Pipeline

StokVigil AI operates across six decoupled tiers engineered for sub-millisecond execution on 100% free-tier cloud resources (zero paid Redis):

```mermaid
flowchart TD
    subgraph DataIngestion ["1. Real-Time & EOD Market Data Ingestion"]
        NSE_BHAV["NSE Security-Wise Delivery Bhavcopy<br/>(4-Day Rolling History & Absorption)"]
        NSE_FO["NSE Derivatives Registry<br/>(fo_mktlots.csv & Option Chain)"]
        FII_DII["NSE FII/DII Daily Cash Turnover"]
        YAHOO["Yahoo Finance High-Concurrency<br/>Keep-Alive HTTP Pool (5m, 15m, Daily)"]
        BSE_API["BSE Scrip Master & API Fallback"]
        RSS_NEWS["Google News RSS / Regulatory Disclosures"]
        BROKER_FEED["Broker WebSocket Ticker Stream<br/>(Breeze / Dhan / Angel One)"]
    end

    subgraph StateTier ["2. Dual-Tier Market Memory & Persistence"]
        RAM_CACHE["Tier-1 Process RAM Cache<br/>(&lt;0.01ms Access, FIFO Bounded to 2,000 Symbols)"]
        UNLOGGED_TBL["Tier-2 Supabase UNLOGGED Table<br/>(market_memory_cache, Bypasses WAL Disk I/O)"]
        PGBOUNCER["PgBouncer Pool (Port 6543, Transaction Mode)<br/>statement_cache_size=0 | Advisory Locks"]
        POSTGRES["PostgreSQL Engine (Supabase)<br/>InitPlan Optimized RLS: (SELECT auth.uid()) = user_id"]
    end

    subgraph CoreEngines ["3. Quantitative Technical & Confluence Engines"]
        TECH_ENG["Vectorized Technical Engine (1,400+ LOC)<br/>Camarilla H4/H3/L3/L4, VWAP ±1σ/±2σ,<br/>Wilder RSI, MACD, TTM Squeeze, ADX 14,<br/>Midday-Hardened RVOL, Mansfield RS, 15m ORB"]
        FLOW_ENG["Order Flow & Derivatives Tracker<br/>Wyckoff VSA Absorption, PCR & Max Pain Strike,<br/>Delta-OI Velocity, Institutional Delivery %"]
        MACRO_ENG["Macro Filter & Regime Classifier<br/>Advance-Decline Breadth, Sector Momentum,<br/>India VIX & NIFTY Trend, 09:00 AM War Room"]
        CONFLUENCE["Adaptive 4-Pillar Confluence Engine<br/>Regime Weights, Veto Filters, Tactical Levels,<br/>5-State Demat Portfolio Lifecycle Manager"]
    end

    subgraph AITier ["4. AI Tier (Mathematical Sovereignty)"]
        GEMINI["Gemini 3.5 Flash Lite Engine (google-genai SDK)<br/>15 Calls/Scan Quota Limiter | Qualitative Rationale Only<br/>&lt;untrusted_external_news&gt; Prompt Injection Defense"]
    end

    subgraph ExecutionDispatch ["5. Dispatch, Anti-Fatigue & Order Routing"]
        AGENT_RUNNER["5-Minute Multi-Tenant Agent Runner<br/>Step 1: Union Deduplicated Pre-computation<br/>Step 2: User Demat Confluence Evaluation"]
        ALERT_LIMITER["Anti-Fatigue Cooldown Manager<br/>(45-Minute Cooldown, Tier-1 Catalyst Bypass)"]
        NOTIFIER["Notification Dispatcher<br/>Telegram HTTP/2 (25 msg/s Leaky Bucket)<br/>Firebase Cloud Messaging (FCM Push)"]
        ORDER_ROUTER["Multi-Broker Order Execution Router<br/>SEBI SL-M Ban Enforcement, Dynamic Tick Snap,<br/>Idempotency Lock, Dynamic CNC/MIS Short Detection"]
    end

    subgraph Clients ["6. Multi-Platform Client Applications"]
        WEB_PORTAL["Next.js 14 Web Portal (App Router)<br/>TradingView Lightweight Charts, Confluence Radar,<br/>Trade Modal, Transparency Audit Ledger, Backtester"]
        MOBILE_APP["Flutter Mobile App (Android/iOS)<br/>Provider State, Supabase Client, FCM,<br/>Candle Chart Modals, Live Demat Sync"]
    end

    %% Wiring Ingestion to Processing
    NSE_BHAV --> FLOW_ENG
    NSE_FO --> FLOW_ENG
    FII_DII --> MACRO_ENG
    YAHOO --> TECH_ENG
    BSE_API --> TECH_ENG
    RSS_NEWS --> GEMINI
    BROKER_FEED --> RAM_CACHE

    %% State Synchronization
    RAM_CACHE <--> UNLOGGED_TBL
    PGBOUNCER <--> POSTGRES
    AGENT_RUNNER <--> PGBOUNCER

    %% Processing Flow
    TECH_ENG --> CONFLUENCE
    FLOW_ENG --> CONFLUENCE
    MACRO_ENG --> CONFLUENCE
    CONFLUENCE --> AGENT_RUNNER
    AGENT_RUNNER -- "Tier-1 Active Catalysts Only" --> GEMINI
    GEMINI --> AGENT_RUNNER

    %% Dispatch Flow
    AGENT_RUNNER --> ALERT_LIMITER
    ALERT_LIMITER --> NOTIFIER
    NOTIFIER --> Clients
    Clients --> ORDER_ROUTER
    ORDER_ROUTER --> BROKER_FEED
```

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
| **Web Portal** | **Next.js 14 (App Router), Tailwind CSS** | TradingView Lightweight Charts, Confluence Radar, interactive backtester, and Demat sync dashboard. |
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
│   │   │   ├── deterministic.py            # 4-Pillar Confluence & Hard Veto Gatekeepers
│   │   │   ├── gemini_ai.py                # Gemini SDK pipeline with quota management
│   │   │   ├── portfolio_sync.py           # Demat holding & cost-basis synchronizer
│   │   │   ├── security_master.py          # O(1) RAM ISIN & Scrip Code Resolver
│   │   │   └── ticker_stream.py            # WebSocket real-time tick processor
│   │   ├── routers/                        # API Endpoints
│   │   │   ├── auth.py                     # Profiles, credentials & Demat holdings
│   │   │   ├── cron.py                     # Scheduled scanning & briefing pipelines
│   │   │   ├── market.py                   # Backtesting, FII/DII, accuracy ledger
│   │   │   ├── orders.py                   # Idempotent broker trade routing
│   │   │   └── stocks.py                   # Quotes, searches, candle history
│   │   ├── schemas/                        # Pydantic v2 Models & Tick Snapping
│   │   ├── accuracy_verifier.py            # Historical OHLCV alert performance verifier
│   │   ├── agent_runner.py                 # Multi-tenant 5-minute scanning engine
│   │   ├── alert_limiter.py                # 45-minute anti-fatigue cooldown manager
│   │   ├── auth.py                         # JWT verification & IDOR security guards
│   │   ├── backtester.py                   # Vectorized historical backtest engine
│   │   ├── config.py                       # Pydantic BaseSettings environment loader
│   │   ├── db_pool.py                      # PgBouncer async connection pool manager
│   │   ├── fii_dii_tracker.py              # NSE FII/DII cash turnover scraper
│   │   ├── flow_tracker.py                 # NSE delivery bhavcopy & option chain parser
│   │   ├── macro_filter.py                 # Advance-Decline breadth & pre-market briefing
│   │   ├── market_cache.py                 # Dual-Tier RAM / UNLOGGED Table Manager
│   │   ├── notifications.py                # Telegram HTTP/2 (25 msg/s) & FCM Notifier
│   │   ├── technical_engine.py             # 1,417-line vectorized indicator engine
│   │   ├── vault.py                        # Fernet AES-256 cryptographic vault
│   │   └── worker.py                       # Standalone 2-second market hours tick worker
│   ├── tests/                              # Comprehensive Pytest Suite (20+ test files)
│   ├── requirements.txt                    # Python runtime dependencies
│   └── Dockerfile                          # Cloud Run container definition
├── supabase/                               # Database Schemas & Migrations
│   └── migrations/                         # SQL migration history (August - November 2026)
├── web_portal/                             # Next.js 14 Web Portal
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

# 5. Test Dual-Tier UNLOGGED Cache Performance
pytest tests/test_unlogged_cache.py

# 6. Generate Complete Test Coverage Report
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
