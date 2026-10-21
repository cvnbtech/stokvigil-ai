-- ====================================================================
-- Migration: 20261021_add_isin_and_deduplicate_watchlists.sql
-- Description: Adds isin and company_name columns to public.user_watchlists.
-- Normalizes ICICI broker codes and removes all duplicate rows per user,
-- preserving the cost-basis (average_buy_price) and quantities.
-- Establishes immutable depository ISIN as the primary identity anchor
-- and enforces canonical unique constraints to permanently prevent duplicates.
-- ====================================================================

-- 1. Add isin and company_name columns if not existing
ALTER TABLE public.user_watchlists
    ADD COLUMN IF NOT EXISTS isin VARCHAR(12) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS company_name TEXT DEFAULT NULL;

-- 2. Normalize symbols: strip trailing .NS and uppercase all text
UPDATE public.user_watchlists
SET symbol = UPPER(TRIM(REPLACE(symbol, '.NS', '')))
WHERE symbol LIKE '%.NS' OR symbol LIKE '%.ns' OR symbol != UPPER(TRIM(symbol));

-- 3. Translate known ICICI Direct legacy broker codes to clean official exchange symbols
UPDATE public.user_watchlists SET symbol = 'TATAMOTORS', isin = 'INE155A01022' WHERE symbol IN ('TELCO', 'TATMOT');
UPDATE public.user_watchlists SET symbol = 'INFY', isin = 'INE009A01021' WHERE symbol = 'INFTEC';
UPDATE public.user_watchlists SET symbol = 'HDFCBANK', isin = 'INE040A01034' WHERE symbol = 'HDFBAN';
UPDATE public.user_watchlists SET symbol = 'LT', isin = 'INE018A01030' WHERE symbol = 'LARTOU';
UPDATE public.user_watchlists SET symbol = 'SBIN', isin = 'INE062A01020' WHERE symbol = 'STABAN';
UPDATE public.user_watchlists SET symbol = 'MARUTI', isin = 'INE585B01010' WHERE symbol = 'MARUTI' AND isin IS NULL;
UPDATE public.user_watchlists SET symbol = 'RELIANCE', isin = 'INE002A01018' WHERE symbol IN ('RELIND', 'RELIANCE') AND isin IS NULL;
UPDATE public.user_watchlists SET symbol = 'BAJFINANCE', isin = 'INE296A01024' WHERE symbol = 'BAJFI';
UPDATE public.user_watchlists SET symbol = 'BAJAJFINSV', isin = 'INE918I01018' WHERE symbol = 'BAFINS';
UPDATE public.user_watchlists SET symbol = 'AXISBANK', isin = 'INE238A01034' WHERE symbol = 'AXIBAN';
UPDATE public.user_watchlists SET symbol = 'KOTAKBANK', isin = 'INE237A01028' WHERE symbol = 'KOTMAH';
UPDATE public.user_watchlists SET symbol = 'BHARTIARTL', isin = 'INE397D01024' WHERE symbol = 'BHAAIR';
UPDATE public.user_watchlists SET symbol = 'HINDUNILVR', isin = 'INE030A01027' WHERE symbol = 'HINLEV';
UPDATE public.user_watchlists SET symbol = 'ASIANPAINT', isin = 'INE021A01026' WHERE symbol = 'ASIPAI';
UPDATE public.user_watchlists SET symbol = 'TITAN', isin = 'INE280A01028' WHERE symbol = 'TITIND';
UPDATE public.user_watchlists SET symbol = 'SUNPHARMA', isin = 'INE044A01036' WHERE symbol = 'SUNPHA';
UPDATE public.user_watchlists SET symbol = 'TATASTEEL', isin = 'INE081A01020' WHERE symbol = 'TATAST';
UPDATE public.user_watchlists SET symbol = 'TATACONSUM', isin = 'INE192A01025' WHERE symbol = 'TATCON';
UPDATE public.user_watchlists SET symbol = 'HCLTECH', isin = 'INE860A01027' WHERE symbol = 'HCLTEC';
UPDATE public.user_watchlists SET symbol = 'POWERGRID', isin = 'INE752E01010' WHERE symbol = 'POWGRI';
UPDATE public.user_watchlists SET symbol = 'COALINDIA', isin = 'INE522F01014' WHERE symbol = 'COALIN';
UPDATE public.user_watchlists SET symbol = 'ULTRACEMCO', isin = 'INE481G01011' WHERE symbol = 'ULTRAC';
UPDATE public.user_watchlists SET symbol = 'JSWSTEEL', isin = 'INE019A01038' WHERE symbol = 'JSWSTE';
UPDATE public.user_watchlists SET symbol = 'ADANIPORTS', isin = 'INE742F01042' WHERE symbol = 'ADAPOR';
UPDATE public.user_watchlists SET symbol = 'ADANIENT', isin = 'INE423A01024' WHERE symbol = 'ADIENT';
UPDATE public.user_watchlists SET symbol = 'DRREDDY', isin = 'INE089A01023' WHERE symbol = 'DRREDD';
UPDATE public.user_watchlists SET symbol = 'DIVISLAB', isin = 'INE361B01024' WHERE symbol = 'DIVLAB';
UPDATE public.user_watchlists SET symbol = 'APOLLOHOSP', isin = 'INE437A01024' WHERE symbol = 'APOHOS';
UPDATE public.user_watchlists SET symbol = 'EICHERMOT', isin = 'INE066A01021' WHERE symbol = 'EICMOT';
UPDATE public.user_watchlists SET symbol = 'BRITANNIA', isin = 'INE216A01030' WHERE symbol = 'BRIIND';
UPDATE public.user_watchlists SET symbol = 'BAJAJ-AUTO', isin = 'INE917I01010' WHERE symbol = 'BAAUTO';
UPDATE public.user_watchlists SET symbol = 'INDUSINDBK', isin = 'INE095A01012' WHERE symbol = 'INDUSH';
UPDATE public.user_watchlists SET symbol = 'NESTLEIND', isin = 'INE239A01016' WHERE symbol = 'NESIND';
UPDATE public.user_watchlists SET symbol = 'HEROMOTOCO', isin = 'INE158A01026' WHERE symbol = 'HERHON';
UPDATE public.user_watchlists SET symbol = 'HINDALCO', isin = 'INE038A01020' WHERE symbol = 'HINDAL';
UPDATE public.user_watchlists SET symbol = 'VEDL', isin = 'INE205A01025' WHERE symbol = 'VEDAN';

