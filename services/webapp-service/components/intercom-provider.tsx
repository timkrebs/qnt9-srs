'use client'

import { useEffect, useRef } from 'react'
import Intercom from '@intercom/messenger-js-sdk'
import { useAuth } from '@/lib/auth/auth-context'

const INTERCOM_APP_ID = process.env.NEXT_PUBLIC_INTERCOM_APP_ID

export function IntercomProvider({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated, isLoading } = useAuth()
  const isInitialized = useRef(false)

  // Initialize Intercom once when auth state is ready
  useEffect(() => {
    // Skip if Intercom is not configured
    if (!INTERCOM_APP_ID) {
      console.warn('[Intercom] NEXT_PUBLIC_INTERCOM_APP_ID is not set')
      return
    }

    // Wait until auth state is determined
    if (isLoading) return

    // Only initialize once per session
    if (!isInitialized.current) {
      if (isAuthenticated && user) {
        // Initialize Intercom for logged-in users with user data
        console.log('[Intercom] Initializing for user:', user.email)
        Intercom({
          app_id: INTERCOM_APP_ID,
          user_id: user.id,
          name: user.full_name || user.email.split('@')[0],
          email: user.email,
          created_at: user.created_at
            ? Math.floor(new Date(user.created_at).getTime() / 1000)
            : undefined,
        })
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
  }, [isLoading]) // Only depend on isLoading for initial setup

  // Update Intercom when user changes (login/logout)
  useEffect(() => {
    if (!INTERCOM_APP_ID || isLoading || !isInitialized.current) return

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const intercom = (window as any).Intercom
    if (typeof window !== 'undefined' && intercom) {
      if (isAuthenticated && user) {
        console.log('[Intercom] Updating user:', user.email)
        intercom('update', {
          user_id: user.id,
          name: user.full_name || user.email.split('@')[0],
          email: user.email,
        })
      } else {
        // User logged out - shutdown and reinitialize as anonymous
        console.log('[Intercom] User logged out, resetting to anonymous')
        intercom('shutdown')
        Intercom({
          app_id: INTERCOM_APP_ID,
        })
      }
    }
  }, [user, isAuthenticated, isLoading])

  return <>{children}</>
}
