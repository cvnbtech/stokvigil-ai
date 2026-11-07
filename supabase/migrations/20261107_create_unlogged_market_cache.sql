-- Migration: 20261107_create_unlogged_market_cache.sql
-- StokVigil AI: Shared High-Performance Zero-Cost In-Memory State Layer
-- Uses UNLOGGED table to bypass WAL (Write-Ahead Logging) for RAM-like speed at zero cost.

CREATE UNLOGGED TABLE IF NOT EXISTS public.market_memory_cache (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_market_memory_cache_key ON public.market_memory_cache(key);

-- Row Level Security: Server-side worker / service role full access; authenticated users read-only
ALTER TABLE public.market_memory_cache ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow service role full access on market_memory_cache" ON public.market_memory_cache;
CREATE POLICY "Allow service role full access on market_memory_cache"
    ON public.market_memory_cache
    FOR ALL
    USING (true)
    WITH CHECK (true);

DROP POLICY IF EXISTS "Allow authenticated users to read market_memory_cache" ON public.market_memory_cache;
CREATE POLICY "Allow authenticated users to read market_memory_cache"
    ON public.market_memory_cache
    FOR SELECT
    TO authenticated
    USING (true);
