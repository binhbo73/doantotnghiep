'use client'

import React from 'react'
import { useRouter } from 'next/navigation'

interface AccessDeniedPageProps {
    title?: string
    message?: string
    icon?: string
    showBackButton?: boolean
    onGoBack?: () => void
}

/**
 * Standardized Access Denied UI Component
 * Used consistently across all RBAC-protected pages
 */
export function AccessDeniedPage({
    title = 'Truy cập bị hạn chế',
    message = 'Bạn không có quyền truy cập trang này. Vui lòng liên hệ quản trị viên nếu bạn cần được cấp quyền.',
    icon = '🔒',
    showBackButton = true,
    onGoBack,
}: AccessDeniedPageProps) {
    const router = useRouter()

    const handleGoBack = () => {
        if (onGoBack) {
            onGoBack()
        } else {
            router.push('/dashboard')
        }
    }

    return (
        <main
            className="min-h-screen flex items-center justify-center p-4"
            style={{ backgroundColor: '#f9f9ff' }}
        >
            <div className="text-center max-w-md">
                {/* Icon */}
                <div
                    className="w-20 h-20 rounded-2xl flex items-center justify-center mx-auto mb-6"
                    style={{ backgroundColor: '#fff3e0' }}
                >
                    <span className="text-5xl">{icon}</span>
                </div>

                {/* Title */}
                <h2
                    className="text-2xl font-bold mb-3"
                    style={{ color: '#151c27' }}
                >
                    {title}
                </h2>

                {/* Message */}
                <p
                    className="text-sm leading-relaxed mb-8"
                    style={{ color: '#727785' }}
                >
                    {message}
                </p>

                {/* Action Buttons */}
                <div className="flex gap-3 justify-center">
                    {showBackButton && (
                        <button
                            onClick={handleGoBack}
                            className="px-6 py-2.5 rounded-lg text-sm font-medium text-white transition-all hover:opacity-90 active:scale-95"
                            style={{ backgroundColor: '#0058be' }}
                        >
                            ← Về trang chính
                        </button>
                    )}
                    <button
                        onClick={() => router.push('/dashboard')}
                        className="px-6 py-2.5 rounded-lg text-sm font-medium transition-all hover:opacity-90 active:scale-95"
                        style={{
                            backgroundColor: '#f0f3ff',
                            color: '#0058be',
                            border: '1px solid #dce2f3',
                        }}
                    >
                        Dashboard
                    </button>
                </div>

                {/* Contact Support */}
                <div className="mt-8 pt-6 border-t" style={{ borderColor: '#dce2f3' }}>
                    <p
                        className="text-xs"
                        style={{ color: '#999' }}
                    >
                        Nếu bạn cho rằng đây là một lỗi, vui lòng liên hệ hỗ trợ
                    </p>
                </div>
            </div>
        </main>
    )
}

export default AccessDeniedPage
