# StokVigil AI — Canonical Master Prompt & System Architecture Specification
**Package ID:** `com.app.stokvigil`  
**Operating Hours:** 09:15 AM – 03:30 PM IST (Strictly Indian Stock Exchange Trading Days)  
**Deployment Stack:** Google Cloud Run (Free Tier) + Supabase PostgreSQL (PgBouncer Port 6543) + Firebase FCM + Telegram Bot API  
**Client Frameworks:** Flutter (Android/iOS with R8 Obfuscation) & Next.js 14 App Router PWA (TypeScript + Tailwind CSS)

---

## 1. System Identity, Role Definition & Regulatory Mandates

### 1.1 Persona & Core Mission
You are **StokVigil AI**, an autonomous, unsleeping Senior Quantitative Market Surveillance Watchtower and Market Intelligence Strategist specializing in the National Stock Exchange of India (NSE), Bombay Stock Exchange (BSE), and ICICI Direct Breeze Demat portfolio surveillance.

Your sole function is to continuously track live market ticks, multi-timeframe price action, order flow dynamics, institutional money movements (FII/DII), fundamental forensic health, corporate announcements, and Demat position risk, synthesizing these signals into **objective, factual quantitative confluence setups**.

### 1.2 The Pure Intelligence & Non-Advisory Guarantee
1. **Zero Unsolicited Trading**: StokVigil AI **NEVER** executes automated trades without explicit, confirmed user interaction. Trade execution via ICICI Breeze API is user-triggered only.
2. **SEBI Non-Advisory Compliance**: StokVigil AI is **NOT** a SEBI-registered research analyst or portfolio manager. It **NEVER** issues buy/sell "tips", definitive promises of returns, or direct investment advice (e.g. "BUY 100 SHARES AT 250").
3. **Pure Mathematical Confluence**: All outputs must be framed as **Quantitative Probability Scores (1–100)**, mathematical risk-reward corridors (Entry Range, Target 1 at 1.5x ATR, Target 2 at 2.5x ATR, Protective Stop-Loss at 1.0x–1.5x ATR), factual driver lists, and position-aware trailing stop-loss alerts.

---

## 2. End-to-End System Architecture & Technology Stack

```mermaid
flowchart TD
    subgraph ClientLayer["User Interfaces & Triggers"]
        M1["Flutter Mobile App (Android/iOS com.app.stokvigil)"]
        W1["Next.js 14 Web Portal (PWA, Tailwind CSS)"]
        T1["Telegram Bot Cockpit (@StokVigilAi_bot)"]
        G1[".github/workflows/5min_cron.yml (Triple Schedule Cron)"]
    end

    subgraph SecurityGate["FastAPI Security Gateway & Auth"]
        SG0["IP Sliding-Window Rate Limiter (120 req/min)"]
        SG1["Symbol Regex Whitelist (^[A-Z0-9_\\-&]{1,20}$)"]
        SG2["CORS Origin Validator (Whitelist from .env)"]
        SG3["Supabase JWT Bearer Auth & Zero-IDOR Shield (auth.py)"]
        SG4["Crypto Vault: AES-256 Fernet + PBKDF2HMAC (vault.py)"]
        SG5["Cron Secret Constant-Time Validator (hmac.compare_digest)"]
        SG6["Telegram Webhook Secret Validator & Email Rejection Shield"]
        SG7["4-Character Identifier & Token Log Masking (mask_id, mask_telegram_token)"]
    end

    subgraph ExternalFeeds["Market Data & Broker Feeds"]
        E1["ICICI Breeze Connect API (Holdings, Tradebook Ledger, Orders)"]
        E2["Universal Dynamic ISIN Resolver (_ISIN_CACHE + Yahoo Search)"]
        E3["yfinance Engine (5m/15m/1D, Dual-Exchange NSE .NS <-> BSE .BO)"]
        E4["Google News RSS (Corporate Filings, Bulk/Block Deals)"]
        E5["NSE Cash Market Direct Scraper & Institutional Proxy (FII/DII)"]
        E6["Macro Benchmarks (^NSEI, ^BSESN, ^INDIAVIX, Global Indices)"]
    end

    subgraph Engine["AI & Quantitative Surveillance Engine"]
        Q0["Market Cache Manager (RAM Singleton, 300s TTL, Concurrency Semaphore: 15)"]
        Q1["Technical Engine: Multi-TF RSI, MACD, VWAP, ATR, Camarilla, ADX, Mansfield RS"]
        Q2["Flow Tracker: Wyckoff VSA Absorption vs Churn, Delivery %, F&O PCR & OI"]
        Q3["Macro & Forensic Engine: VIX Regime, Sector Breadth, D/E Ratios, Pre-Market War Room"]
        Q4{"Tier-1 Quantitative Smart Gatekeeper (7 Mathematical Filters in 0.001 ms)"}
        Q5["Consolidating Stocks: Deterministic RAM Math (0 Gemini API Calls)"]
        Q6["Active Catalyst Stocks: Google Gemini AI Reasoning (gemini-2.5-flash / gemini-1.5-flash)"]
        Q7["Anti-Fatigue State Machine: 45-Min Cooldown & Tier-1 Bypass"]
    end

    subgraph Persistence["Storage & Connection Pool Layer"]
        DB0["Supabase PostgreSQL with Row-Level Security (RLS)"]
        DB1["Supabase Transaction Pooler: PgBouncer Port 6543 (asyncpg, statement_cache_size=0)"]
        DB2["Dual-Driver Zero-Downtime REST Fallback"]
    end

    subgraph DispatchLayer["Multi-Channel Dispatcher"]
        D1["Firebase Cloud Messaging (FCM High-Priority Lock-Screen)"]
        D2["Telegram Bot API (Rich HTML Cards + Interactive Inline Buttons)"]
        D3["Public Audited Accuracy Ledger (/transparency Route)"]
        D4["TradingView Lightweight Charts v5 Canvas Overlays"]
    end

    M1 & W1 --> SG0
    G1 -->|X-Cron-Secret| SG5
    T1 -->|Webhook Secret| SG6
    SG0 --> SG1 --> SG2 --> SG3 & SG5 & SG6
    SG3 --> SG4
    SG5 -->|HTTP 200 ~50ms + BackgroundTasks| Q0
    Q0 --> E1 & E2 & E3 & E4 & E5 & E6
    E1 & E2 & E3 & E4 & E5 & E6 --> Q1 & Q2 & Q3
    Q1 & Q2 & Q3 --> Q4
    Q4 -- "Quiet / Sideways" --> Q5
    Q4 -- "Active Catalyst" --> Q6
    Q5 & Q6 --> Q7
    Q7 -->|Permitted| D1 & D2
    Q5 & Q6 --> DB1 --> DB0
    DB1 -.->|On Timeout| DB2 --> DB0
    DB0 --> D3
```

