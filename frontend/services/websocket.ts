'use client'

/**
 * WebSocket Service - Real-time permission updates
 * Maintains connection to backend for instant permission change notifications
 */

import { logger } from './logger'
import { getAuthToken } from '@/services/auth'

interface WebSocketMessage {
    type: 'permission_changed' | 'role_changed' | 'department_changed' | 'heartbeat'
    userId?: string
    timestamp?: string
    data?: Record<string, any>
}

class WebSocketService {
    private ws: WebSocket | null = null
    private url: string
    private reconnectAttempts = 0
    private maxReconnectAttempts = 5
    private reconnectDelay = 3000 // 3 seconds
    private heartbeatInterval: NodeJS.Timeout | null = null
    private listeners: Map<string, Set<(data: any) => void>> = new Map()
    private isIntentionallyClosed = false

    constructor() {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || ''
        try {
            const parsedUrl = new URL(apiUrl)
            const protocol = parsedUrl.protocol === 'https:' ? 'wss:' : 'ws:'
            this.url = `${protocol}//${parsedUrl.host}/ws/permissions/`
        } catch {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
            const host = apiUrl.replace(/^https?:\/\//, '').replace(/\/.*$/, '') || 'localhost:8000'
            this.url = `${protocol}//${host}/ws/permissions/`
        }
    }

    /**
     * Connect to WebSocket server
     * Graceful fallback if backend doesn't have WebSocket endpoint
     */
    connect(token?: string) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            logger.debug('✅ WebSocket already connected')
            return
        }

        const authToken = token || getAuthToken()

        // Skip if token is missing
        if (!authToken) {
            logger.warn('⚠️ No auth token available, skipping WebSocket connection')
            return
        }

        try {
            logger.debug('🔌 Attempting WebSocket connection...', { url: this.url })
            this.ws = new WebSocket(`${this.url}?token=${encodeURIComponent(authToken)}`)

            this.ws.onopen = () => this.handleOpen()
            this.ws.onmessage = (event) => this.handleMessage(event)
            this.ws.onerror = (error) => this.handleError(error)
            this.ws.onclose = (event) => this.handleClose(event)
        } catch (error) {
            logger.debug('⚠️ WebSocket connection failed (non-critical)', {
                error: error instanceof Error ? error.message : String(error),
                url: this.url
            })
            // Don't attempt reconnect - it's expected to fail if backend not setup
            this.isIntentionallyClosed = true
        }
    }

    /**
     * Disconnect WebSocket
     */
    disconnect() {
        logger.info('🔌 Disconnecting WebSocket')
        this.isIntentionallyClosed = true
        this.clearHeartbeat()

        if (this.ws) {
            this.ws.close()
            this.ws = null
        }
    }

    /**
     * Handle WebSocket open
     */
    private handleOpen() {
        logger.info('✅ WebSocket connected')
        this.reconnectAttempts = 0
        this.isIntentionallyClosed = false
        this.startHeartbeat()

        // Notify listeners
        this.emit('connected', {})
    }

    /**
     * Handle WebSocket message
     */
    private handleMessage(event: MessageEvent) {
        try {
            const message: WebSocketMessage = JSON.parse(event.data)

            switch (message.type) {
                case 'permission_changed':
                    logger.info('🔄 Permission changed', message.data)
                    this.emit('permission_changed', message.data)
                    // Dispatch event for hooks to listen
                    window.dispatchEvent(new CustomEvent('permission:refresh-needed', { detail: message.data }))
                    break

                case 'role_changed':
                    logger.info('🔄 Role changed', message.data)
                    this.emit('role_changed', message.data)
                    window.dispatchEvent(new CustomEvent('permission:refresh-needed', { detail: message.data }))
                    break

                case 'department_changed':
                    logger.info('🔄 Department changed', message.data)
                    this.emit('department_changed', message.data)
                    break

                case 'heartbeat':
                    // Silent heartbeat
                    break

                default:
                    logger.debug('📨 WebSocket message', message)
                    this.emit(message.type, message.data)
            }
        } catch (error) {
            logger.error('❌ Failed to parse WebSocket message', { error })
        }
    }

    /**
     * Handle WebSocket error
     */
    private handleError(error: Event) {
        logger.error('❌ WebSocket error', {
            type: error.type,
            message: (error as any)?.message || 'WebSocket error event',
            ...(error instanceof CloseEvent ? { code: error.code, reason: error.reason, wasClean: error.wasClean } : {}),
        })
    }

    /**
     * Handle WebSocket close
     */
    private handleClose(event?: CloseEvent) {
        logger.warn('⚠️ WebSocket disconnected', {
            code: event?.code,
            reason: event?.reason,
            wasClean: event?.wasClean,
        })
        this.clearHeartbeat()

        if (!this.isIntentionallyClosed) {
            this.attemptReconnect(this.getToken())
        }

        this.emit('disconnected', {})
    }

    /**
     * Attempt to reconnect
     */
    private attemptReconnect(token: string) {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            logger.error('❌ Max reconnect attempts reached')
            return
        }

        this.reconnectAttempts++
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
        logger.info(`🔄 Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`, { delay })

        setTimeout(() => {
            this.connect(token)
        }, delay)
    }

    /**
     * Start sending heartbeat to keep connection alive
     */
    private startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            if (this.ws?.readyState === WebSocket.OPEN) {
                try {
                    this.ws.send(JSON.stringify({ type: 'heartbeat' }))
                } catch (error) {
                    logger.debug('Heartbeat send failed', { error })
                }
            }
        }, 30000) // 30 seconds
    }

    /**
     * Clear heartbeat
     */
    private clearHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval)
            this.heartbeatInterval = null
        }
    }

    /**
     * Get auth token from localStorage
     */
    private getToken(): string {
        if (typeof window === 'undefined') return ''
        return getAuthToken() || ''
    }

    /**
     * Subscribe to event
     */
    on(event: string, callback: (data: any) => void) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set())
        }
        this.listeners.get(event)?.add(callback)

        return () => {
            this.listeners.get(event)?.delete(callback)
        }
    }

    /**
     * Emit event to listeners
     */
    private emit(event: string, data: any) {
        const callbacks = this.listeners.get(event)
        if (callbacks) {
            callbacks.forEach((callback) => {
                try {
                    callback(data)
                } catch (error) {
                    logger.error(`Error in ${event} listener`, { error })
                }
            })
        }
    }

    /**
     * Get connection status
     */
    isConnected(): boolean {
        return this.ws?.readyState === WebSocket.OPEN
    }
}

// Singleton instance
export const webSocketService = new WebSocketService()

export default WebSocketService
