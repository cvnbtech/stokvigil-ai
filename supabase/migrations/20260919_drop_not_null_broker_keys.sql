-- ==============================================================================
-- Migration: 20260919_drop_not_null_broker_keys.sql
-- Description: Drop NOT NULL constraint on encrypted_app_key and encrypted_secret_key
--              in public.user_credentials.
--
-- Rationale:
-- Under StokVigil AI's Pure Master App Publisher Model, institutional developer
-- credentials (ICICI_MASTER_APP_KEY, ICICI_MASTER_SECRET_KEY) are managed
-- server-side in backend environment secrets. End users only authenticate and
-- provide their daily broker session tokens. Dropping NOT NULL allows the database
-- to store strictly user session tokens with zero redundant master key storage.
-- ==============================================================================

-- 1. Make developer key columns nullable
ALTER TABLE public.user_credentials 
  ALTER COLUMN encrypted_app_key DROP NOT NULL,
  ALTER COLUMN encrypted_secret_key DROP NOT NULL;

-- 2. Clean up existing rows: NULL out redundant stored master keys
UPDATE public.user_credentials 
SET encrypted_app_key = NULL, 
    encrypted_secret_key = NULL;
