'use client'

/**
 * User Table Component
 * Displays users in a table format with sorting and selection
 */

import React from 'react'
import { User } from '@/services/users'
import UserTableHeader from './UserTableHeader'
import UserTableRow from './UserTableRow'
import EmptyState from './EmptyState'

interface UserTableProps {
    users: User[]
    loading?: boolean
    onView?: (user: User) => void
    onEdit?: (user: User) => void
    onDelete?: (user: User) => void
    onResetPassword?: (user: User) => void
    onAddUser?: () => void
    selectedUsers?: Set<string>
    onSelectUser?: (userId: string, selected: boolean) => void
    sortBy?: string
    sortOrder?: 'asc' | 'desc'
    onSort?: (columnId: string) => void
}

const TABLE_COLUMNS = [
    { id: 'checkbox', label: '', sortable: false, width: '48px' },
    { id: 'user', label: 'Người dùng', sortable: false, width: 'flex-1' },
    { id: 'email', label: 'Email', sortable: false, width: '200px' },
    { id: 'department', label: 'Phòng ban', sortable: false, width: '150px' },
    { id: 'role', label: 'Vai trò', sortable: false, width: '130px' },
    { id: 'status', label: 'Trạng thái', sortable: false, width: '120px' },
    { id: 'lastLogin', label: 'Lần đăng nhập', sortable: false, width: '140px' },
    { id: 'actions', label: '', sortable: false, width: '50px' },
]

export function UserTable({
    users,
    loading = false,
    onView,
    onEdit,
    onDelete,
    onResetPassword,
    onAddUser,
    selectedUsers = new Set(),
    onSelectUser,
    sortBy,
    sortOrder = 'asc',
    onSort,
}: UserTableProps) {
    if (!loading && users.length === 0) {
        return <EmptyState onAction={onAddUser} />
    }

    return (
        <div
            className="rounded-lg overflow-hidden border"
            style={{
                backgroundColor: '#ffffff',
                borderColor: '#dce2f3',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)',
            }}
        >
            <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                    <UserTableHeader
                        columns={TABLE_COLUMNS}
                        onSort={onSort}
                        sortBy={sortBy}
                        sortOrder={sortOrder}
                    />

                    <tbody>
                        {users.map((user) => (
                            <UserTableRow
                                key={user.id}
                                user={user}
                                onView={onView}
                                onEdit={onEdit}
                                onDelete={onDelete}
                                onResetPassword={onResetPassword}
                                isSelected={selectedUsers.has(user.id)}
                                onSelect={onSelectUser}
                            />
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    )
}

export default UserTable
