/**
 * Authentication Service - Handle login, register, token management
 * Based on backend Account model and API response wrapper
 */

import { api } from '@/services/api/client'
import { logger } from '@/services/logger'
import type { LoginRequest, LoginResponse, RegisterRequest, LoginData, Account } from '@/types/api'

// Re-export types for convenience
export type { LoginRequest, RegisterRequest, Account, LoginData, LoginResponse }

function getCookie(name: string): string | null {
    if (typeof document === 'undefined') return null
    const cookieMatch = document.cookie.match(
        new RegExp('(?:^|; )' + name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + '=([^;]*)')
    )
    return cookieMatch ? decodeURIComponent(cookieMatch[1]) : null
}

/**
 * Get auth token from localStorage or cookie fallback
 */
export function getAuthToken(): string | null {
    if (typeof window === 'undefined') {
        console.warn('⚠️ [getAuthToken] Called on server-side (window is undefined)')
        return null
    }

    try {
        const fromStorage = localStorage.getItem('auth_token')
        const fromCookie = getCookie('auth_token')

        const token = fromStorage || fromCookie

        if (token && token.includes('placeholder')) {
            console.debug('ℹ️ [getAuthToken] Ignoring stale placeholder token')
            return null
        }

        if (token) {
            console.debug(`✅ [getAuthToken] Token retrieved (length: ${token.length}, source: ${fromStorage ? 'localStorage' : 'cookie'})`)
        } else {
            console.debug('ℹ️ [getAuthToken] No token found in localStorage or cookies')
        }

        return token
    } catch (err) {
        console.error('❌ [getAuthToken] Error retrieving token:', err)
        return null
    }
}

/**
 * Get refresh token from localStorage or cookie fallback
 */
export function getRefreshToken(): string | null {
    if (typeof window === 'undefined') return null
    return localStorage.getItem('refresh_token') || getCookie('refresh_token')
}

/**
 * Get current user from localStorage
 */
