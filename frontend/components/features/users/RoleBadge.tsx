'use client'

/**
 * Role Badge Component
 * Displays user role with color coding
 */

import React from 'react'

interface RoleBadgeProps {
    role: string
    className?: string
}

const ROLE_COLORS: Record<string, { bg: string; text: string }> = {
    admin: { bg: '#fff3e0', text: '#e65100' },
    administrator: { bg: '#fff3e0', text: '#e65100' },
    manager: { bg: '#e3f2fd', text: '#1565c0' },
    supervisor: { bg: '#f3e5f5', text: '#6a1b9a' },
    employee: { bg: '#e8f5e9', text: '#2e7d32' },
    user: { bg: '#e8f5e9', text: '#2e7d32' },
    viewer: { bg: '#f5f5f5', text: '#424242' },
}

export function RoleBadge({ role, className = '' }: RoleBadgeProps) {
    const roleLower = role.toLowerCase()
    const colors = ROLE_COLORS[roleLower] || ROLE_COLORS.user

    return (
        <span
            className={`inline-block px-2.5 py-1 rounded-full text-xs font-medium ${className}`}
            style={{
                backgroundColor: colors.bg,
                color: colors.text,
            }}
        >
            {role}
        </span>
    )
}

export default RoleBadge