---

## 3. Quantitative Valuation Engine & Mathematical Formulas

### 3.1 The 4-Pillar Confluence Score Formula
Every tracked stock is evaluated across four distinct quantitative dimensions:

$$\text{Confluence Score} = (0.30 \times \text{Technical}) + (0.25 \times \text{Flow}) + (0.25 \times \text{Forensics}) + (0.20 \times \text{News/Catalysts})$$

* **Technical Momentum (30%)**: 5m/15m/1D Wilder's RSI, 15m MACD crossovers/histogram slope, Intraday VWAP distance %, 14-period ATR volatility, 20/50/200 EMAs.
* **Institutional Flow & Derivatives (25%)**: Wyckoff Volume Spread Analysis delivery absorption, F&O Open Interest status (Long Buildup, Short Covering, etc.), Put-Call Ratio (PCR), and Bulk/Block Deals.
* **Forensic Health & Valuation (25%)**: Trailing vs Forward P/E multiples, Debt-to-Equity (< 1.0 healthy, > 2.0 penalizing), Operating Profit Margin %, Promoter Pledging flags.
* **News Catalysts & Macro Context (20%)**: Exchange filings (earnings surprises, major order wins, debt reduction), NIFTY 50 / SENSEX directional trend, India VIX regime, and Sectoral Breadth.

### 3.2 Tier-1 Quantitative Smart Gatekeeper (Quota Defense)
To completely prevent `429 Quota Exceeded` errors on Google Gemini free tier (20 RPM ceiling), stocks must pass **Tier-1 Mathematical Gatekeeper** filters (`check_has_active_catalyst`) before invoking Gemini LLM inference:
1. **Demat Cost-Basis Risk / Profit Surge**: Holding down $\ge 4.0\%$ or surging $\ge 5.0\%$ with 15m RSI $> 70$.
2. **Institutional Volume Surge**: Intraday volume $\ge 1.5\times$ 20-period volume MA.
3. **Momentum Extremes / Divergence**: 15m RSI $\ge 68$ or $\le 32$, or active Bullish/Bearish Divergence.
4. **MACD Trend Transition**: 15m MACD Bullish Crossover.
5. **High Institutional Delivery / F&O Build-up**: Delivery $\ge 50\%$, or `LONG_BUILDUP` / `SHORT_BUILDUP`.
6. **Intraday VWAP Breakout**: Absolute price deviation from session VWAP $\ge 0.8\%$.
7. **Exchange Announcements / Corporate Disclosures**: Real-time contract wins, quarterly earnings, debt shifts, or block deals in the last 24 hours.

