'use client'

/**
 * Empty State Component
 * Displayed when there are no users to show
 */

import React from 'react'
import { Users } from 'lucide-react'

interface EmptyStateProps {
    title?: string
    description?: string
    onAction?: () => void
    actionLabel?: string
    icon?: React.ReactNode
}

export function EmptyState({
    title = 'Chưa có người dùng',
    description = 'Bắt đầu bằng cách thêm người dùng mới vào hệ thống.',
    onAction,
    actionLabel = 'Thêm người dùng',
    icon,
}: EmptyStateProps) {
    return (
        <div className="flex flex-col items-center justify-center py-12">
            <div
                className="w-16 h-16 rounded-full flex items-center justify-center mb-4"
                style={{ backgroundColor: '#e6eeff' }}
            >
                {icon || <Users size={32} style={{ color: '#0058be' }} />}
            </div>

            <h3 className="text-lg font-semibold mb-2" style={{ color: '#0d1c2e' }}>
                {title}
            </h3>

            <p className="text-sm text-center max-w-md mb-6" style={{ color: '#584237' }}>
                {description}
            </p>

            {onAction && (
                <button
                    onClick={onAction}
                    className="px-6 py-2 rounded-lg font-medium text-white transition-all hover:shadow-lg"
                    style={{
                        backgroundColor: '#9d4300',
                        backgroundImage: 'linear-gradient(to bottom, #9d4300, #783200)',
                    }}
                >
                    {actionLabel}
                </button>
            )}
        </div>
    )
}

export default EmptyState
