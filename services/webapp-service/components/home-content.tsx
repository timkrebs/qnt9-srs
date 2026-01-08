"use client"

import { useRef, useEffect, useState, useCallback } from "react"
import {
  ArrowUp,
  Search,
  Loader2,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Shield,
  Zap,
  Globe,
  Bell,
  LineChart,
  ArrowRight,
  ExternalLink,
  Plus,
  Star,
  Clock,
  Sparkles,
} from "lucide-react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useSearch } from "@/hooks/use-search"
import { useAuth } from "@/lib/auth/auth-context"
import { useWatchlist } from "@/hooks/use-watchlist"
import { cn } from "@/lib/utils"
import { stockService, NewsArticle } from "@/lib/api/stock"
import Footer from "@/components/footer"

// Types
interface MarketStock {
  ticker: string
  name: string
  price: number | null
  change_percent: number | null
  isLoading: boolean
}

interface FeatureCard {
  icon: React.ReactNode
  title: string
  description: string
}

// Constants
const FEATURED_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA"]

const FEATURES: FeatureCard[] = [
  {
    icon: <BarChart3 className="w-6 h-6" />,
    title: "Real-Time Data",
    description: "Access live market data with sub-second updates for informed trading decisions.",
  },
  {
    icon: <Shield className="w-6 h-6" />,
    title: "Secure Platform",
    description: "Enterprise-grade security protecting your portfolio data and transactions.",
  },
  {
    icon: <Zap className="w-6 h-6" />,
    title: "Fast Execution",
    description: "Lightning-fast API responses with 99.9% uptime guarantee.",
  },
  {
    icon: <Globe className="w-6 h-6" />,
    title: "Global Markets",
    description: "Track stocks across all major US exchanges and international markets.",
  },
  {
    icon: <Bell className="w-6 h-6" />,
    title: "Smart Alerts",
    description: "Customizable price alerts and portfolio notifications via email or push.",
  },
  {
    icon: <LineChart className="w-6 h-6" />,
    title: "Advanced Analytics",
    description: "Comprehensive charts, technical indicators, and fundamental analysis.",
  },
]

const SEARCH_SUGGESTIONS = [
  "Search AAPL",
  "Find Tesla stock",
  "MSFT quote",
  "Amazon price",
  "Google stock",
]

