'use client'

import { useEffect } from 'react'
import Intercom from '@intercom/messenger-js-sdk'
import { useAuth } from '@/lib/auth/auth-context'

const INTERCOM_APP_ID = process.env.NEXT_PUBLIC_INTERCOM_APP_ID

export function IntercomProvider({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated, isLoading } = useAuth()

  useEffect(() => {
    // Skip if Intercom is not configured
    if (!INTERCOM_APP_ID) return

    // Wait until auth state is determined
    if (isLoading) return

    if (isAuthenticated && user) {
      // Initialize Intercom for logged-in users with user data
      Intercom({
        app_id: INTERCOM_APP_ID,
        user_id: user.id,
        name: user.full_name || user.email.split('@')[0],
        email: user.email,
        created_at: user.created_at
          ? Math.floor(new Date(user.created_at).getTime() / 1000)
          : undefined,
        // Custom attributes
        user_hash: undefined, // Add if you implement identity verification
        custom_attributes: {
          tier: user.tier,
          role: user.role,
          last_login: user.last_login,
        },
      })
    } else {
      // Initialize Intercom for anonymous visitors
      Intercom({
        app_id: INTERCOM_APP_ID,
      })
    }

    // Cleanup on unmount
    return () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const intercom = (window as any).Intercom
      if (typeof window !== 'undefined' && intercom) {
        intercom('shutdown')
      }
    }
  }, [user, isAuthenticated, isLoading])

  // Update Intercom when user changes (login/logout)
  useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const intercom = (window as any).Intercom
    if (typeof window !== 'undefined' && intercom) {
      if (isAuthenticated && user) {
        intercom('update', {
          user_id: user.id,
          name: user.full_name || user.email.split('@')[0],
          email: user.email,
        })
      } else if (!isLoading) {
        // User logged out - reset to anonymous
        intercom('shutdown')
        intercom('boot', {
          app_id: INTERCOM_APP_ID,
        })
      }
    }
  }, [user, isAuthenticated, isLoading])

  return <>{children}</>
}
