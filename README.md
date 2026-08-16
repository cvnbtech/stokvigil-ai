# StokVigil AI (Package ID: `com.app.stokvigil`)
**100% Free AI-Powered Stock Alert & Market Intelligence Application**

StokVigil AI is an automated, unsleeping 5-minute market watchtower operating strictly during Indian Stock Exchange trading hours (09:15 AM to 03:30 PM IST). 

---

## 🛡️ Pure Intelligence & Non-Advisory Guarantee
- **No Trade Execution**: The application never executes automated trades or places unsolicited orders on demat accounts.
- **No SEBI Advisory**: All alerts stick 100% to factual data (block/bulk deals, quarterly earnings surprises, debt-to-equity shifts, price breakouts).

---

## 🏗️ Tech Stack (100% Free Tier Architecture)
- **Mobile Frontend**: Flutter (Dart) for Android (`com.app.stokvigil`) & iOS.
- **Web Portal**: Next.js 14 (TypeScript) + Vanilla CSS (PWA Enabled).
- **Backend API**: Python 3.11 + FastAPI containerized for Google Cloud Run (2M free requests/mo) / Render.
- **AI Agent Engine**: `google-generativeai` powered by `gemini-3.6-flash` (Primary) with automated fallback to `gemini-2.5-flash` and `gemini-1.5-flash`.
- **Database & Vault**: Supabase PostgreSQL with Row-Level Security (RLS) & Fernet AES-256 encryption.
- **Integrations**: `breeze-connect` (ICICI Demat holdings), `yfinance` (Valuation metrics), `feedparser` (Google News RSS).
- **Alert Dispatch**: Firebase Cloud Messaging (FCM) + Multi-Tenant Telegram Bot API (`@StokVigilAi_bot`).

---

## 🧠 AI Agent Evaluation Engine & Models
StokVigil AI evaluates your portfolio and watchlist every 5 minutes during NSE market hours (09:15–15:30 IST).

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
- **`⚡ Volume Surge`**: Institutional volume spikes and sudden volume-to-average breaks.
- **`🔥 High Impact / Strong Buy`**: High-confidence catalysts ($\ge 80\%$) combining quarterly earnings beats and block deals.
- **`📈 Earnings Beat`**: Revenue/P&L outperformance, EBITDA expansion, and positive quarterly surprises.
- **`🚀 Price Breakout`**: Technical momentum breaks above key 52-week or moving-average resistance levels.
- **`📊 FII Buying`**: Institutional bulk/block deals and institutional flow entries.
- **`⚪ Hold / Neutral`**: Moderate-impact events and maintenance signals.

---

## 📱 Push Notifications & Telegram Alerts Architecture

### 1. Firebase Cloud Messaging (FCM)
- **OFF by default (`fcm_enabled = false`)**: Users have full control to toggle Push Notifications ON or OFF from the Settings screen.
- **Automated Token Sync**: The Android app automatically retrieves the device token on startup, login, or token refresh (`onTokenRefresh`), and synchronizes `fcm_device_token` with Supabase `profiles` without overriding user preferences.
- **CI/CD Integration**: GitHub Actions workflow (`build_apk.yml`) injects `GOOGLE_SERVICES_JSON` from GitHub Secrets directly into `mobile_app/android/app/google-services.json` before compilation.

### 2. Multi-Tenant Telegram Bot (`@StokVigilAi_bot`)
- **Single Central Bot Architecture**: A single bot handle (`@StokVigilAi_bot`) serves unlimited individual users with complete tenant isolation and private alert routing.
- **1-Tap Deep Link Pairing**: Clicking **`Connect →`** opens `https://t.me/StokVigilAi_bot?start=<USER_ID>`.
- **Private Webhook Routing**: The FastAPI webhook (`/api/telegram/webhook`) maps `chat_id` to the user's `profiles` record. Alerts for User A are delivered **only** to User A's private chat.

---

## 🎨 Design System & Settings Screen Hierarchy (Option 2)

```
┌────────────────────────────────────────────────────────┐
│ 🔔 REAL-TIME NOTIFICATIONS                             │
│   • Telegram Bot Channel (@StokVigilAi_bot)  [Connect] │
│   • AI Alert Frequency (High / All / FII)              │
│   • Push Notification Alerts (FCM Toggle: OFF/ON)      │
├────────────────────────────────────────────────────────┤
│ 🔒 SECURITY & ACCESS                                   │
│   • Change Password                                  → │
├────────────────────────────────────────────────────────┤
│ ⚠️ DANGER ZONE                                         │
│   • Delete Account & Data                              │
│   [ 🗑️ Delete My Account ] (2-Step Modal: Type DELETE) │
├────────────────────────────────────────────────────────┤
│ [ 🚪 Sign Out ] (Vibrant 4-Stop Brand Gradient Pill)   │
└────────────────────────────────────────────────────────┘
```

