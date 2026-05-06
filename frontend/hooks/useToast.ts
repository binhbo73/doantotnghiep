'use client'

import { useState, useCallback, useEffect } from 'react'
import { logger } from '@/services/logger'

interface ToastOptions {
    title?: string
    description?: string
    message?: string
    type?: 'success' | 'error' | 'info'
    variant?: 'default' | 'destructive'
    duration?: number
}

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

    const toast = useCallback((options: ToastOptions) => {
        const message = options.description || options.title || options.message || ''
        const type = options.variant === 'destructive' ? 'error' : (options.type || 'info')
        return showToast(message, type, options.duration)
    }, [showToast])

    // Real-time notifications listener
    useEffect(() => {
        const handlePermissionChanged = (event: CustomEvent) => {
            const data = event.detail
            logger.info('🔔 Real-time permission notification', data)
            showInfo(`Quyền của bạn đã được cập nhật`)
        }

        const handleRoleChanged = (event: CustomEvent) => {
            const data = event.detail
            logger.info('👤 Real-time role notification', data)
            showInfo(`Vai trò của bạn đã được thay đổi`)
        }

        const handleDepartmentChanged = (event: CustomEvent) => {
            const data = event.detail
            logger.info('🏢 Real-time department notification', data)
            showInfo(`Thông tin phòng ban đã được cập nhật`)
        }

        const handleDocumentShared = (event: CustomEvent) => {
            const data = event.detail
            logger.info('📄 Document shared notification', data)
            showInfo(`Tài liệu "${data.documentName || 'mới'}" đã được chia sẻ với bạn`)
        }

        const handleUploadComplete = (event: CustomEvent) => {
            const data = event.detail
            logger.info('✅ Upload complete notification', data)
            showSuccess(`Tải lên "${data.fileName}" thành công`)
        }

        const handleUploadFailed = (event: CustomEvent) => {
            const data = event.detail
            logger.error('❌ Upload failed notification', data)
            showError(`Tải lên "${data.fileName}" thất bại: ${data.error || 'Lỗi không xác định'}`)
        }

        // Add event listeners
        window.addEventListener('permission:refresh-needed', handlePermissionChanged)
        window.addEventListener('role:refresh-needed', handleRoleChanged)
        window.addEventListener('department:refresh-needed', handleDepartmentChanged)
        window.addEventListener('document:shared', handleDocumentShared)
        window.addEventListener('upload:complete', handleUploadComplete)
        window.addEventListener('upload:failed', handleUploadFailed)

        // Cleanup
        return () => {
            window.removeEventListener('permission:refresh-needed', handlePermissionChanged)
            window.removeEventListener('role:refresh-needed', handleRoleChanged)
            window.removeEventListener('department:refresh-needed', handleDepartmentChanged)
            window.removeEventListener('document:shared', handleDocumentShared)
            window.removeEventListener('upload:complete', handleUploadComplete)
            window.removeEventListener('upload:failed', handleUploadFailed)
        }
    }, [showInfo, showSuccess, showError])

    return {
        toasts,
        toast,
        showToast,
        removeToast,
        showSuccess,
        showError,
        showInfo,
    }
}
