'use client'

/**
 * useWebSocketPermissions Hook
 * Activates WebSocket connection for real-time permission updates
 * Call this in DashboardLayout to enable real-time permission sync
 */

import { useEffect, useRef } from 'react'
import { useAuthContext } from '@/context'
import { getAuthToken } from '@/services/auth'
import { webSocketService } from '@/services/websocket'
import { logger } from '@/services/logger'

export function useWebSocketPermissions() {
    const { user } = useAuthContext()
    const unsubscribeRef = useRef<(() => void) | null>(null)

    useEffect(() => {
        if (!user) return

        const token = getAuthToken()
        if (!token) {
            logger.warn('⚠️ WebSocket disabled because no auth token was found')
            return
        }

        // Connect to WebSocket for real-time permission updates
        try {
            logger.info('🔌 Activating WebSocket for real-time permission updates')
            webSocketService.connect(token)

            const unsubscribes: Array<() => void> = []

            unsubscribes.push(
                webSocketService.on('permission_changed', (data) => {
                    logger.info('🔄 Real-time permission update received', data)
                    window.dispatchEvent(new CustomEvent('permission:refresh-needed', { detail: data }))
                })
            )

            unsubscribes.push(
                webSocketService.on('role_changed', (data) => {
                    logger.info('👤 Real-time role update received', data)
                    window.dispatchEvent(new CustomEvent('role:refresh-needed', { detail: data }))
                })
            )

            unsubscribes.push(
                webSocketService.on('department_changed', (data) => {
                    logger.info('🏢 Real-time department update received', data)
                    window.dispatchEvent(new CustomEvent('department:refresh-needed', { detail: data }))
                })
            )

            unsubscribeRef.current = () => {
                unsubscribes.forEach((unsubscribe) => unsubscribe())
            }

        } catch (error) {
            logger.error('Failed to connect WebSocket', { error })
            logger.info('🔄 Falling back to polling-based updates')
        }

        return () => {
            if (unsubscribeRef.current) {
                unsubscribeRef.current()
                unsubscribeRef.current = null
            }
        }
    }, [user])

    return {
        isConnected: webSocketService.isConnected(),
        disconnect: () => webSocketService.disconnect(),
    }
}

export default useWebSocketPermissions
