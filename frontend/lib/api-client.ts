import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { env } from '@/config/environment'

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

    constructor() {
        this.instance = axios.create({
            baseURL: env.apiUrl,
            timeout: env.defaultTimeout,
            headers: {
                'Accept': 'application/json',
            },
        })

        // Request interceptor - Add auth token
        this.instance.interceptors.request.use(
            (config) => {
                const token = this.getToken()
                console.log('🔐 Request Interceptor:', {
                    url: config.url,
                    method: config.method,
                    hasToken: !!token,
                    tokenPrefix: token ? token.substring(0, 20) + '...' : 'NO_TOKEN'
                })

                if (token) {
                    config.headers.Authorization = `Bearer ${token}`
                    console.log('✅ Token added to headers')
                } else {
                    console.warn('❌ No token found in localStorage!')
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
                    const refreshToken = this.getRefreshToken()

                    if (refreshToken) {
                        try {
                            // Attempt to refresh token
                            const response = await axios.post(
                                `${env.apiUrl}/auth/refresh/`,
                                { refresh: refreshToken },
                                { timeout: env.defaultTimeout }
                            )

                            const newAccessToken = response.data.access
                            this.setToken(newAccessToken)

                            // Retry original request with new token
                            if (originalRequest.headers) {
                                originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
                            }

                            return this.instance(originalRequest)
                        } catch (refreshError) {
                            // Token refresh failed - clear storage and redirect to login
                            this.clearTokens()
                            window.location.href = '/login'
                            return Promise.reject(refreshError)
                        }
                    } else {
                        // No refresh token - redirect to login
                        this.clearTokens()
                        window.location.href = '/login'
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
                    console.error(`API Error [${statusCode}]:`, errorMessage)
                }

                return Promise.reject(error)
            }
        )
    }

    private getToken(): string | null {
        if (typeof window !== 'undefined') {
            const token = localStorage.getItem('auth_token')  // Changed from 'access_token'
            console.log('🔑 getToken() from localStorage:', {
                key: 'auth_token',
                found: !!token,
                preview: token ? token.substring(0, 30) + '...' : 'null'
            })
            return token
        }
        return null
    }

    private getRefreshToken(): string | null {
        if (typeof window !== 'undefined') {
            const token = localStorage.getItem('refresh_token')
            console.log('🔄 getRefreshToken() from localStorage:', {
                key: 'refresh_token',
                found: !!token,
                preview: token ? token.substring(0, 30) + '...' : 'null'
            })
            return token
        }
        return null
    }

    private setToken(token: string): void {
        if (typeof window !== 'undefined') {
            localStorage.setItem('auth_token', token)  // Changed from 'access_token'
            console.log('💾 setToken() to localStorage with key: auth_token')
        }
    }

    private clearTokens(): void {
        if (typeof window !== 'undefined') {
            localStorage.removeItem('auth_token')  // Changed from 'access_token'
            localStorage.removeItem('refresh_token')
            console.log('🗑️ Tokens cleared from localStorage')
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
