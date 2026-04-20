'use client'

import { useState, useCallback } from 'react'

interface Toast {
    id: string
    message: string
    type: 'success' | 'error' | 'info'
}

export function useToast() {
    const [toasts, setToasts] = useState<Toast[]>([])

    const showToast = useCallback(
        (message: string, type: 'success' | 'error' | 'info' = 'info', duration = 3000) => {
            const id = `toast-${Date.now()}-${Math.random()}`
            setToasts((prev) => [...prev, { id, message, type }])

            // Auto remove after duration
            setTimeout(() => {
                setToasts((prev) => prev.filter((t) => t.id !== id))
            }, duration)

            return id
        },
        []
    )

    const removeToast = useCallback((id: string) => {
        setToasts((prev) => prev.filter((t) => t.id !== id))
    }, [])

    const showSuccess = useCallback(
        (message: string) => showToast(message, 'success', 3000),
        [showToast]
    )

    const showError = useCallback(
        (message: string) => showToast(message, 'error', 4000),
        [showToast]
    )

    const showInfo = useCallback(
        (message: string) => showToast(message, 'info', 3000),
        [showToast]
    )

    return {
        toasts,
        showToast,
        removeToast,
        showSuccess,
        showError,
        showInfo,
    }
}
