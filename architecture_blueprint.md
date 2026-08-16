# StokVigil AI — System Architecture Blueprint & Design Specification
**Package Name:** `com.app.stokvigil`  
**Deployment Target:** Google Cloud Run (Free Tier) + Supabase + Firebase FCM + Telegram Bot API  
**Target Platform:** Flutter (Android / iOS) & Next.js 14 PWA  

---

## 1. System Purpose & Pure Intelligence Guarantee
StokVigil AI is an automated, unsleeping market watchtower operating strictly during Indian Stock Exchange hours (09:15 AM – 03:30 PM IST). 

> **Mandatory Operational Constraint:**  
> The system **does not execute trades** and **does not issue SEBI-registered financial advisory tips** (e.g. "BUY AT 200, TARGET 250"). It fetches real-time data from ICICI Demat accounts (via Breeze API), Google News RSS feeds, and Yahoo Finance (`yfinance`), feeds the facts into the Gemini AI Agent Engine, filters out market noise, and dispatches **purely factual data alerts** (catalysts, volume spikes, block/bulk deals, quarterly result deviations, debt shifts) directly to user mobile devices and Telegram chats.

---

## 2. End-to-End System Data Flow

```mermaid
flowchart TD
    subgraph Clients["User Interaction Layer"]
        A1["Flutter Mobile App (com.app.stokvigil)"]
        A2["Next.js 14 Web PWA"]
        A3["Telegram Messenger (@StokVigilBot)"]
    end

    subgraph AuthVault["Authentication & Security Layer"]
        B1["Supabase Auth (Email / Google OAuth)"]
        B2["PostgreSQL RLS (Row Level Security)"]
        B3["FastAPI Crypto Vault (AES-256 Fernet)"]
    end

    subgraph DataIntegrations["External Market Integrations"]
        C1["ICICI Breeze Connect API (Holdings/Positions)"]
        C2["yfinance API (PE, Debt/Eq, Live Prices)"]
        C3["Google News RSS (Block Deals, Results)"]
    end

    subgraph Engine["AI Agent Engine (FastAPI on Cloud Run)"]
        D1["5-Min Market Scheduler (GitHub Actions Cron)"]
        D2["Gemini AI Evaluation Agent (3.6 Flash -> 2.5 Flash -> 1.5 Flash)"]
        D3["Noise Filter & Impact Calculator (1-100 Score)"]
    end

    subgraph Dispatch["Multi-Channel Notification Dispatcher"]
        E1["Firebase Cloud Messaging (FCM Lock-screen)"]
        E2["Telegram Bot API (Markdown Chat Alerts)"]
    end

    A1 -->|OAuth & Session Token| B1
    A2 -->|Login & Setup| B1
    B1 -->|Retrieve Encrypted Keys| B3
    D1 -->|Triggers /api/cron/multi-user-scan| D2
    B3 -->|Decrypt App Key & Token| C1
    D2 -->|Fetch Demat Holdings| C1
    D2 -->|Fetch Valuation & Debt| C2
    D2 -->|Fetch Catalysts & News| C3
    C1 & C2 & C3 --> D3
    D3 -->|Impact Score >= 60| E1 & E2
    E1 -->|Push Notification| A1
    E2 -->|Styled Alert Message| A3
```

---

## 2.1 AI Agent Evaluation Engine & Models

Every 5 minutes during Indian market trading hours (`09:15–15:30 IST`), `agent_runner.py` compiles real-time portfolio holdings, fundamental valuations (P/E, Debt-to-Equity), and live RSS feeds into a strict evaluation prompt.

### Model Execution Fallback Chain
1. **Primary Model**: `gemini-3.6-flash` — High-frequency financial catalyst evaluation with structured JSON output.
2. **First Fallback**: `gemini-2.5-flash` — Low-latency secondary reasoning engine.
3. **Second Fallback**: `gemini-1.5-flash` — Reliable structured payload processor.
4. **Offline Rule Engine**: Deterministic fallback algorithm ensuring 100% uptime when external AI endpoints are unreachable.

### Supported Alert Categories
- `⚡ Volume Surge` (Volume breaks)
- `🔥 High Impact / Strong Buy` (Score $\ge 80\%$)
- `📈 Earnings Beat` (Quarterly profit & margin surprise)
- `🚀 Price Breakout` (52-week & technical level breaks)
- `📊 FII Buying` (Institutional block & bulk deals)
- `⚪ Hold / Neutral` (Maintenance watch signals)

