-- Add service role policies for backend services
-- This allows backend services (using postgres role) to manage watchlists on behalf of users

-- Service role can insert watchlists for any user
CREATE POLICY "Service role can insert watchlists"
    ON public.watchlists FOR INSERT
    TO postgres
    WITH CHECK (true);

-- Service role can view all watchlists
CREATE POLICY "Service role can view watchlists"
    ON public.watchlists FOR SELECT
    TO postgres
    USING (true);

-- Service role can update any watchlist
CREATE POLICY "Service role can update watchlists"
    ON public.watchlists FOR UPDATE
    TO postgres
    USING (true);

-- Service role can delete any watchlist
CREATE POLICY "Service role can delete watchlists"
    ON public.watchlists FOR DELETE
    TO postgres
    USING (true);
