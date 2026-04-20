'use client'

import { useEffect, useRef } from 'react'
import { logger } from '@/services/logger'

/**
 * Hook to proactively refresh JWT token before expiration
 * - Decodes JWT to find expiration time
 * - Schedules refresh 5 minutes before expiry
 * - Can be called from any component that needs token protection
 * - Reschedules on successful refresh
 */
export function useTokenRefresh() {
    const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null)

    const scheduleTokenRefresh = (token?: string) => {
        try {
            if (typeof window === 'undefined') return

            // Get token from localStorage if not provided
            const authToken = token || localStorage.getItem('auth_token')
            if (!authToken) {
                logger.debug('No auth token found for refresh scheduling')
                return
            }

            // Decode JWT to get expiration time
            const parts = authToken.split('.')
            if (parts.length !== 3) {
                logger.warn('Invalid JWT format')
                return
            }

            // Decode payload (add padding if needed for base64)
            const padding = '='.repeat((4 - (parts[1].length % 4)) % 4)
            const payload = JSON.parse(atob(parts[1] + padding))

            if (!payload.exp) {
                logger.warn('No expiration time in token')
                return
            }

            // Calculate time until expiration (exp is in seconds, convert to ms)
            const expiresAt = payload.exp * 1000
            const now = Date.now()
            const timeUntilExpiry = expiresAt - now

            // Refresh 5 minutes before expiry (300000ms)
            const REFRESH_BUFFER = 5 * 60 * 1000
            const refreshTime = timeUntilExpiry - REFRESH_BUFFER

            logger.debug('Token refresh scheduled', {
                expiresAt: new Date(expiresAt).toISOString(),
                now: new Date(now).toISOString(),
                refreshInMs: refreshTime,
                refreshAt: new Date(now + refreshTime).toISOString(),
            })

            // Clear any existing timeout
            if (refreshTimeoutRef.current) {
                clearTimeout(refreshTimeoutRef.current)
            }

            // If token expires within 5 minutes, refresh now
            if (refreshTime <= 0) {
                logger.info('Token expiring soon, refreshing immediately')
                performTokenRefresh()
                return
            }

            // Schedule refresh for later
            refreshTimeoutRef.current = setTimeout(() => {
                logger.info('Token refresh timer triggered')
                performTokenRefresh()
            }, Math.max(1000, refreshTime)) // Minimum 1 second

        } catch (error) {
            logger.error('Failed to schedule token refresh', {
                error: error instanceof Error ? error.message : String(error),
            })
        }
    }

    useEffect(() => {
        // Schedule initial refresh
        scheduleTokenRefresh()

        // Listen for successful token refreshes from API client
        const handleTokenRefreshed = (event: Event) => {
            const customEvent = event as CustomEvent
            logger.debug('Token refresh event received, rescheduling', {
                detail: customEvent.detail,
            })
            // Reschedule with new token if available
            scheduleTokenRefresh(customEvent.detail?.token)
        }

        window.addEventListener('token:refreshed', handleTokenRefreshed)

        // Cleanup on unmount
        return () => {
            window.removeEventListener('token:refreshed', handleTokenRefreshed)
            if (refreshTimeoutRef.current) {
                clearTimeout(refreshTimeoutRef.current)
            }
        }
    }, [])
}

/**
 * Perform the actual token refresh
 */
async function performTokenRefresh() {
    try {
        // Dynamically import to avoid circular imports
        const { refreshToken } = await import('@/services/auth')
        const newToken = await refreshToken()

        logger.info('Token successfully refreshed from useTokenRefresh hook')

        // Dispatch event so other hooks/components know about the refresh
        window.dispatchEvent(
            new CustomEvent('token:refreshed', {
                detail: { token: newToken, timestamp: Date.now() },
            })
        )
    } catch (error) {
        logger.error('Failed to refresh token from useTokenRefresh hook', {
            error: error instanceof Error ? error.message : String(error),
        })
        // Token refresh failed - middleware will handle the 401 on next request
        window.dispatchEvent(new CustomEvent('auth:tokenRefreshFailed'))
    }
}