-- 4. Deduplicate rows: For duplicate (user_id, symbol), preserve the master row with average_buy_price & quantity
WITH ranked_duplicates AS (
    SELECT 
        id,
        user_id,
        symbol,
        ROW_NUMBER() OVER (
            PARTITION BY user_id, symbol 
            ORDER BY 
                CASE WHEN average_buy_price IS NOT NULL AND average_buy_price > 0 THEN 1 ELSE 2 END,
                CASE WHEN quantity IS NOT NULL AND quantity > 0 THEN 1 ELSE 2 END,
                CASE WHEN is_auto_synced = TRUE THEN 1 ELSE 2 END,
                created_at ASC
        ) as rn
    FROM public.user_watchlists
)
DELETE FROM public.user_watchlists
WHERE id IN (
    SELECT id FROM ranked_duplicates WHERE rn > 1
);

-- 5. Deduplicate rows with matching non-null ISIN: preserve the master row with cost basis
WITH ranked_isin_duplicates AS (
    SELECT 
        id,
        user_id,
        isin,
        ROW_NUMBER() OVER (
            PARTITION BY user_id, isin 
            ORDER BY 
                CASE WHEN average_buy_price IS NOT NULL AND average_buy_price > 0 THEN 1 ELSE 2 END,
                CASE WHEN quantity IS NOT NULL AND quantity > 0 THEN 1 ELSE 2 END,
                CASE WHEN is_auto_synced = TRUE THEN 1 ELSE 2 END,
                created_at ASC
        ) as rn
    FROM public.user_watchlists
    WHERE isin IS NOT NULL
)
DELETE FROM public.user_watchlists
WHERE id IN (
    SELECT id FROM ranked_isin_duplicates WHERE rn > 1
);

-- 6. Drop legacy fragile literal text constraint if exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'user_watchlists_user_id_symbol_key' 
        AND conrelid = 'public.user_watchlists'::regclass
    ) THEN
        ALTER TABLE public.user_watchlists DROP CONSTRAINT user_watchlists_user_id_symbol_key;
    END IF;
END $$;

-- 7. Create unique constraint on (user_id, isin)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'uq_user_watchlists_user_isin' 
        AND conrelid = 'public.user_watchlists'::regclass
    ) THEN
        ALTER TABLE public.user_watchlists 
            ADD CONSTRAINT uq_user_watchlists_user_isin UNIQUE (user_id, isin);
    END IF;
END $$;

-- 8. Create canonical unique index on (user_id, symbol) to prevent duplicates without ISIN
CREATE UNIQUE INDEX IF NOT EXISTS uq_user_watchlists_user_canonical_symbol 
    ON public.user_watchlists (user_id, UPPER(TRIM(REPLACE(symbol, '.NS', '')))) 
    WHERE isin IS NULL;

-- 9. Create index on isin for fast lookups
CREATE INDEX IF NOT EXISTS idx_watchlists_isin 
    ON public.user_watchlists(isin);
