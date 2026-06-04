'use client'

/**
 * Periodically refreshes current-user permissions and also refreshes when
 * the dashboard tab becomes active again.
 */

import { useEffect, useRef } from 'react'
import { useRefreshUserPermissions } from './useRefreshUserPermissions'
import { useAuthContext } from '@/context'
import { logger } from '@/services/logger'

const PERMISSION_CHECK_INTERVAL = 5 * 60 * 1000
const PERMISSION_FOCUS_REFRESH_THROTTLE = 30 * 1000

export function usePeriodicPermissionCheck() {
    const { refreshUserPermissions } = useRefreshUserPermissions()
    const { user } = useAuthContext()
    const intervalRef = useRef<NodeJS.Timeout | null>(null)
    const lastCheckRef = useRef(0)
    const refreshRef = useRef(refreshUserPermissions)

    useEffect(() => {
        refreshRef.current = refreshUserPermissions
    }, [refreshUserPermissions])

    useEffect(() => {
        if (!user?.id) return

        const runCheck = async (force = false) => {
            const now = Date.now()
            if (!force && now - lastCheckRef.current < PERMISSION_FOCUS_REFRESH_THROTTLE) {
                return
            }
            lastCheckRef.current = now

            try {
                logger.debug('Running permission refresh check')
                await refreshRef.current()
            } catch (error) {
                logger.debug('Permission refresh check failed', {
                    error: error instanceof Error ? error.message : String(error),
                })
            }
        }

        void runCheck(true)

        intervalRef.current = setInterval(() => {
            void runCheck(true)
        }, PERMISSION_CHECK_INTERVAL)

        const handleFocus = () => {
            void runCheck()
        }

        const handleVisibilityChange = () => {
            if (document.visibilityState === 'visible') {
                void runCheck()
            }
        }

        window.addEventListener('focus', handleFocus)
        document.addEventListener('visibilitychange', handleVisibilityChange)

        return () => {
            if (intervalRef.current) {
                clearInterval(intervalRef.current)
            }
            window.removeEventListener('focus', handleFocus)
            document.removeEventListener('visibilitychange', handleVisibilityChange)
        }
    }, [user?.id])
}
