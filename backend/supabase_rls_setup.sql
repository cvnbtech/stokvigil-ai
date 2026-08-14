-- ============================================================================
-- STOKVIGIL AI — COMPLETE SUPABASE DATABASE SCHEMA & RLS PROTECTION SCRIPT
-- Run this script in your Supabase Dashboard SQL Editor (https://supabase.com/dashboard/project/_/sql)
-- Matches exact table name: public.stok_alerts
-- ============================================================================

-- 1. Create Catalyst Type Enum
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'catalyst_type_enum') THEN
        CREATE TYPE catalyst_type_enum AS ENUM (
            'BLOCK_DEAL',
            'EARNINGS_BEAT',
            'DEBT_CHANGE',
            'PRICE_BREAKOUT',
            'NEWS_CATALYST'
        );
    END IF;
END$$;

-- 2. Create Profiles Table (Linked to Supabase Auth)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    fcm_device_token TEXT DEFAULT NULL,
    telegram_chat_id TEXT DEFAULT NULL,
    telegram_enabled BOOLEAN DEFAULT FALSE,
    tnc_accepted BOOLEAN DEFAULT TRUE,
    tnc_accepted_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS on profiles
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view their own profile" ON public.profiles;
CREATE POLICY "Users can view their own profile"
    ON public.profiles FOR SELECT
    USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update their own profile" ON public.profiles;
CREATE POLICY "Users can update their own profile"
    ON public.profiles FOR UPDATE
    USING (auth.uid() = id);

DROP POLICY IF EXISTS "Service role full access on profiles" ON public.profiles;
CREATE POLICY "Service role full access on profiles"
    ON public.profiles FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- Trigger to automatically create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, created_at)
    VALUES (NEW.id, NEW.email, NOW())
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();


-- 3. Create User Credentials Table (AES-256 Encrypted Vault)
CREATE TABLE IF NOT EXISTS public.user_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE UNIQUE,
    encrypted_app_key TEXT NOT NULL,
    encrypted_secret_key TEXT NOT NULL,
    encrypted_session_token TEXT NOT NULL,
    token_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS on user_credentials
ALTER TABLE public.user_credentials ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view their own credentials" ON public.user_credentials;
CREATE POLICY "Users can view their own credentials"
    ON public.user_credentials FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert/update their own credentials" ON public.user_credentials;
CREATE POLICY "Users can insert/update their own credentials"
    ON public.user_credentials FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update existing credentials" ON public.user_credentials;
CREATE POLICY "Users can update existing credentials"
    ON public.user_credentials FOR UPDATE
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role full access on user_credentials" ON public.user_credentials;
CREATE POLICY "Service role full access on user_credentials"
    ON public.user_credentials FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');


-- 4. Create User Watchlists Table
CREATE TABLE IF NOT EXISTS public.user_watchlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    is_auto_synced BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, symbol)
);

-- Enable RLS on user_watchlists
ALTER TABLE public.user_watchlists ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage their watchlists" ON public.user_watchlists;
CREATE POLICY "Users can manage their watchlists"
    ON public.user_watchlists FOR ALL
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role full access on user_watchlists" ON public.user_watchlists;
CREATE POLICY "Service role full access on user_watchlists"
    ON public.user_watchlists FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');


-- 5. Create Stok Alerts Ledger Table (Correct table name: stok_alerts)
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

-- Enable RLS on stok_alerts
ALTER TABLE public.stok_alerts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view their own alerts" ON public.stok_alerts;
CREATE POLICY "Users can view their own alerts"
    ON public.stok_alerts FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role full access on stok_alerts" ON public.stok_alerts;
CREATE POLICY "Service role full access on stok_alerts"
    ON public.stok_alerts FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');


-- 6. Indexes for High-Performance Queries
CREATE INDEX IF NOT EXISTS idx_watchlists_user ON public.user_watchlists(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_user_date ON public.stok_alerts(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_symbol ON public.stok_alerts(symbol);
CREATE INDEX IF NOT EXISTS idx_credentials_date ON public.user_credentials(token_date);
