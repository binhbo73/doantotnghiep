// services/auth.ts - Authentication API service
import { api } from './api'
import type { ApiResponse } from '@/types'

export interface LoginRequest {
    email: string
    password: string
}

export interface LoginResponse {
    access: string
    refresh: string
    user: {
        id: string
        email: string
        name: string
    }
}

export interface RegisterRequest {
    email: string
    password: string
    name: string
}

export const authService = {
    async login(credentials: LoginRequest): Promise<LoginResponse> {
        const data = await api.post<ApiResponse<LoginResponse>>('/auth/login', credentials)

        // Store token
        if (data.data?.access) {
            localStorage.setItem('auth_token', data.data.access)
            if (data.data.refresh) {
                localStorage.setItem('refresh_token', data.data.refresh)
            }
        }

        return data.data
    },

    async register(userData: RegisterRequest): Promise<LoginResponse> {
        const data = await api.post<ApiResponse<LoginResponse>>('/auth/register', userData)

        if (data.data?.access) {
            localStorage.setItem('auth_token', data.data.access)
            if (data.data.refresh) {
                localStorage.setItem('refresh_token', data.data.refresh)
            }
        }

        return data.data
    },

    async logout(): Promise<void> {
        try {
            await api.post('/auth/logout')
        } finally {
            localStorage.removeItem('auth_token')
            localStorage.removeItem('refresh_token')
        }
    },

    async refreshToken(): Promise<string> {
        const refreshToken = localStorage.getItem('refresh_token')
        if (!refreshToken) throw new Error('No refresh token available')

        const data = await api.post<ApiResponse<{ access: string }>>('/auth/refresh', {
            refresh: refreshToken,
        })

        if (data.data?.access) {
            localStorage.setItem('auth_token', data.data.access)
            return data.data.access
        }

        throw new Error('Failed to refresh token')
    },

    getToken(): string | null {
        if (typeof window === 'undefined') return null
        return localStorage.getItem('auth_token')
    },

    isAuthenticated(): boolean {
        return !!this.getToken()
    },
}
