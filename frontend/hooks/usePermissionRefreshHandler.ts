'use client'

/**
 * usePermissionRefreshHandler Hook
 * Listens for 'permission:refresh-needed' event and refreshes user permissions
 * Called from DashboardLayout to handle permission changes during session
 */

import { useEffect } from 'react'
import { useRefreshUserPermissions } from './useRefreshUserPermissions'
import { logger } from '@/services/logger'

export function usePermissionRefreshHandler() {
    const { refreshUserPermissions } = useRefreshUserPermissions()

    useEffect(() => {
        const handlePermissionRefresh = async () => {
            logger.info('📢 Permission refresh event received')
            try {
                await refreshUserPermissions()
            } catch (error) {
                logger.error('Failed to refresh permissions on event', {
                    error: error instanceof Error ? error.message : String(error),
                })
            }
        }

        // Listen for permission refresh events (triggered by 403 errors or manual triggers)
        window.addEventListener('permission:refresh-needed', handlePermissionRefresh)

        return () => {
            window.removeEventListener('permission:refresh-needed', handlePermissionRefresh)
        }
    }, [refreshUserPermissions])
}
