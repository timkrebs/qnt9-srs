/**
 * Stock data API module using Massive API endpoints.
 * 
 * Provides:
 * - Ticker search across all US exchanges
 * - Real-time stock snapshots with price data
 * - Historical chart data (OHLC)
 * - Batch price lookups
 * - Extended company details
 * - Company news articles
 */

import { apiRequest } from './client'

// Ticker search types
export interface TickerSearchResult {
  ticker: string
  name: string
  exchange: string
  type: string
  market: string
  active: boolean
  currency: string | null
}

export interface TickerSearchResponse {
  success: boolean
  results: TickerSearchResult[]
  query: string
  total_count: number
  message: string
}

// Extended ticker detail types
export interface AddressInfo {
  address1: string | null
  city: string | null
  state: string | null
  postal_code: string | null
}

export interface TickerDetail {
  ticker: string
  name: string
  exchange: string
  type: string
  market: string
  active: boolean
  currency: string | null
  // Extended company details
  description: string | null
  homepage_url: string | null
  phone_number: string | null
  total_employees: number | null
  list_date: string | null
  market_cap: number | null
  shares_outstanding: number | null
  weighted_shares_outstanding: number | null
  round_lot: number | null
  // Classification
  sic_code: string | null
  sic_description: string | null
  // Address
  address: AddressInfo | null
  // Branding
  logo_url: string | null
  icon_url: string | null
}

export interface TickerDetailResponse {
  success: boolean
  data: TickerDetail
  message: string
}

// News types
export interface NewsArticle {
  id: string
  title: string
  author: string | null
  published_utc: string
  article_url: string
  description: string | null
  image_url: string | null
  publisher_name: string | null
  publisher_logo_url: string | null
  tickers: string[]
  keywords: string[] | null
}

export interface TickerNewsResponse {
  success: boolean
  articles: NewsArticle[]
  ticker: string
  count: number
  message: string
}

// Stock snapshot types
export interface DayBar {
  open: number | null
  high: number | null
  low: number | null
  close: number | null
  volume: number | null
  vwap: number | null
}

export interface MinuteBar {
  open: number | null
  high: number | null
  low: number | null
  close: number | null
  volume: number | null
}

export interface LastTrade {
  price: number | null
  size: number | null
  timestamp: number | null
}

export interface StockSnapshot {
  ticker: string
  name: string | null
  price: number | null
  change: number | null
  change_percent: number | null
  prev_close: number | null
  day: DayBar | null
  minute: MinuteBar | null
  last_trade: LastTrade | null
  updated: number | null
  market_status: string
}

export interface StockSnapshotResponse {
  success: boolean
  data: StockSnapshot
  message: string
}

export interface SimplePriceResponse {
  ticker: string
  price: number | null
  change: number | null
  change_percent: number | null
  prev_close: number | null
}

export interface BatchPricesResponse {
  prices: Record<string, {
    price: number | null
    change: number | null
    change_percent: number | null
  }>
  errors: string[]
  success_count: number
  error_count: number
}

// Chart data types
export type ChartRange = '1D' | '5D' | '1M' | '3M' | '6M' | 'YTD' | '1Y' | '5Y' | 'MAX'
export type ChartInterval = '1m' | '5m' | '15m' | '30m' | '1h' | '4h' | '1d' | '1w' | '1mo'

export interface OHLCBar {
  timestamp: number
  open: number
  high: number
  low: number
  close: number
  volume: number
  vwap: number | null
}

export interface ChartMetadata {
  ticker: string
  interval: string
  range: string
  from_date: string
  to_date: string
  bar_count: number
  adjusted: boolean
}

export interface ChartResponse {
  success: boolean
  data: OHLCBar[]
  metadata: ChartMetadata
  message: string
}

export interface PreviousCloseResponse {
  ticker: string
  timestamp: number
  open: number
  high: number
  low: number
  close: number
  volume: number
  vwap: number | null
}

/**
 * Stock data service using Massive API endpoints.
 */
