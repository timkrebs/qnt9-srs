/**
 * OAuth authentication helpers for Supabase social login.
 *
 * Supports Google and Apple sign-in via Supabase Auth.
 */

import { createSupabaseBrowserClient, isSupabaseConfigured } from '@/lib/supabase/client'
import type { Provider } from '@supabase/supabase-js'

export type OAuthProvider = 'google' | 'apple'

/**
 * Get the OAuth callback URL for the current environment.
 */
function getCallbackUrl(): string {
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_SITE_URL
      ? `${process.env.NEXT_PUBLIC_SITE_URL}/auth/callback`
      : 'http://localhost:3000/auth/callback'
  }
  return `${window.location.origin}/auth/callback`
}

/**
 * Initiate OAuth sign-in with the specified provider.
 *
 * This will redirect the user to the OAuth provider's login page.
 * After authentication, the user will be redirected back to /auth/callback.
 *
 * @param provider - The OAuth provider to use ('google' or 'apple')
 * @param redirectTo - Optional path to redirect to after successful login
 * @throws Error if Supabase is not configured or if the sign-in fails
 */
export async function signInWithOAuth(
  provider: OAuthProvider,
  redirectTo?: string
): Promise<void> {
  if (!isSupabaseConfigured) {
    throw new Error(
      'Supabase is not configured. Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.'
    )
  }

  const supabase = createSupabaseBrowserClient()
  const callbackUrl = getCallbackUrl()
  const redirectUrl = redirectTo
    ? `${callbackUrl}?next=${encodeURIComponent(redirectTo)}`
    : callbackUrl

  const { error } = await supabase.auth.signInWithOAuth({
    provider: provider as Provider,
    options: {
      redirectTo: redirectUrl,
      queryParams: provider === 'google' ? {
        access_type: 'offline',
        prompt: 'consent',
      } : undefined,
    },
  })

  if (error) {
    console.error(`OAuth sign-in error (${provider}):`, error)
    throw new Error(error.message)
  }
}

/**
 * Sign in with Google OAuth.
 *
 * @param redirectTo - Optional path to redirect to after successful login
 */
export async function signInWithGoogle(redirectTo?: string): Promise<void> {
  return signInWithOAuth('google', redirectTo)
}

/**
 * Sign in with Apple OAuth.
 *
 * @param redirectTo - Optional path to redirect to after successful login
 */
export async function signInWithApple(redirectTo?: string): Promise<void> {
  return signInWithOAuth('apple', redirectTo)
}