- **Cancel & Delete Account Buttons**: Dark glass Cancel (`#131A2B`) + Dynamic Fiery Red Gradient Delete button (`#EF4444` $\rightarrow$ `#DC2626` $\rightarrow$ `#B91C1C`) activated when `DELETE` is typed.
- **Sign Out CTA**: 4-Stop brand gradient pill button (`#00B4D8` $\rightarrow$ `#0284C7` $\rightarrow$ `#6366F1` $\rightarrow$ `#8B5CF6`) with glowing ambient shadow.

---

## 🔑 ICICI Direct Breeze API Authentication Workflow

Per SEBI regulations, broker session tokens expire daily at midnight IST. StokVigil AI provides an automated flow for both mobile and web:

1. **Broker App Configuration**: In the [ICICI Direct Breeze Portal](https://api.icicidirect.com/apiuser/home), register your App with **Redirect URL** set to:
   - **Official URL**: `https://stokvigil-ai.vercel.app/api/auth/icici-callback`
   - **Alternative**: `https://stokvigil-ai.vercel.app/callback`
2. **1-Tap Web Login**: In the app or web portal, enter your `App Key` & `Secret Key` and tap **`🌐 1-Tap ICICI Web Login`**.
3. **Automated Token Capture**:
   - `/api/auth/icici-callback` supports both `GET` query parameters and `POST` form data from ICICI Direct.
   - Displays a 1-tap **`📋 Copy Session Token`** button, **`📱 1-Tap Open in StokVigil App →`** deep link (`stokvigil://breeze-callback`), and **`🌐 Open in StokVigil Web Portal →`**.
4. **Direct Supabase Encrypted Vault**: Tokens are encrypted and saved directly to the user's `user_credentials` table via Supabase RLS policies.

---

## 🗑️ Account Deletion & Privacy Compliance

Users can permanently delete their account directly from the **Settings** page:
- **Danger Zone**: Includes an interactive **2-Step Verification Modal** (requires typing `DELETE`).
- **Cascade Deletion (`POST /api/user/delete-account`)**:
  - Wipes all encrypted ICICI Breeze session tokens & API keys from `user_credentials`.
  - Removes all custom watchlist entries from `user_watchlists`.
  - Clears registered device push notification tokens and Telegram bindings from `user_devices`.
  - Permanently deletes the authentication identity from Supabase Auth (`auth.admin.delete_user`).

---

## 🚀 Step-by-Step Setup & Deployment Guide

### 1. Database Setup (Supabase PostgreSQL)
1. Log into your [Supabase Dashboard](https://supabase.com).
2. Open the SQL Editor and execute the migration script located at:
   `backend/supabase_rls_setup.sql`
3. Copy your `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY`.

### 2. Backend Deployment (Google Cloud Run / Render)
1. Navigate to `backend/`:
   ```bash
   cd backend
   ```
2. Copy `.env.example` to `.env` and fill in your keys:
   ```bash
   cp ../.env.example .env
   ```
3. Set environment variables: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`.
4. Deploy using `cloudrun.sh` or Render.

### 3. Telegram Bot Setup (@BotFather)
1. Open Telegram and search for `@BotFather`.
2. Send `/newbot`, name it `StokVigil AI Bot`, and set username to `StokVigilAi_bot`.
3. Copy the HTTP API token and set it in your backend environment as `TELEGRAM_BOT_TOKEN`.
4. Register the Webhook:
   ```bash
   curl -X POST "https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/setWebhook?url=<YOUR_BACKEND_URL>/api/telegram/webhook"
   ```

### 4. Compiling the Flutter Android APK (`com.app.stokvigil`)
1. In your GitHub Repository $\rightarrow$ **Settings** $\rightarrow$ **Secrets and variables** $\rightarrow$ **Actions**, set:
   - `GOOGLE_SERVICES_JSON`: Content of your Android client `google-services.json` from Firebase Console.
   - `SUPABASE_URL`: Your Supabase URL.
   - `SUPABASE_ANON_KEY`: Your Supabase Anon Public Key.
   - `STOKVIGIL_BACKEND_URL`: Your backend URL.
2. Push to `main` branch or trigger **Build Flutter Android APK** workflow manually.
3. Download the compiled release APK from GitHub Actions artifacts.

### 5. Running the Web Portal (Next.js PWA)
1. Navigate to `web_portal/`:
   ```bash
   cd web_portal
   npm install
   npm run dev
   ```
2. Access the portal at `http://localhost:3000`.

---

## ⏰ 5-Minute Indian Market Hours Cron
The GitHub Action workflow (`.github/workflows/5min_cron.yml`) executes `POST /api/cron/multi-user-scan` every 5 minutes Monday–Friday from 09:15 AM to 03:30 PM IST (`03:45 UTC` to `10:00 UTC`).
