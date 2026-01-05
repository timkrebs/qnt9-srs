/**
 * WebSocket hook for real-time stock price updates.
 * 
 * Connects to the search-service WebSocket proxy which
 * forwards price updates from Massive API.
 */

'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

export interface PriceUpdate {
  ticker: string
  price: number
  size: number
  timestamp: number
  event: 'trade' | 'aggregate'
}

export interface WebSocketStatus {
  connected: boolean
  error: string | null
  reconnecting: boolean
}

interface UseStockWebSocketOptions {
  /** Initial tickers to subscribe to */
  tickers?: string[]
  /** Called when a price update is received */
  onPriceUpdate?: (update: PriceUpdate) => void
  /** Auto-reconnect on disconnect */
  autoReconnect?: boolean
  /** Reconnect delay in ms */
  reconnectDelay?: number
}

interface UseStockWebSocketReturn {
  /** Current connection status */
  status: WebSocketStatus
  /** Latest prices by ticker */
  prices: Record<string, PriceUpdate>
  /** Subscribe to additional tickers */
  subscribe: (tickers: string[]) => void
  /** Unsubscribe from tickers */
  unsubscribe: (tickers: string[]) => void
  /** Manually connect */
  connect: () => void
  /** Manually disconnect */
  disconnect: () => void
}

// Get WebSocket URL from environment or default
function getWebSocketUrl(): string {
  // In development, connect directly to search-service
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    // Use search service port
    return `${protocol}//localhost:8000/ws/prices`
  }
  return 'ws://localhost:8000/ws/prices'
}

/**
 * Hook for real-time stock price updates via WebSocket.
 * 
 * @example
 * ```tsx
 * const { prices, subscribe, status } = useStockWebSocket({
 *   tickers: ['AAPL', 'MSFT'],
 *   onPriceUpdate: (update) => console.log('Price update:', update),
 * })
 * 
 * // Subscribe to more tickers
 * subscribe(['GOOGL', 'AMZN'])
 * 
 * // Access latest price
 * const applePrice = prices['AAPL']?.price
 * ```
 */
