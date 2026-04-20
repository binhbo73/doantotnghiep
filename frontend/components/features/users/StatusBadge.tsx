'use client'

/**
 * Status Badge Component
 * Displays user status with appropriate styling
 */

import React from 'react'
import { Check, X, AlertCircle } from 'lucide-react'

interface StatusBadgeProps {
    isActive?: boolean
    status?: 'active' | 'blocked' | 'inactive'
    className?: string
}

export function StatusBadge({ isActive = true, status, className = '' }: StatusBadgeProps) {
    // Determine status based on status param or isActive param
    const activeStatus = status ? status === 'active' : isActive
    const isBlocked = status === 'blocked'

    return (
        <div
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${className}`}
            style={{
                backgroundColor: isBlocked
                    ? '#fce4ec'
                    : activeStatus
                        ? '#e8f5e9'
                        : '#ffebee',
                color: isBlocked
                    ? '#c2185b'
                    : activeStatus
                        ? '#2e7d32'
                        : '#c62828',
            }}
        >
            {isBlocked ? (
                <>
                    <AlertCircle size={14} />
                    <span>Bị chặn</span>
                </>
            ) : activeStatus ? (
                <>
                    <Check size={14} />
                    <span>Hoạt động</span>
                </>
            ) : (
                <>
                    <X size={14} />
                    <span>Không hoạt động</span>
                </>
            )}
        </div>
    )
}

export default StatusBadge
