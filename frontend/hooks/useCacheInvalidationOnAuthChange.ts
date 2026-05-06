'use client'

/**
 * useCacheInvalidationOnAuthChange Hook
 * Listens for auth changes and invalidates React Query cache
 * Called from DashboardLayout when auth changes (account switching)
 */

import { useEffect } from 'react'
import { queryClient } from '@/lib/queryClient'
import { logger } from '@/services/logger'

export function useCacheInvalidationOnAuthChange() {
    useEffect(() => {
        const handleAuthChange = async () => {
            logger.info('🔄 Auth change detected - invalidating all queries...')

            try {
                // Invalidate all queries when user changes
                // This forces refetch of all data (roles, permissions, etc) with new user's credentials
                await queryClient.invalidateQueries()

                logger.info('✅ All queries invalidated successfully')
            } catch (error) {
                logger.error('Failed to invalidate queries', {
                    error: error instanceof Error ? error.message : String(error),
                })
            }
        }

        // Listen for auth change events
        window.addEventListener('auth:user-changed', handleAuthChange)

        return () => {
            window.removeEventListener('auth:user-changed', handleAuthChange)
        }
    }, [])
}
