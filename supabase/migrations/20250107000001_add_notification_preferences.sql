-- Add notification preferences column to user_profiles
-- This migration adds JSONB column for storing user notification preferences

-- Add notification_preferences column if it doesn't exist
ALTER TABLE public.user_profiles 
ADD COLUMN IF NOT EXISTS notification_preferences JSONB DEFAULT '{
  "email_notifications": true,
  "product_updates": true,
  "usage_alerts": true,
  "security_alerts": true,
  "marketing_emails": false
}'::jsonb;

-- Create index for faster queries on notification preferences
CREATE INDEX IF NOT EXISTS idx_user_profiles_notification_preferences 
ON public.user_profiles USING GIN (notification_preferences);

-- Update existing rows to have default preferences if null
UPDATE public.user_profiles 
SET notification_preferences = '{
  "email_notifications": true,
  "product_updates": true,
  "usage_alerts": true,
  "security_alerts": true,
  "marketing_emails": false
}'::jsonb
WHERE notification_preferences IS NULL;

-- Add comment to document the column
COMMENT ON COLUMN public.user_profiles.notification_preferences IS 
'User notification preferences stored as JSONB with keys: email_notifications, product_updates, usage_alerts, security_alerts, marketing_emails';
