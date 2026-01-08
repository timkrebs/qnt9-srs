'use client'

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from 'react'
import {
  authService,
  type UserResponse,
  type SignInRequest,
  type SignUpRequest,
} from '@/lib/api/auth'
import { ApiError, clearTokens, getRefreshToken, setTokens } from '@/lib/api/client'
import { createSupabaseBrowserClient, isSupabaseConfigured } from '@/lib/supabase/client'

interface AuthContextType {
  user: UserResponse | null
  isLoading: boolean
  isAuthenticated: boolean
  isAdmin: boolean
  isEditor: boolean
  canManageBlog: boolean
  login: (data: SignInRequest) => Promise<void>
  signup: (data: SignUpRequest) => Promise<void>
  logout: () => Promise<void>
  refreshSession: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

interface AuthProviderProps {
  children: ReactNode
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [user, setUser] = useState<UserResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const validateSession = useCallback(async () => {
    console.log('[Auth] Starting session validation...')
    try {
      const currentUser = await authService.getCurrentUser()
      console.log('[Auth] Got current user:', currentUser?.email, 'role:', currentUser?.role)
      setUser(currentUser)
    } catch (error) {
      console.log('[Auth] Session validation error:', error)
      // Only clear session for authentication errors (401)
      if (error instanceof ApiError && error.status === 401) {
        console.log('[Auth] Got 401, attempting token refresh...')
        // Try to refresh the token first
        const refreshToken = getRefreshToken()
        if (refreshToken) {
          try {
            const response = await authService.refresh()
            console.log('[Auth] Token refresh successful')
            setUser(response.user)
            return
          } catch (refreshError) {
            // Refresh failed, clear everything
            console.log('[Auth] Token refresh failed:', refreshError)
            clearTokens()
            setUser(null)
          }
        } else {
          // No refresh token available, clear everything
          console.log('[Auth] No refresh token available')
          clearTokens()
          setUser(null)
        }
      } else {
        // For non-401 errors (network issues, parsing errors, etc.)
        // Don't clear tokens - user may still have a valid session
        // Just log the error and don't update user state
        console.warn('[Auth] Session validation failed (non-auth error):', error)
        // Don't clear user here - preserve existing state if any
      }
    }
  }, [])

  useEffect(() => {
    const initAuth = async () => {
      console.log('[Auth] Initializing auth...')
      
      // First, check for existing localStorage token
      const token =
        typeof window !== 'undefined'
          ? localStorage.getItem('access_token')
          : null
      console.log('[Auth] localStorage token found:', !!token)
      
      if (token) {
        await validateSession()
        setIsLoading(false)
        return
      }
      
      // No localStorage token - check for Supabase OAuth session
      if (isSupabaseConfigured) {
        console.log('[Auth] Checking Supabase session...')
        try {
          const supabase = createSupabaseBrowserClient()
          const { data: { session }, error } = await supabase.auth.getSession()
          
          if (error) {
            console.error('[Auth] Supabase getSession error:', error)
          } else if (session) {
            console.log('[Auth] Found Supabase session for:', session.user?.email)
            console.log('[Auth] Provider:', session.user?.app_metadata?.provider)
            
            // Store Supabase tokens in localStorage for auth-service calls
            setTokens(session.access_token, session.refresh_token)
            console.log('[Auth] Tokens stored, validating session...')
            
            // Now validate with auth-service (which accepts Supabase tokens)
            await validateSession()
            setIsLoading(false)
            return
          } else {
            console.log('[Auth] No Supabase session found')
          }
        } catch (err) {
          console.error('[Auth] Error checking Supabase session:', err)
        }
      }
      
      console.log('[Auth] No token or session, user is not authenticated')
      setIsLoading(false)
    }

    initAuth()
    
    // Subscribe to Supabase auth state changes (for OAuth callbacks)
    if (isSupabaseConfigured) {
      const supabase = createSupabaseBrowserClient()
      const { data: { subscription } } = supabase.auth.onAuthStateChange(
        async (event, session) => {
          console.log('[Auth] Supabase auth state change:', event, session?.user?.email)
          
          if (event === 'SIGNED_IN' && session) {
            // OAuth sign-in completed - store tokens and validate
            console.log('[Auth] OAuth sign-in detected, storing tokens...')
            setTokens(session.access_token, session.refresh_token)
            await validateSession()
          } else if (event === 'SIGNED_OUT') {
            console.log('[Auth] Supabase sign-out detected')
            clearTokens()
            setUser(null)
          } else if (event === 'TOKEN_REFRESHED' && session) {
            console.log('[Auth] Supabase token refreshed')
            setTokens(session.access_token, session.refresh_token)
          }
        }
      )
      
      return () => {
        subscription.unsubscribe()
      }
    }
  }, [validateSession])

  const login = useCallback(async (data: SignInRequest) => {
    const response = await authService.signIn(data)
    setUser(response.user)
  }, [])

  const signup = useCallback(async (data: SignUpRequest) => {
    const response = await authService.signUp(data)
    setUser(response.user)
  }, [])

  const logout = useCallback(async () => {
    try {
      // Sign out from auth-service
      await authService.signOut()
    } catch {
      // Ignore auth-service errors
    }
    
    try {
      // Also sign out from Supabase (clears cookies)
      if (isSupabaseConfigured) {
        const supabase = createSupabaseBrowserClient()
        await supabase.auth.signOut()
      }
    } catch {
      // Ignore Supabase errors
    }
    
    clearTokens()
    setUser(null)
  }, [])

  const refreshSession = useCallback(async () => {
    const response = await authService.refresh()
    setUser(response.user)
  }, [])

  const isAdmin = user?.role === 'admin'
  const isEditor = user?.role === 'editor'
  const canManageBlog = isAdmin || isEditor

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user,
    isAdmin,
    isEditor,
    canManageBlog,
    login,
    signup,
    logout,
    refreshSession,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
