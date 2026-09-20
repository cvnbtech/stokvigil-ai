-- ==============================================================================
-- StokVigil AI Migration: 20260920_fii_dii_service_role_policy.sql
-- Purpose: Grant backend service_role full write/insert/update access on fii_dii_flows
-- ==============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'fii_dii_flows' AND policyname = 'Service role full access on fii_dii_flows'
    ) THEN
        CREATE POLICY "Service role full access on fii_dii_flows"
            ON public.fii_dii_flows FOR ALL
            USING (auth.jwt() ->> 'role' = 'service_role');
    END IF;
END
$$;
