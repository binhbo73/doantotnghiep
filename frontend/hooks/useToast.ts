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

        const onPermissionChanged = handlePermissionChanged as EventListener
        const onRoleChanged = handleRoleChanged as EventListener
        const onDepartmentChanged = handleDepartmentChanged as EventListener
        const onDocumentShared = handleDocumentShared as EventListener
        const onUploadComplete = handleUploadComplete as EventListener
        const onUploadFailed = handleUploadFailed as EventListener

        // Add event listeners
        window.addEventListener('permission:refresh-needed', onPermissionChanged)
        window.addEventListener('role:refresh-needed', onRoleChanged)
        window.addEventListener('department:refresh-needed', onDepartmentChanged)
        window.addEventListener('document:shared', onDocumentShared)
        window.addEventListener('upload:complete', onUploadComplete)
        window.addEventListener('upload:failed', onUploadFailed)

        // Cleanup
        return () => {
            window.removeEventListener('permission:refresh-needed', onPermissionChanged)
            window.removeEventListener('role:refresh-needed', onRoleChanged)
            window.removeEventListener('department:refresh-needed', onDepartmentChanged)
            window.removeEventListener('document:shared', onDocumentShared)
            window.removeEventListener('upload:complete', onUploadComplete)
            window.removeEventListener('upload:failed', onUploadFailed)
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