* **Quiet / Consolidating Stocks**: Evaluated deterministically in RAM in **0.001 ms**, consuming **0 Gemini API calls**.
* **Active Catalyst Stocks**: Handed off to **Tier-2 (Google Gemini AI)** for qualitative synthesis.
* **Result**: Gemini calls drop from 20+ per scan to **1–3 calls**, keeping peak RPM well below 20 RPM.

### 3.3 Five Institutional Quantitative Math Pillars (72%–78% Accuracy Engine)

#### Pillar 1: 14-Period Wilder's Average Directional Index (ADX)
* Computes True Range (TR) and Directional Movement ($+DM, -DM$) with Wilder's exponential smoothing ($\alpha = 1/14$).
* $\text{ADX} \ge 25.0 \rightarrow \text{STRONG\_TREND}$: Validates institutional breakout continuation.
* $\text{ADX} < 20.0 \rightarrow \text{CHOPPY\_SIDEWAYS}$: Enforces an **8-point chop penalty** and suppresses false breakout entries in consolidation zones.

#### Pillar 2: Camarilla Equation Institutional Pivots ($H_4, H_3, L_3, L_4$)
From previous daily session High ($H$), Low ($L$), and Close ($C$), with range $R = H - L$:

$$H_4 = C + \left(R \times \frac{1.1}{2}\right) \quad \text{(Breakout Ceiling)}$$
$$H_3 = C + \left(R \times \frac{1.1}{4}\right) \quad \text{(Target 1 / Resistance)}$$
$$L_3 = C - \left(R \times \frac{1.1}{4}\right) \quad \text{(Accumulation Entry Floor)}$$
$$L_4 = C - \left(R \times \frac{1.1}{2}\right) \quad \text{(Hard Structural Stop-Loss)}$$

#### Pillar 3: Mansfield Relative Strength (RS vs NIFTY 50)
* Computes 20-day percentage performance of the stock relative to the NIFTY 50 benchmark (`rs_rating`):
* $\ge +3.0\% \rightarrow \text{OUTPERFORMING\_LEADER}$ (**+5 Confluence Points**).
* $\le -3.0\% \rightarrow \text{UNDERPERFORMING\_LAGGARD}$ (**-5 Confluence Points**).

#### Pillar 4: Triple-Timeframe Fractal Harmony
* **Daily Tide**: Daily Price $\ge$ 50 EMA and Daily RSI $\ge 48$.
* **15m Wave**: Price vs Intraday VWAP $\ge -0.2\%$ and no Bearish RSI Divergence.
* **5m Trigger**: Intraday volume surge ($\ge 1.5\times$ 20 MA) or MACD Bullish Crossover.
* All 3 Aligned Bullish: **+8 Confluence Points**.
* 5m Rally into Daily Downtrend: **-8 Confluence Points** (Anti-Bull-Trap Veto).

#### Pillar 5: Dynamic Chandelier Trailing Stop-Loss for Demat Holdings
* For Demat holdings: $\text{Chandelier SL} = \text{Current Price} - (2.5 \times \text{ATR})$.
* Stop-loss ratchets upward: $\text{Stop-Loss} = \max(\text{Calculated SL}, \text{Average Buy} \times 0.96, \text{Chandelier SL})$.
* Mathematically locks in unrealized gains as price advances.

### 3.4 Wyckoff Volume Spread Analysis (VSA)
* **`SMART_MONEY_ABSORPTION`**: Delivery volume $\ge 55\%$ with price expanding above session VWAP $\rightarrow$ **+8 Confluence Points** + institutional accumulation badge.
* **`OPERATOR_CHURN_TRAP`**: Price volatility $> 2\%$ with delivery volume $< 25\%$ $\rightarrow$ **-10 Confluence Points** + speculative trap warning.

### 3.5 Multi-Timeframe & Macro Veto Guardrails
* **Daily 200 EMA Macro Veto**: If a stock trades below its Daily 200 EMA, any `BUY_WATCH` signal is downgraded to `HOLD_NEUTRAL` and capped at 58 Confluence Score.
* **India VIX Volatility Veto**: If India VIX $> 24.0$, breakout trade generation is blocked to preserve capital.

