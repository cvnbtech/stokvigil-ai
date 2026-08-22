-- ====================================================================
-- StokVigil AI (com.app.stokvigil) - Enhanced Schema Migration
-- Migration File: 20260822_enhance_stokalerts.sql
-- Description: Adds action_bias, tactical_levels, and multi-tenant performance indexes
-- ====================================================================

-- 1. Add new Catalyst Enum values if not already present
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'catalyst_type_enum') THEN
        CREATE TYPE catalyst_type_enum AS ENUM (
            'BLOCK_DEAL',
            'EARNINGS_BEAT',
            'DEBT_CHANGE',
            'PRICE_BREAKOUT',
            'NEWS_CATALYST',
            'VOLUME_SURGE',
            'TECHNICAL_BREAKOUT',
            'TRAILING_STOP_TRIGGER'
        );
    ELSE
        -- Alter existing enum to support new catalyst types safely
        ALTER TYPE catalyst_type_enum ADD VALUE IF NOT EXISTS 'VOLUME_SURGE';
        ALTER TYPE catalyst_type_enum ADD VALUE IF NOT EXISTS 'TECHNICAL_BREAKOUT';
        ALTER TYPE catalyst_type_enum ADD VALUE IF NOT EXISTS 'TRAILING_STOP_TRIGGER';
    END IF;
END$$;

-- 2. Add columns to profiles for alert customization
ALTER TABLE public.profiles 
    ADD COLUMN IF NOT EXISTS alert_sensitivity TEXT DEFAULT 'HIGH',
    ADD COLUMN IF NOT EXISTS execution_mode TEXT DEFAULT 'CONFIRM',
    ADD COLUMN IF NOT EXISTS tnc_accepted BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS tnc_accepted_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS demat_auto_sync BOOLEAN DEFAULT FALSE;

-- 3. Add indexes for high-throughput 5-minute cron scanning
CREATE INDEX IF NOT EXISTS idx_stok_alerts_created_at ON public.stok_alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_stok_alerts_symbol_user ON public.stok_alerts(symbol, user_id);
CREATE INDEX IF NOT EXISTS idx_profiles_telegram ON public.profiles(telegram_chat_id) WHERE telegram_enabled = true;
