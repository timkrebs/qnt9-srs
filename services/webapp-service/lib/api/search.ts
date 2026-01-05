import { apiRequest } from './client'

export interface StockSearchResult {
  symbol: string
  name: string
  exchange: string
  type?: string
  isin?: string
  wkn?: string
  currency?: string
  price?: number
  change?: number
  change_percent?: number
  relevance_score?: number
  match_score?: number
  match_type?: string
  priority?: number
}

export interface InstantSearchResponse {
  success: boolean
  query: string
  results: StockSearchResult[]
  count: number
  latency_ms?: number
}

export interface AutocompleteResponse {
  query: string
  results: StockSearchResult[]
  total: number
  latency_ms?: number
}

export interface SimpleSearchResponse {
  results: StockSearchResult[]
  query: string
  total_matches: number
}

// Massive API response types
interface MassiveTickerResult {
  ticker: string
  name: string
  exchange: string
  type: string
  market: string
  active: boolean
  currency?: string
}

interface MassiveSearchResponse {
  success: boolean
  results: MassiveTickerResult[]
  query: string
  total_count: number
  message: string
}

export interface StockQuote {
  symbol: string
  name: string
  price: number
  change: number
  change_percent: number
  open: number
  high: number
  low: number
  previous_close: number
  volume: number
  market_cap?: number
  timestamp: string
}

/**
 * Transform Massive API result to StockSearchResult format
 */
const transformMassiveResult = (result: MassiveTickerResult): StockSearchResult => ({
  symbol: result.ticker,
  name: result.name,
  exchange: result.exchange,
  type: result.type,
  currency: result.currency,
})

export const searchService = {
  /**
   * Primary search endpoint - uses Massive API for comprehensive stock coverage.
   * Searches across ALL US stock exchanges including NYSE, NASDAQ, BATS, etc.
   */
  instantSearch: async (query: string): Promise<InstantSearchResponse> => {
    if (!query || query.trim().length < 1) {
      return {
        success: true,
        query: '',
        results: [],
        count: 0,
      }
    }

    try {
      // Use the Massive API ticker search endpoint for comprehensive coverage
      const response = await apiRequest<MassiveSearchResponse>(
        'search',
        `/api/v1/tickers/search?q=${encodeURIComponent(query.trim())}&limit=25`,
        { skipAuth: true },
      )

      // Transform Massive API response to expected format
      return {
        success: response.success,
        query: response.query,
        results: response.results.map(transformMassiveResult),
        count: response.total_count,
      }
    } catch (error) {
      // Fallback to legacy endpoint if Massive API fails
      console.warn('Massive API search failed, falling back to legacy:', error)
      try {
        const response = await apiRequest<SimpleSearchResponse>(
          'search',
          `/search?q=${encodeURIComponent(query.trim())}`,
          { skipAuth: true },
        )
        return {
          success: true,
          query: response.query,
          results: response.results,
          count: response.total_matches,
        }
      } catch {
        return {
          success: false,
          query: query.trim(),
          results: [],
          count: 0,
        }
      }
    }
  },

  autocomplete: async (query: string): Promise<AutocompleteResponse> => {
    if (!query || query.trim().length < 1) {
      return {
        query: '',
        results: [],
        total: 0,
      }
    }

    try {
      // Use Massive API for autocomplete with smaller limit
      const response = await apiRequest<MassiveSearchResponse>(
        'search',
        `/api/v1/tickers/search?q=${encodeURIComponent(query.trim())}&limit=8`,
        { skipAuth: true },
      )

      return {
        query: response.query,
        results: response.results.map(transformMassiveResult),
        total: response.total_count,
      }
    } catch {
      return {
        query: query.trim(),
        results: [],
        total: 0,
      }
    }
  },

  simpleSearch: async (query: string): Promise<SimpleSearchResponse> => {
    if (!query || query.trim().length < 1) {
      return {
        results: [],
        query: '',
        total_matches: 0,
      }
    }

    try {
      // Use Massive API
      const response = await apiRequest<MassiveSearchResponse>(
        'search',
        `/api/v1/tickers/search?q=${encodeURIComponent(query.trim())}&limit=25`,
        { skipAuth: true },
      )

      return {
        results: response.results.map(transformMassiveResult),
        query: response.query,
        total_matches: response.total_count,
      }
    } catch {
      // Fallback to legacy
      return apiRequest<SimpleSearchResponse>(
        'search',
        `/search?q=${encodeURIComponent(query.trim())}`,
        { skipAuth: true },
      )
    }
  },

  getQuote: async (symbol: string): Promise<StockQuote> => {
    return apiRequest<StockQuote>(
      'search',
      `/api/v1/stocks/${encodeURIComponent(symbol)}/quote`,
      { skipAuth: true },
    )
  },

  searchByISIN: async (isin: string): Promise<SimpleSearchResponse> => {
    return searchService.simpleSearch(isin)
  },

  searchByWKN: async (wkn: string): Promise<SimpleSearchResponse> => {
    return searchService.simpleSearch(wkn)
  },
}
