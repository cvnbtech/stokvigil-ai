-- ==============================================================================
-- Migration: 20260927_add_broker_id_to_user_credentials.sql
-- Description: Adds broker_id column to user_credentials for multi-broker support
--              with default 'icici'.
-- ==============================================================================

-- 1. Add broker_id column if it doesn't already exist
ALTER TABLE public.user_credentials
ADD COLUMN IF NOT EXISTS broker_id TEXT DEFAULT 'icici';

-- 2. Populate default for existing rows if null
UPDATE public.user_credentials
SET broker_id = 'icici'
WHERE broker_id IS NULL;