export default function HomeContent() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()
  const { items: watchlistItems, isLoading: watchlistLoading, total: watchlistTotal, limit: watchlistLimit, tier } = useWatchlist()
  const { query, setQuery, results, isLoading, error } = useSearch({
    debounceMs: 300,
    minQueryLength: 1,
  })

  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const [marketStocks, setMarketStocks] = useState<MarketStock[]>(
    FEATURED_TICKERS.map((ticker) => ({
      ticker,
      name: "",
      price: null,
      change_percent: null,
      isLoading: true,
    }))
  )
  const [newsArticles, setNewsArticles] = useState<NewsArticle[]>([])
  const [newsLoading, setNewsLoading] = useState(true)
  const [personalizedNews, setPersonalizedNews] = useState<NewsArticle[]>([])
  const [personalizedNewsLoading, setPersonalizedNewsLoading] = useState(true)

  // Fetch market data
  const fetchMarketData = useCallback(async () => {
    const promises = FEATURED_TICKERS.map(async (ticker) => {
      try {
        const response = await stockService.getPrice(ticker)
        const detailResponse = await stockService.getTickerDetails(ticker)
        return {
          ticker,
          name: detailResponse.data?.name || ticker,
          price: response.price,
          change_percent: response.change_percent,
          isLoading: false,
        }
      } catch {
        return {
          ticker,
          name: ticker,
          price: null,
          change_percent: null,
          isLoading: false,
        }
      }
    })

    const results = await Promise.all(promises)
    setMarketStocks(results)
  }, [])

  // Fetch news data (for logged-out users)
  const fetchNewsData = useCallback(async () => {
    try {
      setNewsLoading(true)
      const response = await stockService.getNews("SPY", 6)
      if (response.success && response.articles) {
        setNewsArticles(response.articles)
      }
    } catch {
      console.error("Failed to fetch news")
    } finally {
      setNewsLoading(false)
    }
  }, [])

  // Fetch personalized news for watchlist tickers
  const fetchPersonalizedNews = useCallback(async () => {
    if (!isAuthenticated || watchlistItems.length === 0) {
      setPersonalizedNewsLoading(false)
      return
    }

    try {
      setPersonalizedNewsLoading(true)
      const tickersToFetch = watchlistItems.slice(0, 3).map((item) => item.symbol)
      const newsPromises = tickersToFetch.map((ticker) =>
        stockService.getNews(ticker, 2).catch(() => ({ success: false, articles: [] }))
      )
      const responses = await Promise.all(newsPromises)
      const allNews = responses
        .filter((r) => r.success)
        .flatMap((r) => r.articles || [])
      // Deduplicate articles by id to avoid React key warnings
      const uniqueNews = Array.from(
        new Map(allNews.map((article) => [article.id, article])).values()
      ).slice(0, 6)
      setPersonalizedNews(uniqueNews)
    } catch {
      console.error("Failed to fetch personalized news")
    } finally {
      setPersonalizedNewsLoading(false)
    }
  }, [isAuthenticated, watchlistItems])

  useEffect(() => {
    fetchMarketData()
    if (!isAuthenticated) {
      fetchNewsData()
    }
  }, [fetchMarketData, fetchNewsData, isAuthenticated])

  useEffect(() => {
    if (isAuthenticated && !watchlistLoading) {
      fetchPersonalizedNews()
    }
  }, [isAuthenticated, watchlistLoading, fetchPersonalizedNews])

  // Event handlers
  const handleSearch = () => {
    if (!query.trim()) return
    router.push(`/search?q=${encodeURIComponent(query.trim())}`)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch()
    }
  }

  const handleResultClick = (symbol: string) => {
    router.push(`/stock/${encodeURIComponent(symbol)}`)
  }

  const handleSuggestionClick = (suggestion: string) => {
    const searchTerm = suggestion
      .replace(/^(Search |Find |)/, "")
      .replace(/ (stock|quote|price)$/, "")
    setQuery(searchTerm)
    inputRef.current?.focus()
  }

  const handleStockClick = (ticker: string) => {
    router.push(`/stock/${ticker}`)
  }

  const handleGetStarted = () => {
    router.push("/signup")
  }

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        // Keep results but don't clear them
      }
    }

    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const showDropdown = query.length >= 1 && (results.length > 0 || isLoading || error)

  // Utility functions
  const formatPrice = (price: number | null): string => {
    if (price === null) return "--"
    return `$${price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  const formatPercent = (percent: number | string | null): string => {
    if (percent === null || percent === undefined) return "--"
    const num = typeof percent === 'string' ? parseFloat(percent) : percent
    if (isNaN(num)) return "--"
    const sign = num >= 0 ? "+" : ""
    return `${sign}${num.toFixed(2)}%`
  }

  const formatDate = (dateStr: string): string => {
    const date = new Date(dateStr)
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" })
  }

  const getGreeting = (): string => {
    const hour = new Date().getHours()
    if (hour < 12) return "Good morning"
    if (hour < 18) return "Good afternoon"
    return "Good evening"
  }

  const getFirstName = (): string => {
    if (!user?.full_name) return ""
    return user.full_name.split(" ")[0]
  }

  // Show loading state while checking auth
  if (authLoading) {
    return (
      <main className="flex-1 pt-14">
        <div className="flex items-center justify-center min-h-[60vh]">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      </main>
    )
  }

  // Logged-in Dashboard View
  if (isAuthenticated) {
    return (
      <main className="flex-1 pt-14 bg-gray-50 min-h-screen">
        {/* Dashboard Header */}
        <section className="bg-white border-b border-gray-100">
          <div className="max-w-6xl mx-auto px-4 md:px-8 py-6 md:py-8">
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-2xl font-semibold text-gray-900">
                  {getGreeting()}, {getFirstName()}
                </h1>
                <p className="text-gray-500 mt-1">
                  Welcome back to your research dashboard
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="px-3 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-600 capitalize">
                  {tier} Plan
                </span>
              </div>
            </div>

            {/* Search Bar */}
            <div className="mt-6 max-w-2xl relative">
              <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  ref={inputRef}
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Search stocks..."
                  aria-label="Search stocks"
                  className="w-full px-5 py-3 pl-12 pr-12 rounded-xl border border-gray-200 bg-gray-50 focus:bg-white focus:border-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-100 text-base transition-all"
                />
                <button
                  onClick={handleSearch}
                  disabled={!query.trim()}
                  aria-label="Submit search"
                  className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-lg bg-gray-900 text-white flex items-center justify-center hover:bg-gray-800 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <ArrowUp className="w-4 h-4" />
                  )}
                </button>
              </div>

              {/* Search Dropdown */}
              {showDropdown && (
                <div
                  ref={dropdownRef}
                  className="absolute top-full left-0 right-0 mt-2 bg-white rounded-xl border border-gray-200 shadow-lg overflow-hidden z-50"
                >
                  {isLoading && results.length === 0 && (
                    <div className="px-5 py-3 text-gray-500 flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Searching...</span>
                    </div>
                  )}
                  {error && (
                    <div className="px-5 py-3 text-red-500 text-sm">{error}</div>
                  )}
                  {!error && results.length > 0 && (
                    <ul className="max-h-64 overflow-y-auto">
                      {results.slice(0, 5).map((result, index) => (
                        <li key={`${result.symbol}-${index}`}>
                          <button
                            onClick={() => handleResultClick(result.symbol)}
                            className="w-full px-5 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors text-left"
                          >
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center font-semibold text-gray-600 text-xs">
                                {result.symbol.slice(0, 2)}
                              </div>
                              <div>
                                <div className="font-medium text-gray-900 text-sm">
                                  {result.symbol}
                                </div>
                                <div className="text-xs text-gray-500 truncate max-w-xs">
                                  {result.name}
                                </div>
                              </div>
                            </div>
                            {result.price !== undefined && (
                              <div className="text-right">
                                <div className="font-medium text-gray-900 text-sm">
                                  ${result.price.toFixed(2)}
                                </div>
                                {result.change_percent !== undefined && (
                                  <div
                                    className={cn(
                                      "text-xs",
                                      result.change_percent >= 0 ? "text-green-600" : "text-red-600"
                                    )}
                                  >
                                    {formatPercent(result.change_percent)}
                                  </div>
                                )}
                              </div>
                            )}
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          </div>
        </section>

        {/* Dashboard Content */}
        <div className="max-w-6xl mx-auto px-4 md:px-8 py-6 md:py-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Main Content - 2 columns */}
            <div className="lg:col-span-2 space-y-6">
              {/* Watchlist Widget */}
              <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Star className="w-5 h-5 text-yellow-500" />
                    <h2 className="font-semibold text-gray-900">My Watchlist</h2>
                    <span className="text-sm text-gray-500">
                      ({watchlistTotal}/{watchlistLimit})
                    </span>
                  </div>
                  <Link
                    href="/watchlist"
                    className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1 transition-colors"
                  >
                    View all <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>
                <div className="p-4">
                  {watchlistLoading ? (
                    <div className="space-y-3">
                      {[...Array(3)].map((_, i) => (
                        <div key={i} className="animate-pulse flex items-center justify-between p-3">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-gray-100 rounded-lg" />
                            <div>
                              <div className="h-4 bg-gray-100 rounded w-16 mb-1" />
                              <div className="h-3 bg-gray-100 rounded w-24" />
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="h-4 bg-gray-100 rounded w-16 mb-1" />
                            <div className="h-3 bg-gray-100 rounded w-12" />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : watchlistItems.length > 0 ? (
                    <div className="space-y-1">
                      {watchlistItems.slice(0, 5).map((item) => (
                        <button
                          key={item.id}
                          onClick={() => handleStockClick(item.symbol)}
                          className="w-full flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 transition-colors text-left"
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center font-semibold text-gray-700 text-sm">
                              {item.symbol.slice(0, 2)}
                            </div>
                            <div>
                              <div className="font-medium text-gray-900">{item.symbol}</div>
                              <div className="text-sm text-gray-500 truncate max-w-[200px]">
                                {item.name || item.symbol}
                              </div>
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="font-medium text-gray-900">
                              {formatPrice(item.price ?? null)}
                            </div>
                            <div
                              className={cn(
                                "text-sm flex items-center gap-1 justify-end",
                                (item.change_percent ?? 0) >= 0 ? "text-green-600" : "text-red-600"
                              )}
                            >
                              {(item.change_percent ?? 0) >= 0 ? (
                                <TrendingUp className="w-3 h-3" />
                              ) : (
                                <TrendingDown className="w-3 h-3" />
                              )}
                              {formatPercent(item.change_percent ?? null)}
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <Star className="w-12 h-12 text-gray-200 mx-auto mb-3" />
                      <p className="text-gray-500 mb-4">Your watchlist is empty</p>
                      <button
                        onClick={() => inputRef.current?.focus()}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-900 text-white text-sm hover:bg-gray-800 transition-colors"
                      >
                        <Plus className="w-4 h-4" />
                        Add stocks
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Personalized News */}
              <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-purple-500" />
                    <h2 className="font-semibold text-gray-900">Your News Feed</h2>
                  </div>
                </div>
                <div className="p-4">
                  {personalizedNewsLoading ? (
                    <div className="space-y-4">
                      {[...Array(3)].map((_, i) => (
                        <div key={i} className="animate-pulse flex gap-4">
                          <div className="w-20 h-16 bg-gray-100 rounded-lg shrink-0" />
                          <div className="flex-1">
                            <div className="h-4 bg-gray-100 rounded w-full mb-2" />
                            <div className="h-3 bg-gray-100 rounded w-3/4" />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : personalizedNews.length > 0 ? (
                    <div className="space-y-4">
                      {personalizedNews.slice(0, 4).map((article) => (
                        <a
                          key={article.id}
                          href={article.article_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex gap-4 p-2 -mx-2 rounded-lg hover:bg-gray-50 transition-colors group"
                        >
                          {article.image_url ? (
                            <img
                              src={article.image_url}
                              alt=""
                              className="w-20 h-16 object-cover rounded-lg shrink-0"
                            />
                          ) : (
                            <div className="w-20 h-16 bg-gray-100 rounded-lg shrink-0 flex items-center justify-center">
                              <BarChart3 className="w-6 h-6 text-gray-300" />
                            </div>
                          )}
                          <div className="flex-1 min-w-0">
                            <h3 className="font-medium text-gray-900 text-sm line-clamp-2 group-hover:text-gray-700 transition-colors">
                              {article.title}
                            </h3>
                            <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                              {article.publisher_name && (
                                <span>{article.publisher_name}</span>
                              )}
                              <span>{formatDate(article.published_utc)}</span>
                            </div>
                          </div>
                        </a>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <Bell className="w-12 h-12 text-gray-200 mx-auto mb-3" />
                      <p className="text-gray-500">
                        Add stocks to your watchlist to see personalized news
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Sidebar - 1 column */}
            <div className="space-y-6">
              {/* Market Overview Card */}
              <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-100">
                  <h2 className="font-semibold text-gray-900">Market Overview</h2>
                </div>
                <div className="p-2">
                  {marketStocks.map((stock) => (
                    <button
                      key={stock.ticker}
                      onClick={() => handleStockClick(stock.ticker)}
                      className="w-full flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 transition-colors text-left"
                    >
                      {stock.isLoading ? (
                        <div className="animate-pulse flex items-center justify-between w-full">
                          <div className="h-4 bg-gray-100 rounded w-12" />
                          <div className="h-4 bg-gray-100 rounded w-16" />
                        </div>
                      ) : (
                        <>
                          <span className="font-medium text-gray-900 text-sm">{stock.ticker}</span>
                          <div className="flex items-center gap-2">
                            <span className="text-sm text-gray-700">{formatPrice(stock.price)}</span>
                            <span
                              className={cn(
                                "text-xs font-medium",
                                stock.change_percent !== null && stock.change_percent >= 0
                                  ? "text-green-600"
                                  : "text-red-600"
                              )}
                            >
                              {formatPercent(stock.change_percent)}
                            </span>
                          </div>
                        </>
                      )}
                    </button>
                  ))}
                </div>
              </div>

              {/* Quick Actions Card */}
              <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-100">
                  <h2 className="font-semibold text-gray-900">Quick Actions</h2>
                </div>
                <div className="p-4 space-y-2">
                  <Link
                    href="/watchlist"
                    className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className="w-10 h-10 rounded-lg bg-yellow-50 flex items-center justify-center">
                      <Star className="w-5 h-5 text-yellow-600" />
                    </div>
                    <div>
                      <div className="font-medium text-gray-900 text-sm">Manage Watchlist</div>
                      <div className="text-xs text-gray-500">{watchlistTotal} stocks tracked</div>
                    </div>
                  </Link>
                  <Link
                    href="/settings"
                    className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center">
                      <Bell className="w-5 h-5 text-blue-600" />
                    </div>
                    <div>
                      <div className="font-medium text-gray-900 text-sm">Price Alerts</div>
                      <div className="text-xs text-gray-500">Configure notifications</div>
                    </div>
                  </Link>
                  <Link
                    href="/profile"
                    className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center">
                      <Clock className="w-5 h-5 text-gray-600" />
                    </div>
                    <div>
                      <div className="font-medium text-gray-900 text-sm">Account Settings</div>
                      <div className="text-xs text-gray-500">View profile and plan</div>
                    </div>
                  </Link>
                </div>
              </div>

              {/* Upgrade Card (for free tier) */}
              {tier === "free" && (
                <div className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-xl p-6 text-white">
                  <h3 className="font-semibold mb-2">Upgrade to Premium</h3>
                  <p className="text-sm text-gray-300 mb-4">
                    Unlock unlimited watchlist, advanced alerts, and API access.
                  </p>
                  <Link
                    href="/settings?tab=billing"
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white text-gray-900 text-sm font-medium hover:bg-gray-100 transition-colors"
                  >
                    <Sparkles className="w-4 h-4" />
                    Upgrade Now
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    )
  }

  // Logged-Out Landing Page View
  return (
    <main className="flex-1 pt-14">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-gray-50 via-white to-gray-100">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-blue-50 via-transparent to-transparent opacity-60" />
        <div className="relative max-w-6xl mx-auto px-4 md:px-8 py-12 md:py-20">
          <div className="flex flex-col items-center text-center">
            <h1 className="text-3xl md:text-4xl lg:text-5xl font-semibold tracking-tight text-gray-900 mb-4">
              Stock Research Platform
            </h1>
            <p className="text-lg md:text-xl text-gray-600 mb-8 md:mb-10 max-w-2xl">
              Professional-grade market data, real-time quotes, and comprehensive
              analytics for informed investment decisions.
            </p>

            {/* Search Input */}
            <div className="w-full max-w-2xl mb-6 relative">
              <div className="relative">
                <Search className="absolute left-5 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  ref={inputRef}
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Search by symbol, name, or ISIN..."
                  aria-label="Search stocks"
                  className="w-full px-6 py-4 pl-14 pr-14 rounded-full border border-gray-200 bg-white focus:border-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-100 text-base shadow-sm transition-all"
                />
                <button
                  onClick={handleSearch}
                  disabled={!query.trim()}
                  aria-label="Submit search"
                  className="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-gray-900 text-white flex items-center justify-center hover:bg-gray-800 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <ArrowUp className="w-4 h-4" />
                  )}
                </button>
              </div>

              {/* Search Results Dropdown */}
              {showDropdown && (
                <div
                  ref={dropdownRef}
                  className="absolute top-full left-0 right-0 mt-2 bg-white rounded-2xl border border-gray-200 shadow-lg overflow-hidden z-50"
                >
                  {isLoading && results.length === 0 && (
                    <div className="px-6 py-4 text-gray-500 flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Searching...</span>
                    </div>
                  )}

                  {error && (
                    <div className="px-6 py-4 text-red-500 text-sm">{error}</div>
                  )}

                  {!error && results.length > 0 && (
                    <ul className="max-h-80 overflow-y-auto">
                      {results.slice(0, 6).map((result, index) => (
                        <li key={`${result.symbol}-${index}`}>
                          <button
                            onClick={() => handleResultClick(result.symbol)}
                            className="w-full px-6 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors text-left"
                          >
                            <div className="flex items-center gap-4">
                              <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center font-semibold text-gray-600 text-sm">
                                {result.symbol.slice(0, 2)}
                              </div>
                              <div>
                                <div className="font-medium text-gray-900">
                                  {result.symbol}
                                </div>
                                <div className="text-sm text-gray-500 truncate max-w-xs">
                                  {result.name}
                                </div>
                              </div>
                            </div>
                            <div className="text-right">
                              {result.price !== undefined && (
                                <div className="font-medium text-gray-900">
                                  ${result.price.toFixed(2)}
                                </div>
                              )}
                              {result.change_percent !== undefined && (
                                <div
                                  className={cn(
                                    "text-sm flex items-center gap-1 justify-end",
                                    result.change_percent >= 0
                                      ? "text-green-600"
                                      : "text-red-600"
                                  )}
                                >
                                  {result.change_percent >= 0 ? (
                                    <TrendingUp className="w-3 h-3" />
                                  ) : (
                                    <TrendingDown className="w-3 h-3" />
                                  )}
                                  {formatPercent(result.change_percent)}
                                </div>
                              )}
                            </div>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}

                  {!isLoading && !error && results.length > 0 && (
                    <div className="px-6 py-3 border-t border-gray-100 bg-gray-50">
                      <button
                        onClick={handleSearch}
                        className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
                      >
                        View all results for &quot;{query}&quot;
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Suggestion Pills */}
            <div className="flex flex-wrap gap-2 justify-center">
              {SEARCH_SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="px-4 py-2 rounded-full border border-gray-200 bg-white text-sm text-gray-600 hover:bg-gray-50 hover:border-gray-300 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Market Overview Section */}
      <section className="bg-white border-y border-gray-100">
        <div className="max-w-6xl mx-auto px-6 md:px-8 py-12">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-2xl font-semibold text-gray-900">Market Overview</h2>
              <p className="text-gray-500 mt-1">Top stocks by market cap</p>
            </div>
            <button
              onClick={() => router.push("/search")}
              className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1 transition-colors"
            >
              View all <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {marketStocks.map((stock) => (
              <button
                key={stock.ticker}
                onClick={() => handleStockClick(stock.ticker)}
                className="p-4 rounded-xl border border-gray-100 bg-gray-50/50 hover:bg-gray-100 hover:border-gray-200 transition-all text-left group"
              >
                {stock.isLoading ? (
                  <div className="animate-pulse">
                    <div className="h-4 bg-gray-200 rounded w-12 mb-2" />
                    <div className="h-6 bg-gray-200 rounded w-16 mb-1" />
                    <div className="h-4 bg-gray-200 rounded w-14" />
                  </div>
                ) : (
                  <>
                    <div className="font-semibold text-gray-900 group-hover:text-gray-700">
                      {stock.ticker}
                    </div>
                    <div className="text-lg font-medium text-gray-800 mt-1">
                      {formatPrice(stock.price)}
                    </div>
                    <div
                      className={cn(
                        "text-sm flex items-center gap-1 mt-0.5",
                        stock.change_percent !== null && stock.change_percent >= 0
                          ? "text-green-600"
                          : "text-red-600"
                      )}
                    >
                      {stock.change_percent !== null && stock.change_percent >= 0 ? (
                        <TrendingUp className="w-3 h-3" />
                      ) : (
                        <TrendingDown className="w-3 h-3" />
                      )}
                      {formatPercent(stock.change_percent)}
                    </div>
                  </>
                )}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="bg-gray-50">
        <div className="max-w-6xl mx-auto px-6 md:px-8 py-16">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-semibold text-gray-900 mb-4">
              Everything you need for market research
            </h2>
            <p className="text-gray-600 max-w-2xl mx-auto">
              Professional tools and data to help you make informed investment decisions.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map((feature, index) => (
              <div
                key={index}
                className="p-6 rounded-xl bg-white border border-gray-100 hover:border-gray-200 hover:shadow-sm transition-all"
              >
                <div className="w-12 h-12 rounded-lg bg-gray-100 flex items-center justify-center text-gray-700 mb-4">
                  {feature.icon}
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-gray-600 text-sm leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* News Section */}
      <section className="bg-white">
        <div className="max-w-6xl mx-auto px-6 md:px-8 py-16">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-2xl font-semibold text-gray-900">Market News</h2>
              <p className="text-gray-500 mt-1">Latest financial headlines</p>
            </div>
          </div>

          {newsLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="animate-pulse">
                  <div className="h-40 bg-gray-100 rounded-xl mb-3" />
                  <div className="h-4 bg-gray-100 rounded w-3/4 mb-2" />
                  <div className="h-4 bg-gray-100 rounded w-1/2" />
                </div>
              ))}
            </div>
          ) : newsArticles.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {newsArticles.map((article) => (
                <a
                  key={article.id}
                  href={article.article_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group block"
                >
                  <div className="rounded-xl border border-gray-100 overflow-hidden hover:border-gray-200 hover:shadow-sm transition-all">
                    {article.image_url ? (
                      <div className="h-40 bg-gray-100 overflow-hidden">
                        <img
                          src={article.image_url}
                          alt=""
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        />
                      </div>
                    ) : (
                      <div className="h-40 bg-gradient-to-br from-gray-100 to-gray-50 flex items-center justify-center">
                        <BarChart3 className="w-12 h-12 text-gray-300" />
                      </div>
                    )}
                    <div className="p-4">
                      <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
                        {article.publisher_name && (
                          <span className="font-medium">{article.publisher_name}</span>
                        )}
                        <span>{formatDate(article.published_utc)}</span>
                      </div>
                      <h3 className="font-medium text-gray-900 line-clamp-2 group-hover:text-gray-700 transition-colors">
                        {article.title}
                      </h3>
                      <div className="mt-3 flex items-center text-xs text-gray-500 group-hover:text-gray-700 transition-colors">
                        <span>Read more</span>
                        <ExternalLink className="w-3 h-3 ml-1" />
                      </div>
                    </div>
                  </div>
                </a>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500">
              No news articles available at this time.
            </div>
          )}
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-gray-900">
        <div className="max-w-6xl mx-auto px-6 md:px-8 py-16 text-center">
          <h2 className="text-3xl font-semibold text-white mb-4">
            Ready to start researching?
          </h2>
          <p className="text-gray-400 mb-8 max-w-xl mx-auto">
            Get access to comprehensive market data, real-time quotes, and advanced
            analytics tools.
          </p>
          <button
            onClick={handleGetStarted}
            className="px-8 py-3 rounded-full bg-white text-gray-900 font-medium hover:bg-gray-100 transition-colors"
          >
            Get Started
          </button>
        </div>
      </section>

      <Footer />
    </main>
  )
}
