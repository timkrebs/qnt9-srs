import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

/**
 * Get the actual origin URL for redirects.
 * 
 * Priority:
 * 1. NEXT_PUBLIC_SITE_URL (most reliable - set at build time)
 * 2. x-forwarded headers from reverse proxy
 * 3. Fallback to request URL (only works in development)
 */
function getOriginUrl(request: NextRequest): string {
  // Primary: Use the configured site URL (set at build time)
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL
  if (siteUrl) {
    console.log('[getOriginUrl] Using NEXT_PUBLIC_SITE_URL:', siteUrl)
    return siteUrl
  }
  
  // Secondary: Use forwarded headers from reverse proxy
  const forwardedProto = request.headers.get('x-forwarded-proto')
  const forwardedHost = request.headers.get('x-forwarded-host') || request.headers.get('host')
  
  if (forwardedProto && forwardedHost) {
    const origin = `${forwardedProto}://${forwardedHost}`
    console.log('[getOriginUrl] Using x-forwarded headers:', origin)
    return origin
  }
  
  // Fallback: Request URL origin (will be wrong behind proxy)
  const fallback = new URL(request.url).origin
  console.log('[getOriginUrl] WARNING: Using fallback (will be wrong in production):', fallback)
  return fallback
}

/**
 * Auth callback route for handling Supabase authentication flows.
 *
 * This handles:
 * - Password reset (recovery) flows
 * - Email verification
 * - OAuth callbacks (Google, Apple) with PKCE flow
 *
 * Supabase redirects here after verifying tokens, then we redirect
 * to the appropriate page with the session established.
 */
export async function GET(request: NextRequest) {
  const origin = getOriginUrl(request)
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const token_hash = requestUrl.searchParams.get('token_hash')
  const type = requestUrl.searchParams.get('type')
  const next = requestUrl.searchParams.get('next') ?? '/'
  const error = requestUrl.searchParams.get('error')
  const error_description = requestUrl.searchParams.get('error_description')

  console.log('=== AUTH CALLBACK ===')
  console.log('URL:', request.url)
  console.log('Origin (with x-forwarded):', origin)
  console.log('code:', code ? 'present' : 'none')
  console.log('token_hash:', token_hash ? 'present' : 'none')
  console.log('type:', type)
  console.log('next:', next)
  console.log('error:', error)

  // Handle errors from Supabase/OAuth provider
  if (error) {
    console.error('Auth callback error:', error, error_description)
    const redirectUrl = new URL('/login', origin)
    redirectUrl.searchParams.set('error', error)
    if (error_description) {
      redirectUrl.searchParams.set('error_description', error_description)
    }
    return NextResponse.redirect(redirectUrl)
  }

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

  if (!supabaseUrl || !supabaseAnonKey) {
    console.error('Supabase not configured')
    return NextResponse.redirect(new URL('/login?error=configuration', origin))
  }

  // Create response that we'll modify with cookies
  let response = NextResponse.redirect(new URL(next, origin))

  // Create Supabase client with cookie handling for PKCE flow
  const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll()
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value, options }) => {
          response.cookies.set(name, value, options)
        })
      },
    },
  })

  // Handle PKCE flow with code (OAuth and magic links)
  if (code) {
    console.log('Exchanging code for session...')
    try {
      const { data, error: exchangeError } = await supabase.auth.exchangeCodeForSession(code)

      if (exchangeError) {
        console.error('Code exchange error:', exchangeError)
        return NextResponse.redirect(new URL(`/login?error=${encodeURIComponent(exchangeError.message)}`, origin))
      }

      console.log('Session established for user:', data.user?.email)
      console.log('Auth provider:', data.user?.app_metadata?.provider)

      // For recovery type, redirect to reset-password with token in hash
      if (type === 'recovery') {
        response = NextResponse.redirect(new URL('/reset-password', origin))
        // Pass the access token in hash for the reset page to use
        const redirectUrl = new URL('/reset-password', origin)
        redirectUrl.hash = `access_token=${data.session?.access_token}&type=recovery`
        return NextResponse.redirect(redirectUrl)
      }

      // For OAuth sign-in (Google, Apple), cookies are already set by the SSR client
      console.log('OAuth login successful, redirecting to:', next)
      return response
    } catch (err) {
      console.error('Auth callback error:', err)
      return NextResponse.redirect(new URL('/login?error=callback_failed', origin))
    }
  }

  // Handle token_hash flow (older email links)
  if (token_hash && type) {
    try {
      const { data, error: verifyError } = await supabase.auth.verifyOtp({
        token_hash,
        type: type as 'recovery' | 'signup' | 'invite' | 'magiclink' | 'email_change',
      })

      if (verifyError) {
        console.error('Token verification error:', verifyError)
        return NextResponse.redirect(new URL(`/reset-password?error=${encodeURIComponent(verifyError.message)}`, origin))
      }

      console.log('OTP verified for user:', data.user?.email)

      // For recovery, redirect to reset-password with token
      if (type === 'recovery') {
        const redirectUrl = new URL('/reset-password', origin)
        redirectUrl.hash = `access_token=${data.session?.access_token}&type=recovery`
        return NextResponse.redirect(redirectUrl)
      }

      return response
    } catch (err) {
      console.error('OTP verification error:', err)
      return NextResponse.redirect(new URL('/reset-password?error=verification_failed', origin))
    }
  }

  // No code or token_hash, redirect to home
  console.log('No code or token_hash provided, redirecting to home')
  return NextResponse.redirect(new URL('/', origin))
}