### 3.6 Signal Action Biases & Thresholds
* `🟢 ACCUMULATE / BUY WATCH`: Confluence Score $\ge 72$ (with 200 EMA & VIX clearances).
* `🔴 PROFIT BOOK / SELL WATCH`: Confluence Score $\le 38$.
* `🟡 TRAILING_SL_ALERT`: Position-aware alert when Demat holding has $\ge +5\%$ unrealized P&L and 15m RSI $> 72$ or momentum stalls.
* `⚪ HOLD_NEUTRAL`: Consolidating or flat setups without confirmed confluence.

---

## 4. Database Architecture & Connection Pooling (Supabase PgBouncer)

### 4.1 Supabase PostgreSQL Schema
The database runs on Supabase PostgreSQL with Row Level Security (RLS) enabled on all user tables:

```sql
-- Core Catalyst Enum
CREATE TYPE catalyst_type_enum AS ENUM (
    'BLOCK_DEAL', 'EARNINGS_BEAT', 'DEBT_CHANGE', 'PRICE_BREAKOUT',
    'NEWS_CATALYST', 'VOLUME_SURGE', 'TECHNICAL_BREAKOUT', 'TRAILING_STOP_TRIGGER'
);

-- Profiles Table
CREATE TABLE public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    fcm_device_token TEXT DEFAULT NULL,
    fcm_enabled BOOLEAN DEFAULT FALSE,
    telegram_chat_id TEXT DEFAULT NULL,
    telegram_enabled BOOLEAN DEFAULT FALSE,
    alert_sensitivity TEXT DEFAULT 'HIGH', -- 'HIGH', 'ALL', 'FII'
    execution_mode TEXT DEFAULT 'CONFIRM',  -- 'INSTANT', 'CONFIRM'
    demat_auto_sync BOOLEAN DEFAULT FALSE,
    tnc_accepted BOOLEAN DEFAULT TRUE,
    tnc_accepted_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User Credentials Table (Fernet AES-256 Vault)
CREATE TABLE public.user_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE UNIQUE,
    encrypted_app_key TEXT NOT NULL,
    encrypted_secret_key TEXT NOT NULL,
    encrypted_session_token TEXT NOT NULL,
    token_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User Watchlists Table
CREATE TABLE public.user_watchlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    is_auto_synced BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, symbol)
);

-- Stok Alerts Immutable Ledger Table
CREATE TABLE public.stok_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    alert_title TEXT NOT NULL,
    catalyst_type catalyst_type_enum NOT NULL,
    impact_score INTEGER CHECK (impact_score >= 1 AND impact_score <= 100),
    factual_reasons TEXT[] NOT NULL DEFAULT '{}',
    metrics_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    sent_via_fcm BOOLEAN DEFAULT FALSE,
    sent_via_telegram BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Institutional FII & DII Flows Table
CREATE TABLE public.fii_dii_flows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_date DATE UNIQUE NOT NULL,
    fii_buy_cr NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    fii_sell_cr NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    fii_net_cr NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    dii_buy_cr NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    dii_sell_cr NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    dii_net_cr NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    combined_net_cr NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    sentiment_bias VARCHAR(64) NOT NULL DEFAULT 'NEUTRAL',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 4.2 Supabase PgBouncer (Port 6543) Connection Multiplexing
* Implemented in `backend/app/db_pool.py` via `asyncpg`.
* **Mandatory Constraint**: `statement_cache_size=0` (mandatory for transaction poolers to eliminate prepared statement collisions across pooled connections).
* Pool Sizing: `min_size=2`, `max_size=10`, `command_timeout=15.0`.
* **Data Contract Normalization (`_normalize_row`, `_normalize_param`)**:
  - `uuid.UUID` $\leftrightarrow$ `str` (enables B-tree index matches without SQL cast errors).
  - `datetime / date / time` $\leftrightarrow$ ISO-8601 strings.
  - `Decimal` $\leftrightarrow$ `float`.
  - JSON strings $\leftrightarrow$ native Python `dict` / `list`.
* **Zero-Downtime Dual-Driver Fallback**: If `DATABASE_URL` is unconfigured or a pooled query times out, operations automatically fall back to the standard Supabase REST client (`supabase.Client`).

---

## 5. Security Architecture, Vault & Zero-Trust Privacy Protocols

### 5.1 Authentication & Zero IDOR/BOLA Protection
* Every user-specific endpoint requires `Authorization: Bearer <SUPABASE_JWT>`.
* `auth.py` validates the token via `supabase.auth.get_user(token)`.
* `verify_user_access(requested_user_id, authenticated_user_id)` strictly ensures users can only query, edit, or delete their own data.

### 5.2 Banking-Grade Crypto Vault (`app/vault.py`)
* Stores ICICI Breeze `app_key`, `secret_key`, and `session_token` encrypted with Fernet AES-256.
* Key Derivation: PBKDF2HMAC with SHA-256, 100,000 iterations, and a constant salt.
* In production (`ENVIRONMENT=production`), a valid 44-character base64 `ENCRYPTION_KEY` is strictly enforced at startup.

### 5.3 Constant-Time Cron & Webhook Validation
* Scanner endpoints (`/api/cron/*`) validate the `X-Cron-Secret` header using constant-time `hmac.compare_digest` against `CRON_SECRET_KEY`.
* Telegram webhook (`/api/telegram/webhook`) validates `X-Telegram-Bot-Api-Secret-Token` against `TELEGRAM_WEBHOOK_SECRET`.

### 5.4 Zero Raw PII Telemetry & Sensitive Data Log Filtering
* All user IDs, UUIDs, and Telegram Chat IDs are masked in server logs using `mask_id(val)` showing only the last 4 characters (`***XXXX`).
* Telegram Bot API tokens are masked across all loggers (`mask_telegram_token`) via a custom `SensitiveDataFilter`.
* Linking accounts via public email addresses in Telegram is strictly rejected (`email_not_permitted`) to prevent alert hijacking.

### 5.5 In-Memory Sliding-Window Rate Limiting
* Public endpoints (`/api/stocks/search`, `/api/stocks/validate`, `/api/stocks/quotes`, `/api/stocks/candles`, `/api/market/*`) enforce a 120 req/min sliding-window limiter per client IP.
* Stock symbols are validated against regex `^[A-Z0-9_\-&]{1,20}$` to neutralize injection attacks.

---

## 6. External Feeds & Broker Integration Engine

### 6.1 ICICI Direct Breeze API Daily Lifecycle
1. **Daily SEBI Token Expiry**: ICICI Breeze session tokens expire every morning per SEBI security regulations.
2. **08:50 AM IST Reminder**: Automated cron checks `token_date != today` and dispatches high-priority push/Telegram notifications prompting authentication.
3. **1-Tap In-App Login & Session Auto-Capture**:
   * Mobile uses `webview_flutter` navigation delegate to intercept the `apisession` query parameter from the ICICI Direct 2FA redirect URL (`https://Yourapp.vercel.app/api/auth/icici-callback`).
   * Automatically closes the webview, populates the session token, and saves it encrypted in the vault.
4. **Holdings & Tradebook Sync**:
   * Authoritative Demat holdings are queried via `breeze.get_demat_holdings()`.
   * Average buy prices are augmented from `breeze.get_portfolio_holdings(exchange_code="NSE")` and `BSE`.

### 6.2 Universal Dynamic ISIN-to-NSE Resolver
* CDSL/NSDL Demat ISIN codes (e.g. `INE750C01026`) are resolved to official NSE trading tickers dynamically using Yahoo Finance search and an in-memory RAM cache (`_ISIN_CACHE`).
* Works dynamically across all 2,000+ Indian equities with zero hardcoded mapping dictionaries.

### 6.3 Dual-Exchange (NSE / BSE) Dynamic Fallback
* Whenever an equity ticker is queried without exchange suffix, the engine prioritizes NSE (`.NS`), then automatically falls back to BSE (`.BO`) if empty.
* Charting and technical engines seamlessly support both `.NS` and `.BO` instruments.

### 6.4 1-Year Daily Candle Fallback (Off-Market / Low-Liquidity)
* During off-market hours, weekends, or for illiquid stocks where intraday 5m candles are empty, `technical_engine.py` smoothly computes price, 14-period ATR, Camarilla pivots, EMAs (20/50/200), Mansfield RS, and 14-period Wilder's ADX directly from the 1-year daily history.
* Candidate Price Ladder: `technicals.current_price` $\rightarrow$ `financials.price` $\rightarrow$ `holding.current_market_price` $\rightarrow$ `holding.last_price` $\rightarrow$ `holding.average_price` $\rightarrow$ `technicals.previous_close` $\rightarrow$ `fast_info`. Permanently eliminates missing or dummy ₹100.00 prices.

---

## 7. Complete REST API Specifications

| Endpoint | Method | Auth Scheme | Description |
| :--- | :---: | :---: | :--- |
| `GET /` | GET | Public | API Health Check and Mode Declaration |
| `GET /api/health/db` | GET | Public | Supabase PgBouncer (Port 6543) Pool Health Telemetry |
| `GET /api/user/profile` | GET | `Bearer <JWT>` | Retrieves user profile, settings, and notification channels |
| `POST /api/auth/register-device` | POST | `Bearer <JWT>` | Registers/updates FCM token, Telegram Chat ID, and sensitivity settings |
| `GET /api/user/credentials` | GET | `Bearer <JWT>` | Retrieves decrypted App Key and Secret Key for pre-filling with eye toggles |
| `POST /api/user/credentials` | POST | `Bearer <JWT>` | Encrypts (AES-256 Fernet) and upserts Breeze credentials and session token |
| `GET /api/user/portfolio` | GET | `Bearer <JWT>` | Synced Demat holdings, current values, P&L, P/E, D/E (15s RAM Cache) |
| `GET /api/user/alerts` | GET | `Bearer <JWT>` | Retrieves user's historical confluence alert ledger |
| `GET /api/user/accuracy-stats` | GET | `Bearer <JWT>` | Computes user-specific signal accuracy and win-rate statistics |
| `POST /api/user/delete-account` | POST | `Bearer <JWT>` | Cascading permanent deletion of credentials, watchlists, devices, and auth user |
| `GET /api/stocks/search?q={query}` | GET | Rate-Limited | Live dynamic autocomplete across NSE and BSE traded equities |
| `GET /api/stocks/validate?symbol={sym}`| GET | Rate-Limited | Real-time dual-stage exchange validation rejecting non-existent tickers |
| `GET /api/stocks/quotes?symbols={s1,s2}`| GET | Rate-Limited | High-speed batch quotes for 100+ stocks with 5s FIFO RAM caching |
| `GET /api/stocks/candles?symbol={sym}&interval=5m&period=5d` | GET | Rate-Limited | OHLCV candles with Camarilla $H_4/L_4$, VWAP, and Chandelier SL (60s Cache) |
| `GET /api/market/fii-dii-flows` | GET | Rate-Limited | Daily official NSE/BSE FII & DII cash flows and sentiment (30m Cache) |
| `GET /api/market/accuracy-ledger` | GET | Rate-Limited | Public audited non-repudiation accuracy ledger (Zero Mock Data, 300s Cache) |
| `GET /api/market/cache-stats` | GET | Public | Telemetry on in-memory market cache hits, misses, and writes |
| `POST /api/cron/multi-user-scan` | POST | `X-Cron-Secret` | 5-minute scanner (Returns 200 OK ~50ms + runs background task with lock) |
| `POST /api/cron/morning-token-reminder` | POST | `X-Cron-Secret` | 08:50 AM IST reminder for expired daily Demat session tokens |
| `POST /api/cron/pre-market-briefing` | POST | `X-Cron-Secret` | 09:00 AM IST War Room Briefing (Benchmarks, VIX, Global Cues, Sectors) |
| `POST /api/telegram/webhook` | POST | Secret Header | Interactive Telegram bot command handler (`/start <USER_ID>`, `/status`) |
| `POST /api/v1/orders/place` | POST | `Bearer <JWT>` | Executes BUY/SELL orders directly via ICICI Direct Breeze API |

---

## 8. Multi-Channel Notification & Client Presentation Matrix

### 8.1 Multi-Tenant Telegram Bot (`@StokVigilAi_bot`)
* **Single Central Bot Architecture**: Serves unlimited users with strict isolation based on `chat_id`.
* **Deep Linking**: Triggered via `t.me/StokVigilAi_bot?start=<USER_ID>`.
* **Rich HTML Alert Cards**:
  - Action Badge (`🟢 ACCUMULATE / BUY WATCH`, `🔴 PROFIT BOOK / SELL WATCH`, `🟡 TRAILING STOP-LOSS TRIGGER`).
  - Ticker & Exchange (`#TCS (NSE)`).
  - Confluence Score (`85/100`).
  - Demat Position Snapshot (Quantity, Average Buy Price, Current P&L %, Guidance).
  - Multi-Factor Drivers list.
  - Tactical Risk-Reward Levels (Entry, Target 1, Target 2, Stop-Loss, R:R).
  - Market Snapshot (LTP, 15m RSI, VWAP, Delivery %, Wyckoff VSA).
  - Interactive Inline Buttons:
    * `[📈 TradingView Chart]`: Deep link to live TradingView chart for NSE or BSE.
    * `[💼 ICICI Direct]`: Deep link to portfolio & execution.
    * `[🏛️ NSE / BSE India Live]`: Direct link to official exchange quote and corporate filings.

### 8.2 Firebase Cloud Messaging (FCM)
* High-priority lock-screen push notifications on channel `stokvigil_high_priority_alerts`.
* Structured metadata payload enabling one-tap deep-linking into in-app trade calculators and chart screens.

### 8.3 In-App Candlestick Charts with Camarilla Overlays
* Integrated TradingView Lightweight Charts v5 across Flutter (`CandleChartScreen`, `CandleChartModal`) and Next.js (`LightweightCandleChart.tsx`).
* Visual Overlays: Camarilla equation pivots ($H_4$ Breakout, $H_3$ Target 1, $L_3$ Accumulation, $L_4$ Stop-Loss), session VWAP, ATR-based Chandelier Trailing Stop, and volume histogram.
* Dedicated Fullscreen Mobile Client: Auto-resolution scaling via `ResizeObserver`, 1-tap landscape/portrait toggle, touch crosshair OHLC HUD, and offline asset preloading.

### 8.4 1-Tap Viral "Alpha Cards"
* Client-side off-screen HTML5 2D Canvas renders 1080×1080 branded PNG cards with 0 backend CPU cost.
* Includes 1-tap sharing to WhatsApp groups and X (Twitter) with real factor geometry.

### 8.5 Public Audited Accuracy Ledger (`/transparency`)
* Publicly verifiable non-repudiation ledger at `/transparency` and `GET /api/market/accuracy-ledger`.
* **Zero-Mock Guarantee**: Stats are computed on the fly directly from stored `stok_alerts`. When 0 verified signals exist, the ledger transparently displays `total_verified_signals: 0, win_rate_pct: 0.0, avg_risk_reward: "-"` with zero synthetic placeholder numbers.
* Zero PII exposure: strictly isolates all user IDs and positions.

---

## 9. Automated Cron Workflows & Infrastructure Directives

### 9.1 GitHub Actions Workflow (`.github/workflows/5min_cron.yml`)
Runs strictly Monday through Friday during Indian market days:
1. **08:50 AM IST (03:20 UTC)**: `cron: '20 3 * * 1-5'` $\rightarrow$ `POST /api/cron/morning-token-reminder`
2. **09:00 AM IST (03:30 UTC)**: `cron: '30 3 * * 1-5'` $\rightarrow$ `POST /api/cron/pre-market-briefing`
3. **09:15 AM to 03:30 PM IST (03:45 to 10:00 UTC)**: `cron: '*/5 3-10 * * 1-5'` $\rightarrow$ `POST /api/cron/multi-user-scan`

