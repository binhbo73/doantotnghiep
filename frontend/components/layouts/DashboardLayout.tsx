'use client'

import React, { useEffect } from 'react'
import { Sidebar } from './Sidebar'
import { useLogout } from '@/hooks/useLogout'
import { useTokenRefresh } from '@/hooks/useTokenRefresh'
import { usePermissionRefreshHandler } from '@/hooks/usePermissionRefreshHandler'
import { usePeriodicPermissionCheck } from '@/hooks/usePeriodicPermissionCheck'
import { useCacheInvalidationOnAuthChange } from '@/hooks/useCacheInvalidationOnAuthChange'
import { useRefreshUserPermissions } from '@/hooks/useRefreshUserPermissions'
import { logger } from '@/services/logger'

interface DashboardLayoutProps {
    children: React.ReactNode
    onLogout?: () => void
}

export function DashboardLayout({
    children,
    onLogout,
}: DashboardLayoutProps) {
    const { logout } = useLogout()
    const { refreshUserPermissions } = useRefreshUserPermissions()

    // Activate proactive token refresh
    useTokenRefresh()

    // Activate permission refresh handler (listens for 403 errors or manual refresh events)
    usePermissionRefreshHandler()

    // Activate periodic permission check (every 5 minutes)
    usePeriodicPermissionCheck()

    // Activate cache invalidation when user changes (account switching)
    useCacheInvalidationOnAuthChange()

    // Listen for auth changes and refresh permissions
    useEffect(() => {
        const handleAuthChange = async () => {
            logger.info('👤 Account switched - refreshing user data...')
            try {
                await refreshUserPermissions()
                logger.info('✅ User data refreshed after account switch')
            } catch (error) {
                logger.error('Failed to refresh user after account switch', {
                    error: error instanceof Error ? error.message : String(error),
                })
            }
        }

        window.addEventListener('auth:user-changed', handleAuthChange)
        return () => window.removeEventListener('auth:user-changed', handleAuthChange)
    }, [refreshUserPermissions])

    const handleLogout = () => {
        logout()
    }

    const handleUpgrade = () => {
        console.log('Upgrade workspace')
    }

    return (
        <div className="flex h-screen overflow-hidden">
            {/* Sidebar */}
            <Sidebar
                onLogout={handleLogout}
                onUpgrade={handleUpgrade}
            />

            {/* Main Content */}
            <main
                className="flex-1 overflow-y-auto overflow-x-hidden"
                style={{
                    backgroundColor: '#f9f9ff',
                }}
            >
                {children}
            </main>
        </div>
    )
}
