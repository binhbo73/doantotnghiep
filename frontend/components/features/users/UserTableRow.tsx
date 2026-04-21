'use client'

/**
 * User Table Row Component
 * Displays a single user in the table
 */

import React from 'react'
import { User } from '@/services/users'
import UserAvatar from './UserAvatar'
import StatusBadge from './StatusBadge'
import RoleBadge from './RoleBadge'
import ActionMenu from './ActionMenu'

interface UserTableRowProps {
    user: User
    onView?: (user: User) => void
    onEdit?: (user: User) => void
    onDelete?: (user: User) => void
    onResetPassword?: (user: User) => void
    isSelected?: boolean
    onSelect?: (userId: string, selected: boolean) => void
}

export function UserTableRow({
    user,
    onView,
    onEdit,
    onDelete,
    onResetPassword,
    isSelected = false,
    onSelect,
}: UserTableRowProps) {
    // Extract initials from full_name or fallback to first two letters of full_name
    const getInitials = () => {
        if (!user.full_name) return 'U'
        const parts = user.full_name.split(' ')
        return parts
            .slice(0, 2)
            .map((p) => p.charAt(0))
            .join('')
            .toUpperCase()
    }

    return (
        <tr
            className="border-b hover:bg-gray-50 transition-colors cursor-pointer"
            style={{ borderColor: '#dce2f3' }}
            onClick={() => onView?.(user)}
        >
            {/* Checkbox */}
            <td className="px-3 py-2 w-12" onClick={(e) => e.stopPropagation()}>
                <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={(e) => onSelect?.(user.id, e.target.checked)}
                    className="w-4 h-4 rounded border-gray-300 cursor-pointer"
                    style={{ accentColor: '#9d4300' }}
                />
            </td>

            {/* User Info */}
            <td className="px-3 py-2">
                <div className="flex items-center gap-2">
                    <UserAvatar
                        src={user.avatar_url}
                        alt={user.full_name}
                        initials={getInitials()}
                        size="sm"
                    />
                    <div className="min-w-0">
                        <div className="font-medium text-sm truncate" style={{ color: '#0d1c2e' }}>
                            {user.full_name}
                        </div>
                        <div className="text-xs truncate" style={{ color: '#9d4300' }}>
                            @{user.username}
                        </div>
                    </div>
                </div>
            </td>

            {/* Email */}
            <td className="px-3 py-2">
                <div className="text-sm truncate" style={{ color: '#584237' }}>
                    {user.email}
                </div>
            </td>

            {/* Department */}
            <td className="px-3 py-2">
                <div className="text-sm" style={{ color: '#584237' }}>
                    {user.department_name || 'N/A'}
                </div>
            </td>

            {/* Role */}
            <td className="px-3 py-2">
                <div className="flex flex-wrap gap-1">
                    {user.roles && user.roles.length > 0 ? (
                        user.roles.map((role, idx) => (
                            <RoleBadge key={`${role.id}-${idx}`} role={role.name} />
                        ))
                    ) : (
                        <span className="text-sm" style={{ color: '#584237' }}>N/A</span>
                    )}
                </div>
            </td>

            {/* Status */}
            <td className="px-3 py-2">
                <StatusBadge status={user.status} />
            </td>

            {/* Last Login */}
            <td className="px-3 py-2">
                <div className="text-xs" style={{ color: '#584237' }}>
                    {user.last_login
                        ? new Date(user.last_login).toLocaleDateString('vi-VN')
                        : 'Chưa đăng nhập'}
                </div>
            </td>

            {/* Actions */}
            <td className="px-3 py-2 text-right" onClick={(e) => e.stopPropagation()}>
                <ActionMenu
                    onView={() => onView?.(user)}
                    onEdit={() => onEdit?.(user)}
                    onDelete={() => onDelete?.(user)}
                    onResetPassword={() => onResetPassword?.(user)}
                />
            </td>
        </tr>
    )
}

export default UserTableRow
