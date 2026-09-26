# 🏛️ STOKVIGIL AI: MASTER SYSTEM BUILD PROMPT & ARCHITECTURAL SPECIFICATION

> **Instructions for the AI Assistant / Developer:**
> You are tasked with building **StokVigil AI** (`com.app.stokvigil`), a production-grade, 100% free-tier institutional Indian stock market alert and surveillance application for Web (Next.js 16 PWA) and Mobile (Flutter Android/iOS). 
> 
> Build the entire application following the strict specifications, data schemas, mathematical engines, security controls, and design patterns described below. Do not omit any module, security safeguard, or mathematical formula.

---

## 📑 TABLE OF CONTENTS
1. [System Mission & Non-Negotiable Invariants](#1-system-mission--non-negotiable-invariants)
2. [Tech Stack & Free-Tier Architecture](#2-tech-stack--free-tier-architecture)
3. [Database Architecture & SQL Migrations (Supabase)](#3-database-architecture--sql-migrations-supabase)
4. [Quantitative Engine & 13 Algorithmic Upgrades](#4-quantitative-engine--13-algorithmic-upgrades)
5. [Pluggable Broker Architecture & Master Publisher Model](#5-pluggable-broker-architecture--master-publisher-model)
6. [Financial Trade Execution Safeguards](#6-financial-trade-execution-safeguards)
7. [FastAPI Backend API & Security Implementation](#7-fastapi-backend-api--security-implementation)
8. [Next.js 16 Web Portal Specification](#8-nextjs-16-web-portal-specification)
9. [Flutter Mobile App Specification (`com.app.stokvigil`)](#9-flutter-mobile-app-specification-comappstokvigil)
10. [Multi-Channel Notification Dispatchers (Telegram & FCM)](#10-multi-channel-notification-dispatchers-telegram--fcm)
11. [Automated Market Cron Workflows (GitHub Actions)](#11-automated-market-cron-workflows-github-actions)
12. [Environment Configuration (`.env.example`)](#12-environment-configuration-envexample)
13. [Step-by-Step Implementation Roadmap](#13-step-by-step-implementation-roadmap)

---

## 1. SYSTEM MISSION & NON-NEGOTIABLE INVARIANTS

### 1.1 Core Purpose
StokVigil AI is an automated, unsleeping market surveillance watchtower operating strictly during Indian Stock Exchange trading hours (**09:15 AM to 03:30 PM IST**, Monday through Friday). It monitors user Demat holdings and custom watchlists, runs real-time quantitative multi-factor calculations, and dispatches actionable, factual alerts directly to user devices via Telegram Bot API and Firebase Cloud Messaging (FCM).

### 1.2 Non-Negotiable Architectural Invariants

1. **Pure Quantitative Intelligence & Zero Unsolicited Trades**:
   - The application **NEVER executes automated trades** without explicit user confirmation.
   - All trade orders are strictly user-initiated via interactive trade confirmation modals.

2. **SEBI Non-Advisory Regulatory Compliance**:
   - The system strictly does NOT provide SEBI-unregistered investment tips (e.g. "BUY AT 200, TARGET 250").
   - Projections are mathematically computed and strictly labeled as:
     - **Tactical Resistance 1 (1.5x ATR Benchmark)**
     - **Expansion Resistance 2 (2.5x ATR Benchmark)**
     - **Tactical Support 1 (1.5x ATR Benchmark)** / **Extended Support 2**
     - **Protective Stop-Loss (1.5x ATR Volatility Floor)**
   - Every alert notification, Telegram card, and Web/Mobile dashboard embeds the mandatory SEBI disclaimer:
     > *"⚖️ SEBI Non-Advisory Compliance Disclosure: StokVigil AI provides algorithmic quantitative data and mathematical tracking strictly for educational and surveillance purposes. Not investment advice or research recommendations. Trading in securities involves capital risk. Consult a SEBI-registered advisor before executing orders."*

3. **Strict Zero-Default Data Integrity Guarantee**:
   - **Never display or compute fake synthetic fallback defaults** when actual market values are unavailable (e.g. NEVER substitute dummy `50.0` RSI, `20.0` ADX, `52.0%` delivery, `1.0` PCR, `₹0.00` tactical levels, fake `24500.0` / `80000.0` index prices, `14.5` VIX, fake `+1,270.60 Cr` FII/DII proxy, fake 5-session history deltas, or dummy `₹100.0` stock prices).
   - If market feeds fail, volume is zero, or candle history is insufficient, functions must return clean `None` (JSON `null`).
   - UIs must display clean `"--"` indicators. Buttons for unpriced stocks must be disabled (`not-allowed`).

4. **100% Free-Tier Architecture ($0.00/Month Run Cost)**:
   - Must operate entirely within free tiers:
     - **Compute**: Google Cloud Run (2M free requests/mo, 360,000 vCPU-seconds/mo) or Render Free Tier.
     - **Database**: Supabase PostgreSQL Free Tier (500 MB) with PgBouncer Port 6543 connection pooling and automated 30-day alert pruning.
     - **AI Model**: Google Gemini API Free Tier (15 RPM limit) via the 2-Tier Gatekeeper Architecture.
     - **Notifications**: Telegram Bot API (100% free) + Firebase Cloud Messaging (100% free).
     - **Data**: Yahoo Finance (`yfinance` direct chart metadata v8), NSE official archives (`fo_mktlots.csv`), and Google News RSS.

5. **Bank-Grade Security & PII Privacy**:
   - Supabase Auth JWT token validation on all user-scoped endpoints (eliminating BOLA/IDOR).
   - Server-side AES-256 Fernet vault encryption with PBKDF2HMAC for broker session tokens.
   - PII log masking (`mask_id`) exposing strictly the last 4 characters (`***XXXX`).
   - Constant-time `hmac.compare_digest` for cron secrets (`X-Cron-Secret`) and Telegram webhook secrets (`X-Telegram-Bot-Api-Secret-Token`).
   - Telegram anti-hijacking: account linking via email is strictly rejected; only internal User UUID is permitted.
   - Reverse-proxy sliding-window rate limiting (120 req/min) with trusted subnet verification and anti-OOM capacity limits.
   - CI/CD Secret Isolation: `SUPABASE_SERVICE_ROLE_KEY` is NEVER bundled into client APKs or web builds.

---

## 2. TECH STACK & FREE-TIER ARCHITECTURE

| Component | Technology | Version / Specifics | Free-Tier Strategy |
| :--- | :--- | :--- | :--- |
| **Backend API** | Python + FastAPI | 3.11 / FastAPI 0.110+ | Containerized for Google Cloud Run (2M req/mo free) |
| **AI Engine** | `google-genai` SDK | `gemini-3.5-flash-lite` (primary), fallback to `gemini-2.0-flash` & `gemini-1.5-flash` | 2-Tier Smart Gatekeeper: deterministic math for quiet stocks, reserving 15 RPM Gemini quota for active breakouts |
| **Database** | Supabase PostgreSQL | PostgreSQL 15+ / PostgREST | Multiplexed via PgBouncer / Supavisor on **Port 6543** (`asyncpg`, `statement_cache_size=0`) |
| **Web Portal** | Next.js + React + Tailwind | Next.js 16 (App Router), React 19, TypeScript | Deployed on Vercel Free Tier (PWA enabled) |
| **Mobile App** | Flutter (Dart) | Flutter 3.19+ / Dart 3.3+ | Android (`com.app.stokvigil`) & iOS with ProGuard/R8 obfuscation |
| **Charting** | TradingView Lightweight Charts | `@tradingview/lightweight-charts` v5 | Bundled offline local JS asset, Camarilla pivots, VWAP, Chandelier SL, SV watermark |
| **Broker Engine** | Pluggable Broker Adapter | ICICI Direct (`breeze-connect`) | Pure Master App Publisher Model (server-side master keys; zero developer keys for users) |
| **Market Feeds** | `yfinance`, NSE Archives, RSS | Direct Yahoo v8 chart API, `fo_mktlots.csv`, Google News | 60s macro cache, 15m indicator RAM cache, 8h daily candle cache, Akamai cookie bypass |
| **Notifications** | FCM + Telegram Bot | Firebase Admin SDK + `httpx` async | High-priority Android lock screen + Rich Telegram HTML cards with deep-link buttons |
| **Automation** | GitHub Actions Workflows | 5 cron workflows (Mon-Fri) | Synchronous HTTP calls with Cloud Run 100% CPU allocation |

---

## 3. DATABASE ARCHITECTURE & SQL MIGRATIONS (SUPABASE)

Execute the following migrations in Supabase SQL Editor in exact chronological order:

### Migration 1: `20260809_init_stokvigil.sql`
```sql
-- 1. Create Catalyst Type Enum
CREATE TYPE catalyst_type_enum AS ENUM (
    'BLOCK_DEAL',
    'EARNINGS_BEAT',
    'DEBT_CHANGE',
    'PRICE_BREAKOUT',
    'NEWS_CATALYST'
);

-- 2. Create Profiles Table (Linked to Supabase Auth)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    fcm_device_token TEXT DEFAULT NULL,
    telegram_chat_id TEXT DEFAULT NULL,
    telegram_enabled BOOLEAN DEFAULT FALSE,
    demat_auto_sync BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own profile"
    ON public.profiles FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile"
    ON public.profiles FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Service role full access on profiles"
    ON public.profiles FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Trigger to automatically create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, created_at)
    VALUES (NEW.id, NEW.email, NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- 3. Create User Credentials Table (AES-256 Encrypted Vault)
CREATE TABLE IF NOT EXISTS public.user_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE UNIQUE,
    encrypted_app_key TEXT DEFAULT NULL,
    encrypted_secret_key TEXT DEFAULT NULL,
    encrypted_session_token TEXT NOT NULL,
    token_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.user_credentials ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own credentials"
    ON public.user_credentials FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert/update their own credentials"
    ON public.user_credentials FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update existing credentials"
    ON public.user_credentials FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Service role full access on user_credentials"
    ON public.user_credentials FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- 4. Create User Watchlists Table
CREATE TABLE IF NOT EXISTS public.user_watchlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    is_auto_synced BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, symbol)
);

ALTER TABLE public.user_watchlists ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their watchlists"
    ON public.user_watchlists FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Service role full access on user_watchlists"
    ON public.user_watchlists FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- 5. Create Stok Alerts Ledger Table
CREATE TABLE IF NOT EXISTS public.stok_alerts (
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

ALTER TABLE public.stok_alerts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own alerts"
    ON public.stok_alerts FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Service role full access on stok_alerts"
    ON public.stok_alerts FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Indexes
CREATE INDEX IF NOT EXISTS idx_watchlists_user ON public.user_watchlists(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_user_date ON public.stok_alerts(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_symbol ON public.stok_alerts(symbol);
CREATE INDEX IF NOT EXISTS idx_credentials_date ON public.user_credentials(token_date);
```

### Migration 2: `20260822_enhance_stokalerts.sql`
```sql
-- Expand Catalyst Enum
ALTER TYPE catalyst_type_enum ADD VALUE IF NOT EXISTS 'VOLUME_SURGE';
ALTER TYPE catalyst_type_enum ADD VALUE IF NOT EXISTS 'TECHNICAL_BREAKOUT';
ALTER TYPE catalyst_type_enum ADD VALUE IF NOT EXISTS 'TRAILING_STOP_TRIGGER';

-- Profile customization columns
ALTER TABLE public.profiles 
    ADD COLUMN IF NOT EXISTS alert_sensitivity TEXT DEFAULT 'HIGH',
    ADD COLUMN IF NOT EXISTS execution_mode TEXT DEFAULT 'CONFIRM',
    ADD COLUMN IF NOT EXISTS tnc_accepted BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS tnc_accepted_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS demat_auto_sync BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_stok_alerts_created_at ON public.stok_alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_stok_alerts_symbol_user ON public.stok_alerts(symbol, user_id);
CREATE INDEX IF NOT EXISTS idx_profiles_telegram ON public.profiles(telegram_chat_id) WHERE telegram_enabled = true;
```

### Migration 3: `20260906_fii_dii_flows.sql`
```sql
CREATE TABLE IF NOT EXISTS public.fii_dii_flows (
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
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_fii_dii_trade_date ON public.fii_dii_flows (trade_date DESC);
ALTER TABLE public.fii_dii_flows ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public Read FII DII Flows"
    ON public.fii_dii_flows FOR SELECT USING (true);

CREATE POLICY "Service role full access on fii_dii_flows"
    ON public.fii_dii_flows FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
```

### Migration 4: `20260911_prune_old_alerts_cron.sql`
```sql
CREATE OR REPLACE FUNCTION public.prune_historical_stok_alerts(retention_days INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARATION
    deleted_rows INTEGER;
BEGIN
    DELETE FROM public.stok_alerts
    WHERE created_at < (NOW() - (retention_days || ' days')::INTERVAL);
    GET DIAGNOSTICS deleted_rows = ROW_COUNT;
    RETURN deleted_rows;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION public.prune_historical_stok_alerts(INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION public.prune_historical_stok_alerts(INTEGER) TO postgres;
```

---

## 4. QUANTITATIVE ENGINE & 13 ALGORITHMIC UPGRADES

### 4.1 The 2-Tier Smart Gatekeeper Architecture (`agent_runner.py`)
To prevent exceeding the Gemini API free tier 15 RPM limit and eliminate latency:
- **Tier-1 RAM Math Gatekeeper (`check_has_active_catalyst`)**:
  - Runs in 0.001 ms in RAM before any AI model call.
  - Quiet, sideways, or consolidating stocks are deterministically evaluated in RAM (`compute_deterministic_confluence`), consuming **0 Gemini API calls**.
  - A stock qualifies as an **Active Catalyst** only if it meets at least one of these criteria:
    1. Demat holding unrealized P&L drops $\le -3.5\%$ (capital defense stop) or surges $\ge +5.0\%$ with $15\text{m RSI} > 70.0$.
    2. Active position reaches Tactical Resistance 1 (`TARGET_1_TRAIL_ALERT`).
    3. Intraday price surge or breakdown magnitude $|\Delta P| \ge 2.5\%$.
    4. 15-Minute Opening Range Breakout (`BULLISH_ORB_BREAKOUT` or `BEARISH_ORB_BREAKDOWN`) with candle close confirmation.
    5. Upper or Lower Circuit Lock freeze.
    6. Volume surge $\ge 1.5\times$ 20-period volume MA.
    7. Momentum extremes ($15\text{m RSI} \ge 68$ or $\le 32$, or RSI divergence).
    8. 15m MACD bullish or bearish trend transition crossover.
    9. Institutional delivery $\ge 50\%$ or aggressive F&O open interest build-up.
    10. Intraday VWAP breakout (price deviates $\ge 0.8\%$ from VWAP).
    11. Real-time news catalyst, order win, earnings beat, or block deal.
- **Tier-2 Google Gemini AI Synthesis (`evaluate_stock_with_ai`)**:
  - Handed off only for active catalysts, bounded by `MAX_AI_CALLS_PER_SCAN = 15`.
  - Uses `google-genai` SDK with fallback chain: `gemini-3.5-flash-lite` $\rightarrow$ `gemini-2.0-flash` $\rightarrow$ `gemini-1.5-flash` $\rightarrow$ Deterministic RAM fallback.

### 4.2 Dynamic Regime-Adaptive Confluence Equation
$$\text{Confluence Score} = (W_{\text{tech}} \times \text{Tech}) + (W_{\text{flow}} \times \text{Flow}) + (W_{\text{forensics}} \times \text{Forensics}) + (W_{\text{news}} \times \text{News})$$

Dynamic Weights allocation based on India VIX (`^INDIAVIX`) and Advance-Decline Ratio (ADR):
1. **High Volatility / Distribution Regime** ($\text{India VIX} > 16.5$ or $\text{ADR} < 0.80$):
   - $W_{\text{flow}} = 0.35, W_{\text{forensics}} = 0.35, W_{\text{tech}} = 0.15, W_{\text{news}} = 0.15$ (Defensive Posture).
2. **Bull Momentum Trend Regime** ($\text{India VIX} \le 14.5$ and $\text{ADR} \ge 1.20$):
   - $W_{\text{tech}} = 0.40, W_{\text{flow}} = 0.30, W_{\text{forensics}} = 0.15, W_{\text{news}} = 0.15$ (Trend Following).
3. **Balanced / Normal Market**:
   - $W_{\text{tech}} = 0.30, W_{\text{flow}} = 0.25, W_{\text{forensics}} = 0.25, W_{\text{news}} = 0.20$.

### 4.3 The 13 Critical Algorithmic Upgrades
1. **Hard Risk Veto for Severe Supply Shocks**: When $\Delta P \le -3.5\%$, price is below session VWAP, or Camarilla $L_4$ is breached, hard-cap Confluence Score at $\le 28$, force `action_bias = "SELL_WATCH"`. Overrides fundamental buoys to eliminate the "Linear Blend Fallacy".
2. **Demat Downside Capital Preservation Shield**: For active Demat holdings, if unrealized loss $\le -3.5\%$, immediately fire emergency `TRAILING_SL_ALERT` bypassing score thresholds.
3. **Positive Momentum Surge Driver**: If $\Delta P \ge +5.0\%$ with confirmed `BULLISH_ORB_BREAKOUT`, award **+6 points** bonus, tag as `PRICE_BREAKOUT`.
4. **15-Minute Opening Range Breakout (ORB) Engine**: Isolates first 15 minutes (09:15–09:30 IST) across the first three 5m candles into `orb_high_15m` and `orb_low_15m`. Penalizes breakdown (-10 pts) and rewards breakout (+10 pts).
5. **Date-Aware Camarilla Institutional Pivots**: If `daily_df.index[-1].date() == today`, strictly compute levels from `daily_df.iloc[-2]` (prior completed day). Prevents the currently forming intraday bar from distorting institutional pivot floors.
   $$H_4 = C + 1.1 \times \frac{H - L}{2}, \quad H_3 = C + 1.1 \times \frac{H - L}{4}$$
   $$L_3 = C - 1.1 \times \frac{H - L}{4}, \quad L_4 = C - 1.1 \times \frac{H - L}{2}$$
6. **Upper & Lower Circuit Lock Freeze Detection**: Detects sub-tick high/low equality ($|H - L| < 10^{-4}$ and $|C - L| < 10^{-4}$) with $|\Delta P| \ge 1.90\%$. Flags `UPPER_CIRCUIT` or `LOWER_CIRCUIT`.
7. **Granular Near-Month Options Expiry Filtering**: Restricts NSE option chain calculations strictly to the nearest expiry date (`records["expiryDates"][0]`), eliminating far-month illiquid options from skewing PCR and Max Pain.
8. **Universal Sensitivity Delivery Gate**: User configured with `ALL` sensitivity receives all valid actionable alerts, breakdowns, and trailing stops.
9. **Two-Way 200 EMA Macro Trend Anchor**: If price is below the Daily 200 EMA, any `BUY_WATCH` is vetoed to `HOLD_NEUTRAL`. If price is above the Daily 200 EMA, any `SELL_WATCH` is vetoed to `HOLD_NEUTRAL`.
10. **15-Minute Candle Close Confirmation & Wick Rejection Engine**: Evaluates breakout catalysts strictly on completed candle close. Filters out upper/lower wick rejections (`ORB_UPPER_WICK_REJECTION`, `ORB_LOWER_WICK_REJECTION`).
11. **Target 1 Achieved & Trail-to-Cost Lifecycle Alert (`TARGET_1_TRAIL_ALERT`)**: When price crosses Tactical Resistance 1, dispatches notification: *"🎯 TARGET 1 REACHED: Lock 50% Gains & Trail Stop-Loss to Breakeven Cost"*.
12. **SEBI Non-Advisory Mathematical Disclaimers & Terminology Shift**: Uses strictly "Tactical Resistance 1 (1.5x ATR Benchmark)" and "Expansion Resistance 2 (2.5x ATR Benchmark)".
13. **Stop-Loss Limit (`SL-L`) Execution Routing & SEBI/NSE `SL-M` Ban Enforcement**: Rejects any stop order with `order_type == "MARKET"` (`HTTP 422`). Requires explicit `price` and `trigger_price`, both snapped to Indian exchange ₹0.05 ticks.

### 4.4 Wyckoff Volume Spread Analysis (VSA) & Dynamic F&O Discovery
- **Dynamic F&O Universe Discovery (`get_dynamic_fo_universe` in `flow_tracker.py`)**: Fetches active contracts daily from official NSE archives (`https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv`, 24h cache). Instant 0.0001ms bypass for BSE scrips.
- **`SMART_MONEY_ABSORPTION`**: Delivery volume $\ge 55\%$ (or volume multiple $\ge 1.8\times$) with positive price expansion above VWAP $\rightarrow$ **+8 points**.
- **`OPERATOR_CHURN_TRAP`**: Price volatility $> 2\%$ with delivery $< 25\%$, or volume surge $\ge 1.8\times$ with narrow spread $\le 0.2\% \rightarrow$ **-10 points**.
- **Intraday $\Delta \text{OI}$ Momentum Velocity**:
  - `CALL_UNWINDING_SHORT_COVERING`: Aggressive call unwinding + put building $\rightarrow$ Short squeeze setup.
  - `AGGRESSIVE_PUT_WRITING`: Put change $> 1.5\times$ call change $\rightarrow$ Institutional floor.
  - `AGGRESSIVE_CALL_WRITING`: Call change $> 1.5\times$ put change $\rightarrow$ Overhead supply ceiling.

### 4.5 Additional Quantitative Math Pillars
- **TTM Squeeze Volatility Compression**: Bollinger Bands ($20, 2.0\sigma$) compressing inside Keltner Channels ($20, 1.5\text{x ATR}_{14}$) (`SQUEEZE_ON`) and explosive releases (`SQUEEZE_RELEASE`) with 5-period smoothed momentum histogram.
- **Session VWAP Volatility Bands**: Volume-weighted standard deviation bands ($\pm 1\sigma, \pm 2\sigma$) around intraday VWAP.
- **14-Period Wilder's ADX**: $\text{ADX} \ge 25$ validates trend; $\text{ADX} < 20$ triggers an 8-point chop penalty.
- **Direction-Aware Tactical Levels & 1% Capital Risk Sizer**:
  - Bullish: Resistance 1 $\ge \text{Price} \times 1.02$; Resistance 2 $\ge \text{Price} \times 1.05$; Stop Loss $\le \text{Price} \times 0.98$.
  - Bearish: Support 1 $\le \text{Price} \times 0.98$; Support 2 $\le \text{Price} \times 0.95$; Buy-Stop $\ge \text{Price} \times 1.02$.
  - Risk Sizing:
    $$\text{Risk Per Share} = \max(0.5, |\text{Current Price} - \text{Stop Loss}|)$$
    $$\text{Recommended Quantity} = \max\left(1, \left\lfloor \frac{\text{Risk Budget}}{\text{Risk Per Share}} \right\rfloor\right)$$
- **FII/DII Net Cash Flow Tracker (`fii_dii_tracker.py`)**: Queries daily official NSE cash turnover with cookie session warmup (bypassing Akamai WAF), normalizes date to ISO, upserts into `fii_dii_flows`, and classifies sentiment (`STRONG_ACCUMULATION`, `HEAVY_DISTRIBUTION`, etc.).
- **Vectorized Strategy Backtester (`backtester.py`)**: Sub-1-second vectorized NumPy/Pandas backtester evaluating historical OHLCV candles, 1% risk position sizing, Win Rate %, Target 1 Hit Rate %, Profit Factor, Max Drawdown %, and Sharpe Ratio.
- **Real Price-Tracking Accuracy Verifier (`accuracy_verifier.py`)**: Cryptographically tracks every alert and verifies outcomes against subsequent real OHLCV candles (`TARGET_1_REACHED`, `STOP_LOSS_HIT`, or `OPEN_MONITORING`).

---

## 5. PLUGGABLE BROKER ARCHITECTURE & MASTER PUBLISHER MODEL

### 5.1 Broker Adapter Pattern (`backend/app/brokers/`)
- `BaseBrokerAdapter` (Abstract Base Class in `base.py`):
  - `get_login_url(redirect_uri) -> str`
  - `save_credentials(db, vault, user_id, session_token, **kwargs) -> Dict`
  - `fetch_holdings(decrypted_creds) -> List[Dict]`
  - `place_order(decrypted_creds, order_params) -> Dict`
  - `validate_session(user_id) -> bool`
- `BrokerRegistry` (in `registry.py`):
  - Catalog managing `icici`, `zerodha`, `angelone`, `upstox`.
- `IciciBrokerAdapter` (in `icici_adapter.py`):
  - Implements Breeze Connect integration.

### 5.2 Pure Master App Publisher Model (Zero Manual Keys)
- Users NEVER register developer apps or handle developer API keys.
- `ICICI_MASTER_APP_KEY` and `ICICI_MASTER_SECRET_KEY` are secured exclusively server-side.
- Flow:
  1. User clicks **`1-Tap Login`** $\rightarrow$ opens official ICICI login with server pre-configured master app key.
  2. User logs in with retail credentials & 2FA $\rightarrow$ pastes generated session token (or mobile auto-captures via deep link `stokvigil://breeze-callback?apisession=...`).
  3. Backend encrypts session token with Fernet AES-256 and stores in `user_credentials`.

---

## 6. FINANCIAL TRADE EXECUTION SAFEGUARDS (`POST /api/v1/orders/place`)

1. **Financial Idempotency & In-Flight Replay Shield (`_ORDER_IDEMPOTENCY_CACHE`)**:
   - `X-Idempotency-Key` header cached for 120 seconds.
   - SHA-256 in-flight fingerprint `(user_id, symbol, action, quantity, price)` with 15-second debounce window. Returns `HTTP 409 Conflict` during active execution to prevent double-click orders.
2. **Silent Broker RMS Rejection Interception (HTTP 422)**:
   - Inspects ICICI Breeze JSON response. Any non-200 status or error payload immediately raises `HTTP 422 Unprocessable Entity` with the exact broker RMS error message.
3. **Strict Limit Price Validation & ₹0.05 Tick Snapping (`snap_to_exchange_tick`)**:
   - Requires `price > 0.0` for LIMIT orders.
   - Snaps price to Indian exchange standard ₹0.05 tick size: `round(price * 20) / 20`.
4. **SEBI/NSE Stop-Loss Market (`SL-M`) Ban Enforcement**:
   - Stop-Loss Market orders are rejected with `HTTP 422`. Stop orders must be `SL-L` with explicit `price` and `trigger_price`.
5. **Dynamic Product Resolution & SEBI Intraday MIS Margin Short Notice**:
   - If selling shares held in Demat $\rightarrow$ routes as `product="cash"` (CNC delivery).
   - If selling unheld shares $\rightarrow$ routes as `product="margin"` (intraday short) and injects mandatory SEBI warning banner.
6. **Indian Market Session Awareness (`get_market_session_status`)**:
   - Checks if within 09:15 to 15:30 IST, Mon-Fri. Warns user if placing AMO orders.
7. **Automated BSE Order Routing & Ticker Sanitation**:
   - Strips `.BO` suffixes, maps 6-digit numeric BSE security codes, routes `exchange_code="BSE"` vs `"NSE"`.

---

## 7. FASTAPI BACKEND API & SECURITY IMPLEMENTATION

### 7.1 Key Endpoints
| Endpoint | Method | Auth Scheme | Description |
| :--- | :---: | :---: | :--- |
| `/` | `GET` | Public | Health check |
| `/api/health/db` | `GET` | Public | Supabase PgBouncer (Port 6543) health status |
| `/api/brokers` | `GET` | Public | Catalog of active and upcoming brokers |
| `/api/brokers/{broker_id}/login-url` | `GET` | Public | Dynamic official 1-tap broker login URL |
| `/api/user/credentials` | `GET` / `POST` | Bearer JWT | Fetch status / Save encrypted broker session token |
| `/api/user/profile` | `GET` | Bearer JWT | User profile & notification settings |
| `/api/auth/register-device` | `POST` | Bearer JWT | Register FCM token, Telegram chat ID, preferences |
| `/api/user/portfolio` | `GET` | Bearer JWT | Live Demat portfolio holdings & P&L (background pre-warming) |
| `/api/user/alerts` | `GET` | Bearer JWT | Historical alerts ledger with tactical levels |
| `/api/user/accuracy-stats` | `GET` | Bearer JWT | Real price-tracking win rates and signal outcomes |
| `/api/market/backtest` | `GET` / `POST` | Bearer JWT | Vectorized NumPy/Pandas strategy replay |
| `/api/user/delete-account` | `POST` | Bearer JWT | Cascading permanent deletion of user data |
| `/api/cron/multi-user-scan` | `POST` | `X-Cron-Secret` | Synchronous 5-minute multi-user portfolio & watchlist scanner |
| `/api/cron/morning-token-reminder`| `POST` | `X-Cron-Secret` | 08:50 AM IST reminder for expired broker tokens |
| `/api/cron/pre-market-briefing` | `POST` | `X-Cron-Secret` | 09:00 AM IST War Room Briefing |
| `/api/cron/post-market-summary` | `POST` | `X-Cron-Secret` | 03:45 PM IST Closing Bell Telegram Digest |
| `/api/stocks/candles` | `GET` | Rate-Limited | OHLCV candles with Camarilla, VWAP, Chandelier SL |
| `/api/market/fii-dii-flows` | `GET` | Rate-Limited | Daily FII & DII cash flows & sentiment bias |
| `/api/market/accuracy-ledger` | `GET` | Rate-Limited | Public audited non-repudiation accuracy ledger |
| `/api/telegram/webhook` | `POST` | Secret Header | Telegram bot command handler (`/start`, `/status`, `/help`) |
| `/api/stocks/search` | `GET` | Rate-Limited | Dynamic autocomplete across NSE & BSE traded equities |
| `/api/stocks/validate` | `GET` | Rate-Limited | Dual-stage exchange validation (zero dummy tickers) |
| `/api/stocks/quotes` | `GET` | Rate-Limited | High-speed batch quotes (20s market TTL, 300s off-market TTL) |
| `/api/v1/orders/place` | `POST` | Bearer JWT | ICICI Breeze trade execution with 7 safeguards |

### 7.2 Security Implementation
- **Supabase PgBouncer Connection Pool (`app/db_pool.py`)**: `asyncpg` pool with `statement_cache_size=0`, `min_size=2`, `max_size=10`, `command_timeout=10.0`, `max_inactive_connection_lifetime=180.0`. Dual-driver execution fallback to PostgREST REST API.
- **Proxy-Aware Sliding-Window Rate Limiter**: Max 120 req/min per client IP. Inspects `CF-Connecting-IP`, `X-Forwarded-For`, and `X-Real-IP` ONLY if direct socket peer is in trusted private subnets. Auto-prunes expired buckets and caps memory at 10,000 buckets.
- **Crypto Vault (`app/vault.py`)**: Fernet AES-256 with PBKDF2HMAC fallback for encrypting session tokens.
- **Auth & IDOR Defense (`app/auth.py`)**: Validates Supabase JWT Bearer token on every request. Masks IDs in logs (`mask_id`).

---

## 8. NEXT.JS 16 WEB PORTAL SPECIFICATION (`web_portal/`)

### 8.1 Architecture & Design System
- **Framework**: Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS.
- **Theme Palette (`DesignTokens.ts`)**:
  - Background: `#070913`, Card: `#0D111E`, Card 2: `#12172A`
  - Borders: `rgba(255,255,255,0.08)`, Border Cyan: `rgba(6,182,212,0.35)`, Border Violet: `rgba(139,92,246,0.35)`
  - Accents: Cyan `#06B6D4`, Violet `#8B5CF6`, Emerald `#10B981`, Rose `#EF4444`, Amber `#F59E0B`
- **Tabs (`page.tsx`)**:
  - `HomeTab.tsx`: Portfolio summary cards, privacy masking toggle, FII/DII net flow sentiment bar, holdings grid.
  - `AlertsTab.tsx`: Real-time catalyst alerts stream, filters, Confluence Radar toggle, 1-tap Share Alpha Card button.
  - `WatchlistTab.tsx`: Ticker search with dynamic autocomplete, Demat Auto-Sync toggle, stock cards with Target/SL metrics and `[⚡ Trade Order]` button.
  - `SettingsTab.tsx`: Multi-broker switcher, 1-tap Breeze login, Telegram pairing, alert sensitivity, account deletion, plus integrated **Audit Ledger** and **Strategy Backtester**.
- **Modals**:
  - `TradeOrderModal.tsx`: Breeze interactive order placement with live tick snapping, SEBI MIS notice, SL-L enforcement.
  - `StockDetailModal.tsx`: Detailed holding metrics and valuation breakdown.
  - `IciciKeyModal.tsx`: 2-step token copy & paste with 4-color neon action button.
  - `ShareAlphaCardModal.tsx`: Generates 1080×1080 offscreen HTML5 2D Canvas branded PNG cards with 1-tap WhatsApp and X share.
  - `PasswordModal.tsx` & `DeleteAccountModal.tsx`.
- **TradingView Charts (`LightweightCandleChart.tsx`)**:
  - `@tradingview/lightweight-charts` v5 with complete attribution logo/link suppression (`attributionLogo: false`).
  - Overlays: Camarilla pivots ($H_4, H_3, L_3, L_4$), intraday VWAP, Chandelier Trailing Stop, Volume histogram.
  - Subtle 'SV' canvas watermark and pro terminal badge.
  - Fullscreen dynamic maximize mode (`calc(85vh - 240px)` / 96vw).
- **Public Transparency Route (`/transparency/page.tsx`)**:
  - Public audited accuracy ledger and live performance KPIs.

---

## 9. FLUTTER MOBILE APP SPECIFICATION (`mobile_app/`)

### 9.1 Architecture & Android Obfuscation
- **Package ID**: `com.app.stokvigil`
- **Theme (`theme.dart`)**: Identical dark cyan-violet theme matching Web Portal design tokens.
- **Navigation (`main.dart`)**:
  - Bottom Navigation Bar with 4 primary destinations:
    1. **Surveillance Dashboard** (`dashboard_screen.dart`): Portfolio cards, FII/DII flow bar, holdings list.
    2. **Alerts Feed** (`alerts_screen.dart`): Real-time alerts stream with Confluence Radar modal and Alpha Card share sheet.
    3. **Watchlist** (`watchlist_screen.dart`): Dynamic NSE/BSE ticker search, Demat sync toggle, stock cards with Target/SL.
    4. **Settings / Control Center** (`notification_settings_screen.dart`): Broker credentials, Telegram pairing, Audit Ledger (`audit_ledger_screen.dart`), and Strategy Backtester (`backtest_screen.dart`).
- **Deep Linking & Lifecycle Auto-Capture**:
  - Listens for `stokvigil://breeze-callback?apisession=...` intents.
  - `WidgetsBindingObserver` in `icici_credentials_screen.dart` auto-detects and pastes session token from clipboard when returning from browser.
- **Offline Bundled TradingView Charts (`candle_chart_screen.dart` & `candle_chart_modal.dart`)**:
  - Bundles `assets/js/lightweight-charts.standalone.production.js` locally to eliminate CDN failure or WebView white screens.
  - 1-Tap Landscape / Portrait orientation toggle (`SystemChrome.setPreferredOrientations`).
  - Bi-directional JavaScript `ChartChannel` bridge broadcasting crosshair coordinates into native OHLC header banner.
  - Configured with `EagerGestureRecognizer` for smooth pan and pinch-zoom.
- **Vector Broker Logos (`broker_icons.dart`)**:
  - CustomPainter implementations for ICICI Direct, Zerodha Kite, and Angel One logos.
- **Android ProGuard / R8 Obfuscation (`android/app/proguard-rules.pro`)**:
  - Enforces ProGuard code shrinking and obfuscation in `build.gradle` for production APKs.

---

## 10. MULTI-CHANNEL NOTIFICATION DISPATCHERS

### 10.1 Telegram Bot Cockpit (`@StokVigilAi_bot`)
- Formatted in clean HTML with HTML entity sanitization (`html_lib.escape`).
- Dynamic Live Market Snapshot: LTP, Day Change %, 15m ORB, Delivery %, 15m RSI, VWAP, F&O OI.
- Tactical Risk-Reward Levels: Entry Range, Tactical Resistance 1 (1.5x ATR), Expansion Resistance 2 (2.5x ATR), Protective Stop-Loss, R:R Ratio, Position Sizing (Recommended Qty & Capital at Risk).
- Inline Keyboard Buttons:
  - `[📊 StokVigil Chart]`: Deep-links to Web PWA (`WEB_PORTAL_URL/chart?symbol=...`) or TradingView.
  - `[💼 ICICI Direct]`: Deep-links to ICICI Direct order page.
  - `[🏛️ Exchange Live]`: Links to official NSE/BSE live quote page.
- Mandatory SEBI Non-Advisory Compliance Footnote on every card.

### 10.2 Firebase Cloud Messaging (FCM Push)
- Android Notification Channel: `stokvigil_high_priority_alerts` (`priority='high'`, `sound='default'`).
- Injects structured data payload (`symbol`, `action_bias`, `confluence_score`, `catalyst_type`) enabling tap-to-open trade calculators.

---

## 11. AUTOMATED MARKET CRON WORKFLOWS (GITHUB ACTIONS)

Configure 5 GitHub Actions workflows running strictly Monday through Friday:

1. **08:50 AM IST Demat Token Reminder (`morning_token_reminder.yml`)**:
   - Cron: `20 3 * * 1-5` (03:20 UTC)
   - Dispatches FCM and Telegram reminders to users whose ICICI session tokens are expired.
2. **09:00 AM IST Pre-Market War Room Briefing (`pre_market_war_room.yml`)**:
   - Cron: `30 3 * * 1-5` (03:30 UTC)
   - Calls `POST /api/cron/pre-market-briefing` with `X-Cron-Secret`.
   - Synthesizes NIFTY/SENSEX pre-open, India VIX, overnight global cues (Dow, Nasdaq, Nikkei), FII/DII net flows, and sector momentum. Executes automated 30-day alert retention pruning.
3. **5-Minute Market Surveillance Scanner (`5min_cron.yml`)**:
   - Cron: `45,50,55 3 * * 1-5`, `*/5 4-9 * * 1-5`, `0 10 * * 1-5` (03:45 UTC to 10:00 UTC)
   - Synchronously awaits `POST /api/cron/multi-user-scan` with `X-Cron-Secret` via `curl -s -m 480`. Guarantees 100% CPU allocation under Cloud Run free tier. Protected by `_scan_in_progress` concurrency lock.
4. **03:45 PM IST Post-Market Summary (`post_market_summary.yml`)**:
   - Cron: `15 10 * * 1-5` (10:15 UTC)
   - Calls `POST /api/cron/post-market-summary`. Dispatches closing bell scorecard (NIFTY/SENSEX closes, VIX, ADR, FII/DII cash turnover, sector leaders/laggards, verified Target 1 hit rate).
5. **Android Release APK Builder (`build_apk.yml`)**:
   - Compiles release APK strictly with `SUPABASE_ANON_KEY`, isolating `SUPABASE_SERVICE_ROLE_KEY` to guarantee administrative database keys are never leaked in client binaries.

---

## 12. ENVIRONMENT CONFIGURATION (`.env.example`)

```ini
ENVIRONMENT=production
APP_NAME=StokVigil AI
PACKAGE_ID=com.app.stokvigil

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
DATABASE_URL=postgresql://postgres.yourprojectref:yourpassword@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?pgbouncer=true

# Vault Encryption (Fernet AES-256)
ENCRYPTION_KEY=your-fernet-aes256-base64-key

# AI Engine
GEMINI_API_KEY=your-gemini-api-key

# Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
TELEGRAM_WEBHOOK_SECRET=your-telegram-webhook-secret
WEB_PORTAL_URL=https://app.stokvigil.com

# Cron & Admin Secrets
CRON_SECRET_KEY=your-cron-secret-key
ADMIN_SECRET_KEY=your-admin-secret-key

# Networking & CORS
STOKVIGIL_BACKEND_URL=https://your-backend.run.app
BACKEND_URL=https://your-backend.run.app
ALLOWED_ORIGINS=https://app.stokvigil.com,http://localhost:3000

# Next.js Client Properties
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
NEXT_PUBLIC_BACKEND_URL=https://your-backend.run.app

# Firebase
FIREBASE_CREDENTIALS_JSON=
GOOGLE_SERVICES_JSON=

# Institutional Master App Broker Credentials
ICICI_MASTER_APP_KEY=your-icici-direct-app-key
ICICI_MASTER_SECRET_KEY=your-icici-direct-secret-key
ZERODHA_MASTER_API_KEY=
ANGELONE_MASTER_API_KEY=
```

---

## 13. STEP-BY-STEP IMPLEMENTATION ROADMAP

Follow this sequence when executing the build:

1. **Step 1: Database Setup**:
   - Create Supabase project.
   - Run the 4 SQL migrations (`20260809_init_stokvigil.sql`, `20260822_enhance_stokalerts.sql`, `20260906_fii_dii_flows.sql`, `20260911_prune_old_alerts_cron.sql`).
   - Enable Email auth in Supabase Auth settings.

2. **Step 2: Backend Core & Security Layer**:
   - Implement `backend/app/config.py` with Pydantic settings.
   - Implement `backend/app/vault.py` with AES-256 Fernet.
   - Implement `backend/app/auth.py` with Supabase JWT validation and PII masking.
   - Implement `backend/app/db_pool.py` with `asyncpg` connection pooler for Port 6543.
   - Implement `backend/app/market_cache.py` with thread-safe in-memory caching and atomic live tick updates.

3. **Step 3: Quantitative & Market Engines**:
   - Implement `backend/app/technical_engine.py` (Indicators, Camarilla, TTM Squeeze, VWAP bands, ADX, ORB, circuit locks).
   - Implement `backend/app/flow_tracker.py` (Wyckoff VSA, dynamic F&O discovery, option chain analysis).
   - Implement `backend/app/fii_dii_tracker.py` (Akamai cookie bypass, daily flow ingestion, sentiment).
   - Implement `backend/app/macro_filter.py` (Direct v8 chart ingestion, 60s cache, ADR, sector alpha, War Room data).
   - Implement `backend/app/alert_limiter.py` (45-minute anti-fatigue state machine).
   - Implement `backend/app/backtester.py` (vectorized strategy replay).
   - Implement `backend/app/accuracy_verifier.py` (real candle price-tracking verification).

4. **Step 4: AI Agent Runner & Broker Adapter Layer**:
   - Implement `backend/app/brokers/` (`base.py`, `registry.py`, `icici_adapter.py`).
   - Implement `backend/app/agent_runner.py` (2-Tier Gatekeeper, dynamic factor weights, Google GenAI SDK integration with fallbacks, deterministic RAM math).
   - Implement `backend/app/notifications.py` (Telegram HTML formatting with inline buttons, FCM payload).

5. **Step 5: FastAPI Routes & Safeguards (`main.py`)**:
   - Implement sliding-window rate limiter with trusted proxy subnet check.
   - Wire all routes, order execution with 7 safeguards, background pre-warming, and synchronous multi-user scan.

6. **Step 6: Next.js 16 Web Portal (`web_portal/`)**:
   - Setup Next.js 16 App Router, Tailwind CSS, Design Tokens.
   - Build UI Atoms, Confluence Radar (SVG), Lightweight Candle Chart (TradingView v5), Alpha Card Modal (HTML5 Canvas).
   - Build Tabs (`HomeTab`, `AlertsTab`, `WatchlistTab`, `SettingsTab`, `AuditLedgerView`, `BacktestView`).
   - Build Modals (`TradeOrderModal`, `StockDetailModal`, `IciciKeyModal`).

7. **Step 7: Flutter Mobile App (`mobile_app/`)**:
   - Setup theme, models, services (`supabase_service.dart`, `api_service.dart`, `fcm_service.dart`).
   - Bundle `lightweight-charts.standalone.production.js` in assets.
   - Build screens (`dashboard_screen.dart`, `alerts_screen.dart`, `watchlist_screen.dart`, `candle_chart_screen.dart`, `audit_ledger_screen.dart`, `backtest_screen.dart`, `notification_settings_screen.dart`, `icici_credentials_screen.dart`).
   - Build custom widgets (CustomPainter Confluence Radar, Broker vector logos).
   - Configure deep links and ProGuard/R8 rules.

8. **Step 8: Automated Cron & CI/CD Pipelines**:
   - Setup GitHub Actions workflows for 5-minute scans, morning reminders, pre-market war room, post-market summary, and APK builds.
   - Verify all unit test suites (`pytest backend/tests`).