---

## 3. Database Architecture (Supabase PostgreSQL + RLS)

### Tables Definition
1. **`profiles`**: Primary user identity and notification endpoints.
2. **`user_credentials`**: Encrypted ICICI Breeze API credentials (AES-256 Fernet), restricted by RLS to `auth.uid() = user_id`.
3. **`user_watchlists`**: Tracks Demat holdings (auto-synced) and manually added NSE symbols.
4. **`stok_alerts`**: Persistent ledger of evaluated catalysts, factual metrics snapshots, impact scores, and dispatch metrics.

---

## 4. Telegram Integration Flow

1. **Bot Setup**: The user opens Telegram and searches for `@StokVigilBot` or clicks the link in the StokVigil app (`t.me/StokVigilBot?start=USER_ID`).
2. **Account Linking**: The bot receives the `/start <USER_ID>` deep link payload via Webhook (`/api/telegram/webhook`).
3. **Registration**: The FastAPI backend maps `chat_id` to the user's `profiles` record in Supabase and sets `telegram_enabled = true`.
4. **Instant Alerts**: During 5-minute scans, high-impact alerts formatted in Telegram MarkdownV2 (with green/yellow/red impact emojis) are pushed to the user's chat.

---

## 5. Directory Structure in `G:\stokvigil-ai`

```
G:\stokvigil-ai\
├── architecture_blueprint.md
├── .env.example
├── README.md
├── supabase/
│   └── migrations/
│       └── 20260809_init_stokvigil.sql
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── vault.py
│   │   ├── notifications.py
│   │   ├── agent_runner.py
│   │   └── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── cloudrun.sh
│   └── render.yaml
├── mobile_app/
│   ├── pubspec.yaml
│   ├── assets/
│   │   ├── app_icon.png
│   │   └── app_icon.svg
│   ├── android/app/src/main/res/mipmap-*/
│   │   ├── ic_launcher.png
│   │   └── ic_launcher_round.png
│   └── lib/
│       ├── main.dart
│       ├── config/theme.dart
│       ├── models/models.dart
│       ├── services/
│       │   ├── supabase_service.dart
│       │   ├── api_service.dart
│       │   └── fcm_service.dart
│       └── screens/
│           ├── onboarding_modal.dart
│           ├── auth_screen.dart
│           ├── icici_credentials_screen.dart
│           ├── dashboard_screen.dart
│           ├── alerts_screen.dart
│           ├── notification_settings_screen.dart
│           └── watchlist_screen.dart
├── web_portal/
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── public/
│   │   ├── manifest.json
│   │   ├── app_icon.png
│   │   ├── app_icon.svg
│   │   ├── apple-touch-icon.png
│   │   ├── favicon.ico
│   │   ├── icon-192.png
│   │   └── icon-512.png
│   └── src/
│       └── app/
│           ├── layout.tsx
│           ├── page.tsx
│           ├── callback/
│           │   └── page.tsx
│           └── api/
│               ├── auth/icici-callback/route.ts
│               └── icici/callback/route.ts
└── .github/
    └── workflows/
        ├── 5min_cron.yml
        └── android_build.yml
```

---

## 7. REST API & Endpoint Specifications

| Endpoint | Method | Purpose |
| :--- | :---: | :--- |
| `/api/user/credentials` | `POST` | Stores AES-256 encrypted ICICI App Key, Secret Key, and Session Token |
| `/api/user/portfolio` | `GET` | Returns live portfolio holdings, valuation, and P&L breakdown |
| `/api/user/alerts` | `GET` | Retrieves historical catalyst alerts with confidence metrics |
| `/api/user/delete-account` | `POST` | Cascades permanent deletion across credentials, watchlists, devices, and auth identity |
| `/api/auth/register-device` | `POST` | Registers FCM notification token and Telegram chat ID |
| `/api/cron/multi-user-scan` | `POST` | Evaluates all active portfolios/watchlists every 5 minutes during NSE hours |
| `/api/telegram/webhook` | `POST` | Telegram bot interactive command handler (`/start`, `/status`, `/help`) |

