/**
 * Token Management - Auth token lifecycle for API requests
 *
 * Strategy:
 * 1. Do not create a token until real login succeeds
 * 2. Use loginAndGetToken() to get real JWT from backend
 * 3. Store in localStorage only when backend token cookies are unavailable
 */

import { buildApiUrl } from '@/config/api'
import { logger } from '@/services/logger'

const TOKEN_KEY = 'auth_token'
const REFRESH_TOKEN_KEY = 'refresh_token'

export function initializeToken(): void {
    if (typeof window === 'undefined') return

    try {
        const existing = localStorage.getItem(TOKEN_KEY)
        if (existing && existing.trim() !== '') {
            logger.debug('Token already present in localStorage on startup')
        } else {
            logger.debug('No auth token found in localStorage on startup')
        }
    } catch (err) {
        logger.error('Error checking token on startup', err)
    }
}

/**
 * Login to backend and get real JWT token
 */
export async function loginAndGetToken(username: string, password: string): Promise<string> {
    try {
        logger.debug('Logging in via legacy token service', { username })

        const response = await fetch(buildApiUrl('/auth/login'), {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
            signal: AbortSignal.timeout(10000)
        })

        if (!response.ok) {
            const errorText = await response.text()
            throw new Error(`Login failed with status ${response.status}: ${errorText.substring(0, 300)}`)
        }

        const data = await response.json()
        const token = data?.data?.access_token || data?.access_token || data?.token
        const refreshToken = data?.data?.refresh_token || data?.refresh_token

        if (!token) {
            logger.error('No access_token in login response')
            throw new Error('No token in login response')
        }

        if (typeof window !== 'undefined') {
            if (refreshToken) {
                localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
            }
            localStorage.setItem(TOKEN_KEY, token)
        }

        return token
    } catch (err) {
        logger.error('Legacy login error', err)
        throw err
    }
}

/**
 * Get current token from localStorage (sync)
 */
export function getAuthTokenForAPI(): string {
    if (typeof window === 'undefined') return ''

    try {
        return localStorage.getItem(TOKEN_KEY) || ''
    } catch (err) {
        logger.error('Error retrieving token', err)
        return ''
    }
}

/**
 * Store token in localStorage
 */
export function setAuthToken(token: string): void {
    if (typeof window === 'undefined') return

    try {
        localStorage.setItem(TOKEN_KEY, token)
        logger.debug('Legacy auth token stored in localStorage')
    } catch (err) {
        logger.error('Error storing token', err)
    }
}

/**
 * Get refresh token from localStorage
 */
export function getRefreshToken(): string {
    if (typeof window === 'undefined') return ''

    try {
        return localStorage.getItem(REFRESH_TOKEN_KEY) || ''
    } catch (err) {
        logger.error('Error retrieving refresh token', err)
        return ''
    }
}

let refreshPromise: Promise<string | null> | null = null

/**
 * Refresh access token using refresh token
 */
export async function refreshAccessToken(): Promise<string | null> {
    if (refreshPromise) {
        logger.debug('Reusing in-flight token refresh promise')
        return refreshPromise
    }

    refreshPromise = (async () => {
        try {
            const refreshToken = getRefreshToken()

            if (!refreshToken) {
                logger.warn('No refresh token available for legacy refresh flow')
                return null
            }

            logger.debug('Attempting refresh in legacy token service')

            const refreshPayload: Record<string, unknown> = { refresh: refreshToken }
            const response = await fetch(buildApiUrl('/auth/refresh'), {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(refreshPayload),
                signal: AbortSignal.timeout(10000)
            })

            if (!response.ok) {
                return null
            }

            const data = await response.json()
            const newAccessToken = data?.data?.access || data?.access

            if (!newAccessToken) {
                logger.error('No access token in refresh response')
                return null
            }

            setAuthToken(newAccessToken)
            return newAccessToken
        } catch (err) {
            logger.error('Legacy token refresh failed', err)
            return null
        } finally {
            refreshPromise = null
        }
    })()

    return refreshPromise
}

/**
 * Clear all tokens on logout
 */
export function clearAuthToken(): void {
    if (typeof window === 'undefined') return

    try {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(REFRESH_TOKEN_KEY)
        logger.debug('Legacy auth tokens cleared from localStorage')
    } catch (err) {
        logger.error('Error clearing legacy auth tokens', err)
    }
}

/**
 * Logout from backend and clear local tokens
 */
export async function logoutUser(): Promise<void> {
    try {
        const accessToken = getAuthTokenForAPI()
        const refreshToken = getRefreshToken()

        logger.debug('Legacy logout attempt', {
            hasAccessToken: !!accessToken,
            hasRefreshToken: !!refreshToken
        })

        if (!accessToken || accessToken.includes('placeholder')) {
            logger.warn('No valid access token to logout with')
            clearAuthToken()
            return
        }

        const response = await fetch(buildApiUrl('/auth/logout'), {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {})
            },
            body: JSON.stringify({ refresh: refreshToken }),
            signal: AbortSignal.timeout(5000)
        })

        if (!response.ok) {
            logger.error('Legacy logout API returned non-OK status', { status: response.status })
        } else {
            logger.debug('Legacy logout API successful', { status: response.status })
        }

        clearAuthToken()
    } catch (err) {
        logger.error('Legacy logout error', err)
        clearAuthToken()
    }
}

