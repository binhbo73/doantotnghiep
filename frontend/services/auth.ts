/**
 * Authentication Service - Handle login, register, token management
 * Based on backend Account model
 */

import { api } from '@/services/api/client'
import { logger } from '@/services/logger'
import type { LoginRequest, LoginResponse, RegisterRequest, Account } from '@/types/api'

/**
 * Get auth token from localStorage
 */
export function getAuthToken(): string | null {
    if (typeof window === 'undefined') return null
    return localStorage.getItem('auth_token')
}

/**
 * Get refresh token from localStorage
 */
export function getRefreshToken(): string | null {
    if (typeof window === 'undefined') return null
    return localStorage.getItem('refresh_token')
}

/**
 * Set auth tokens in localStorage
 */
function setAuthTokens(accessToken: string, refreshToken?: string) {
    localStorage.setItem('auth_token', accessToken)
    if (refreshToken) {
        localStorage.setItem('refresh_token', refreshToken)
    }
}

/**
 * Clear auth tokens from localStorage
 */
function clearAuthTokens() {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('refresh_token')
}

/**
 * Login with email and password
 */
export async function login(credentials: LoginRequest): Promise<LoginResponse> {
    try {
        logger.info('Attempting login', { email: credentials.email })

        const response = await api.post<LoginResponse>('/auth/login', credentials)

        // Store tokens
        if (response.access) {
            setAuthTokens(response.access, response.refresh)
            logger.info('Login successful', { userId: response.user.id })
        }

        return response
    } catch (error) {
        logger.error('Login failed', {
            error: error instanceof Error ? error.message : String(error),
        })
        throw error
    }
}

/**
 * Register new account
 */
export async function register(data: RegisterRequest): Promise<LoginResponse> {
    try {
        logger.info('Attempting registration', { email: data.email })

        const response = await api.post<LoginResponse>('/auth/register', data)

        // Store tokens
        if (response.access) {
            setAuthTokens(response.access, response.refresh)
            logger.info('Registration successful', { userId: response.user.id })
        }

        return response
    } catch (error) {
        logger.error('Registration failed', {
            error: error instanceof Error ? error.message : String(error),
        })
        throw error
    }
}

/**
 * Logout - clear tokens
 */
export async function logout(): Promise<void> {
    try {
        // Try to notify backend (but don't fail if it errors)
        await api.post('/auth/logout').catch(() => {
            // Fail silently
        })
    } finally {
        clearAuthTokens()
        logger.info('Logout successful')
    }
}

/**
 * Refresh access token
 */
export async function refreshToken(): Promise<string> {
    try {
        const refreshToken = getRefreshToken()
        if (!refreshToken) {
            throw new Error('No refresh token available')
        }

        logger.debug('Refreshing auth token')

        const response = await api.post<{ access: string }>('/auth/refresh', {
            refresh: refreshToken,
        })

        if (response.access) {
            setAuthTokens(response.access, refreshToken)
            logger.debug('Token refreshed successfully')
            return response.access
        }

        throw new Error('Failed to refresh token')
    } catch (error) {
        logger.error('Token refresh failed', {
            error: error instanceof Error ? error.message : String(error),
        })
        clearAuthTokens()
        throw error
    }
}

/**
 * Change password
 */
export async function changePassword(
    currentPassword: string,
    newPassword: string
): Promise<void> {
    try {
        await api.post('/auth/change-password', {
            current_password: currentPassword,
            new_password: newPassword,
        })
        logger.info('Password changed successfully')
    } catch (error) {
        logger.error('Password change failed', {
            error: error instanceof Error ? error.message : String(error),
        })
        throw error
    }
}

/**
 * Get current user profile
 */
export async function getProfile(): Promise<Account> {
    try {
        const response = await api.get<Account>('/users/profile')
        return response
    } catch (error) {
        logger.error('Failed to fetch profile', {
            error: error instanceof Error ? error.message : String(error),
        })
        throw error
    }
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
    return !!getAuthToken()
}

/**
 * Watch for auth changes (401, 403 errors)
 */
if (typeof window !== 'undefined') {
    window.addEventListener('auth:unauthorized', () => {
        clearAuthTokens()
        logger.warn('Authentication cleared due to unauthorized response')
    })

    window.addEventListener('auth:forbidden', () => {
        logger.warn('User received forbidden response')
    })
}

/**
 * Export all functions as service object
 */
export const authService = {
    getAuthToken,
    getRefreshToken,
    login,
    register,
    logout,
    refreshToken,
    changePassword,
    getProfile,
    isAuthenticated,
}
