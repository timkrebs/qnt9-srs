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
import { ApiError, clearTokens, getRefreshToken } from '@/lib/api/client'

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
      const token =
        typeof window !== 'undefined'
          ? localStorage.getItem('access_token')
          : null
      console.log('[Auth] Token found:', !!token)
      if (token) {
        await validateSession()
      } else {
        console.log('[Auth] No token, skipping validation')
      }
      setIsLoading(false)
      console.log('[Auth] Init complete, isLoading=false')
    }

    initAuth()
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
      await authService.signOut()
    } catch {
      clearTokens()
    } finally {
      setUser(null)
    }
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
