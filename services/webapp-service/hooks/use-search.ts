'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  searchService,
  type StockSearchResult,
  type InstantSearchResponse,
} from '@/lib/api/search'
import { ApiError } from '@/lib/api/client'

interface UseSearchOptions {
  debounceMs?: number
  minQueryLength?: number
}

interface UseSearchReturn {
  results: StockSearchResult[]
  isLoading: boolean
  error: string | null
  query: string
  setQuery: (query: string) => void
  search: (query: string) => Promise<void>
  clearResults: () => void
  totalResults: number
  latencyMs: number | null
}

export const useSearch = (options: UseSearchOptions = {}): UseSearchReturn => {
  const { debounceMs = 300, minQueryLength = 1 } = options

  const [query, setQuery] = useState('')
  const [results, setResults] = useState<StockSearchResult[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [totalResults, setTotalResults] = useState(0)
  const [latencyMs, setLatencyMs] = useState<number | null>(null)

  const abortControllerRef = useRef<AbortController | null>(null)
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null)

  const clearResults = useCallback(() => {
    setResults([])
    setTotalResults(0)
    setError(null)
    setLatencyMs(null)
  }, [])

  const search = useCallback(
    async (searchQuery: string) => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }

      if (!searchQuery || searchQuery.trim().length < minQueryLength) {
        clearResults()
        setIsLoading(false)
        return
      }

      abortControllerRef.current = new AbortController()
      setIsLoading(true)
      setError(null)

      try {
        const response: InstantSearchResponse =
          await searchService.instantSearch(searchQuery.trim())

        if (abortControllerRef.current?.signal.aborted) {
          return
        }

        setResults(response.results || [])
        setTotalResults(response.count || 0)
        setLatencyMs(response.latency_ms || null)
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') {
          return
        }

        const errorMessage =
          err instanceof ApiError
            ? err.message
            : 'Failed to search. Please try again.'
        setError(errorMessage)
        setResults([])
        setTotalResults(0)
      } finally {
        setIsLoading(false)
      }
    },
    [minQueryLength, clearResults],
  )

  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }

    if (!query || query.trim().length < minQueryLength) {
      clearResults()
      return
    }

    setIsLoading(true)

    debounceTimerRef.current = setTimeout(() => {
      search(query)
    }, debounceMs)

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
  }, [query, debounceMs, minQueryLength, search, clearResults])

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
  }, [])

  return {
    results,
    isLoading,
    error,
    query,
    setQuery,
    search,
    clearResults,
    totalResults,
    latencyMs,
  }
}
