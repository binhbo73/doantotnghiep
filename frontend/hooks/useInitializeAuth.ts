'use client'

import { useEffect, useState } from 'react'
import { initializeToken } from '@/services/token'
import { logger } from '@/services/logger'

/**
 * Initialize authentication on app load
 * Sets up placeholder token for later real login
 */
export function useInitializeAuth() {
    const [isInitialized, setIsInitialized] = useState(false)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        try {
            logger.debug('Initializing auth on startup')
            initializeToken()
            logger.debug('Auth initialized successfully')
            setIsInitialized(true)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Unknown error'
            setError(message)
            logger.error('Auth initialization failed', err)
            setIsInitialized(true)
        }
    }, [])

    return { isInitialized, error }
}
