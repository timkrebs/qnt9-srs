-- Add user roles for access control
-- Migration: 006_add_user_roles.sql
-- Description: Adds role column to users table for admin/editor access control

-- Add role column to users table
ALTER TABLE public.users 
ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'user' 
CHECK (role IN ('user', 'admin', 'editor'));

-- Create index for role lookups
CREATE INDEX IF NOT EXISTS idx_users_role ON public.users(role);

-- Update blog_posts RLS policies to restrict write access to admins/editors only
-- First, drop existing policies that allow any authenticated user to write
DROP POLICY IF EXISTS "Authenticated users can create posts" ON public.blog_posts;
DROP POLICY IF EXISTS "Authenticated users can update posts" ON public.blog_posts;
DROP POLICY IF EXISTS "Authenticated users can delete posts" ON public.blog_posts;

-- Create new policies that check user role
-- Note: These policies query the public.users table to check roles
-- For this to work with Supabase Auth, ensure the JWT contains the user's role claim

-- Allow admins and editors to create posts
CREATE POLICY "Admins and editors can create posts" ON public.blog_posts
    FOR INSERT 
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE users.id = auth.uid()::uuid 
            AND users.role IN ('admin', 'editor')
        )
    );

-- Allow admins and editors to update posts
CREATE POLICY "Admins and editors can update posts" ON public.blog_posts
    FOR UPDATE 
    USING (
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE users.id = auth.uid()::uuid 
            AND users.role IN ('admin', 'editor')
        )
    );

-- Allow only admins to delete posts
CREATE POLICY "Only admins can delete posts" ON public.blog_posts
    FOR DELETE 
    USING (
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE users.id = auth.uid()::uuid 
            AND users.role = 'admin'
        )
    );

-- Add comment explaining role values
COMMENT ON COLUMN public.users.role IS 'User role for access control: user (default), editor (can create/edit blog posts), admin (full access)';

-- Function to promote a user to admin (for manual use)
CREATE OR REPLACE FUNCTION public.promote_user_to_admin(user_email VARCHAR(255))
RETURNS void AS $$
BEGIN
    UPDATE public.users 
    SET role = 'admin' 
    WHERE email = user_email;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'User with email % not found', user_email;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to set user role (for manual use)
CREATE OR REPLACE FUNCTION public.set_user_role(user_email VARCHAR(255), new_role VARCHAR(20))
RETURNS void AS $$
BEGIN
    IF new_role NOT IN ('user', 'admin', 'editor') THEN
        RAISE EXCEPTION 'Invalid role: %. Must be user, admin, or editor', new_role;
    END IF;
    
    UPDATE public.users 
    SET role = new_role 
    WHERE email = user_email;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'User with email % not found', user_email;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
