/**
 * Authentication Service - Handle login, register, token management
 * Based on backend Account model and API response wrapper
 */

import { api } from '@/services/api/client'
import { logger } from '@/services/logger'
import type { LoginRequest, LoginResponse, RegisterRequest, LoginData, Account } from '@/types/api'

// Re-export types for convenience
export type { LoginRequest, RegisterRequest, Account, LoginData, LoginResponse }

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
 * Get current user from localStorage
 */
export function getCurrentUser(): Account | null {
    if (typeof window === 'undefined') return null
    const userJson = localStorage.getItem('current_user')
    if (!userJson) return null
    try {
        return JSON.parse(userJson)
    } catch {
        return null
    }
}

/**
 * Get user permissions from localStorage
 */
export function getUserPermissions(): string[] {
    if (typeof window === 'undefined') return []
    const permsJson = localStorage.getItem('user_permissions')
    if (!permsJson) return []
    try {
        return JSON.parse(permsJson)
    } catch {
        return []
    }
}

/**
 * Set auth tokens and user info in localStorage
 */
function setAuthData(data: LoginData) {
    const { access_token, refresh_token, user, permissions } = data

    localStorage.setItem('auth_token', access_token)
    if (refresh_token) {
        localStorage.setItem('refresh_token', refresh_token)
    }
    localStorage.setItem('current_user', JSON.stringify(user))
    if (permissions && permissions.length > 0) {
        localStorage.setItem('user_permissions', JSON.stringify(permissions))
    }
}

/**
 * Clear auth data from localStorage
 */
function clearAuthData() {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('current_user')
    localStorage.removeItem('user_permissions')
}

/**
 * Login with email and password
 * Returns the login data from the backend response
 */
export async function login(credentials: LoginRequest): Promise<LoginData> {
    try {
        logger.info('Attempting login', { email: credentials.email })

        // Call API - backend wraps response in ResponseBuilder
        const response = await api.post<LoginResponse>('/auth/login', credentials)

        // Extract the data from the wrapper
        if (!response.success || !response.data) {
            throw new Error(response.message || 'Đăng nhập thất bại')
        }

        const loginData = response.data

        // Store tokens and user info
        setAuthData(loginData)
        logger.info('Login successful', { userId: loginData.user.id })

        return loginData
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
export async function register(data: RegisterRequest): Promise<LoginData> {
    try {
        logger.info('Attempting registration', { email: data.email })

        const response = await api.post<LoginResponse>('/auth/register', data)

        if (!response.success || !response.data) {
            throw new Error(response.message || 'Đăng ký thất bại')
        }

        const loginData = response.data

        // Store tokens and user info
        setAuthData(loginData)
        logger.info('Registration successful', { userId: loginData.user.id })

        return loginData
    } catch (error) {
        logger.error('Registration failed', {
            error: error instanceof Error ? error.message : String(error),
        })
        throw error
    }
}

/**
 * Logout - clear tokens and user info
 */
export async function logout(): Promise<void> {
    try {
        const refreshToken = getRefreshToken()

        // Try to notify backend (but don't fail if it errors)
        if (refreshToken) {
            await api.post('/auth/logout', { refresh: refreshToken }).catch(() => {
                // Fail silently
            })
        }
    } catch (err) {
        logger.warn('Error during logout notification', { error: err })
    } finally {
        clearAuthData()
        logger.info('Logout successful')
    }
}

/**
 * Refresh access token
 */
export async function refreshToken(): Promise<string> {
    try {
        const refreshTokenValue = getRefreshToken()
        if (!refreshTokenValue) {
            throw new Error('Không có refresh token')
        }

        logger.debug('Refreshing auth token')

        // Backend refresh endpoint response format
        const response = await api.post<any>('/auth/refresh', {
            refresh: refreshTokenValue,
        })

        // Handle wrapped response
        if (!response.success || !response.data) {
            throw new Error(response.message || 'Làm mới token thất bại')
        }

        const accessToken = response.data.access || response.data.access_token
        if (!accessToken) {
            throw new Error('Không nhận được access token')
        }

        // Update only the access token
        localStorage.setItem('auth_token', accessToken)
        logger.debug('Token refreshed successfully')

        return accessToken
    } catch (error) {
        logger.error('Token refresh failed', {
            error: error instanceof Error ? error.message : String(error),
        })
        clearAuthData()
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
        const response = await api.post<any>('/auth/change-password', {
            current_password: currentPassword,
            new_password: newPassword,
        })

        if (!response.success) {
            throw new Error(response.message || 'Đổi mật khẩu thất bại')
        }

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
        const response = await api.get<any>('/auth/account')

        if (!response.success || !response.data) {
            throw new Error(response.message || 'Lấy thông tin tài khoản thất bại')
        }

        return response.data as Account
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
 * Request password reset link
 * Sends email with reset link to user
 */
export async function forgotPassword(email: string): Promise<void> {
    try {
        logger.info('Requesting password reset', { email })

        const response = await api.post<any>('/auth/forgot-password', {
            email,
        })

        if (!response.success) {
            throw new Error(response.message || 'Gửi email reset password thất bại')
        }

        logger.info('Password reset email sent successfully')
    } catch (error) {
        logger.error('Forgot password request failed', {
            error: error instanceof Error ? error.message : String(error),
        })
        throw error
    }
}

/**
 * Reset password using token from email
 * Called after user clicks reset link and enters new password
 */
export async function resetPassword(
    token: string,
    newPassword: string,
    confirmPassword: string
): Promise<void> {
    try {
        logger.info('Resetting password with token')

        const response = await api.post<any>('/auth/reset-password', {
            token,
            new_password: newPassword,
            confirm_password: confirmPassword,
        })

        if (!response.success) {
            throw new Error(response.message || 'Đặt lại mật khẩu thất bại')
        }

        logger.info('Password reset successfully')
    } catch (error) {
        logger.error('Password reset failed', {
            error: error instanceof Error ? error.message : String(error),
        })
        throw error
    }
}

/**
 * Watch for auth changes (401, 403 errors)
 */
if (typeof window !== 'undefined') {
    window.addEventListener('auth:unauthorized', () => {
        clearAuthData()
        logger.warn('Authentication cleared due to unauthorized response')
    })

    window.addEventListener('auth:forbidden', () => {
        logger.warn('User received forbidden response')
    })
}

/**
 * Auth service object - Convenient namespace for all auth functions
 */
export const authService = {
    getAuthToken,
    getRefreshToken,
    getCurrentUser,
    getUserPermissions,
    login,
    register,
    logout,
    refreshToken,
    changePassword,
    forgotPassword,
    resetPassword,
    getProfile,
    isAuthenticated,
}
