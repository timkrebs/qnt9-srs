"use client"

import { useEffect, useCallback, useState } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import {
  ArrowUp,
  Search,
  Loader2,
  TrendingUp,
  TrendingDown,
  Building2,
  ExternalLink,
  ArrowLeft,
  Star,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useSearch } from "@/hooks/use-search"
import { useWatchlist } from "@/hooks/use-watchlist"
import { useAuth } from "@/lib/auth/auth-context"
import { useToast } from "@/hooks/use-toast"
import { cn } from "@/lib/utils"

export default function SearchContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const initialQuery = searchParams.get("q") || ""
  const { toast } = useToast()
  const { isAuthenticated } = useAuth()
  const { isInWatchlist, toggleWatchlist, isAtLimit, tier, total, limit } = useWatchlist()
  const [togglingSymbol, setTogglingSymbol] = useState<string | null>(null)

  const { query, setQuery, results, isLoading, error, totalResults, latencyMs } =
    useSearch({
      debounceMs: 300,
      minQueryLength: 1,
    })

  // Set initial query from URL params
  useEffect(() => {
    if (initialQuery && !query) {
      setQuery(initialQuery)
    }
  }, [initialQuery, query, setQuery])

  // Update URL when query changes
  const updateUrl = useCallback(
    (newQuery: string) => {
      if (newQuery.trim()) {
        router.replace(`/search?q=${encodeURIComponent(newQuery.trim())}`, {
          scroll: false,
        })
      } else {
        router.replace("/search", { scroll: false })
      }
    },
    [router],
  )

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newQuery = e.target.value
    setQuery(newQuery)
    updateUrl(newQuery)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      router.push("/")
    }
  }

  const handleToggleWatchlist = async (e: React.MouseEvent, symbol: string) => {
    e.stopPropagation()

    if (!isAuthenticated) {
      toast({
        title: "Login required",
        description: "Please log in to add stocks to your watchlist",
        variant: "destructive",
      })
      router.push("/login")
      return
    }

    const inWatchlist = isInWatchlist(symbol)

    if (!inWatchlist && isAtLimit) {
      toast({
        title: "Watchlist limit reached",
        description: `You have reached your ${tier} tier limit of ${limit} stocks. Upgrade for unlimited watchlist.`,
        variant: "destructive",
      })
      return
    }

    setTogglingSymbol(symbol)
    const success = await toggleWatchlist(symbol)
    setTogglingSymbol(null)

    if (success) {
      toast({
        title: inWatchlist ? "Removed from watchlist" : "Added to watchlist",
        description: inWatchlist
          ? `${symbol} has been removed from your watchlist`
          : `${symbol} has been added to your watchlist (${total + 1}/${limit})`,
      })
    }
  }

  return (
    <main className="pt-14 min-h-screen px-4 md:px-8 pb-16">
      <div className="max-w-4xl mx-auto">
        {/* Back Button */}
        <div className="pt-8 pb-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push("/")}
            className="text-gray-500 hover:text-gray-900"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Home
          </Button>
        </div>

        {/* Search Input */}
        <div className="mb-8">
          <div className="relative">
            <Search className="absolute left-0 top-1/2 -translate-y-1/2 w-8 h-8 text-gray-300" />
            <input
              type="text"
              value={query}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              className="w-full text-4xl md:text-5xl font-normal border-none outline-none bg-transparent text-black placeholder-gray-300 pl-12"
              placeholder="Search stocks..."
              autoFocus
            />
          </div>
          <div className="h-px bg-gray-200 mt-4" />

          {/* Search Stats */}
          {!isLoading && results.length > 0 && (
            <div className="mt-3 flex items-center gap-4 text-sm text-gray-500">
              <span>
                {totalResults} result{totalResults !== 1 ? "s" : ""}
              </span>
              {latencyMs !== null && <span>({latencyMs}ms)</span>}
            </div>
          )}
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
            <span className="ml-3 text-gray-500">Searching...</span>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
            <p className="text-red-600">{error}</p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setQuery(query)}
              className="mt-4"
            >
              Try Again
            </Button>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !error && query && results.length === 0 && (
          <div className="text-center py-16">
            <Search className="w-16 h-16 text-gray-200 mx-auto mb-4" />
            <h3 className="text-xl font-medium text-gray-900 mb-2">
              No results found
            </h3>
            <p className="text-gray-500">
              Try searching for a different stock symbol, company name, ISIN, or
              WKN
            </p>
          </div>
        )}

        {/* Results Grid */}
        {!isLoading && !error && results.length > 0 && (
          <div className="grid gap-4">
            {results.map((result, index) => {
              const inWatchlist = isInWatchlist(result.symbol)
              const isToggling = togglingSymbol === result.symbol

              return (
              <Card
                key={`${result.symbol}-${index}`}
                className="hover:shadow-md transition-shadow cursor-pointer group"
                onClick={() => router.push(`/stock/${result.symbol}`)}
              >
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    {/* Left Side - Stock Info */}
                    <div className="flex items-start gap-4">
                      <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center font-bold text-gray-600 text-lg">
                        {result.symbol.slice(0, 2)}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-xl font-semibold text-gray-900">
                            {result.symbol}
                          </h3>
                          <ExternalLink className="w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </div>
                        <p className="text-gray-600 mt-0.5">{result.name}</p>
                        <div className="flex items-center gap-2 mt-2">
                          {result.exchange && (
                            <Badge variant="secondary" className="text-xs">
                              <Building2 className="w-3 h-3 mr-1" />
                              {result.exchange}
                            </Badge>
                          )}
                          {result.type && (
                            <Badge variant="outline" className="text-xs">
                              {result.type}
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Right Side - Price Info & Watchlist Button */}
                    <div className="flex items-start gap-4">
                      <div className="text-right">
                      {result.price !== undefined && (
                        <div className="text-2xl font-semibold text-gray-900">
                          ${result.price.toFixed(2)}
                        </div>
                      )}
                      {result.change !== undefined &&
                        result.change_percent !== undefined && (
                          <div
                            className={cn(
                              "flex items-center gap-2 justify-end mt-1",
                              result.change >= 0
                                ? "text-green-600"
                                : "text-red-600",
                            )}
                          >
                            {result.change >= 0 ? (
                              <TrendingUp className="w-4 h-4" />
                            ) : (
                              <TrendingDown className="w-4 h-4" />
                            )}
                            <span className="font-medium">
                              {result.change >= 0 ? "+" : ""}
                              {result.change.toFixed(2)} (
                              {result.change_percent >= 0 ? "+" : ""}
                              {result.change_percent.toFixed(2)}%)
                            </span>
                          </div>
                        )}
                      {result.volume !== undefined && (
                        <div className="text-sm text-gray-400 mt-2">
                          Vol: {(result.volume / 1000000).toFixed(2)}M
                        </div>
                      )}
                      </div>

                      {/* Watchlist Button */}
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={(e) => handleToggleWatchlist(e, result.symbol)}
                        disabled={isToggling}
                        className={cn(
                          "transition-colors",
                          inWatchlist
                            ? "text-amber-500 hover:text-amber-600 hover:bg-amber-50"
                            : "text-gray-400 hover:text-amber-500 hover:bg-amber-50"
                        )}
                        aria-label={inWatchlist ? `Remove ${result.symbol} from watchlist` : `Add ${result.symbol} to watchlist`}
                      >
                        {isToggling ? (
                          <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                          <Star className={cn("w-5 h-5", inWatchlist && "fill-current")} />
                        )}
                      </Button>
                    </div>
                  </div>

                  {/* Additional Info Row */}
                  {(result.isin || result.wkn) && (
                    <div className="mt-4 pt-4 border-t border-gray-100 flex gap-6 text-sm text-gray-500">
                      {result.isin && (
                        <span>
                          <span className="font-medium">ISIN:</span>{" "}
                          {result.isin}
                        </span>
                      )}
                      {result.wkn && (
                        <span>
                          <span className="font-medium">WKN:</span> {result.wkn}
                        </span>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
              )
            })}
          </div>
        )}

        {/* Scroll to Top Button */}
        <Button
          variant="ghost"
          size="icon"
          className="fixed bottom-8 right-8 w-12 h-12 rounded-full bg-black text-white hover:bg-gray-800 shadow-lg"
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
        >
          <ArrowUp className="w-5 h-5" />
        </Button>
      </div>
    </main>
  )
}
