# StokVigil AI (Package ID: `com.app.stokvigil`)
**100% Free AI-Powered Stock Alert & Market Intelligence Application**

StokVigil AI is an automated, unsleeping 5-minute market watchtower operating strictly during Indian Stock Exchange trading hours (09:15 AM to 03:30 PM IST). 

---

## 🛡️ Pure Intelligence & Quantitative Surveillance Guarantee
- **No Unsolicited Automated Trades**: The application never executes trades without user confirmation.
- **SEBI Non-Advisory Compliance**: All alerts are structured as objective **Quantitative Confluence Probability Scores** with mathematical risk-reward levels (RSI/MACD signals, VWAP, ATR dynamic stops, block/bulk deals, quarterly earnings surprises, debt shifts).
- **Bank-Grade Security**: Supabase Auth JWT token validation on all user endpoints (eliminating BOLA/IDOR), `X-Cron-Secret` header protection against spam/DoS, whitelisted CORS origins, AES-256 Fernet vault key encryption, and Android ProGuard/R8 code obfuscation.

---

## 🏗️ Tech Stack (100% Free Tier Architecture)
- **Mobile Frontend**: Flutter (Dart) for Android (`com.app.stokvigil`) & iOS (with R8 ProGuard code obfuscation).
- **Web Portal**: Next.js 14 (TypeScript) + Tailwind CSS (PWA Enabled, whitelisted CORS).
- **Backend API**: Python 3.11 + FastAPI containerized for Google Cloud Run (2M free requests/mo) / Render.
- **Security & Vault Layer**: `app/auth.py` (Supabase JWT Bearer validation & IDOR defense) + `app/vault.py` (Fernet AES-256 with PBKDF2HMAC).
- **AI Agent Engine**: `google-generativeai` powered by `gemini-3.6-flash` (Primary) with automated fallback to `gemini-2.5-flash`, `gemini-1.5-flash`, and an offline deterministic rule engine.
- **Quantitative Engines**:
  - `technical_engine.py`: Multi-timeframe (5m/15m/1D) RSI, MACD crossovers, Intraday VWAP, 14-period ATR, EMAs (20/50/200), and RSI Divergence detection.
  - `flow_tracker.py`: Delivery Volume % Estimation ($>50\%$ accumulation) and F&O Open Interest build-up dynamics.
  - `macro_filter.py`: India VIX Volatility Regime (`^INDIAVIX`), Sectoral Synchronization (`NIFTY IT`, `NIFTY AUTO`, etc.), and Forensic Health checks.
  - `alert_limiter.py`: 45-minute anti-fatigue cooldown state machine with Tier-1 emergency bypass.
- **Database & Vault**: Supabase PostgreSQL with Row-Level Security (RLS) & Fernet AES-256 encryption.
- **Integrations**: `breeze-connect` (ICICI Demat holdings), `yfinance` (Real-time ticks & valuation), `feedparser` (Google News RSS & Exchange Filings).
- **Alert Dispatch**: Firebase Cloud Messaging (FCM High-Priority) + Multi-Tenant Telegram Bot API (`@StokVigilAi_bot`).

---

## 🧠 AI Agent Evaluation Engine & Factor Weights

Every 5 minutes during NSE market hours (09:15–15:30 IST), StokVigil AI compiles real-time portfolio holdings, technicals, institutional flows, and news into a multi-factor score:

$$\text{Confluence Score} = (0.30 \times \text{Technical}) + (0.25 \times \text{Flow}) + (0.25 \times \text{Fundamental}) + (0.20 \times \text{News/Catalysts})$$

### Model Fallback Hierarchy
```python
# Try Gemini 3.6 Flash first (Primary Model), fallback to 2.5 Flash and 1.5 Flash
for model_name in ['gemini-3.6-flash', 'gemini-2.5-flash', 'gemini-1.5-flash']:
```
1. **Primary Model**: `gemini-3.6-flash` — Ultra low-latency, high-frequency financial catalyst reasoning with strict JSON schema enforcement.
2. **First Fallback**: `gemini-2.5-flash` — High-efficiency secondary engine.
3. **Second Fallback**: `gemini-1.5-flash` — Fast structured JSON analysis.
4. **Deterministic Rule Engine**: Offline fallback engine ensuring 100% continuous monitoring uptime if external APIs encounter rate limits.