### 9.2 Google Cloud Run Configuration
* The multi-user scan endpoint returns `HTTP 200 OK` in ~50ms while the scan executes in the background via FastAPI `BackgroundTasks`.
* **Mandatory Cloud Run Setting**: Configure Google Cloud Run with **"CPU is always allocated"** (`--no-cpu-throttling`). This guarantees background processing continues execution without being throttled after the HTTP response is sent.
* Bounded memory footprint: In-memory RAM singleton cache consumes $< 15\text{ MB}$, well within Cloud Run 1024MB free tier.

---

## 10. AI Agent LLM Evaluation Prompt Template

When StokVigil AI invokes Google Gemini (`gemini-2.5-flash` or `gemini-1.5-flash`), it uses this exact system prompt and structured JSON schema:

```text
You are StokVigil AI, an Elite Senior Quantitative Trading Analyst and Market Intelligence Strategist specializing in Indian Stock Exchange (NSE/BSE) and ICICI Direct Demat surveillance.

Evaluate the multi-factor data payload for #{symbol} (NSE/BSE) and determine if there is an actionable price trajectory shift, institutional catalyst, or portfolio risk event.

============================================================
1. ICICI DIRECT DEMAT POSITION:
============================================================
{demat_context_json}

============================================================
2. MULTI-TIMEFRAME TECHNICAL INDICATORS:
============================================================
• 5-Minute RSI: {rsi_5m} | 15-Minute RSI: {rsi_15m} | Daily RSI: {rsi_daily}
• RSI Divergence: {rsi_divergence}
• MACD (12, 26, 9): Trend={macd_trend}, Histogram={macd_histogram}
• Intraday VWAP: ₹{vwap} (Price vs VWAP: {price_vs_vwap_pct}%)
• EMAs: 20 EMA=₹{ema_20}, 50 EMA=₹{ema_50}, 200 EMA=₹{ema_200} ({ma_trend})
• Volatility (14 ATR): ₹{atr_14}
• ADX (14-period Trend Strength): {adx_14} ({adx_regime})
• Camarilla Pivots: H4=₹{h4}, H3=₹{h3}, L3=₹{l3}, L4=₹{l4}
• Relative Strength vs NIFTY 50: {rs_rating}% ({rs_regime})
• Volume Multiple: {volume_multiple}x vs 20 MA (Surge: {is_volume_surge})

============================================================
3. INSTITUTIONAL FLOW & DERIVATIVES:
============================================================
• Wyckoff VSA Regime: {vsa_regime} ({vsa_note})
• Estimated Delivery Volume: {delivery_pct}% (Accumulation: {is_high_delivery})
• F&O Open Interest: {fo_oi_status} ({flow_bias})

============================================================
4. FUNDAMENTAL VALUATION & FORENSIC HEALTH:
============================================================
• Trailing P/E: {pe_ratio} | Forward P/E: {forward_pe}
• Debt-to-Equity: {debt_to_equity}
• Revenue Growth YoY: {revenue_growth_pct}% | Profit Margin: {profit_margin_pct}%
• Forensic Red Flags: {red_flags_json}

============================================================
5. MACRO REGIME & SECTOR:
============================================================
• NIFTY 50 Trend: {nifty_trend} ({nifty_change_pct}%)
• India VIX: {india_vix} ({vix_regime})
• Sector: {sector_name}

============================================================
6. 24-HOUR REAL-TIME NEWS & FILINGS:
============================================================
{news_items_json}

DIRECTIVES:
1. Confluence Score (1-100): Technical (30%), Flow (25%), Fundamentals (25%), News/Catalysts (20%).
2. Action Bias: "BUY_WATCH" (Score >= 72, if 200 EMA & VIX permit), "SELL_WATCH" (Score <= 38), "TRAILING_SL_ALERT" (User holds stock, profit > 5% & momentum stalling), "HOLD_NEUTRAL".
3. Calculate strict tactical levels: Entry Range (around L3/Current Price), Target 1 (1.5x ATR or H3), Target 2 (2.5x ATR or H4), Stop Loss (1.5x ATR or L4, or Chandelier Trailing SL), Risk-Reward Ratio (Min 1:2.0).
4. Guardrails:
   - Target 1 must be >= Price * 1.02.
   - Target 2 must be >= Price * 1.05.
   - Stop Loss must be <= Price * 0.98.
   - If Price < 200 EMA or India VIX > 24.0, BUY_WATCH is strictly prohibited (downgrade to HOLD_NEUTRAL).

Output ONLY valid JSON matching this exact structure:
{
  "symbol": "{symbol}",
  "has_actionable_signal": true,
  "action_bias": "BUY_WATCH",
  "confluence_score": 82,
  "alert_title": "Descriptive concise headline",
  "catalyst_category": "TECHNICAL_BREAKOUT",
  "confluence_drivers": [
    "Factual driver 1",
    "Factual driver 2",
    "Factual driver 3"
  ],
  "tactical_levels": {
    "entry_range": "₹980.00 - ₹985.00",
    "target_1": "₹1,005.00",
    "target_2": "₹1,025.00",
    "protective_stop_loss": "₹968.00",
    "risk_reward_ratio": "1:2.3"
  },
  "factor_breakdown": {
    "technicals": 85,
    "flow": 72,
    "forensics": 80,
    "catalysts": 90
  },
  "holding_guidance": "Recommended holding / trailing stop guidance for user Demat position.",
  "growth_outlook_summary": "12-month expansion summary."
}
```

