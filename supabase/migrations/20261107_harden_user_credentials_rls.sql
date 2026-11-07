-- ==============================================================================
-- StokVigil AI Migration: 20261107_harden_user_credentials_rls.sql
-- Description: Hardens user_credentials table security to eliminate cleartext / direct
--              client read/write exposure (CWE-312 / Finding 2).
--
-- Actions:
--   1. Drop client-side policies allowing direct SELECT, INSERT, UPDATE on user_credentials.
--   2. Ensure Row Level Security is strictly enabled.
--   3. Enforce service_role-only access policy for backend AES-256 Vault operations.
--   4. Revoke direct SELECT, INSERT, UPDATE privileges from 'anon' and 'authenticated' roles.
-- ==============================================================================

-- 1. Ensure Row Level Security is active
ALTER TABLE public.user_credentials ENABLE ROW LEVEL SECURITY;

-- 2. Drop all client-facing RLS policies that allowed direct client queries/modifications
DROP POLICY IF EXISTS "Users can view their own credentials" ON public.user_credentials;
DROP POLICY IF EXISTS "Users can insert/update their own credentials" ON public.user_credentials;
DROP POLICY IF EXISTS "Users can update existing credentials" ON public.user_credentials;
DROP POLICY IF EXISTS "Users can manage their credentials" ON public.user_credentials;
DROP POLICY IF EXISTS "Service role full access on user_credentials" ON public.user_credentials;

-- 3. Dedicated Service Role Policy: Backend API vault retains full operational control
CREATE POLICY "Service role full access on user_credentials"
    ON public.user_credentials FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role' OR (SELECT current_user) IN ('service_role', 'postgres'));

-- 4. Revoke direct table privileges from client roles to block PostgREST exposure
REVOKE ALL ON TABLE public.user_credentials FROM anon;
REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLE public.user_credentials FROM authenticated;
GRANT ALL ON TABLE public.user_credentials TO service_role;
GRANT ALL ON TABLE public.user_credentials TO postgres;
