// services/api.ts - API client with interceptors, error handling, retries
// Force rebuild: 2025-04-20
import { API_TIMEOUTS } from '@/constants/api'
import { getAuthTokenForAPI, refreshAccessToken, clearAuthToken } from './token'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

// Custom error types
export class ApiError extends Error {
    constructor(
        public status: number,
        message: string,
        public data?: unknown
    ) {
        super(message)
        this.name = 'ApiError'
    }
}

export class NetworkError extends Error {
    constructor(message: string) {
        super(message)
        this.name = 'NetworkError'
    }
}

export class TimeoutError extends Error {
    constructor(message: string) {
        super(message)
        this.name = 'TimeoutError'
    }
}

interface RequestOptions {
    timeout?: number
    retries?: number
    headers?: Record<string, string>
    signal?: AbortSignal
    isRetryAfterRefresh?: boolean // Flag to prevent infinite refresh loops
}

// Retry logic with exponential backoff
async function fetchWithRetry(
    url: string,
    options: RequestInit & RequestOptions,
    retryCount = 0
): Promise<Response> {
    const { timeout = API_TIMEOUTS.DEFAULT, retries = 3, ...fetchOptions } = options

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), timeout)

    try {
        const response = await fetch(url, {
            ...fetchOptions,
            signal: controller.signal,
        })

        clearTimeout(timeoutId)
        return response
    } catch (error) {
        clearTimeout(timeoutId)

        // Retry on network errors or timeout
        if (retryCount < retries && (error instanceof TypeError || error instanceof Error)) {
            const delay = Math.min(1000 * Math.pow(2, retryCount), 10000) // Exponential backoff: 1s, 2s, 4s, etc.
            await new Promise(resolve => setTimeout(resolve, delay))
            return fetchWithRetry(url, options, retryCount + 1)
        }

        if (error instanceof Error && error.name === 'AbortError') {
            throw new TimeoutError(`Request timeout after ${timeout}ms`)
        }

        throw new NetworkError(error instanceof Error ? error.message : 'Network request failed')
    }
}

// Handle API response
async function handleResponse<T>(response: Response): Promise<T> {
    const contentType = response.headers.get('content-type')
    const isJson = contentType?.includes('application/json')

    let data: unknown

    // Handle 204 No Content or empty responses
    if (response.status === 204 || response.status === 200) {
        const text = await response.text()
        if (!text) {
            data = null
        } else if (isJson) {
            try {
                data = JSON.parse(text)
            } catch (e) {
                data = text
            }
        } else {
            data = text
        }
    } else if (isJson) {
        try {
            data = await response.json()
        } catch (e) {
            data = await response.text()
        }
    } else {
        data = await response.text()
    }

    if (!response.ok) {
        // Log error details
        if (response.status === 401) {
            console.error('❌ 401 Unauthorized - Token invalid or expired')
        } else if (response.status === 403) {
            console.error('❌ 403 Forbidden - Access denied')
        } else if (response.status === 500) {
            console.error('❌ 500 Server Error')
        }

        throw new ApiError(
            response.status,
            typeof data === 'object' && data !== null && 'message' in data
                ? (data as Record<string, unknown>).message as string
                : `HTTP Error: ${response.status}`,
            data
        )
    }

    return data as T
}

export const api = {
    baseUrl: API_BASE_URL,

    async request<T>(
        method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH',
        endpoint: string,
        data?: unknown,
        options?: RequestOptions
    ): Promise<T> {
        // Skip token refresh retry for refresh and login endpoints
        const isAuthEndpoint = endpoint.includes('/auth/')
        const isRetryAfterRefresh = options?.isRetryAfterRefresh

        const url = `${API_BASE_URL}${endpoint}`
        const token = getAuthTokenForAPI()

        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
            ...options?.headers,
        }

        // Add auth token if available
        if (token) {
            headers['Authorization'] = `Bearer ${token}`
            console.log(`📡 Request: ${method} ${endpoint} [WITH TOKEN]`)
        } else {
            console.warn(`⚠️ Request: ${method} ${endpoint} [NO TOKEN]`)
        }

        const fetchOptions: RequestInit & RequestOptions = {
            method,
            headers,
            timeout: options?.timeout,
            retries: options?.retries,
            signal: options?.signal,
        }

        if (data && method !== 'GET') {
            fetchOptions.body = JSON.stringify(data)
        }

        try {
            const response = await fetchWithRetry(url, fetchOptions)
            return handleResponse<T>(response)
        } catch (error) {
            // Handle 401 Unauthorized with token refresh
            if (
                error instanceof ApiError &&
                error.status === 401 &&
                !isAuthEndpoint &&
                !isRetryAfterRefresh
            ) {
                console.log('🔄 [401] Attempting token refresh...')

                // Try to refresh the token
                const newToken = await refreshAccessToken()

                if (newToken) {
                    console.log('✅ Token refreshed, retrying original request...')

                    // Retry original request with new token
                    const retryOptions = {
                        ...options,
                        isRetryAfterRefresh: true, // Prevent infinite loop
                    }

                    return this.request<T>(method, endpoint, data, retryOptions)
                } else {
                    console.error('❌ Token refresh failed - logging out...')

                    // Refresh failed, clear auth and redirect to login
                    if (typeof window !== 'undefined') {
                        clearAuthToken()
                        // Redirect to login
                        window.location.href = '/login'
                    }

                    throw new ApiError(
                        401,
                        'Token expired and refresh failed. Please login again.'
                    )
                }
            }

            throw error
        }
    },

    async get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
        return this.request<T>('GET', endpoint, undefined, options)
    },

    async post<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
        return this.request<T>('POST', endpoint, data, options)
    },

    async put<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
        return this.request<T>('PUT', endpoint, data, options)
    },

    async patch<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
        return this.request<T>('PATCH', endpoint, data, options)
    },

    async delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
        return this.request<T>('DELETE', endpoint, undefined, options)
    },
}