export function useStockWebSocket(
  options: UseStockWebSocketOptions = {}
): UseStockWebSocketReturn {
  const {
    tickers = [],
    onPriceUpdate,
    autoReconnect = true,
    reconnectDelay = 3000,
  } = options

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const subscribedTickersRef = useRef<Set<string>>(new Set(tickers))

  const [status, setStatus] = useState<WebSocketStatus>({
    connected: false,
    error: null,
    reconnecting: false,
  })

  const [prices, setPrices] = useState<Record<string, PriceUpdate>>({})

  const connect = useCallback(() => {
    // Don't connect if already connected
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    // Clear any pending reconnect
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    try {
      const url = getWebSocketUrl()
      
      // Add initial tickers to URL if any
      const tickerParams = Array.from(subscribedTickersRef.current).join(',')
      const fullUrl = tickerParams ? `${url}?tickers=${tickerParams}` : url
      
      const ws = new WebSocket(fullUrl)
      wsRef.current = ws

      ws.onopen = () => {
        setStatus({ connected: true, error: null, reconnecting: false })
        console.log('[WebSocket] Connected to price feed')
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.type === 'price') {
            const update: PriceUpdate = {
              ticker: data.ticker,
              price: data.price,
              size: data.size,
              timestamp: data.timestamp,
              event: data.event,
            }
            
            setPrices(prev => ({
              ...prev,
              [update.ticker]: update,
            }))
            
            onPriceUpdate?.(update)
          } else if (data.type === 'subscribed') {
            console.log('[WebSocket] Subscribed to:', data.tickers)
          } else if (data.type === 'status') {
            // Handle status messages from server
            if (data.status === 'connected') {
              console.log('[WebSocket] Server connected:', data.message)
            } else if (data.status === 'limited') {
              // Real-time not available on current plan - use REST polling instead
              console.log('[WebSocket] Real-time limited:', data.message)
              setStatus(prev => ({ ...prev, error: null })) // Clear any error
            }
          } else if (data.type === 'error') {
            console.error('[WebSocket] Server error:', data.message)
          }
        } catch (err) {
          console.error('[WebSocket] Failed to parse message:', err)
        }
      }

      ws.onerror = (error) => {
        // Only log meaningful error info, WebSocket error events are often empty
        console.warn('[WebSocket] Connection issue, will use REST API for prices')
        setStatus(prev => ({ ...prev, error: null })) // Don't show error to user)
      }

      ws.onclose = (event) => {
        console.log('[WebSocket] Closed:', event.code, event.reason)
        setStatus(prev => ({ ...prev, connected: false }))
        wsRef.current = null

        // Auto-reconnect if enabled
        if (autoReconnect && !event.wasClean) {
          setStatus(prev => ({ ...prev, reconnecting: true }))
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('[WebSocket] Attempting reconnect...')
            connect()
          }, reconnectDelay)
        }
      }
    } catch (err) {
      console.error('[WebSocket] Failed to connect:', err)
      setStatus({ connected: false, error: 'Failed to connect', reconnecting: false })
    }
  }, [autoReconnect, reconnectDelay, onPriceUpdate])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect')
      wsRef.current = null
    }

    setStatus({ connected: false, error: null, reconnecting: false })
  }, [])

  const subscribe = useCallback((newTickers: string[]) => {
    const upperTickers = newTickers.map(t => t.toUpperCase())
    
    // Add to tracked subscriptions
    upperTickers.forEach(t => subscribedTickersRef.current.add(t))

    // Send subscribe message if connected
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'subscribe',
        tickers: upperTickers,
      }))
    }
  }, [])

  const unsubscribe = useCallback((tickersToRemove: string[]) => {
    const upperTickers = tickersToRemove.map(t => t.toUpperCase())
    
    // Remove from tracked subscriptions
    upperTickers.forEach(t => subscribedTickersRef.current.delete(t))

    // Send unsubscribe message if connected
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'unsubscribe',
        tickers: upperTickers,
      }))
    }

    // Remove from prices state
    setPrices(prev => {
      const next = { ...prev }
      upperTickers.forEach(t => delete next[t])
      return next
    })
  }, [])

  // Connect on mount
  useEffect(() => {
    connect()
    return () => {
      disconnect()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Update initial tickers when they change
  useEffect(() => {
    const upperTickers = tickers.map(t => t.toUpperCase())
    subscribedTickersRef.current = new Set(upperTickers)
    
    if (wsRef.current?.readyState === WebSocket.OPEN && upperTickers.length > 0) {
      wsRef.current.send(JSON.stringify({
        action: 'subscribe',
        tickers: upperTickers,
      }))
    }
  }, [tickers])

  return {
    status,
    prices,
    subscribe,
    unsubscribe,
    connect,
    disconnect,
  }
}

/**
 * Hook to get real-time price for a single stock.
 */
export function useStockPrice(ticker: string | null): {
  price: number | null
  change: number | null
  changePercent: number | null
  loading: boolean
  connected: boolean
} {
  const [priceData, setPriceData] = useState<{
    price: number | null
    change: number | null
    changePercent: number | null
  }>({
    price: null,
    change: null,
    changePercent: null,
  })

  const { prices, status, subscribe, unsubscribe } = useStockWebSocket({
    tickers: ticker ? [ticker] : [],
    onPriceUpdate: (update) => {
      if (ticker && update.ticker === ticker.toUpperCase()) {
        setPriceData(prev => ({
          ...prev,
          price: update.price,
        }))
      }
    },
  })

  useEffect(() => {
    if (ticker) {
      subscribe([ticker])
      return () => {
        unsubscribe([ticker])
      }
    }
  }, [ticker, subscribe, unsubscribe])

  // Get price from state
  const latestPrice = ticker ? prices[ticker.toUpperCase()] : null

  return {
    price: latestPrice?.price ?? priceData.price,
    change: priceData.change,
    changePercent: priceData.changePercent,
    loading: !status.connected && !latestPrice,
    connected: status.connected,
  }
}
