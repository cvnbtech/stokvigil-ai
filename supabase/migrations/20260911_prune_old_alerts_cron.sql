-- ====================================================================
-- StokVigil AI: Database Retention & Free-Tier Storage Optimization
-- Migration: 20260911_prune_old_alerts_cron.sql
-- Purges historical alerts older than 30 days to protect 500 MB Supabase free tier.
-- ====================================================================

-- 1. Create maintenance stored procedure
CREATE OR REPLACE FUNCTION public.prune_historical_stok_alerts(retention_days INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_rows INTEGER;
BEGIN
    DELETE FROM public.stok_alerts
    WHERE created_at < (NOW() - (retention_days || ' days')::INTERVAL);
    
    GET DIAGNOSTICS deleted_rows = ROW_COUNT;
    RETURN deleted_rows;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 2. Grant execution permission to service_role and postgres
GRANT EXECUTE ON FUNCTION public.prune_historical_stok_alerts(INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION public.prune_historical_stok_alerts(INTEGER) TO postgres;

-- 3. Optional: Native pg_cron schedule (if pg_cron extension is enabled on Supabase)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        PERFORM cron.schedule(
            'stokvigil_daily_alert_prune',
            '0 3 * * *', -- Daily at 03:00 UTC (08:30 AM IST)
            'SELECT public.prune_historical_stok_alerts(30);'
        );
    END IF;
END $$;
