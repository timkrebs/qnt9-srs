'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import Intercom from '@intercom/messenger-js-sdk'
import { useAuth } from '@/lib/auth/auth-context'

const INTERCOM_APP_ID = process.env.NEXT_PUBLIC_INTERCOM_APP_ID

/**
 * Fetches a signed JWT from our API for Intercom identity verification.
 * This prevents users from impersonating others.
 */
async function fetchIntercomToken(userId: string, email: string): Promise<string | null> {
  try {
    const response = await fetch('/api/intercom/token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ user_id: userId, email }),
    })

    if (!response.ok) {
      console.warn('[Intercom] Failed to fetch JWT:', response.status)
      return null
    }

    const data = await response.json()
    return data.token
  } catch (error) {
    console.error('[Intercom] Error fetching JWT:', error)
    return null
  }
}

export function IntercomProvider({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated, isLoading } = useAuth()
  const isInitialized = useRef(false)
  const [intercomToken, setIntercomToken] = useState<string | null>(null)

  // Fetch JWT when user is authenticated
  const fetchToken = useCallback(async () => {
    if (isAuthenticated && user) {
      const token = await fetchIntercomToken(user.id, user.email)
      setIntercomToken(token)
    } else {
      setIntercomToken(null)
    }
  }, [isAuthenticated, user])

  // Fetch token when auth state changes
  useEffect(() => {
    if (!isLoading) {
      fetchToken()
    }
  }, [isLoading, fetchToken])

  // Initialize Intercom once when auth state and token are ready
  useEffect(() => {
    // Skip if Intercom is not configured
    if (!INTERCOM_APP_ID) {
      console.warn('[Intercom] NEXT_PUBLIC_INTERCOM_APP_ID is not set')
      return
    }

    // Wait until auth state is determined
    if (isLoading) return

    // For authenticated users, wait for token (but don't block if it fails)
    if (isAuthenticated && user && intercomToken === null) {
      // Token is still being fetched, wait
      return
    }

    // Only initialize once per session
    if (!isInitialized.current) {
      if (isAuthenticated && user) {
        // Initialize Intercom for logged-in users with JWT identity verification
        console.log('[Intercom] Initializing for user:', user.email, 'with JWT:', !!intercomToken)
        
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const intercomConfig: any = {
          app_id: INTERCOM_APP_ID,
          user_id: user.id,
          name: user.full_name || user.email.split('@')[0],
          email: user.email,
          created_at: user.created_at
            ? Math.floor(new Date(user.created_at).getTime() / 1000)
            : undefined,
          // Session duration: 24 hours (in milliseconds)
          session_duration: 86400000,
        }

        // Add JWT if available (secure mode)
        if (intercomToken) {
          intercomConfig.user_hash = intercomToken
        }

        Intercom(intercomConfig)
      } else {
        // Initialize Intercom for anonymous visitors
        console.log('[Intercom] Initializing for anonymous visitor')
        Intercom({
          app_id: INTERCOM_APP_ID,
        })
      }
      isInitialized.current = true
    }

    // Cleanup on unmount
    return () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const intercom = (window as any).Intercom
      if (typeof window !== 'undefined' && intercom) {
        intercom('shutdown')
        isInitialized.current = false
      }
    }
  }, [isLoading, isAuthenticated, user, intercomToken])

  // Update Intercom when user changes (login/logout)
  useEffect(() => {
    if (!INTERCOM_APP_ID || isLoading || !isInitialized.current) return

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const intercom = (window as any).Intercom
    if (typeof window !== 'undefined' && intercom) {
      if (isAuthenticated && user) {
        console.log('[Intercom] Updating user:', user.email)
        
        const updateConfig: Record<string, unknown> = {
          user_id: user.id,
          name: user.full_name || user.email.split('@')[0],
          email: user.email,
        }

        // Add JWT if available
        if (intercomToken) {
          updateConfig.user_hash = intercomToken
        }

        intercom('update', updateConfig)
      } else {
        // User logged out - shutdown and reinitialize as anonymous
        console.log('[Intercom] User logged out, resetting to anonymous')
        intercom('shutdown')
        Intercom({
          app_id: INTERCOM_APP_ID,
        })
      }
    }
  }, [user, isAuthenticated, isLoading, intercomToken])

  return <>{children}</>
}
