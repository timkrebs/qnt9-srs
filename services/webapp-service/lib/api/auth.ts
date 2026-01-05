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
}