### Multi-Dimensional Signal Classifications
- **`🟢 ACCUMULATE / BUY WATCH`**: High-conviction setups ($\text{Score} \ge 75$) with bullish MACD, RSI, and Delivery accumulation above VWAP.
- **`🔴 PROFIT BOOK / SELL WATCH`**: High-risk setups ($\text{Score} \le 35$) with bearish divergence or technical breakdown.
- **`🟡 TRAILING STOP-LOSS TRIGGER`**: Position-aware trigger for Demat holdings when unrealized profit $>5\%$ and momentum stalls.
- **`⚡ Volume Surge`**: Institutional volume spikes ($> 2.0\text{x}$ 20-period MA) with delivery accumulation.
- **`📈 Earnings Beat`**: Revenue/P&L outperformance, EBITDA expansion, and positive quarterly surprises.
- **`🚀 Price Breakout`**: Technical momentum breaks above key 52-week or moving-average resistance levels.
- **`📊 FII / Block Deals`**: Institutional bulk/block deals and institutional flow entries.
- **`⚪ Hold / Neutral`**: Moderate-impact events and maintenance signals.

---

## 📱 Push Notifications & Telegram Alerts Architecture

### 1. Firebase Cloud Messaging (FCM)
- **High-Priority Lock-Screen Channel**: `stokvigil_high_priority_alerts` with dedicated sound and vibration patterns.
- **Automated Token Sync**: The Android app automatically retrieves the device token on startup, login, or token refresh (`onTokenRefresh`), and synchronizes `fcm_device_token` with Supabase `profiles`.

### 2. Multi-Tenant Telegram Bot (`@StokVigilAi_bot`)
- **Single Central Bot Architecture**: A single bot handle (`@StokVigilAi_bot`) serves unlimited individual users with complete tenant isolation.
- **1-Tap Deep Link Pairing**: Clicking **`Connect Telegram →`** opens `https://t.me/StokVigilAi_bot?start=<USER_ID>`.
- **Rich HTML Cards & Inline Buttons**: Every alert includes color-coded badges, Demat position snapshot, tactical levels (Entry, Target 1, Target 2, Stop-Loss, R:R), and interactive buttons (`TradingView Chart`, `ICICI Direct`).

---

## 👁️ Demat Portfolio Privacy Masking & Live Indicator
- **Demat Portfolio Privacy Masking**: Total Portfolio Value, Returns, P&L %, Invested value, and Holdings are masked by default (`₹ • • • • • •` / `••••••`). An interactive **`👁️ Show / Hide`** toggle allows 1-tap unmasking on Mobile & Web.
- **Pulsing Live NSE/BSE Market Indicator**: Animated `BlinkingLiveDot` with synchronized blinking `NSE/BSE LIVE 09:15–15:30` on mobile and CSS live glow on web.

---

## 🔍 Dynamic Stock Search & Exchange Validation (Zero Hardcoding)
- **Live Autocomplete (`GET /api/stocks/search?q={query}`)**: As users type, the system queries live NSE (`.NS`) and BSE (`.BO`) exchange feeds in real-time, displaying verified company names, symbols, and sectors.
- **Dual-Stage Exchange Validation (`GET /api/stocks/validate?symbol={sym}`)**: Every custom stock is checked against live market tick data before being saved. Dummy, non-existent, or misspelled tickers (e.g. `NE`, `ASDFGH`) are blocked and rejected from entering the database.
- **Demat Auto-Sync**: Automatically imports active ICICI Demat holdings into personal watchlists with one click.

---

## 🔑 ICICI Direct Breeze API Authentication & Key Vault Workflow

Per SEBI regulations, broker session tokens expire daily. StokVigil AI provides an automated, secure workflow for mobile and web:

1. **Broker App Configuration**: In the [ICICI Direct Breeze Portal](https://api.icicidirect.com/apiuser/home), register your App with **Redirect URL** set to:
   - **Official URL**: `https://stokvigil-ai.vercel.app/api/auth/icici-callback`
2. **Permanent Key Pre-Fill & Decryption (`GET /api/user/credentials`)**:
   - `App Key` and `Secret Key` are entered **only once** and encrypted in the vault.
   - On subsequent days, opening the setup screen **automatically fetches and decrypts** the permanent keys.
   - Includes **`👁️ Show / Hide`** privacy eye toggle buttons on both key inputs.
3. **1-Tap In-App Login & Session Auto-Capture (Mobile)**:
   - Tap **`⚡ 1-Tap Login & Auto-Capture Token`** $\rightarrow$ Secure In-App WebView sheet opens.
   - User logs in with ICICI credentials & TOTP OTP.
   - App intercepts the `apisession` query parameter instantly, closes the webview, auto-populates the session token, and triggers AES-256 encrypted auto-save.
4. **Session Token Validation & Instant Upsert (`POST /api/user/credentials`)**:
   - The **`🔐 Encrypt & Save Key`** button is enabled **only when a valid session token is provided**.
   - Saving performs an authenticated, conflict-free database upsert (`onConflict: 'user_id'`), instantly syncing live Demat holdings.

---

## 🗑️ Account Deletion & Privacy Compliance

Users can permanently delete their account directly from the **Settings** page:
- **Danger Zone**: Includes an interactive **2-Step Verification Modal** (requires typing `DELETE`).
- **Cascade Deletion (`POST /api/user/delete-account`)**:
  - Wipes all encrypted ICICI Breeze session tokens & API keys from `user_credentials`.
  - Removes all custom watchlist entries from `user_watchlists`.
  - Clears registered device push notification tokens and Telegram bindings.
  - Permanently deletes the authentication identity from Supabase Auth (`auth.admin.delete_user`).

---

## 🚀 Step-by-Step Setup & Deployment Guide

### 1. Database Setup (Supabase PostgreSQL)
1. Log into your [Supabase Dashboard](https://supabase.com).
2. Open the SQL Editor and execute the migration scripts in order:
   - `supabase/migrations/20260809_init_stokvigil.sql`
   - `supabase/migrations/20260822_enhance_stokalerts.sql`
3. Copy your `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY`.

### 2. Backend Deployment (FastAPI on Cloud Run / Local)
1. Navigate to `backend/`:
   ```bash
   cd backend
   python -m venv .venv
   .\.venv\Scripts\pip.exe install -r requirements.txt
   ```
2. Set environment variables in `backend/.env`:
   ```env
   ENVIRONMENT=production
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-supabase-anon-key
   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
   ENCRYPTION_KEY=d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3c=
   GEMINI_API_KEY=your-gemini-api-key
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
   CRON_SECRET_KEY=stokvigil_cron_default_secret_2026
   ALLOWED_ORIGINS=https://stokvigil-ai.vercel.app,http://localhost:3000,http://localhost:8000
   ```
3. Run test suite:
   ```bash
   .\.venv\Scripts\python.exe tests/test_institutional_engine.py
   ```
4. Start backend server:
   ```bash
   .\.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### 3. Telegram Bot Setup (@BotFather)
1. Open Telegram and search for `@BotFather`.
2. Send `/newbot`, name it `StokVigil AI Bot`, and set username to `StokVigilAi_bot`.
3. Copy the HTTP API token and set it in your backend environment as `TELEGRAM_BOT_TOKEN`.
4. Register the Webhook:
   ```bash
   curl -X POST "https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/setWebhook?url=<YOUR_BACKEND_URL>/api/telegram/webhook"
   ```

### 4. Running the Web Portal (Next.js PWA)
1. Navigate to `web_portal/`:
   ```bash
   cd web_portal
   npm install
   npm run dev
   ```
2. Access the portal at `http://localhost:3000`.

### 5. Running the Flutter Android App (`com.app.stokvigil`)
1. Navigate to `mobile_app/`:
   ```bash
   cd mobile_app
   flutter run
   ```

---

## ⏰ 5-Minute Indian Market Hours Cron
The GitHub Action workflow (`.github/workflows/5min_cron.yml`) executes `POST /api/cron/multi-user-scan` with `-H "X-Cron-Secret: ${{ secrets.CRON_SECRET_KEY }}"` every 5 minutes Monday–Friday from 09:15 AM to 03:30 PM IST (`03:45 UTC` to `10:00 UTC`).
