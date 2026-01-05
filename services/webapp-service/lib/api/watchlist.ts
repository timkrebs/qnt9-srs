import { apiRequest } from './client'

export interface WatchlistItem {
  id: string
  user_id: string
  symbol: string
  alert_enabled: boolean
  alert_price_above: number | null
  alert_price_below: number | null
  notes: string | null
  added_at: string
}

export interface WatchlistResponse {
  watchlist: WatchlistItem[]
  total: number
  tier: string
  limit: number
}

export interface WatchlistCreate {
  symbol: string
  notes?: string
  alert_enabled?: boolean
  alert_price_above?: number
  alert_price_below?: number
}

export interface WatchlistUpdate {
  notes?: string
  alert_enabled?: boolean
  alert_price_above?: number
  alert_price_below?: number
}

export interface MessageResponse {
  message: string
  success: boolean
}

export const watchlistService = {
  getWatchlist: async (): Promise<WatchlistResponse> => {
    return apiRequest<WatchlistResponse>('watchlist', '/api/watchlist')
  },

  addStock: async (data: WatchlistCreate): Promise<WatchlistItem> => {
    return apiRequest<WatchlistItem>('watchlist', '/api/watchlist', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  removeStock: async (symbol: string): Promise<MessageResponse> => {
    return apiRequest<MessageResponse>(
      'watchlist',
      `/api/watchlist/${encodeURIComponent(symbol)}`,
      { method: 'DELETE' },
    )
  },

  updateStock: async (
    symbol: string,
    data: WatchlistUpdate,
  ): Promise<WatchlistItem> => {
    return apiRequest<WatchlistItem>(
      'watchlist',
      `/api/watchlist/${encodeURIComponent(symbol)}`,
      {
        method: 'PATCH',
        body: JSON.stringify(data),
      },
    )
  },

  isInWatchlist: async (symbol: string): Promise<boolean> => {
    try {
      const response = await watchlistService.getWatchlist()
      return response.watchlist.some(
        (item) => item.symbol.toUpperCase() === symbol.toUpperCase(),
      )
    } catch {
      return false
    }
  },
}
