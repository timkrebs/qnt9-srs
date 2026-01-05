'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Image from 'next/image'
import { 
  ArrowLeft, 
  Star, 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  BarChart2,
  Building2,
  Globe,
  Users,
  MapPin,
  ExternalLink,
  Lock,
  Newspaper
} from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { 
  stockService, 
  formatPrice, 
  formatChange, 
  formatChangePercent, 
  formatVolume 
} from '@/lib/api/stock'
import type { 
  StockSnapshot, 
  ChartResponse, 
  ChartRange, 
  TickerDetail,
  NewsArticle 
} from '@/lib/api/stock'
import { useWatchlist } from '@/hooks/use-watchlist'
import { useStockWebSocket } from '@/hooks/use-stock-websocket'
import { cn } from '@/lib/utils'

export default function StockDetailPage() {
  const params = useParams()
  const ticker = (params.ticker as string)?.toUpperCase()
  
  const [details, setDetails] = useState<TickerDetail | null>(null)
  const [snapshot, setSnapshot] = useState<StockSnapshot | null>(null)
  const [chart, setChart] = useState<ChartResponse | null>(null)
  const [news, setNews] = useState<NewsArticle[]>([])
  const [selectedRange, setSelectedRange] = useState<ChartRange>('1M')
  const [loading, setLoading] = useState(true)
  const [newsLoading, setNewsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [initialChartLoaded, setInitialChartLoaded] = useState(false)

  const { addStock, removeStock, isInWatchlist } = useWatchlist()
  const inWatchlist = isInWatchlist(ticker)

  // Real-time price updates
  const { prices, status: wsStatus } = useStockWebSocket({
    tickers: ticker ? [ticker] : [],
  })
  const livePrice = prices[ticker]

  // Fetch ticker details, snapshot, and chart
  useEffect(() => {
    if (!ticker) return

    const fetchData = async () => {
      setLoading(true)
      setError(null)

      try {
        const [detailsRes, snapshotRes, chartRes] = await Promise.allSettled([
          stockService.getTickerDetails(ticker),
          stockService.getSnapshot(ticker),
          stockService.getChart(ticker, selectedRange),
        ])

        if (detailsRes.status === 'fulfilled' && detailsRes.value.success) {
          setDetails(detailsRes.value.data)
        }

        if (snapshotRes.status === 'fulfilled' && snapshotRes.value.success) {
          setSnapshot(snapshotRes.value.data)
        }

        if (chartRes.status === 'fulfilled' && chartRes.value.success) {
          setChart(chartRes.value)
          setInitialChartLoaded(true)
        }

        if (
          detailsRes.status === 'rejected' &&
          snapshotRes.status === 'rejected'
        ) {
          setError('Stock not found or data unavailable')
        }
      } catch (err) {
        console.error('Failed to fetch stock data:', err)
        setError('Failed to load stock data')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [ticker])

  // Fetch news separately (lower priority)
  useEffect(() => {
    if (!ticker) return

    const fetchNews = async () => {
      setNewsLoading(true)
      try {
        const newsRes = await stockService.getNews(ticker, 5)
        if (newsRes.success) {
          setNews(newsRes.articles)
        }
      } catch (err) {
        console.error('Failed to fetch news:', err)
      } finally {
        setNewsLoading(false)
      }
    }

    // Delay news fetch slightly to prioritize main data
    const timer = setTimeout(fetchNews, 500)
    return () => clearTimeout(timer)
  }, [ticker])

  // Fetch chart when range changes
  useEffect(() => {
    if (!ticker || !initialChartLoaded) return

    const fetchChart = async () => {
      try {
        const chartRes = await stockService.getChart(ticker, selectedRange)
        if (chartRes.success) {
          setChart(chartRes)
        }
      } catch (err) {
        console.error('Failed to fetch chart:', err)
      }
    }

    fetchChart()
  }, [ticker, selectedRange, initialChartLoaded])

  const handleWatchlistToggle = async () => {
    if (inWatchlist) {
      await removeStock(ticker)
    } else {
      await addStock(ticker)
    }
  }

  // Use live price if available, otherwise use snapshot
  const currentPrice = livePrice?.price ?? snapshot?.price
  const priceChange = snapshot?.change
  const priceChangePercent = snapshot?.change_percent
  const isPositive = (priceChange ?? 0) >= 0

  const changeDisplay = formatChange(priceChange)
  const changePercentDisplay = formatChangePercent(priceChangePercent)

  if (loading) {
    return <StockDetailSkeleton />
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Link href="/search" className="inline-flex items-center text-muted-foreground hover:text-foreground mb-6">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Search
        </Link>
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-lg text-muted-foreground">{error}</p>
            <Button asChild className="mt-4">
              <Link href="/search">Search for stocks</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Back link */}
      <Link href="/search" className="inline-flex items-center text-muted-foreground hover:text-foreground mb-6">
        <ArrowLeft className="h-4 w-4 mr-2" />
        Back to Search
      </Link>

      {/* Header with Logo */}
      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-8">
        <div className="flex items-start gap-4">
          {/* Company Logo */}
          {details?.logo_url && (
            <div className="h-16 w-16 rounded-lg bg-white border overflow-hidden flex items-center justify-center p-2 flex-shrink-0">
              <Image
                src={details.logo_url}
                alt={`${details.name} logo`}
                width={48}
                height={48}
                className="object-contain"
                unoptimized
              />
            </div>
          )}
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold">{ticker}</h1>
              {wsStatus.connected && (
                <span className="flex items-center text-xs text-green-500">
                  <Activity className="h-3 w-3 mr-1 animate-pulse" />
                  Live
                </span>
              )}
            </div>
            <p className="text-lg text-muted-foreground">
              {details?.name || 'Loading...'}
            </p>
            <p className="text-sm text-muted-foreground">
              {details?.exchange} - {details?.type}
            </p>
          </div>
        </div>

        <div className="flex flex-col items-start md:items-end gap-2">
          <div className="flex items-center gap-4">
            <div className="text-right">
              <div className="text-3xl font-bold">
                {formatPrice(currentPrice)}
              </div>
              <div className={cn('flex items-center gap-1 text-lg', changeDisplay.colorClass)}>
                {isPositive ? (
                  <TrendingUp className="h-4 w-4" />
                ) : (
                  <TrendingDown className="h-4 w-4" />
                )}
                <span>{changeDisplay.text}</span>
                <span>({changePercentDisplay.text})</span>
              </div>
            </div>
          </div>
          
          <Button
            variant={inWatchlist ? 'default' : 'outline'}
            onClick={handleWatchlistToggle}
            className="gap-2"
          >
            <Star className={cn('h-4 w-4', inWatchlist && 'fill-current')} />
            {inWatchlist ? 'In Watchlist' : 'Add to Watchlist'}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content - Left 2 columns */}
        <div className="lg:col-span-2 space-y-6">
          {/* Chart Section */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <BarChart2 className="h-5 w-5" />
                  Price Chart
                </CardTitle>
                <div className="flex gap-1">
                  {(['1D', '5D', '1M', '3M', '6M', 'YTD', '1Y', '5Y'] as ChartRange[]).map((range) => (
                    <Button
                      key={range}
                      variant={selectedRange === range ? 'default' : 'ghost'}
                      size="sm"
                      onClick={() => setSelectedRange(range)}
                      className="text-xs px-2"
                    >
                      {range}
                    </Button>
                  ))}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {chart && chart.data.length > 0 ? (
                <div className="h-64 w-full">
                  <ChartPlaceholder data={chart.data} isPositive={isPositive} />
                </div>
              ) : (
                <div className="h-64 flex items-center justify-center text-muted-foreground">
                  No chart data available
                </div>
              )}
              {chart && (
                <p className="text-xs text-muted-foreground mt-2">
                  {chart.metadata.bar_count} data points from {chart.metadata.from_date} to {chart.metadata.to_date}
                </p>
              )}
            </CardContent>
          </Card>

          {/* Company Description */}
          {details?.description && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Building2 className="h-5 w-5" />
                  About {details.name}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {details.description}
                </p>
                {details.homepage_url && (
                  <a 
                    href={details.homepage_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-sm text-primary hover:underline mt-4"
                  >
                    <Globe className="h-4 w-4" />
                    {details.homepage_url.replace(/^https?:\/\//, '').replace(/\/$/, '')}
                    <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </CardContent>
            </Card>
          )}

          {/* News Section */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Newspaper className="h-5 w-5" />
                    Latest News
                  </CardTitle>
                  <CardDescription>
                    Recent headlines for {ticker}
                  </CardDescription>
                </div>
                <Badge variant="outline" className="gap-1">
                  <Lock className="h-3 w-3" />
                  Premium
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              {newsLoading ? (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="flex gap-4">
                      <Skeleton className="h-20 w-32 flex-shrink-0" />
                      <div className="flex-1 space-y-2">
                        <Skeleton className="h-4 w-full" />
                        <Skeleton className="h-4 w-3/4" />
                        <Skeleton className="h-3 w-1/2" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : news.length > 0 ? (
                <div className="space-y-4">
                  {news.slice(0, 3).map((article) => (
                    <NewsCard key={article.id} article={article} />
                  ))}
                  
                  {/* Premium Upsell */}
                  <Separator className="my-4" />
                  <div className="text-center py-4">
                    <p className="text-sm text-muted-foreground mb-3">
                      Get unlimited news, real-time alerts, and AI-powered insights
                    </p>
                    <Button className="gap-2">
                      <Lock className="h-4 w-4" />
                      Unlock Premium
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Newspaper className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No recent news available</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar - Right column */}
        <div className="space-y-6">
          {/* Basic Information */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Basic Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <InfoRow label="Market" value={details?.market || '--'} />
              <InfoRow label="Type" value={details?.type || '--'} />
              <InfoRow label="Currency" value={details?.currency?.toUpperCase() || 'USD'} />
              <InfoRow label="Status" value={details?.active ? 'Active' : 'Inactive'} />
              {details?.list_date && (
                <InfoRow 
                  label="Listed" 
                  value={new Date(details.list_date).toLocaleDateString('en-US', {
                    month: 'numeric',
                    day: 'numeric',
                    year: 'numeric'
                  })} 
                />
              )}
              <InfoRow label="Exchange" value={details?.exchange || '--'} />
            </CardContent>
          </Card>

          {/* Company Details */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Company Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {details?.total_employees && (
                <InfoRow 
                  label="Employees" 
                  value={details.total_employees.toLocaleString()}
                  icon={<Users className="h-4 w-4" />}
                />
              )}
              {details?.shares_outstanding && (
                <InfoRow 
                  label="Shares Outstanding" 
                  value={formatLargeNumber(details.shares_outstanding)}
                />
              )}
              {details?.weighted_shares_outstanding && (
                <InfoRow 
                  label="Weighted Shares" 
                  value={formatLargeNumber(details.weighted_shares_outstanding)}
                />
              )}
              {details?.round_lot && (
                <InfoRow label="Round Lot" value={details.round_lot.toString()} />
              )}
              {details?.market_cap && (
                <InfoRow 
                  label="Market Cap" 
                  value={formatMarketCap(details.market_cap)}
                />
              )}
              {details?.homepage_url && (
                <InfoRow 
                  label="Website"
                  value={
                    <a 
                      href={details.homepage_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline inline-flex items-center gap-1"
                    >
                      {details.homepage_url.replace(/^https?:\/\//, '').replace(/\/$/, '')}
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  }
                  icon={<Globe className="h-4 w-4" />}
                />
              )}
              {details?.address && (
                <InfoRow 
                  label="Headquarters"
                  value={formatAddress(details.address)}
                  icon={<MapPin className="h-4 w-4" />}
                />
              )}
              {details?.sic_description && (
                <InfoRow label="Industry" value={details.sic_description} />
              )}
            </CardContent>
          </Card>

          {/* Trading Statistics */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Trading Statistics</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <InfoRow label="Open" value={formatPrice(snapshot?.day?.open)} />
              <InfoRow label="High" value={formatPrice(snapshot?.day?.high)} />
              <InfoRow label="Low" value={formatPrice(snapshot?.day?.low)} />
              <InfoRow label="Previous Close" value={formatPrice(snapshot?.prev_close)} />
              <InfoRow label="Volume" value={formatVolume(snapshot?.day?.volume)} />
              <InfoRow label="VWAP" value={formatPrice(snapshot?.day?.vwap)} />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

// Helper Components
function InfoRow({ 
  label, 
  value, 
  icon 
}: { 
  label: string
  value: string | React.ReactNode
  icon?: React.ReactNode
}) {
  return (
    <div className="flex justify-between items-start gap-2">
      <span className="text-sm text-muted-foreground flex items-center gap-1.5">
        {icon}
        {label}
      </span>
      <span className="text-sm font-medium text-right">{value}</span>
    </div>
  )
}

function NewsCard({ article }: { article: NewsArticle }) {
  const publishedDate = new Date(article.published_utc)
  const timeAgo = getTimeAgo(publishedDate)

  return (
    <a 
      href={article.article_url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex gap-4 group hover:bg-muted/50 p-2 -mx-2 rounded-lg transition-colors"
    >
      {article.image_url && (
        <div className="h-20 w-32 flex-shrink-0 rounded-md overflow-hidden bg-muted">
          <Image
            src={article.image_url}
            alt={article.title}
            width={128}
            height={80}
            className="h-full w-full object-cover"
            unoptimized
          />
        </div>
      )}
      <div className="flex-1 min-w-0">
        <h4 className="text-sm font-medium line-clamp-2 group-hover:text-primary transition-colors">
          {article.title}
        </h4>
        {article.description && (
          <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
            {article.description}
          </p>
        )}
        <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
          {article.publisher_name && (
            <span>{article.publisher_name}</span>
          )}
          <span>-</span>
          <span>{timeAgo}</span>
        </div>
      </div>
    </a>
  )
}

function StockDetailSkeleton() {
  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <Skeleton className="h-4 w-32 mb-6" />
      <div className="flex justify-between mb-8">
        <div className="flex gap-4">
          <Skeleton className="h-16 w-16 rounded-lg" />
          <div>
            <Skeleton className="h-8 w-24 mb-2" />
            <Skeleton className="h-5 w-48 mb-1" />
            <Skeleton className="h-4 w-32" />
          </div>
        </div>
        <div className="text-right">
          <Skeleton className="h-8 w-32 mb-2" />
          <Skeleton className="h-5 w-24" />
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Skeleton className="h-80 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
        <div className="space-y-6">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    </div>
  )
}

function ChartPlaceholder({ data, isPositive }: { data: Array<{ close: number }>, isPositive: boolean }) {
  if (data.length === 0) return null

  const prices = data.map(d => d.close)
  const min = Math.min(...prices)
  const max = Math.max(...prices)
  const range = max - min || 1

  const width = 800
  const height = 200
  const padding = 20

  const points = prices.map((price, i) => {
    const x = padding + (i / (prices.length - 1)) * (width - padding * 2)
    const y = height - padding - ((price - min) / range) * (height - padding * 2)
    return `${x},${y}`
  }).join(' ')

  const strokeColor = isPositive ? '#22c55e' : '#ef4444'

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full">
      <polyline
        fill="none"
        stroke={strokeColor}
        strokeWidth="2"
        points={points}
      />
      <polygon
        fill={isPositive ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)'}
        points={`${padding},${height - padding} ${points} ${width - padding},${height - padding}`}
      />
    </svg>
  )
}

// Utility functions
function formatLargeNumber(num: number): string {
  if (num >= 1_000_000_000_000) {
    return `${(num / 1_000_000_000_000).toFixed(2)}T`
  }
  if (num >= 1_000_000_000) {
    return `${(num / 1_000_000_000).toFixed(2)}B`
  }
  if (num >= 1_000_000) {
    return `${(num / 1_000_000).toFixed(2)}M`
  }
  return num.toLocaleString()
}

function formatMarketCap(cap: number): string {
  if (cap >= 1_000_000_000_000) {
    return `$${(cap / 1_000_000_000_000).toFixed(2)}T`
  }
  if (cap >= 1_000_000_000) {
    return `$${(cap / 1_000_000_000).toFixed(2)}B`
  }
  if (cap >= 1_000_000) {
    return `$${(cap / 1_000_000).toFixed(2)}M`
  }
  return `$${cap.toLocaleString()}`
}

function formatAddress(address: { address1?: string | null; city?: string | null; state?: string | null }): string {
  const parts = []
  if (address.city) parts.push(address.city)
  if (address.state) parts.push(address.state)
  return parts.join(', ') || '--'
}

function getTimeAgo(date: Date): string {
  const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000)
  
  if (seconds < 60) return 'just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`
  
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}
