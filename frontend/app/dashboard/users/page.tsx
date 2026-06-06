'use client'

/**
 * Users Management Page
 * RBAC: rendered from backend permission codes.
 */

import React, { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import {
    getAllUsers,
    getUserById,
    createUser,
    createUsersBulk,
    updateUser,
    deleteUser,
    resetUserPassword,
    User,
    CreateUserPayload,
    UpdateUserPayload,
    PaginatedResponse,
} from '@/services/users'
import {
    PageHeader,
    UserTable,
    FilterBar,
    CreateUserModal,
    ResetPasswordModal,
    Pagination,
    LoadingSkeleton,
    type FilterOptions,
    type CreateUserFormData,
    type CreateUsersBulkFormData,
} from '@/components/features/users'
import { useRBAC } from '@/hooks/useRBAC'
import { AccessDeniedPage } from '@/components/common/AccessDeniedPage'

export default function UsersPage() {
    const router = useRouter()
    const { hasPermission, hasAnyPermission } = useRBAC()
    const canReadUsers = hasPermission('user_read')
    const canCreateUser = hasPermission('user_create')
    const canUpdateUser = hasPermission('user_update')
    const canDeleteUsers = hasPermission('user_delete')
    const canChangeUserRole = hasPermission('user_change_role')
    const canResetPassword = hasPermission('user_reset_password')

    const [users, setUsers] = useState<User[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [success, setSuccess] = useState<string | null>(null)

    // Pagination state
    const [currentPage, setCurrentPage] = useState(1)
    const [pageSize, setPageSize] = useState(10)
    const [totalItems, setTotalItems] = useState(0)
    const [totalPages, setTotalPages] = useState(1)

    // Sorting state
    const [sortBy, setSortBy] = useState<string>('created_at')
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

    // Filter state
    const [filters, setFilters] = useState<FilterOptions>({})

    // Modal state
    const [isModalOpen, setIsModalOpen] = useState(false)
    const [editingUser, setEditingUser] = useState<User | null>(null)
    const [modalLoading, setModalLoading] = useState(false)
    const [isResetPasswordModalOpen, setIsResetPasswordModalOpen] = useState(false)
    const [resettingUser, setResettingUser] = useState<User | null>(null)

    // Selection state
    const [selectedUsers, setSelectedUsers] = useState<Set<string>>(new Set())

    /**
     * Fetch users from API
     */
    const fetchUsers = useCallback(async () => {
        if (!canReadUsers) {
            setLoading(false)
            return
        }

        try {
            setLoading(true)
            setError(null)

            const response = await getAllUsers(
                currentPage,
                pageSize,
                filters.search,
                filters.department,
                filters.role,
                filters.status === 'active'
                    ? true
                    : filters.status === 'inactive'
                        ? false
                        : undefined
            )

            setUsers(response.data || [])
            setTotalItems(response.pagination.total)
            setTotalPages(response.pagination.total_pages)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to fetch users'
            setError(message)
            console.error('Error fetching users:', err)
        } finally {
            setLoading(false)
        }
    }, [canReadUsers, currentPage, pageSize, filters])

    /**
     * Load users on mount and when dependencies change
     */
    useEffect(() => {
        fetchUsers()
    }, [fetchUsers])

    /**
     * Handle user creation/update
     */
    const handleUserSubmit = async (data: CreateUserFormData) => {
        try {
            setModalLoading(true)

            const canManageUser = (target: User | null | undefined) => {
                if (!target) return false
                return hasAnyPermission(['user_update', 'user_change_role'])
            }

            if (editingUser) {
                if (!canManageUser(editingUser)) {
                    throw new Error('Bạn không có quyền chỉnh sửa người dùng này')
                }
                // Update existing user
                const updatePayload: UpdateUserPayload = {
                    email: data.email,
                    first_name: data.first_name,
                    last_name: data.last_name,
                    full_name: `${data.first_name} ${data.last_name}`.trim(),
                    department_id: data.role_code === 'admin' ? null : data.department_id || null,
                    role_id: data.role_id,
                }
                // Filter out empty values
                const filteredPayload = Object.fromEntries(
                    Object.entries(updatePayload).filter(([key, value]) => value !== '' && (value !== null || key === 'department_id'))
                ) as UpdateUserPayload
                await updateUser(editingUser.id, filteredPayload)
                setSuccess('Người dùng đã được cập nhật thành công')
            } else {
                if (!canCreateUser) throw new Error('Bạn không có quyền tạo người dùng')
                // Create new user
                const payload: CreateUserPayload = {
                    username: data.username,
                    email: data.email,
                    first_name: data.first_name,
                    last_name: data.last_name,
                    department_id: data.department_id,
                    role_id: data.role_id,
                }
                await createUser(payload)
                setSuccess('Người dùng mới đã được tạo thành công')
            }

            setIsModalOpen(false)
            setEditingUser(null)
            setCurrentPage(1)
            fetchUsers()

            // Clear success message after 3 seconds
            setTimeout(() => setSuccess(null), 3000)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to save user'
            setError(message)
            console.error('Error saving user:', err)
        } finally {
            setModalLoading(false)
        }
    }

    const handleBulkUserSubmit = async (data: CreateUsersBulkFormData) => {
        if (!canCreateUser) throw new Error('Báº¡n khÃ´ng cÃ³ quyá»n táº¡o ngÆ°á»i dÃ¹ng')

        try {
            setModalLoading(true)
            const result = await createUsersBulk({
                accounts: data.accounts,
                department_id: data.role_code === 'admin' ? undefined : data.department_id || undefined,
                role_id: data.role_id || undefined,
                send_email: true,
            })

            const errorSuffix = result.error_count > 0 ? `, ${result.error_count} lỗi` : ''
            setSuccess(`Đã tạo ${result.created_count}/${result.requested_count} tài khoản${errorSuffix}`)

            if (result.error_count > 0) {
                const firstErrors = result.errors
                    .slice(0, 3)
                    .map((item) => `Dòng ${item.index + 1}: ${item.message}`)
                    .join('; ')
                setError(firstErrors)
            }

            setIsModalOpen(false)
            setEditingUser(null)
            setCurrentPage(1)
            fetchUsers()
            setTimeout(() => setSuccess(null), 3000)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to create users'
            setError(message)
            console.error('Error bulk creating users:', err)
            throw err
        } finally {
            setModalLoading(false)
        }
    }

    /**
     * Handle user deletion
     */
    const handleDeleteUser = async (targetUser: User) => {
        // Permission check before delete.
        if (!canDeleteUsers) {
            alert('Bạn không có quyền xóa người dùng này')
            return
        }

        if (!confirm(`Bạn có chắc chắn muốn xóa người dùng ${targetUser.full_name}?`)) {
            return
        }

        try {
            setLoading(true)
            await deleteUser(targetUser.account_id)
            setSuccess('Người dùng đã được xóa thành công')
            setCurrentPage(1)
            fetchUsers()

            setTimeout(() => setSuccess(null), 3000)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to delete user'
            setError(message)
            console.error('Error deleting user:', err)
        } finally {
            setLoading(false)
        }
    }

    /**
     * Handle opening edit modal
     */

    const handleOpenResetPassword = (user: User) => {
        if (!canResetPassword) {
            alert('Bạn không có quyền đặt lại mật khẩu')
            return
        }
        setResettingUser(user)
        setIsResetPasswordModalOpen(true)
    }

    const handleResetPasswordSubmit = async (newPassword: string, confirmPassword: string, sendEmail: boolean) => {
        if (!resettingUser) return
        try {
            setModalLoading(true)
            const res = await resetUserPassword(resettingUser.account_id, { new_password: newPassword, confirm_password: confirmPassword, send_email: sendEmail })
            setSuccess(res.note || 'Mật khẩu đã được đặt lại thành công')
            setIsResetPasswordModalOpen(false)
            setResettingUser(null)
            setTimeout(() => setSuccess(null), 3000)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to reset password'
            setError(message)
            throw err
        } finally {
            setModalLoading(false)
        }
    }

    const handleEditUser = (targetUser: User) => {
        if (!hasAnyPermission(['user_update', 'user_change_role'])) {
            alert('Bạn không có quyền chỉnh sửa người dùng này')
            return
        }
        setEditingUser(targetUser)
        setIsModalOpen(true)
    }

    /**
     * Handle viewing user details
     */
    const handleViewUser = (user: User) => {
        router.push(`/dashboard/users/${user.id}`)
    }

    /**
     * Handle adding new user
     */
    const handleAddUser = () => {
        setEditingUser(null)
        setIsModalOpen(true)
    }

    /**
     * Handle search
     */
    const handleSearch = (query: string) => {
        setFilters({ ...filters, search: query })
        setCurrentPage(1)
    }

    /**
     * Handle filter change
     */
    const handleFilterChange = (newFilters: FilterOptions) => {
        setFilters(newFilters)
        setCurrentPage(1)
    }

    /**
     * Handle sorting
     */
    const handleSort = (columnId: string) => {
        if (sortBy === columnId) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
        } else {
            setSortBy(columnId)
            setSortOrder('asc')
        }
    }

    /**
     * Handle user selection
     */
    const handleSelectUser = (userId: string, selected: boolean) => {
        const newSelected = new Set(selectedUsers)
        if (selected) {
            newSelected.add(userId)
        } else {
            newSelected.delete(userId)
        }
        setSelectedUsers(newSelected)
    }

    /**
     * RBAC Guard - requires user_read from backend.
     * Keep this after hooks/callbacks so React hook order stays stable while
     * auth state is hydrating.
     */
    if (!canReadUsers) {
        return (
            <AccessDeniedPage
                title="Truy cập bị hạn chế"
                message="Bạn cần quyền user_read để truy cập trang Quản lý người dùng. Vui lòng liên hệ quản trị viên hệ thống nếu bạn cần được cấp quyền."
                icon="🔒"
                showBackButton={true}
                onGoBack={() => router.push('/dashboard')}
            />
        )
    }

    return (
        <main
            className="min-h-screen p-2 lg:p-4"
            style={{ backgroundColor: '#f9f9ff' }}
        >
            <div className="w-full px-2 lg:px-4 mx-auto">
                {/* Header */}
                <PageHeader
                    title="Quản lý người dùng"
                    description="Quản lý tài khoản người dùng, phân quyền và cấu hình hệ thống"
                    onAddNew={canCreateUser ? handleAddUser : undefined}
                    actionLabel="Thêm người dùng mới"
                />

                {/* Error Message */}
                {error && (
                    <div
                        className="mb-6 p-4 rounded-lg"
                        style={{ backgroundColor: '#ffebee', color: '#c62828' }}
                    >
                        <p className="font-medium">{error}</p>
                        <button
                            onClick={() => setError(null)}
                            className="text-sm underline mt-2"
                        >
                            Đóng
                        </button>
                    </div>
                )}

                {/* Success Message */}
                {success && (
                    <div
                        className="mb-6 p-4 rounded-lg"
                        style={{ backgroundColor: '#e8f5e9', color: '#2e7d32' }}
                    >
                        <p className="font-medium">{success}</p>
                    </div>
                )}

                {/* Filters */}
                <div className="mb-6">
                    <FilterBar
                        onSearch={handleSearch}
                        onFilterChange={handleFilterChange}
                        showAdvanced={true}
                    />
                </div>

                {/* Table */}
                <div className="mb-6">
                    {loading ? (
                        <LoadingSkeleton rows={5} />
                    ) : (
                        <UserTable
                            users={users}
                            loading={loading}
                            onView={handleViewUser}
                            onEdit={handleEditUser}
                            onDelete={handleDeleteUser}
                            onResetPassword={handleOpenResetPassword}
                            onAddUser={canCreateUser ? handleAddUser : undefined}
                            canEdit={canUpdateUser || canChangeUserRole}
                            canDelete={canDeleteUsers}
                            canResetPassword={canResetPassword}
                            selectedUsers={selectedUsers}
                            onSelectUser={handleSelectUser}
                            sortBy={sortBy}
                            sortOrder={sortOrder}
                            onSort={handleSort}
                        />
                    )}
                </div>

                {/* Pagination */}
                {!loading && users.length > 0 && (
                    <Pagination
                        currentPage={currentPage}
                        totalPages={totalPages}
                        totalItems={totalItems}
                        pageSize={pageSize}
                        onPageChange={setCurrentPage}
                        onPageSizeChange={(newPageSize) => {
                            setPageSize(newPageSize)
                            setCurrentPage(1)
                        }}
                    />
                )}

                {/* Create/Edit User Modal */}
                <CreateUserModal
                    isOpen={isModalOpen}
                    onClose={() => {
                        setIsModalOpen(false)
                        setEditingUser(null)
                    }}
                    onSubmit={handleUserSubmit}
                    onBulkSubmit={handleBulkUserSubmit}
                    editingUser={editingUser}
                    loading={modalLoading}
                />

                <ResetPasswordModal
                    isOpen={isResetPasswordModalOpen}
                    onClose={() => {
                        setIsResetPasswordModalOpen(false)
                        setResettingUser(null)
                    }}
                    onSubmit={handleResetPasswordSubmit}
                    targetUser={resettingUser}
                    loading={modalLoading}
                />
            </div>
        </main>
    )
}
