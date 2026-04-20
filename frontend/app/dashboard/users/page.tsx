'use client'

/**
 * Users Management Page
 * Main page for managing users with full CRUD functionality
 */

import React, { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import {
    getAllUsers,
    getUserById,
    createUser,
    updateUser,
    deleteUser,
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
    Pagination,
    LoadingSkeleton,
    type FilterOptions,
    type CreateUserFormData,
} from '@/components/features/users'

export default function UsersPage() {
    const router = useRouter()
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

    // Selection state
    const [selectedUsers, setSelectedUsers] = useState<Set<string>>(new Set())

    /**
     * Fetch users from API
     */
    const fetchUsers = useCallback(async () => {
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
            console.error('❌ Error fetching users:', err)
        } finally {
            setLoading(false)
        }
    }, [currentPage, pageSize, filters])

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

            if (editingUser) {
                // Update existing user
                const updatePayload: UpdateUserPayload = {
                    email: data.email,
                    first_name: data.first_name,
                    last_name: data.last_name,
                    department_id: data.department_id,
                    role_id: data.role_id,
                }
                await updateUser(editingUser.id, updatePayload)
                setSuccess('Người dùng đã được cập nhật thành công')
            } else {
                // Create new user
                const payload: CreateUserPayload = {
                    username: data.username,
                    email: data.email,
                    first_name: data.first_name,
                    last_name: data.last_name,
                    department_id: data.department_id,
                    role_id: data.role_id,
                    password: data.password,
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
            console.error('❌ Error saving user:', err)
        } finally {
            setModalLoading(false)
        }
    }

    /**
     * Handle user deletion
     */
    const handleDeleteUser = async (user: User) => {
        if (!confirm(`Bạn có chắc chắn muốn xóa người dùng ${user.full_name}?`)) {
            return
        }

        try {
            setLoading(true)
            await deleteUser(user.id)
            setSuccess('Người dùng đã được xóa thành công')
            setCurrentPage(1)
            fetchUsers()

            setTimeout(() => setSuccess(null), 3000)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to delete user'
            setError(message)
            console.error('❌ Error deleting user:', err)
        } finally {
            setLoading(false)
        }
    }

    /**
     * Handle opening edit modal
     */
    const handleEditUser = (user: User) => {
        setEditingUser(user)
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

    return (
        <main
            className="min-h-screen p-6"
            style={{ backgroundColor: '#f9f9ff' }}
        >
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <PageHeader
                    title="👥 Quản lý người dùng"
                    description="Quản lý tài khoản người dùng, phân quyền và cấu hình hệ thống"
                    onAddNew={handleAddUser}
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
                            onAddUser={handleAddUser}
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
                    editingUser={editingUser}
                    loading={modalLoading}
                />
            </div>
        </main>
    )
}
