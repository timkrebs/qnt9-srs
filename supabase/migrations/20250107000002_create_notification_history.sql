-- Create notification_history table for tracking sent notifications
-- This table stores all notification delivery history with status and metadata

-- Create notification_history table
CREATE TABLE IF NOT EXISTS public.notification_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delivery_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    resend_id VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_notification_history_user_id 
ON public.notification_history(user_id);

CREATE INDEX IF NOT EXISTS idx_notification_history_sent_at 
ON public.notification_history(sent_at DESC);

CREATE INDEX IF NOT EXISTS idx_notification_history_type_sent_at 
ON public.notification_history(notification_type, sent_at DESC);

CREATE INDEX IF NOT EXISTS idx_notification_history_user_type_sent 
ON public.notification_history(user_id, notification_type, sent_at DESC);

CREATE INDEX IF NOT EXISTS idx_notification_history_metadata 
ON public.notification_history USING GIN (metadata);

-- Add comments to document the table
COMMENT ON TABLE public.notification_history IS 
'Tracks all notification delivery attempts with status and metadata';

COMMENT ON COLUMN public.notification_history.notification_type IS 
'Type of notification: price_alert, marketing, product_update, security_alert, welcome';

COMMENT ON COLUMN public.notification_history.delivery_status IS 
'Delivery status: pending, sent, delivered, failed, bounced';

COMMENT ON COLUMN public.notification_history.resend_id IS 
'External ID from Resend API for tracking email delivery';

COMMENT ON COLUMN public.notification_history.metadata IS 
'Additional data about the notification (symbol, price, template, etc.)';

-- Enable RLS
ALTER TABLE public.notification_history ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Users can view their own notification history"
ON public.notification_history
FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Service can insert notification history"
ON public.notification_history
FOR INSERT
WITH CHECK (true);

-- Admins can view all notification history
CREATE POLICY "Admins can view all notification history"
ON public.notification_history
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM public.user_profiles
        WHERE id = auth.uid() AND role = 'admin'
    )
);
