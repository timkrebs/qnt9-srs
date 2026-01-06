-- Add audit_log table for auth-service audit logging
-- This table matches the schema expected by app/audit.py

CREATE TABLE IF NOT EXISTS public.audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,  -- Can be NULL for unauthenticated actions
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100),
    entity_id VARCHAR(255),
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON public.audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON public.audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON public.audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON public.audit_log(created_at DESC);

-- RLS policies
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;

-- Only service role can insert (from backend services)
CREATE POLICY "Service role can insert audit logs"
    ON public.audit_log
    FOR INSERT
    TO service_role
    WITH CHECK (true);

-- Service role can read all logs
CREATE POLICY "Service role can read audit logs"
    ON public.audit_log
    FOR SELECT
    TO service_role
    USING (true);

-- Authenticated users can read their own logs
CREATE POLICY "Users can read own audit logs"
    ON public.audit_log
    FOR SELECT
    TO authenticated
    USING (auth.uid()::text = user_id::text);

COMMENT ON TABLE public.audit_log IS 'Audit trail for tracking user actions and system events';
COMMENT ON COLUMN public.audit_log.action IS 'Action type (e.g., user.signin, user.signup, password.change)';
COMMENT ON COLUMN public.audit_log.entity_type IS 'Type of entity affected (e.g., user, session)';
COMMENT ON COLUMN public.audit_log.entity_id IS 'ID of the affected entity';
COMMENT ON COLUMN public.audit_log.old_values IS 'Previous values before the action (for updates)';
COMMENT ON COLUMN public.audit_log.new_values IS 'New values after the action';
