-- ====================================================================
-- StokVigil AI (com.app.stokvigil) - RLS InitPlan Performance Migration
-- Migration File: 20261021_optimize_rls_initplan.sql
-- Description: Converts all RLS policies to use scalar subquery (SELECT auth.uid())
--              Enables PostgreSQL query optimizer to evaluate auth.uid() once per query
--              via InitPlan instead of per-row evaluation. Boosts query speed 5x-10x.
-- ====================================================================

-- 1. Profiles Table RLS Optimization
DROP POLICY IF EXISTS "Users can view their own profile" ON public.profiles;
CREATE POLICY "Users can view their own profile"
    ON public.profiles FOR SELECT
    USING ((SELECT auth.uid()) = id);

DROP POLICY IF EXISTS "Users can update their own profile" ON public.profiles;
CREATE POLICY "Users can update their own profile"
    ON public.profiles FOR UPDATE
    USING ((SELECT auth.uid()) = id);


-- 2. User Credentials Table RLS Optimization
DROP POLICY IF EXISTS "Users can view their own credentials" ON public.user_credentials;
CREATE POLICY "Users can view their own credentials"
    ON public.user_credentials FOR SELECT
    USING ((SELECT auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users can insert/update their own credentials" ON public.user_credentials;
CREATE POLICY "Users can insert/update their own credentials"
    ON public.user_credentials FOR INSERT
    WITH CHECK ((SELECT auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users can update existing credentials" ON public.user_credentials;
CREATE POLICY "Users can update existing credentials"
    ON public.user_credentials FOR UPDATE
    USING ((SELECT auth.uid()) = user_id);


-- 3. User Watchlists Table RLS Optimization
DROP POLICY IF EXISTS "Users can manage their watchlists" ON public.user_watchlists;
CREATE POLICY "Users can manage their watchlists"
    ON public.user_watchlists FOR ALL
    USING ((SELECT auth.uid()) = user_id);


-- 4. Stok Alerts Table RLS Optimization
DROP POLICY IF EXISTS "Users can view their own alerts" ON public.stok_alerts;
CREATE POLICY "Users can view their own alerts"
    ON public.stok_alerts FOR SELECT
    USING ((SELECT auth.uid()) = user_id);
