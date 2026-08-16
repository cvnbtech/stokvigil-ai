# StokVigil AI (Package ID: `com.app.stokvigil`)
**100% Free AI-Powered Stock Alert & Market Intelligence Application**

StokVigil AI is an automated, unsleeping 5-minute market watchtower operating strictly during Indian Stock Exchange hours (09:15 AM to 03:30 PM IST). 

---

## 🛡️ Pure Intelligence & Non-Advisory Guarantee
- **No Trade Execution**: The application never executes automated trades or places orders on demat accounts.
- **No SEBI Advisory**: All alerts stick 100% to factual data (block/bulk deals, quarterly earnings surprises, debt-to-equity shifts, price breakouts).

---

## 🏗️ Tech Stack (100% Free Tier Architecture)
- **Mobile Frontend**: Flutter (Dart) for Android (`com.app.stokvigil`) & iOS.
- **Web Portal**: Next.js 14 (TypeScript) + Vanilla / Tailwind CSS (PWA Enabled).
- **Backend API**: Python 3.11 + FastAPI containerized for Google Cloud Run (2M free requests/mo).
- **AI Agent Engine**: `google-generativeai` powered by `gemini-3.6-flash` (Primary) with automated fallback to `gemini-2.5-flash` and `gemini-1.5-flash`.
- **Database & Vault**: Supabase PostgreSQL with Row-Level Security (RLS) & Fernet AES-256 encryption.
- **Integrations**: `breeze-connect` (ICICI Demat holdings), `yfinance` (Valuation metrics), `feedparser` (Google News RSS).
- **Alert Dispatch**: Firebase Cloud Messaging (FCM) + Telegram Bot API.

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

## 🎨 App Icon & Visual Design System
- **Master App Launcher Icon**: Full-bleed squircle icon (`#0D111E` background, ambient cyan backlight, glowing white **S** + cyan-emerald growth arrow **V**).
- **Mobile Assets**: Located at `mobile_app/assets/app_icon.png` & `app_icon.svg`, automatically configured for Android density targets (`mipmap-mdpi` through `mipmap-xxxhdpi` standard and round launcher icons).
- **Web Portal PWA Icons**: Located at `web_portal/public/icon-192.png`, `icon-512.png`, `apple-touch-icon.png`, and `favicon.ico`.
- **100% Matched Auth Screens**: Android App Sign-In and Web Portal Sign-In feature identical dark radial ambient backdrops, brand typography, 1-tap Google SSO, and shared master `app_icon.png` emblem.

---

## 🚀 Step-by-Step Setup & Deployment Guide

### 1. Database Setup (Supabase PostgreSQL)
1. Log into your [Supabase Dashboard](https://supabase.com).
2. Open the SQL Editor and execute the migration script located at:
   `supabase/migrations/20260809_init_stokvigil.sql`
3. Copy your `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.

### 2. Backend Deployment (Google Cloud Run)
1. Navigate to `backend/`:
   ```bash
   cd backend
   ```
2. Copy `.env.example` to `.env` and fill in your keys:
   ```bash
   cp ../.env.example .env
   ```
3. Run the Cloud Run deployment script:
   ```bash
   chmod +x cloudrun.sh
   ./cloudrun.sh
   ```

### 3. Telegram Bot Setup (@BotFather)
1. Open Telegram and search for `@BotFather`.
2. Send `/newbot`, name it `StokVigil AI Bot`, and choose a username (e.g., `StokVigilAi_bot`).
3. Copy the HTTP API token and set it in your `.env` as `TELEGRAM_BOT_TOKEN`.
4. Set the Telegram Webhook pointing to your deployed Cloud Run URL:
   ```bash
   curl -X POST "https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/setWebhook?url=<YOUR_CLOUD_RUN_URL>/api/telegram/webhook"
   ```

### 4. Compiling the Flutter Android APK (`com.app.stokvigil`)
1. Navigate to `mobile_app/`:
   ```bash
   cd mobile_app
   ```
2. Fetch dependencies:
   ```bash
   flutter pub get
   ```
3. Build release APK:
   ```bash
   flutter build apk --release
   ```
4. Output APK location: `mobile_app/build/app/outputs/flutter-apk/app-release.apk`.

### 5. Running the Web Portal (Next.js PWA)
1. Navigate to `web_portal/`:
   ```bash
   cd web_portal
   npm install
   npm run dev
   ```
2. Access the portal at `http://localhost:3000`.

---

## 🔑 ICICI Direct Breeze API Authentication Workflow

Per SEBI regulations, broker session tokens expire daily at midnight IST. StokVigil AI provides an automated flow for both mobile and web:

1. **Broker App Configuration**: In the [ICICI Direct Breeze Portal](https://api.icicidirect.com/apiuser/home), register your App with **Redirect URL** set to:
   - Web/Cloud: `https://stokvigil-ai.vercel.app/callback` (or `https://stokvigil-ai.vercel.app/api/auth/icici-callback`)
   - Localhost / Desktop: `https://127.0.0.1`
2. **1-Tap Login**: In the StokVigil app or web portal, enter your `App Key` & `Secret Key` and tap **`🌐 1-Tap ICICI Web Login`**.
3. **Automated Token Capture**:
   - Web Portal automatically routes the redirect to `/callback?apisession=...`.
   - Displays a 1-tap **`📋 Copy Session Token`** button and a **`📱 1-Tap Open in StokVigil App →`** deep link (`stokvigil://breeze-callback`).
4. **AES-256 Client-Side Vault**: Tokens are encrypted using AES-256 Fernet before storage, securing all broker interactions.

---

## 🗑️ Account Deletion & Privacy Compliance

Users can permanently delete their account and all associated data directly from the **Settings** page:
- **Danger Zone**: Includes an interactive **2-Step Verification Modal** with safety text validation (user must type `DELETE`).
- **Cascade Deletion (`POST /api/user/delete-account`)**:
  - Wipes all encrypted ICICI Breeze session tokens & API keys from `user_credentials`.
  - Removes all custom watchlist entries from `user_watchlists`.
  - Clears registered device push notification tokens and Telegram bindings from `user_devices`.
  - Permanently deletes the authentication identity from Supabase Auth (`auth.admin.delete_user`).
- **Post-Deletion Teardown**: Clears on-device cache, signs out active sessions, and presents a confirmation message before returning to the login screen.

---

## ⏰ 5-Minute Indian Market Hours Cron
The GitHub Action workflow (`.github/workflows/5min_cron.yml`) automatically executes `POST /api/cron/multi-user-scan` every 5 minutes Monday–Friday from 09:15 AM to 03:30 PM IST (03:45 UTC to 10:00 UTC). Add `STOKVIGIL_BACKEND_URL` to your GitHub Repository Secrets.

