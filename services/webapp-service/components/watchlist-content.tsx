'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  ArrowLeft,
  Star,
  Trash2,
  TrendingUp,
  TrendingDown,
  Loader2,
  ExternalLink,
  AlertCircle,
  Sparkles,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useAuth } from '@/lib/auth/auth-context'
import { useWatchlist, type WatchlistItemWithPrice } from '@/hooks/use-watchlist'
import { cn } from '@/lib/utils'

const WatchlistSkeleton = () => {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map((i) => (
        <Card key={i} className="animate-pulse">
          <CardContent className="p-6">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4">
                <div className="w-14 h-14 rounded-xl bg-gray-200" />
                <div className="space-y-2">
                  <div className="h-6 w-20 bg-gray-200 rounded" />
                  <div className="h-4 w-32 bg-gray-200 rounded" />
                </div>
              </div>
              <div className="space-y-2 text-right">
                <div className="h-6 w-24 bg-gray-200 rounded" />
                <div className="h-4 w-16 bg-gray-200 rounded" />
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

interface WatchlistCardProps {
  item: WatchlistItemWithPrice
  onRemove: (symbol: string) => void
  isRemoving: boolean
}

const WatchlistCard = ({ item, onRemove, isRemoving }: WatchlistCardProps) => {
  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation()
    onRemove(item.symbol)
  }

  const handleOpenYahoo = () => {
    window.open(`https://finance.yahoo.com/quote/${item.symbol}`, '_blank')
  }

  return (
    <Card
      className="hover:shadow-md transition-shadow cursor-pointer group"
      onClick={handleOpenYahoo}
    >
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          {/* Left Side - Stock Info */}
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center font-bold text-gray-600 text-lg">
              {item.symbol.slice(0, 2)}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-xl font-semibold text-gray-900">
                  {item.symbol}
                </h3>
                <ExternalLink className="w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              {item.name && (
                <p className="text-gray-600 mt-0.5">{item.name}</p>
              )}
              <div className="flex items-center gap-2 mt-2">
                <Badge variant="secondary" className="text-xs">
                  <Star className="w-3 h-3 mr-1 fill-current" />
                  Watching
                </Badge>
                {item.notes && (
                  <Badge variant="outline" className="text-xs max-w-[200px] truncate">
                    {item.notes}
                  </Badge>
                )}
              </div>
            </div>
          </div>

          {/* Right Side - Price Info & Actions */}
          <div className="flex items-start gap-4">
            <div className="text-right">
              {item.priceLoading ? (
                <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
              ) : item.price !== undefined ? (
                <>
                  <div className="text-2xl font-semibold text-gray-900">
                    ${Number(item.price).toFixed(2)}
                  </div>
                  {item.change !== undefined && item.change_percent !== undefined && (
                    <div
                      className={cn(
                        'flex items-center gap-1 justify-end mt-1',
                        Number(item.change) >= 0 ? 'text-green-600' : 'text-red-600',
                      )}
                    >
                      {Number(item.change) >= 0 ? (
                        <TrendingUp className="w-4 h-4" />
                      ) : (
                        <TrendingDown className="w-4 h-4" />
                      )}
                      <span className="font-medium">
                        {Number(item.change) >= 0 ? '+' : ''}
                        {Number(item.change).toFixed(2)} ({Number(item.change_percent) >= 0 ? '+' : ''}
                        {Number(item.change_percent).toFixed(2)}%)
                      </span>
                    </div>
                  )}
                </>
              ) : (
                <span className="text-gray-400 text-sm">Price unavailable</span>
              )}
            </div>

            <Button
              variant="ghost"
              size="icon"
              onClick={handleRemove}
              disabled={isRemoving}
              className="text-gray-400 hover:text-red-600 hover:bg-red-50"
              aria-label={`Remove ${item.symbol} from watchlist`}
            >
              {isRemoving ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Trash2 className="w-5 h-5" />
              )}
            </Button>
          </div>
        </div>

        {/* Added Date */}
        <div className="mt-4 pt-4 border-t border-gray-100 text-sm text-gray-400">
          Added {new Date(item.added_at).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
          })}
        </div>
      </CardContent>
    </Card>
  )
}

