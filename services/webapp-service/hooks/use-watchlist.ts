'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  watchlistService,
  type WatchlistItem,
  type WatchlistCreate,
  type WatchlistResponse,
} from '@/lib/api/watchlist'
import { stockService } from '@/lib/api/stock'
import { ApiError } from '@/lib/api/client'
import { useAuth } from '@/lib/auth/auth-context'

export interface WatchlistItemWithPrice extends WatchlistItem {
  price?: number
  change?: number
  change_percent?: number
  name?: string
  priceLoading?: boolean
}

interface UseWatchlistReturn {
  items: WatchlistItemWithPrice[]
  isLoading: boolean
  error: string | null
  total: number
  tier: string
  limit: number
  isAtLimit: boolean
  refresh: () => Promise<void>
  addStock: (symbol: string, notes?: string) => Promise<boolean>
  removeStock: (symbol: string) => Promise<boolean>
  isInWatchlist: (symbol: string) => boolean
  toggleWatchlist: (symbol: string) => Promise<boolean>
}

export const useWatchlist = (): UseWatchlistReturn => {
  const { isAuthenticated } = useAuth()
  const [items, setItems] = useState<WatchlistItemWithPrice[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [watchlistData, setWatchlistData] = useState<WatchlistResponse | null>(
    null,
  )

  const fetchPriceForItem = useCallback(
    async (item: WatchlistItem): Promise<WatchlistItemWithPrice> => {
      try {
        // Use stockService.getPrice for consistency with Market Overview
        const priceData = await stockService.getPrice(item.symbol)
        // Also get ticker details for the name
        let name = item.symbol
        try {
          const details = await stockService.getTickerDetails(item.symbol)
          name = details.data?.name || item.symbol
        } catch {
          // Name fetch is not critical
        }
        return {
          ...item,
          price: priceData.price ?? undefined,
          change: priceData.change ?? undefined,
          change_percent: priceData.change_percent ?? undefined,
          name,
          priceLoading: false,
        }
      } catch {
        return {
          ...item,
          priceLoading: false,
        }
      }
    },
    [],
  )

  const fetchWatchlist = useCallback(async () => {
    if (!isAuthenticated) {
      setItems([])
      setWatchlistData(null)
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const response = await watchlistService.getWatchlist()
      setWatchlistData(response)

      // Set items with loading state for prices
      const itemsWithLoadingState: WatchlistItemWithPrice[] =
        response.watchlist.map((item) => ({
          ...item,
          priceLoading: true,
        }))
      setItems(itemsWithLoadingState)

      // Fetch prices for all items in parallel
      const itemsWithPrices = await Promise.all(
        response.watchlist.map(fetchPriceForItem),
      )
      setItems(itemsWithPrices)
    } catch (err) {
      const errorMessage =
        err instanceof ApiError
          ? err.message
          : 'Failed to load watchlist. Please try again.'
      setError(errorMessage)
      setItems([])
    } finally {
      setIsLoading(false)
    }
  }, [isAuthenticated, fetchPriceForItem])

  useEffect(() => {
    fetchWatchlist()
  }, [fetchWatchlist])

  const addStock = useCallback(
    async (symbol: string, notes?: string): Promise<boolean> => {
      if (!isAuthenticated) {
        setError('Please log in to add stocks to your watchlist')
        return false
      }

      const normalizedSymbol = symbol.toUpperCase()

      // Optimistic update
      const optimisticItem: WatchlistItemWithPrice = {
        id: `temp-${Date.now()}`,
        user_id: '',
        symbol: normalizedSymbol,
        alert_enabled: false,
        alert_price_above: null,
        alert_price_below: null,
        notes: notes || null,
        added_at: new Date().toISOString(),
        priceLoading: true,
      }

      setItems((prev) => [optimisticItem, ...prev])
      setError(null)

      try {
        const data: WatchlistCreate = { symbol: normalizedSymbol }
        if (notes) {
          data.notes = notes
        }

        const newItem = await watchlistService.addStock(data)

        // Replace optimistic item with real item and fetch price
        const itemWithPrice = await fetchPriceForItem(newItem)
        setItems((prev) =>
          prev.map((item) =>
            item.id === optimisticItem.id ? itemWithPrice : item,
          ),
        )

        // Update watchlist data
        setWatchlistData((prev) =>
          prev
            ? {
                ...prev,
                watchlist: [newItem, ...prev.watchlist],
                total: prev.total + 1,
              }
            : null,
        )

        return true
      } catch (err) {
        // Rollback optimistic update
        setItems((prev) => prev.filter((item) => item.id !== optimisticItem.id))

        const errorMessage =
          err instanceof ApiError
            ? err.message
            : 'Failed to add stock to watchlist'
        setError(errorMessage)
        return false
      }
    },
    [isAuthenticated, fetchPriceForItem],
  )

  const removeStock = useCallback(
    async (symbol: string): Promise<boolean> => {
      if (!isAuthenticated) {
        return false
      }

      const normalizedSymbol = symbol.toUpperCase()
      const itemToRemove = items.find(
        (item) => item.symbol.toUpperCase() === normalizedSymbol,
      )

      if (!itemToRemove) {
        return false
      }

      // Optimistic update
      setItems((prev) =>
        prev.filter((item) => item.symbol.toUpperCase() !== normalizedSymbol),
      )
      setError(null)

      try {
        await watchlistService.removeStock(normalizedSymbol)

        // Update watchlist data
        setWatchlistData((prev) =>
          prev
            ? {
                ...prev,
                watchlist: prev.watchlist.filter(
                  (item) => item.symbol.toUpperCase() !== normalizedSymbol,
                ),
                total: Math.max(0, prev.total - 1),
              }
            : null,
        )

        return true
      } catch (err) {
        // Rollback optimistic update
        setItems((prev) => [...prev, itemToRemove])

        const errorMessage =
          err instanceof ApiError
            ? err.message
            : 'Failed to remove stock from watchlist'
        setError(errorMessage)
        return false
      }
    },
    [isAuthenticated, items],
  )

  const isInWatchlist = useCallback(
    (symbol: string): boolean => {
      const normalizedSymbol = symbol.toUpperCase()
      return items.some(
        (item) => item.symbol.toUpperCase() === normalizedSymbol,
      )
    },
    [items],
  )

  const toggleWatchlist = useCallback(
    async (symbol: string): Promise<boolean> => {
      if (isInWatchlist(symbol)) {
        return removeStock(symbol)
      }
      return addStock(symbol)
    },
    [isInWatchlist, addStock, removeStock],
  )

  const total = watchlistData?.total ?? items.length
  const tier = watchlistData?.tier ?? 'free'
  const limit = watchlistData?.limit ?? 3

  const isAtLimit = useMemo(() => {
    return total >= limit
  }, [total, limit])

  return {
    items,
    isLoading,
    error,
    total,
    tier,
    limit,
    isAtLimit,
    refresh: fetchWatchlist,
    addStock,
    removeStock,
    isInWatchlist,
    toggleWatchlist,
  }
}
