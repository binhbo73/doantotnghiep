'use client'

/**
 * usePeriodicPermissionCheck Hook
 * Periodically refreshes user permissions to catch changes from other sessions/admins
 * Runs every 5 minutes to check if user's roles or permissions have changed on backend
 */

import { useEffect, useRef } from 'react'
import { useRefreshUserPermissions } from './useRefreshUserPermissions'
import { useAuthContext } from '@/context'
import { logger } from '@/services/logger'

const PERMISSION_CHECK_INTERVAL = 5 * 60 * 1000 // 5 minutes

export function usePeriodicPermissionCheck() {
    const { refreshUserPermissions } = useRefreshUserPermissions()
    const { user } = useAuthContext()
    const intervalRef = useRef<NodeJS.Timeout | null>(null)

    useEffect(() => {
        // Only check if user is authenticated
        if (!user) return

        const runCheck = async () => {
            try {
                logger.debug('🔄 Running periodic permission check...')
                await refreshUserPermissions()
            } catch (error) {
                logger.debug('Permission check failed (non-critical)', {
                    error: error instanceof Error ? error.message : String(error),
                })
            }
        }

        // Set up interval - check every 5 minutes
        intervalRef.current = setInterval(runCheck, PERMISSION_CHECK_INTERVAL)

        return () => {
            if (intervalRef.current) {
                clearInterval(intervalRef.current)
            }
        }
    }, [user, refreshUserPermissions])
}
