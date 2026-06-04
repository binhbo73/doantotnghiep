import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { env } from '@/config/environment'
import { logger } from '@/services/logger'

/**
 * API Client Configuration
 * Centralized axios instance with token handling and error management
 */

interface ExtendedAxiosRequestConfig extends AxiosRequestConfig {
    skipErrorHandling?: boolean
    skipTokenRefresh?: boolean
}

class APIClient {
    private instance: AxiosInstance
    private inMemoryAccessToken: string | null = null

    constructor() {
        const normalizedBase = env.apiUrl.endsWith('/') ? env.apiUrl : `${env.apiUrl}/`

        this.instance = axios.create({
            baseURL: normalizedBase,
            timeout: env.defaultTimeout,
            withCredentials: true, // rely on HttpOnly cookies when available
            headers: {
                'Accept': 'application/json',
            },
        })

        // Request interceptor - Add auth token
        this.instance.interceptors.request.use(
            (config) => {
                const token = this.getToken()

                // Attach Authorization header only when an in-memory or explicit token exists.
                if (token) {
                    config.headers.Authorization = `Bearer ${token}`
                }

                // Don't override Content-Type if it's already set (e.g., for FormData)
                if (!config.headers['Content-Type'] && !(config.data instanceof FormData)) {
                    config.headers['Content-Type'] = 'application/json'
                }
                return config
            },
            (error) => Promise.reject(error)
        )

        // Response interceptor - Handle token refresh and errors
        this.instance.interceptors.response.use(
            (response) => response,
            async (error: AxiosError) => {
                const originalRequest = error.config as ExtendedAxiosRequestConfig

                // Handle 401 Unauthorized
                if (error.response?.status === 401 && !originalRequest.skipTokenRefresh) {
                    try {
                        // Attempt to refresh token using HttpOnly cookies when available.
                        // We intentionally do not send refresh token in body to prefer backend cookie flow.
                        const refreshPayload: Record<string, unknown> = {}
                        const storedRefresh = this.getRefreshToken()
                        if (storedRefresh) {
                            refreshPayload.refresh = storedRefresh
                        }

                        const response = await axios.post(
                            `${env.apiUrl.replace(/\/$/, '')}/auth/refresh/`,
                            refreshPayload,
                            { timeout: env.defaultTimeout, withCredentials: true }
                        )

                        // Support multiple response shapes including wrapper data and direct token payloads.
                        const respData = response.data || {}
                        const newAccessToken = this.parseAccessToken(respData)

                        if (newAccessToken) {
                            this.setToken(newAccessToken)

                            // Retry original request with new token
                            if (originalRequest.headers) {
                                originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
                            }

                            return this.instance(originalRequest)
                        }

                        // If no token returned, treat as failed refresh
                        this.clearTokens()
                        window.location.href = '/login'
                        return Promise.reject(error)
                    } catch (refreshError) {
                        // Token refresh failed - clear storage and redirect to login
                        this.clearTokens()
                        window.location.href = '/login'
                        return Promise.reject(refreshError)
                    }
                }

                // Handle other errors
                if (!originalRequest.skipErrorHandling && error.response) {
                    const statusCode = error.response.status
                    const data = error.response.data as any

                    const errorMessage = {
                        400: data?.message || 'Yêu cầu không hợp lệ',
                        403: data?.message || 'Bạn không có quyền truy cập',
                        404: data?.message || 'Tài nguyên không tìm thấy',
                        500: data?.message || 'Lỗi máy chủ',
                    }[statusCode] || data?.message || 'Lỗi không xác định'

                    // You can dispatch to a toast/notification system here if needed
                    logger.error(`API Error [${statusCode}]`, { errorMessage, url: error.config?.url })
                }

                return Promise.reject(error)
            }
        )
    }

    // Returns the currently available access token. Prefers in-memory token set by the login/refresh flow.
    public getToken(): string | null {
        if (this.inMemoryAccessToken) return this.inMemoryAccessToken
        if (typeof window !== 'undefined') {
            // Fallback for older deployments that still write tokens to localStorage
            try {
                const token = localStorage.getItem('auth_token')
                return token
            } catch {
                return null
            }
        }
        return null
    }

    public getRefreshToken(): string | null {
        if (typeof window !== 'undefined') {
            try {
                return localStorage.getItem('refresh_token')
            } catch {
                return null
            }
        }
        return null
    }

    private parseAccessToken(payload: any): string | null {
        if (!payload || typeof payload !== 'object') return null
        return (
            payload.access ||
            payload.access_token ||
            payload.token ||
            payload?.data?.access ||
            payload?.data?.access_token ||
            payload?.data?.token ||
            payload?.data?.data?.access ||
            payload?.data?.data?.access_token ||
            payload?.data?.data?.token ||
            null
        )
    }

    // Set token into in-memory store. Avoid persisting tokens in JS-accessible storage.
    public setToken(token: string): void {
        this.inMemoryAccessToken = token
    }

    public clearTokens(): void {
        this.inMemoryAccessToken = null
        if (typeof window !== 'undefined') {
            try {
                localStorage.removeItem('auth_token')
                localStorage.removeItem('refresh_token')
            } catch {
                // ignore
            }
        }
    }

    public get<T = any>(url: string, config?: ExtendedAxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.instance.get(url, config)
    }

    public post<T = any>(
        url: string,
        data?: any,
        config?: ExtendedAxiosRequestConfig
    ): Promise<AxiosResponse<T>> {
        return this.instance.post(url, data, config)
    }

    public patch<T = any>(
        url: string,
        data?: any,
        config?: ExtendedAxiosRequestConfig
    ): Promise<AxiosResponse<T>> {
        return this.instance.patch(url, data, config)
    }

    public put<T = any>(
        url: string,
        data?: any,
        config?: ExtendedAxiosRequestConfig
    ): Promise<AxiosResponse<T>> {
        return this.instance.put(url, data, config)
    }

    public delete<T = any>(url: string, config?: ExtendedAxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.instance.delete(url, config)
    }
}

export const apiClient = new APIClient()
