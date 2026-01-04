-- Migration: Add missing columns to user_profiles table
-- Created: 2026-01-04
-- Description: Adds full_name, last_login, and metadata columns to support user profile management

-- Add full_name column for storing user's display name
ALTER TABLE public.user_profiles 
ADD COLUMN IF NOT EXISTS full_name VARCHAR(255);

-- Add last_login column to track user activity
ALTER TABLE public.user_profiles 
ADD COLUMN IF NOT EXISTS last_login TIMESTAMPTZ;

-- Add metadata column for flexible user data storage
ALTER TABLE public.user_profiles 
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- Create index on last_login for analytics queries
CREATE INDEX IF NOT EXISTS idx_user_profiles_last_login 
ON public.user_profiles(last_login);

-- Comment on new columns
COMMENT ON COLUMN public.user_profiles.full_name IS 'User display name';
COMMENT ON COLUMN public.user_profiles.last_login IS 'Timestamp of last successful login';
COMMENT ON COLUMN public.user_profiles.metadata IS 'Flexible JSONB field for additional user data';
