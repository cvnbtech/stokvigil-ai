-- ==============================================================================
-- StokVigil AI Migration: 20260906_fii_dii_flows.sql
-- Purpose: Institutional FII/DII Net Flow Tracker and Historical Flow Ledger
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.fii_dii_flows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_date DATE UNIQUE NOT NULL,
    fii_buy_cr NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    fii_sell_cr NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    fii_net_cr NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    dii_buy_cr NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    dii_sell_cr NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    dii_net_cr NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    combined_net_cr NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    sentiment_bias VARCHAR(64) NOT NULL DEFAULT 'NEUTRAL',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Index for instant lookup of latest dates
CREATE INDEX IF NOT EXISTS idx_fii_dii_trade_date ON public.fii_dii_flows (trade_date DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE public.fii_dii_flows ENABLE ROW LEVEL SECURITY;

-- Allow public read access to macro flow data
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'fii_dii_flows' AND policyname = 'Public Read FII DII Flows'
    ) THEN
        CREATE POLICY "Public Read FII DII Flows"
            ON public.fii_dii_flows
            FOR SELECT
            USING (true);
    END IF;
END
$$;
