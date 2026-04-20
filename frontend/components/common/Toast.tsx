'use client'

import React, { useEffect } from 'react'

interface ToastProps {
    message: string
    type: 'success' | 'error' | 'info'
    duration?: number
    onClose: () => void
}

export function Toast({ message, type, duration = 3000, onClose }: ToastProps) {
    useEffect(() => {
        const timer = setTimeout(onClose, duration)
        return () => clearTimeout(timer)
    }, [duration, onClose])

    const getStyles = () => {
        switch (type) {
            case 'success':
                return {
                    bg: '#10b981',
                    icon: '✓',
                    light: '#d1fae5',
                }
            case 'error':
                return {
                    bg: '#ef4444',
                    icon: '✕',
                    light: '#fee2e2',
                }
            case 'info':
            default:
                return {
                    bg: '#3b82f6',
                    icon: 'ⓘ',
                    light: '#dbeafe',
                }
        }
    }

    const styles = getStyles()

    return (
        <div
            className="fixed top-4 right-4 z-[1000] animate-in fade-in slide-in-from-right-4 duration-300"
            style={{
                animation: 'slideIn 0.3s ease-out',
            }}
        >
            <style>{`
                @keyframes slideIn {
                    from {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
                @keyframes slideOut {
                    from {
                        transform: translateX(0);
                        opacity: 1;
                    }
                    to {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                }
            `}</style>
            <div
                className="flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg border"
                style={{
                    backgroundColor: styles.light,
                    borderColor: styles.bg,
                    borderWidth: '2px',
                }}
            >
                <span
                    className="font-bold text-lg"
                    style={{
                        color: styles.bg,
                    }}
                >
                    {styles.icon}
                </span>
                <span
                    className="text-sm font-medium"
                    style={{
                        color: styles.bg,
                    }}
                >
                    {message}
                </span>
                <button
                    onClick={onClose}
                    className="ml-2 text-lg font-bold opacity-60 hover:opacity-100 transition"
                    style={{
                        color: styles.bg,
                    }}
                >
                    ✕
                </button>
            </div>
        </div>
    )
}

/**
 * Toast container to manage multiple toasts
 */
interface ToastItem {
    id: string
    message: string
    type: 'success' | 'error' | 'info'
}

interface ToastContainerProps {
    toasts: ToastItem[]
    onRemove: (id: string) => void
}

export function ToastContainer({ toasts, onRemove }: ToastContainerProps) {
    return (
        <div className="fixed top-4 right-4 z-[1000] space-y-2">
            {toasts.map((toast) => (
                <Toast
                    key={toast.id}
                    message={toast.message}
                    type={toast.type}
                    onClose={() => onRemove(toast.id)}
                />
            ))}
        </div>
    )
}
