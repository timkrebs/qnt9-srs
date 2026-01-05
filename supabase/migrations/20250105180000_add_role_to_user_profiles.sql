-- Add role column to user_profiles table for Supabase Auth users
-- Migration: 20250105180000_add_role_to_user_profiles.sql
-- Description: Adds role column to user_profiles for access control with Supabase Auth

-- Add role column to user_profiles table (for Supabase Auth users)
ALTER TABLE public.user_profiles 
ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'user' 
CHECK (role IN ('user', 'admin', 'editor'));

-- Create index for role lookups
CREATE INDEX IF NOT EXISTS idx_user_profiles_role ON public.user_profiles(role);

-- Add comment explaining the role column
COMMENT ON COLUMN public.user_profiles.role IS 'User role for access control: user (default), editor (can create/edit blog posts), admin (full access)';

-- Function to promote a user_profile to admin (for Supabase Auth users)
CREATE OR REPLACE FUNCTION public.promote_user_profile_to_admin(user_email VARCHAR(255))
RETURNS void AS $$
DECLARE
    target_user_id UUID;
BEGIN
    -- Get user ID from auth.users by email
    SELECT id INTO target_user_id 
    FROM auth.users 
    WHERE email = user_email;
    
    IF target_user_id IS NULL THEN
        RAISE EXCEPTION 'User with email % not found in auth.users', user_email;
    END IF;
    
    -- Update the user_profiles table
    UPDATE public.user_profiles 
    SET role = 'admin' 
    WHERE id = target_user_id;
    
    IF NOT FOUND THEN
        -- Insert a profile if it doesn't exist
        INSERT INTO public.user_profiles (id, role, tier)
        VALUES (target_user_id, 'admin', 'free');
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to set user profile role
CREATE OR REPLACE FUNCTION public.set_user_profile_role(user_email VARCHAR(255), new_role VARCHAR(20))
RETURNS void AS $$
DECLARE
    target_user_id UUID;
BEGIN
    IF new_role NOT IN ('user', 'admin', 'editor') THEN
        RAISE EXCEPTION 'Invalid role: %. Must be user, admin, or editor', new_role;
    END IF;
    
    -- Get user ID from auth.users by email
    SELECT id INTO target_user_id 
    FROM auth.users 
    WHERE email = user_email;
    
    IF target_user_id IS NULL THEN
        RAISE EXCEPTION 'User with email % not found in auth.users', user_email;
    END IF;
    
    -- Update the user_profiles table
    UPDATE public.user_profiles 
    SET role = new_role 
    WHERE id = target_user_id;
    
    IF NOT FOUND THEN
        -- Insert a profile if it doesn't exist
        INSERT INTO public.user_profiles (id, role, tier)
        VALUES (target_user_id, new_role, 'free');
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
