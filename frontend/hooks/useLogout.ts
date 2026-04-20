'use client'

import { useState, useCallback } from 'react'
import { logout as logoutFromAuth } from '@/services/auth'
import { useRouter } from 'next/navigation'
import { logger } from '@/services/logger'

/**
 * Hook: useLogout
 * Handles user logout with API call and redirect
 * 
 * Usage:
 * const { logout, isLoading, error } = useLogout()
 * 
 * <button onClick={logout}>Logout</button>
 */
export function useLogout() {
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const router = useRouter()

    const logout = useCallback(async () => {
        try {
            setIsLoading(true)
            setError(null)

            logger.info('🔓 Starting logout...')

            // Call logout API from auth service
            await logoutFromAuth()

            logger.info('✅ Logout complete, redirecting...')

            // Redirect to login
            setTimeout(() => {
                router.push('/login')
            }, 500)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Logout failed'
            setError(message)
            logger.error('❌ Logout error:', { error: message })

            // Still redirect even if API fails (token already cleared locally)
            setTimeout(() => {
                router.push('/login')
            }, 1000)
        } finally {
            setIsLoading(false)
        }
    }, [router])

    return {
        logout,
        isLoading,
        error,
    }
}
