-- Add stock_news preference to notification_preferences
-- This enables daily stock summary emails with watchlist news

-- Update default notification_preferences to include stock_news instead of security_alerts
-- Keep security_alerts for backwards compatibility, add stock_news field

-- Update existing rows to add stock_news field (default true for engaged users)
UPDATE public.user_profiles 
SET notification_preferences = notification_preferences || '{"stock_news": true}'::jsonb
WHERE notification_preferences IS NOT NULL
  AND NOT (notification_preferences ? 'stock_news');

-- Update the default value for new users
ALTER TABLE public.user_profiles 
ALTER COLUMN notification_preferences 
SET DEFAULT '{
  "email_notifications": true,
  "product_updates": true,
  "usage_alerts": true,
  "stock_news": true,
  "marketing_emails": false
}'::jsonb;

-- Add comment to document the change
COMMENT ON COLUMN public.user_profiles.notification_preferences IS 
'User notification preferences stored as JSONB with keys: email_notifications, product_updates, usage_alerts (price alerts), stock_news (daily summary), marketing_emails';
