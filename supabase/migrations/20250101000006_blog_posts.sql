-- Migration: Create blog_posts table for CMS
-- This allows employees to write blog posts in markdown without rebuilding the frontend

-- Create blog_posts table
CREATE TABLE IF NOT EXISTS public.blog_posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  excerpt TEXT,
  content TEXT NOT NULL, -- Markdown content
  category TEXT DEFAULT 'General',
  author_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  author_name TEXT,
  image_url TEXT,
  published BOOLEAN DEFAULT false,
  featured BOOLEAN DEFAULT false,
  published_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_blog_posts_slug ON public.blog_posts(slug);
CREATE INDEX IF NOT EXISTS idx_blog_posts_published ON public.blog_posts(published, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_blog_posts_category ON public.blog_posts(category);

-- Enable RLS
ALTER TABLE public.blog_posts ENABLE ROW LEVEL SECURITY;

-- Policy: Anyone can read published posts
CREATE POLICY "Public can read published posts"
  ON public.blog_posts
  FOR SELECT
  USING (published = true);

-- Policy: Authenticated users can read all posts (for admin)
CREATE POLICY "Authenticated users can read all posts"
  ON public.blog_posts
  FOR SELECT
  TO authenticated
  USING (true);

-- Policy: Authenticated users can insert posts
CREATE POLICY "Authenticated users can insert posts"
  ON public.blog_posts
  FOR INSERT
  TO authenticated
  WITH CHECK (true);

-- Policy: Authenticated users can update posts
CREATE POLICY "Authenticated users can update posts"
  ON public.blog_posts
  FOR UPDATE
  TO authenticated
  USING (true)
  WITH CHECK (true);

-- Policy: Authenticated users can delete posts
CREATE POLICY "Authenticated users can delete posts"
  ON public.blog_posts
  FOR DELETE
  TO authenticated
  USING (true);

-- Function to auto-update updated_at
CREATE OR REPLACE FUNCTION public.update_blog_post_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for updated_at
DROP TRIGGER IF EXISTS blog_posts_updated_at ON public.blog_posts;
CREATE TRIGGER blog_posts_updated_at
  BEFORE UPDATE ON public.blog_posts
  FOR EACH ROW
  EXECUTE FUNCTION public.update_blog_post_updated_at();

-- Insert some sample blog posts
INSERT INTO public.blog_posts (title, slug, excerpt, content, category, author_name, published, featured, published_at)
VALUES
  (
    'Introducing Real-Time WebSocket Quotes',
    'introducing-realtime-websocket-quotes',
    'We are excited to announce real-time streaming quotes for all Pro subscribers, enabling sub-second price updates for your watchlist.',
    '# Introducing Real-Time WebSocket Quotes

We are thrilled to announce a major upgrade to our platform: **real-time WebSocket quotes** are now available for all Pro subscribers!

## What This Means for You

Instead of polling for price updates every few seconds, your watchlist will now receive instant price changes as they happen in the market. This means:

- **Sub-second updates**: See price changes the moment they occur
- **Reduced latency**: No more waiting for the next refresh cycle
- **Lower bandwidth**: WebSocket connections are more efficient than repeated API calls

## How to Enable

Real-time quotes are automatically enabled for Pro subscribers. Simply open your watchlist, and you will see prices updating in real-time with a subtle animation indicating live updates.

## Technical Details

For developers using our API, the WebSocket endpoint is available at:

```
wss://api.qnt9.com/v1/stream
```

Subscribe to tickers by sending:

```json
{
  "action": "subscribe",
  "tickers": ["AAPL", "MSFT", "GOOGL"]
}
```

## Get Started

[Upgrade to Pro](/pricing) today to access real-time quotes and take your trading to the next level.',
    'Product',
    'QNT9 Team',
    true,
    true,
    NOW() - INTERVAL '2 days'
  ),
  (
    'Understanding Market Cap and Valuation',
    'understanding-market-cap-valuation',
    'A comprehensive guide to understanding market capitalization and how it relates to company valuation and investment decisions.',
    '# Understanding Market Cap and Valuation

Market capitalization is one of the most fundamental metrics for evaluating a company''s size and value. In this guide, we will break down what market cap means and how to use it in your investment research.

## What is Market Cap?

Market capitalization (market cap) is calculated by multiplying a company''s outstanding shares by its current stock price:

```
Market Cap = Share Price × Shares Outstanding
```

For example, if a company has 1 billion shares outstanding and trades at $150 per share, its market cap is $150 billion.

## Market Cap Categories

Companies are typically categorized by their market cap:

| Category | Market Cap Range |
|----------|------------------|
| Mega-cap | $200B+ |
| Large-cap | $10B - $200B |
| Mid-cap | $2B - $10B |
| Small-cap | $300M - $2B |
| Micro-cap | $50M - $300M |

## Why Market Cap Matters

1. **Risk Assessment**: Larger companies tend to be more stable but may have slower growth
2. **Liquidity**: Higher market cap usually means more trading volume
3. **Index Inclusion**: Many indices weight by market cap
4. **Comparison**: Useful for comparing companies in the same industry

## Limitations

Market cap alone does not tell the whole story. Consider also:

- Enterprise Value (EV) for a more complete picture
- Price-to-Earnings (P/E) ratio for valuation
- Revenue and earnings growth rates

## Conclusion

Understanding market cap is essential for any investor. Use the QNT9 platform to easily view market cap data for all your watchlist stocks.',
    'Education',
    'QNT9 Team',
    true,
    false,
    NOW() - INTERVAL '8 days'
  ),
  (
    'New API Rate Limits and Best Practices',
    'api-rate-limits-best-practices',
    'Learn about our updated API rate limits and best practices for efficient data retrieval in your applications.',
    '# New API Rate Limits and Best Practices

We have updated our API rate limits to ensure fair usage and optimal performance for all users. Here is what you need to know.

## Updated Rate Limits

| Plan | Requests/Minute | Requests/Day |
|------|-----------------|--------------|
| Free | 60 | 1,000 |
| Pro | 300 | 10,000 |
| Enterprise | 1,000 | Unlimited |

## Best Practices

### 1. Use Batch Endpoints

Instead of making individual requests for each ticker, use our batch endpoints:

```javascript
// Instead of this:
for (const ticker of tickers) {
  await api.getQuote(ticker);
}

// Do this:
const quotes = await api.getBatchQuotes(tickers);
```

### 2. Implement Caching

Cache responses when appropriate:

```javascript
const cache = new Map();
const CACHE_TTL = 5000; // 5 seconds

async function getQuote(ticker) {
  const cached = cache.get(ticker);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.data;
  }
  
  const data = await api.getQuote(ticker);
  cache.set(ticker, { data, timestamp: Date.now() });
  return data;
}
```

### 3. Handle Rate Limit Errors

Implement exponential backoff:

```javascript
async function fetchWithRetry(fn, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (error.status === 429) {
        await sleep(Math.pow(2, i) * 1000);
        continue;
      }
      throw error;
    }
  }
}
```

## Questions?

Contact our support team at api@qnt9.com for help with rate limits or API integration.',
    'API',
    'QNT9 Team',
    true,
    false,
    NOW() - INTERVAL '20 days'
  );
