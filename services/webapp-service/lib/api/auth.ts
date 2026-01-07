import { apiRequest, setTokens, clearTokens, getRefreshToken } from './client'

export interface UserResponse {
  id: string
  email: string
  email_confirmed_at?: string
  phone?: string
  created_at?: string
  last_sign_in_at?: string
  user_metadata: Record<string, unknown>
  app_metadata: Record<string, unknown>
  tier: string
  role?: 'user' | 'admin' | 'editor'
  full_name?: string
  subscription_start?: string
  subscription_end?: string
  stripe_customer_id?: string
  stripe_subscription_id?: string
  metadata: Record<string, unknown>
  last_login?: string
}

export interface SessionResponse {
  access_token: string
  refresh_token: string
  expires_in?: number
  expires_at?: number
  token_type: string
}

export interface AuthResponse {
  user: UserResponse
  session?: SessionResponse
}

export interface MessageResponse {
  message: string
  success: boolean
}

export interface SignUpRequest {
  email: string
  password: string
  full_name?: string
}

export interface SignInRequest {
  email: string
  password: string
}

export interface RefreshTokenRequest {
  refresh_token: string
}

export const authService = {
  signUp: async (data: SignUpRequest): Promise<AuthResponse> => {
    const response = await apiRequest<AuthResponse>(
      'auth',
      '/api/v1/auth/signup',
      {
        method: 'POST',
        body: JSON.stringify(data),
        skipAuth: true,
      },
    )

    if (response.session) {
      setTokens(response.session.access_token, response.session.refresh_token)
    }

    return response
  },

  signIn: async (data: SignInRequest): Promise<AuthResponse> => {
    const response = await apiRequest<AuthResponse>(
      'auth',
      '/api/v1/auth/signin',
      {
        method: 'POST',
        body: JSON.stringify(data),
        skipAuth: true,
      },
    )

    if (response.session) {
      setTokens(response.session.access_token, response.session.refresh_token)
    }

    return response
  },

  signOut: async (): Promise<MessageResponse> => {
    try {
      const response = await apiRequest<MessageResponse>(
        'auth',
        '/api/v1/auth/signout',
        {
          method: 'POST',
        },
      )
      return response
    } finally {
      clearTokens()
    }
  },

  refresh: async (): Promise<AuthResponse> => {
    const refreshToken = getRefreshToken()
    if (!refreshToken) {
      throw new Error('No refresh token available')
    }

    const response = await apiRequest<AuthResponse>(
      'auth',
      '/api/v1/auth/refresh',
      {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken }),
        skipAuth: true,
      },
    )

    if (response.session) {
      setTokens(response.session.access_token, response.session.refresh_token)
    }

    return response
  },

  getCurrentUser: async (): Promise<UserResponse> => {
    const response = await apiRequest<UserResponse>(
      'auth',
      '/api/v1/users/me',
      {
        method: 'GET',
      },
    )
    return response
  },

  updateProfile: async (data: { email?: string; full_name?: string }): Promise<UserResponse> => {
    const response = await apiRequest<UserResponse>(
      'auth',
      '/api/v1/users/me',
      {
        method: 'PATCH',
        body: JSON.stringify(data),
      },
    )
    return response
  },

  updatePassword: async (currentPassword: string, newPassword: string): Promise<MessageResponse> => {
    const response = await apiRequest<MessageResponse>(
      'auth',
      '/api/v1/users/me/password',
      {
        method: 'PATCH',
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      },
    )
    return response
  },

  requestPasswordReset: async (email: string): Promise<MessageResponse> => {
    const response = await apiRequest<MessageResponse>(
      'auth',
      '/api/v1/users/reset-password',
      {
        method: 'POST',
        body: JSON.stringify({ email }),
        skipAuth: true,
      },
    )
    return response
  },

  updatePasswordWithToken: async (accessToken: string, password: string): Promise<MessageResponse> => {
    // This endpoint uses the reset token from Supabase email link
    // The token is passed in Authorization header instead of using stored token
    const baseUrl = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'http://localhost:8010'
    const response = await fetch(`${baseUrl}/api/v1/auth/reset-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ password }),
    })

    if (!response.ok) {
      let errorData
      try {
        errorData = await response.json()
      } catch {
        errorData = { message: response.statusText }
      }
      throw new ApiError(response.status, errorData)
    }

    return response.json()
  },

  deleteAccount: async (): Promise<MessageResponse> => {
    const response = await apiRequest<MessageResponse>(
      'auth',
      '/api/v1/users/me',
      {
        method: 'DELETE',
      },
    )
    return response
  },
}
