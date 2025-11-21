-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table (extends Supabase auth.users)
-- Note: Supabase auth.users already exists, we add our business fields
CREATE TABLE public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    tier VARCHAR(20) NOT NULL DEFAULT 'free' CHECK (tier IN ('free', 'paid', 'enterprise')),
    subscription_start TIMESTAMPTZ,
    subscription_end TIMESTAMPTZ,
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Watchlists
CREATE TABLE public.watchlists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    symbol VARCHAR(10) NOT NULL,
    alert_enabled BOOLEAN DEFAULT FALSE,
    alert_price_above DECIMAL(10, 2),
    alert_price_below DECIMAL(10, 2),
    notes TEXT CHECK (LENGTH(notes) <= 500),
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, symbol)
);

-- Training jobs
CREATE TABLE public.training_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(10) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
    priority INT DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_seconds INT,
    error_message TEXT,
    model_version VARCHAR(50),
    training_samples INT,
    validation_samples INT,
    metrics JSONB,
    hyperparameters JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    retry_count INT DEFAULT 0
);

-- Prediction cache
CREATE TABLE public.prediction_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(10) NOT NULL,
    prediction_date DATE NOT NULL,
    predicted_price DECIMAL(10, 2) NOT NULL,
    confidence_lower DECIMAL(10, 2) NOT NULL,
    confidence_upper DECIMAL(10, 2) NOT NULL,
    trend VARCHAR(20) CHECK (trend IN ('bullish', 'bearish', 'neutral')),
    confidence_score DECIMAL(5, 4) CHECK (confidence_score BETWEEN 0 AND 1),
    model_version VARCHAR(50) NOT NULL,
    training_job_id UUID REFERENCES public.training_jobs(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    UNIQUE(symbol, prediction_date, model_version)
);

-- Stock priority
CREATE TABLE public.stock_priority (
    symbol VARCHAR(10) PRIMARY KEY,
    watchers_count INT DEFAULT 0,
    last_request_at TIMESTAMPTZ,
    priority_score DECIMAL(5, 2) DEFAULT 5.0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_watchlists_user_id ON public.watchlists(user_id);
CREATE INDEX idx_watchlists_symbol ON public.watchlists(symbol);
CREATE INDEX idx_training_jobs_symbol_status ON public.training_jobs(symbol, status);
CREATE INDEX idx_prediction_cache_symbol_date ON public.prediction_cache(symbol, prediction_date);
CREATE INDEX idx_prediction_cache_expires_at ON public.prediction_cache(expires_at);
CREATE INDEX idx_stock_priority_score ON public.stock_priority(priority_score DESC);
CREATE INDEX idx_user_profiles_tier ON public.user_profiles(tier);

-- Row Level Security (RLS) Policies

-- User profiles: Users can only read/update their own profile
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile"
    ON public.user_profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON public.user_profiles FOR UPDATE
    USING (auth.uid() = id);

-- Watchlists: Users can only manage their own watchlists
ALTER TABLE public.watchlists ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own watchlist"
    ON public.watchlists FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own watchlist"
    ON public.watchlists FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own watchlist"
    ON public.watchlists FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own watchlist"
    ON public.watchlists FOR DELETE
    USING (auth.uid() = user_id);

-- Prediction cache: Read-only for all authenticated users
ALTER TABLE public.prediction_cache ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users can view predictions"
    ON public.prediction_cache FOR SELECT
    TO authenticated
    USING (true);

-- Training jobs: Read-only for all authenticated users
ALTER TABLE public.training_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users can view training jobs"
    ON public.training_jobs FOR SELECT
    TO authenticated
    USING (true);

-- Stock priority: Read-only for all authenticated users
ALTER TABLE public.stock_priority ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users can view stock priority"
    ON public.stock_priority FOR SELECT
    TO authenticated
    USING (true);

-- Trigger to create user_profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (id, tier)
    VALUES (NEW.id, 'free');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON public.user_profiles
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