export function getCurrentUser(): any | null {
    if (typeof window === 'undefined') return null
    const userJson = localStorage.getItem('current_user')
    if (!userJson) return null
    try {
        const user = JSON.parse(userJson)
        const roles = JSON.parse(localStorage.getItem('user_roles') || '[]')
        const department_id = localStorage.getItem('user_department_id')
        const permissions = JSON.parse(localStorage.getItem('user_permissions') || '[]')

        return {
            ...user,
            roles,
            department_id,
            permissions
        }
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
 * Set auth tokens and user info in localStorage + cookies
 * EXPORTED: Can be called from anywhere to update user auth data (especially after permission changes)
 */
export function setAuthData(data: LoginData) {
    const { access_token, refresh_token, user, permissions, roles, department_id } = data

    // Validate token before storing
    if (!access_token || typeof access_token !== 'string' || access_token.trim() === '') {
        console.error('❌ [setAuthData] Invalid access_token received:', {
            type: typeof access_token,
            isEmpty: !access_token || access_token.trim() === '',
            length: access_token?.length
        })
        throw new Error('Invalid access_token from backend')
    }

    console.log('🔐 [setAuthData] Starting token storage with token length:', access_token.length)

    // Store old user ID to detect if user changed
    const oldUserJson = localStorage.getItem('current_user')
    const oldUserId = oldUserJson ? JSON.parse(oldUserJson).id : null
    const newUserId = user.id

    // Set in localStorage (for client-side access)
    try {
        localStorage.setItem('auth_token', access_token)
        const storedAccessToken = localStorage.getItem('auth_token')
        if (!storedAccessToken || storedAccessToken !== access_token) {
            console.error('❌ [setAuthData] Failed to store access_token in localStorage!', {
                stored: storedAccessToken?.substring(0, 30),
                original: access_token.substring(0, 30),
                match: storedAccessToken === access_token
            })
        } else {
            console.log('✅ [setAuthData] Access token stored in localStorage (length:', access_token.length, ')')
        }
    } catch (err) {
        console.error('❌ [setAuthData] Error storing access_token:', err)
    }

    if (refresh_token) {
        try {
            localStorage.setItem('refresh_token', refresh_token)
            console.log('✅ [setAuthData] Refresh token stored in localStorage')
        } catch (err) {
            console.error('❌ [setAuthData] Error storing refresh_token:', err)
        }
    }

    try {
        localStorage.setItem('current_user', JSON.stringify(user))
        console.log('✅ [setAuthData] User data stored in localStorage')
    } catch (err) {
        console.error('❌ [setAuthData] Error storing user data:', err)
    }

    if (permissions && permissions.length > 0) {
        try {
            localStorage.setItem('user_permissions', JSON.stringify(permissions))
            console.log('✅ [setAuthData] Permissions stored in localStorage')
        } catch (err) {
            console.error('❌ [setAuthData] Error storing permissions:', err)
        }
    }

    if (roles) {
        try {
            localStorage.setItem('user_roles', JSON.stringify(roles))
            console.log('✅ [setAuthData] Roles stored in localStorage')
        } catch (err) {
            console.error('❌ [setAuthData] Error storing roles:', err)
        }
    }

    if (department_id) {
        try {
            localStorage.setItem('user_department_id', department_id)
            console.log('✅ [setAuthData] Department ID stored in localStorage')
        } catch (err) {
            console.error('❌ [setAuthData] Error storing department_id:', err)
        }
    }

    // Set in cookies (for middleware access)
    // Cookies lưu 24h hoặc theo thời gian token expiry
    try {
        setCookie('auth_token', access_token, 24 * 60 * 60 * 1000) // 24 hours
        console.log('✅ [setAuthData] Auth token cookie set')
    } catch (err) {
        console.error('❌ [setAuthData] Error setting auth_token cookie:', err)
    }

    if (refresh_token) {
        try {
            setCookie('refresh_token', refresh_token, 7 * 24 * 60 * 60 * 1000) // 7 days
            console.log('✅ [setAuthData] Refresh token cookie set')
        } catch (err) {
            console.error('❌ [setAuthData] Error setting refresh_token cookie:', err)
        }
    }

    // Verify token was actually stored
    const verifyAccess = getAuthToken()
    const verifyRefresh = getRefreshToken()
    console.log('🔍 [setAuthData] Verification after storage:', {
        accessTokenStored: verifyAccess ? '✅ Yes' : '❌ No',
        refreshTokenStored: verifyRefresh ? '✅ Yes' : '❌ No',
        accessTokenIsPlaceholder: verifyAccess?.includes('placeholder') ? '⚠️ Yes' : '✅ No',
    })

    // Emit event for same-tab auth change detection (only if user ID changed)
    if (oldUserId && oldUserId !== newUserId) {
        console.log('🔄 User changed from', oldUserId, 'to', newUserId, '- emitting auth:user-changed event')
        window.dispatchEvent(new Event('auth:user-changed'))
    } else if (!oldUserId && newUserId) {
        // First login
        console.log('🔄 User logged in:', newUserId, '- emitting auth:user-changed event')
        window.dispatchEvent(new Event('auth:user-changed'))
    }
}

/**
 * Set a cookie with expiration time
 * @param name Cookie name
 * @param value Cookie value
 * @param expirationMs Expiration time in milliseconds
 */
function setCookie(name: string, value: string, expirationMs: number) {
    if (typeof document === 'undefined') return

    const date = new Date()
    date.setTime(date.getTime() + expirationMs)
    const expires = `expires=${date.toUTCString()}`

    // Set cookie with path to root so middleware can access it
    document.cookie = `${name}=${value}; ${expires}; path=/`
}

/**
 * Clear auth data from localStorage and cookies
 */
function clearAuthData() {
    // Clear from localStorage
    localStorage.removeItem('auth_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('current_user')
    localStorage.removeItem('user_permissions')
    localStorage.removeItem('user_roles')
    localStorage.removeItem('user_department_id')

    // Clear from cookies
    deleteCookie('auth_token')
    deleteCookie('refresh_token')
}

/**
 * Delete a cookie
 */
function deleteCookie(name: string) {
    if (typeof document === 'undefined') return
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/`
}

/**
 * Login with email and password
 * Returns the login data from the backend response
 */
export async function login(credentials: LoginRequest): Promise<LoginData> {
    try {
        logger.info('Attempting login', { email: credentials.email })
        console.log('🔐 [login] Starting login flow for:', credentials.email)

        // Call API - backend wraps response in ResponseBuilder
        const response = await api.post<LoginResponse>('/auth/login', credentials)
        console.log('📡 [login] Backend response status:', response.success)

        // Extract the data from the wrapper
        if (!response.success || !response.data) {
            const errorMsg = response.message || 'Đăng nhập thất bại'
            console.error('❌ [login] Login response not successful:', {
                success: response.success,
                message: errorMsg,
                hasData: !!response.data
            })
            throw new Error(errorMsg)
        }

        const loginData = response.data
        console.log('✅ [login] Login response received with tokens:', {
            hasAccessToken: !!loginData.access_token,
            accessTokenLength: loginData.access_token?.length,
            hasRefreshToken: !!loginData.refresh_token,
            refreshTokenLength: loginData.refresh_token?.length,
            userId: loginData.user.id,
        })

        // Validate tokens before storing
        if (!loginData.access_token) {
            console.error('❌ [login] No access_token in login response!')
            throw new Error('Backend did not return access_token')
        }

        // Store tokens and user info
        console.log('💾 [login] Storing auth data...')
        setAuthData(loginData)

        // Verify token was stored
        const storedToken = getAuthToken()
        console.log('🔍 [login] Token verification after setAuthData:', {
            tokenStored: !!storedToken,
            tokenLength: storedToken?.length,
            isPlaceholder: storedToken?.includes('placeholder'),
        })

        logger.info('Login successful', { userId: loginData.user.id })
        console.log('✅ [login] Login flow completed successfully')

        return loginData
    } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error)
        console.error('❌ [login] Login failed:', errorMsg)
        logger.error('Login failed', {
            error: errorMsg,
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
        const accessToken = getAuthToken()
        const refreshToken = getRefreshToken()

        logger.info('Logout starting', {
            hasAccessToken: !!accessToken,
            hasRefreshToken: !!refreshToken
        })

        // Try to notify backend (but don't fail if it errors)
        if (accessToken && refreshToken) {
            try {
                logger.debug('Sending logout request to backend', {
                    accessTokenLength: accessToken.length,
                    refreshTokenLength: refreshToken.length
                })

                await api.post('/auth/logout', {
                    refresh: refreshToken
                })

                logger.info('Logout API call successful')
            } catch (err) {
                logger.warn('Backend logout notification failed (non-critical)', {
                    error: err instanceof Error ? err.message : String(err)
                })
                // Fail silently - still clear tokens locally
            }
        } else {
            logger.warn('Missing tokens for logout', {
                hasAccessToken: !!accessToken,
                hasRefreshToken: !!refreshToken
            })
        }
    } catch (err) {
        logger.warn('Error during logout', {
            error: err instanceof Error ? err.message : String(err)
        })
    } finally {
        clearAuthData()
        logger.info('Logout completed - tokens cleared locally')
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
 * Check if user is authenticated (has valid real JWT token, not placeholder)
 */
export function isAuthenticated(): boolean {
    const token = getAuthToken()
    // Must have token AND it must not be a placeholder
    return !!token && !token.includes('placeholder')
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
