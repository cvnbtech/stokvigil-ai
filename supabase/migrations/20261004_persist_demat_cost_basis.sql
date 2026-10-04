-- ====================================================================
-- StokVigil AI (com.app.stokvigil) - Persist Demat Cost Basis Migration
-- Migration File: 20261004_persist_demat_cost_basis.sql
-- Description: Adds average_buy_price, quantity, and last_synced_at to user_watchlists
-- ====================================================================

ALTER TABLE public.user_watchlists
    ADD COLUMN IF NOT EXISTS average_buy_price NUMERIC DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS quantity INTEGER DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMPTZ DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_watchlists_user_auto_sync 
    ON public.user_watchlists(user_id, is_auto_synced);