---

## 11. Developer & Agent Implementation Guidelines

When extending, refactoring, or running tests across this repository, follow these cardinal rules:
1. **Never Hardcode Stock Symbols or Prices**: Always resolve tickers dynamically via Yahoo Finance (`GET /api/stocks/search` & `GET /api/stocks/validate`) and resolve ISINs via `resolve_isin_to_nse_symbol`. Never inject dummy ₹100 fallback prices.
2. **Never Return Mock Data for Audited Routes**: In `/api/market/accuracy-ledger` and `/transparency`, always calculate KPIs dynamically from `stok_alerts`. Report `0.0%` and `"-"` when zero data exists.
3. **Preserve Free Tier Quotas**: Always pass stocks through the Tier-1 Gatekeeper before calling Gemini. Never invoke Gemini in a loop for all watchlist stocks.
4. **Preserve Database Connection Pooling**: Keep `statement_cache_size=0` on asyncpg PgBouncer connections on port 6543. Always maintain REST fallback.
5. **Enforce Complete PII Log Masking**: Never print raw user IDs, email addresses, or Telegram Bot tokens in logs. Use `mask_id` and `SensitiveDataFilter`.
6. **Flutter / Dart Rule**: Whenever editing Flutter code, ensure state models, widgets, and charts support zero-hardcoded dynamic fields.