export const stockService = {
  /**
   * Search tickers by name or symbol.
   * Uses Massive API for comprehensive coverage of all US exchanges.
   */
  searchTickers: async (
    query: string,
    options?: {
      market?: string
      active?: boolean
      limit?: number
    }
  ): Promise<TickerSearchResponse> => {
    if (!query || query.trim().length < 1) {
      return {
        success: true,
        results: [],
        query: '',
        total_count: 0,
        message: 'Empty query',
      }
    }

    const params = new URLSearchParams({
      q: query.trim(),
      market: options?.market || 'stocks',
      active: String(options?.active ?? true),
      limit: String(options?.limit || 25),
    })

    return apiRequest<TickerSearchResponse>(
      'search',
      `/api/v1/tickers/search?${params}`,
      { skipAuth: true }
    )
  },

  /**
   * Get detailed information for a specific ticker.
   * Returns extended company data including description, employees, website, etc.
   */
  getTickerDetails: async (ticker: string): Promise<TickerDetailResponse> => {
    return apiRequest<TickerDetailResponse>(
      'search',
      `/api/v1/tickers/${encodeURIComponent(ticker.toUpperCase())}`,
      { skipAuth: true }
    )
  },

  /**
   * Get news articles for a specific ticker.
   * Returns recent financial news from major publishers.
   */
  getNews: async (ticker: string, limit: number = 5): Promise<TickerNewsResponse> => {
    const params = new URLSearchParams({
      limit: String(limit),
    })
    return apiRequest<TickerNewsResponse>(
      'search',
      `/api/v1/tickers/${encodeURIComponent(ticker.toUpperCase())}/news?${params}`,
      { skipAuth: true }
    )
  },

  /**
   * Get current market snapshot for a stock.
   * Includes price, change, day OHLC, and previous close.
   */
  getSnapshot: async (ticker: string): Promise<StockSnapshotResponse> => {
    return apiRequest<StockSnapshotResponse>(
      'search',
      `/api/v1/stocks/${encodeURIComponent(ticker.toUpperCase())}/snapshot`,
      { skipAuth: true }
    )
  },

  /**
   * Get simplified price data for a stock.
   */
  getPrice: async (ticker: string): Promise<SimplePriceResponse> => {
    return apiRequest<SimplePriceResponse>(
      'search',
      `/api/v1/stocks/${encodeURIComponent(ticker.toUpperCase())}/price`,
      { skipAuth: true }
    )
  },

  /**
   * Get prices for multiple stocks in a single request.
   * Useful for watchlist price updates.
   */
  getBatchPrices: async (tickers: string[]): Promise<BatchPricesResponse> => {
    if (tickers.length === 0) {
      return {
        prices: {},
        errors: [],
        success_count: 0,
        error_count: 0,
      }
    }

    const params = new URLSearchParams()
    tickers.forEach(t => params.append('tickers', t.toUpperCase()))

    return apiRequest<BatchPricesResponse>(
      'search',
      `/api/v1/stocks/batch/prices?${params}`,
      { 
        skipAuth: true,
        method: 'POST',
      }
    )
  },

  /**
   * Get chart data with pre-defined range.
   */
  getChart: async (
    ticker: string,
    range: ChartRange = '1M',
    adjusted: boolean = true
  ): Promise<ChartResponse> => {
    const params = new URLSearchParams({
      range,
      adjusted: String(adjusted),
    })

    return apiRequest<ChartResponse>(
      'search',
      `/api/v1/charts/${encodeURIComponent(ticker.toUpperCase())}?${params}`,
      { skipAuth: true }
    )
  },

  /**
   * Get chart data with custom date range and interval.
   */
  getCustomChart: async (
    ticker: string,
    options: {
      interval: ChartInterval
      fromDate: string
      toDate: string
      adjusted?: boolean
      limit?: number
    }
  ): Promise<ChartResponse> => {
    const params = new URLSearchParams({
      interval: options.interval,
      from_date: options.fromDate,
      to_date: options.toDate,
      adjusted: String(options.adjusted ?? true),
      limit: String(options.limit || 5000),
    })

    return apiRequest<ChartResponse>(
      'search',
      `/api/v1/charts/${encodeURIComponent(ticker.toUpperCase())}/custom?${params}`,
      { skipAuth: true }
    )
  },

  /**
   * Get previous day's OHLC bar.
   */
  getPreviousClose: async (ticker: string): Promise<PreviousCloseResponse> => {
    return apiRequest<PreviousCloseResponse>(
      'search',
      `/api/v1/charts/${encodeURIComponent(ticker.toUpperCase())}/previous`,
      { skipAuth: true }
    )
  },
}

/**
 * Helper to format price with appropriate decimals.
 */
export function formatPrice(price: number | null | undefined): string {
  if (price === null || price === undefined) return '--'
  return price.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

/**
 * Helper to format change with sign and color class.
 */
export function formatChange(change: number | null | undefined): {
  text: string
  colorClass: string
} {
  if (change === null || change === undefined) {
    return { text: '--', colorClass: 'text-muted-foreground' }
  }
  
  const sign = change >= 0 ? '+' : ''
  return {
    text: `${sign}${change.toFixed(2)}`,
    colorClass: change >= 0 ? 'text-green-500' : 'text-red-500',
  }
}

/**
 * Helper to format percent change.
 */
export function formatChangePercent(percent: number | null | undefined): {
  text: string
  colorClass: string
} {
  if (percent === null || percent === undefined) {
    return { text: '--', colorClass: 'text-muted-foreground' }
  }
  
  const sign = percent >= 0 ? '+' : ''
  return {
    text: `${sign}${percent.toFixed(2)}%`,
    colorClass: percent >= 0 ? 'text-green-500' : 'text-red-500',
  }
}

/**
 * Helper to format volume.
 */
export function formatVolume(volume: number | null | undefined): string {
  if (volume === null || volume === undefined) return '--'
  
  if (volume >= 1_000_000_000) {
    return `${(volume / 1_000_000_000).toFixed(2)}B`
  }
  if (volume >= 1_000_000) {
    return `${(volume / 1_000_000).toFixed(2)}M`
  }
  if (volume >= 1_000) {
    return `${(volume / 1_000).toFixed(2)}K`
  }
  return volume.toLocaleString()
}