export default function WatchlistContent() {
  const router = useRouter()
  const { user, isLoading: authLoading, isAuthenticated } = useAuth()
  const {
    items,
    isLoading,
    error,
    total,
    tier,
    limit,
    isAtLimit,
    removeStock,
    refresh,
  } = useWatchlist()

  const [removingSymbol, setRemovingSymbol] = useState<string | null>(null)

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [authLoading, isAuthenticated, router])

  const handleRemove = async (symbol: string) => {
    setRemovingSymbol(symbol)
    await removeStock(symbol)
    setRemovingSymbol(null)
  }

  const handleGoToSearch = () => {
    router.push('/search')
  }

  if (authLoading || !isAuthenticated) {
    return (
      <main className="pt-14 min-h-screen px-8 pb-16">
        <div className="max-w-4xl mx-auto">
          <div className="pt-8">
            <WatchlistSkeleton />
          </div>
        </div>
      </main>
    )
  }

  return (
    <main className="pt-14 min-h-screen px-8 pb-16">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="pt-8 pb-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push('/')}
            className="text-gray-500 hover:text-gray-900"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Home
          </Button>
        </div>

        {/* Title & Stats */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">My Watchlist</h1>
              <p className="text-gray-500 mt-1">
                Track your favorite stocks in one place
              </p>
            </div>

            <div className="text-right">
              <div className="flex items-center gap-2">
                <Badge
                  variant={tier === 'free' ? 'secondary' : 'default'}
                  className={cn(
                    tier !== 'free' && 'bg-gradient-to-r from-amber-500 to-orange-500',
                  )}
                >
                  {tier === 'free' ? 'Free' : 'Pro'}
                </Badge>
                <span className="text-sm text-gray-500">
                  {total}/{limit} stocks
                </span>
              </div>
              {isAtLimit && tier === 'free' && (
                <Button
                  variant="link"
                  size="sm"
                  className="text-amber-600 hover:text-amber-700 p-0 h-auto mt-1"
                >
                  <Sparkles className="w-3 h-3 mr-1" />
                  Upgrade for unlimited
                </Button>
              )}
            </div>
          </div>

          {/* Progress Bar */}
          <div className="mt-4 h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={cn(
                'h-full transition-all duration-300 rounded-full',
                isAtLimit
                  ? 'bg-amber-500'
                  : 'bg-gradient-to-r from-gray-800 to-gray-600',
              )}
              style={{ width: `${Math.min((total / limit) * 100, 100)}%` }}
            />
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
            <p className="text-red-600 text-sm">{error}</p>
            <Button
              variant="outline"
              size="sm"
              onClick={refresh}
              className="ml-auto"
            >
              Retry
            </Button>
          </div>
        )}

        {/* Loading State */}
        {isLoading && <WatchlistSkeleton />}

        {/* Empty State */}
        {!isLoading && !error && items.length === 0 && (
          <Card className="border-dashed">
            <CardContent className="py-16 text-center">
              <Star className="w-16 h-16 text-gray-200 mx-auto mb-4" />
              <h3 className="text-xl font-medium text-gray-900 mb-2">
                Your watchlist is empty
              </h3>
              <p className="text-gray-500 mb-6 max-w-md mx-auto">
                Start tracking stocks by searching for them and clicking the star
                icon to add them to your watchlist.
              </p>
              <Button onClick={handleGoToSearch}>
                Search Stocks
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Watchlist Items */}
        {!isLoading && !error && items.length > 0 && (
          <div className="space-y-4">
            {items.map((item) => (
              <WatchlistCard
                key={item.id}
                item={item}
                onRemove={handleRemove}
                isRemoving={removingSymbol === item.symbol}
              />
            ))}
          </div>
        )}

        {/* Add More CTA */}
        {!isLoading && !error && items.length > 0 && !isAtLimit && (
          <div className="mt-6 text-center">
            <Button variant="outline" onClick={handleGoToSearch}>
              Add More Stocks
            </Button>
          </div>
        )}
      </div>
    </main>
  )
}
