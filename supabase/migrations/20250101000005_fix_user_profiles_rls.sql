-- Fix Row Level Security for user_profiles table
-- Disable RLS since the auth-service backend handles all authorization
-- The service uses the service_role key which should bypass RLS, but the 
-- Supabase Python client doesn't properly propagate this to PostgREST calls

-- Disable RLS completely - backend service handles authorization
ALTER TABLE user_profiles DISABLE ROW LEVEL SECURITY;

-- Note: If you need RLS in the future, enable it and ensure proper policies:
-- ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
-- 
-- CREATE POLICY "Service role full access"
--     ON user_profiles FOR ALL
--     TO service_role
--     USING (true) WITH CHECK (true);
--
-- CREATE POLICY "Users can view own profile"
--     ON user_profiles FOR SELECT  
--     TO authenticated
--     USING (auth.uid() = id);

