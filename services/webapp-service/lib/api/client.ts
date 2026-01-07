const API_CONFIG = {
  auth: process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'http://localhost:8010',
  search: process.env.NEXT_PUBLIC_SEARCH_SERVICE_URL || 'http://localhost:8000',
  user: process.env.NEXT_PUBLIC_USER_SERVICE_URL || 'http://localhost:8011',
  watchlist:
    process.env.NEXT_PUBLIC_WATCHLIST_SERVICE_URL || 'http://localhost:8012',
  notifications:
    process.env.NEXT_PUBLIC_NOTIFICATION_SERVICE_URL || 'http://localhost:8040',
} as const

export type ServiceType = keyof typeof API_CONFIG

export interface ApiErrorResponse {
  detail?: string | { msg: string; type: string }[] | { message?: string; error?: string; success?: boolean }
  message?: string
}

export class ApiError extends Error {
  status: number
  data: ApiErrorResponse

  constructor(status: number, data: ApiErrorResponse) {
    const message = ApiError.extractMessage(data)
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }

  static extractMessage(data: ApiErrorResponse): string {
    // Handle string detail
    if (typeof data.detail === 'string') {
      return data.detail
    }
    // Handle FastAPI validation error array
    if (Array.isArray(data.detail) && data.detail.length > 0) {
      return data.detail.map((d) => d.msg).join(', ')
    }
    // Handle nested object with message (our custom error format)
    if (data.detail && typeof data.detail === 'object' && 'message' in data.detail) {
      return (data.detail as { message: string }).message
    }
    // Handle top-level message
    if (data.message) {
      return data.message
    }
    return 'An unexpected error occurred'
  }
}

const getAccessToken = (): string | null => {
  if (typeof window === 'undefined') {
    return null
  }
  return localStorage.getItem('access_token')
}

export const setTokens = (accessToken: string, refreshToken: string): void => {
  if (typeof window === 'undefined') {
    return
  }
  localStorage.setItem('access_token', accessToken)
  localStorage.setItem('refresh_token', refreshToken)
}

export const clearTokens = (): void => {
  if (typeof window === 'undefined') {
    return
  }
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

export const getRefreshToken = (): string | null => {
  if (typeof window === 'undefined') {
    return null
  }
  return localStorage.getItem('refresh_token')
}

export const apiRequest = async <T>(
  service: ServiceType,
  endpoint: string,
  options?: RequestInit & { skipAuth?: boolean },
): Promise<T> => {
  const baseUrl = API_CONFIG[service]
  const { skipAuth, ...fetchOptions } = options || {}
  const token = skipAuth ? null : getAccessToken()

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...fetchOptions?.headers,
  }

  const response = await fetch(`${baseUrl}${endpoint}`, {
    ...fetchOptions,
    headers,
  })

  if (!response.ok) {
    let errorData: ApiErrorResponse
    try {
      errorData = await response.json()
    } catch {
      errorData = { message: response.statusText }
    }
    throw new ApiError(response.status, errorData)
  }

  if (response.status === 204) {
    return {} as T
  }

  return response.json()
}
