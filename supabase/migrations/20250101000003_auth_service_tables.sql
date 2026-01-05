-- Auth Service Tables
-- Creates custom authentication tables for the auth-service microservice
-- This is separate from Supabase's built-in auth.users to maintain microservice independence

-- Users table for custom authentication
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    tier VARCHAR(20) NOT NULL DEFAULT 'free' CHECK (tier IN ('free', 'paid', 'enterprise')),
    email_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    subscription_start TIMESTAMPTZ,
    subscription_end TIMESTAMPTZ,
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Refresh tokens table for JWT token management
CREATE TABLE IF NOT EXISTS public.refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMPTZ,
    ip_address INET,
    user_agent TEXT
);

-- Email verification tokens
CREATE TABLE IF NOT EXISTS public.email_verification_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMPTZ
);

-- Password reset tokens
CREATE TABLE IF NOT EXISTS public.password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMPTZ
);

-- Audit log for authentication events
CREATE TABLE IF NOT EXISTS public.auth_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    event_type VARCHAR(50) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_tier ON public.users(tier);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON public.users(created_at);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON public.refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at ON public.refresh_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token_hash ON public.refresh_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_email_verification_user_id ON public.email_verification_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_password_reset_user_id ON public.password_reset_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_audit_user_id ON public.auth_audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_audit_created_at ON public.auth_audit_log(created_at DESC);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION public.update_users_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at_trigger
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION public.update_users_updated_at();

-- Function to clean up expired tokens
CREATE OR REPLACE FUNCTION public.cleanup_expired_tokens()
RETURNS void AS $$
BEGIN
    -- Delete expired refresh tokens
    DELETE FROM public.refresh_tokens
    WHERE expires_at < NOW() AND NOT revoked;
    
    -- Delete expired email verification tokens
    DELETE FROM public.email_verification_tokens
    WHERE expires_at < NOW() AND NOT used;
    
    -- Delete expired password reset tokens
    DELETE FROM public.password_reset_tokens
    WHERE expires_at < NOW() AND NOT used;
END;
$$ LANGUAGE plpgsql;

-- Comment to explain the tables
COMMENT ON TABLE public.users IS 'Custom user authentication table for auth-service microservice';
COMMENT ON TABLE public.refresh_tokens IS 'JWT refresh tokens for maintaining user sessions';
COMMENT ON TABLE public.email_verification_tokens IS 'Tokens for email verification workflow';
COMMENT ON TABLE public.password_reset_tokens IS 'Tokens for password reset workflow';
COMMENT ON TABLE public.auth_audit_log IS 'Audit trail for authentication events';
