'use client'

/**
 * User Detail Page
 * Shows detailed information about a single user
 */

import React, { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, Mail, Calendar, Building, Badge, Trash2, Edit, Clock } from 'lucide-react'
import { getUserById, deleteUser, updateUser, User, UpdateUserPayload } from '@/services/users'
import { UserAvatar, StatusBadge, RoleBadge, CreateUserModal, type CreateUserFormData } from '@/components/features/users'

export default function UserDetailPage() {
    const params = useParams()
    const router = useRouter()
    const userId = params.id as string

    const [user, setUser] = useState<User | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [isDeleting, setIsDeleting] = useState(false)
    const [isEditModalOpen, setIsEditModalOpen] = useState(false)
    const [isEditLoading, setIsEditLoading] = useState(false)

    /**
     * Fetch user details
     */
    useEffect(() => {
        const fetchUser = async () => {
            try {
                setLoading(true)
                setError(null)
                const userData = await getUserById(userId)
                setUser(userData)
            } catch (err) {
                const message = err instanceof Error ? err.message : 'Failed to fetch user'
                setError(message)
                console.error('❌ Error fetching user:', err)
            } finally {
                setLoading(false)
            }
        }

        fetchUser()
    }, [userId])

    /**
     * Handle user deletion
     */
    const handleDelete = async () => {
        if (!confirm('Bạn có chắc chắn muốn xóa người dùng này?')) {
            return
        }

        try {
            setIsDeleting(true)
            await deleteUser(userId)
            router.push('/dashboard/users')
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to delete user'
            setError(message)
            console.error('❌ Error deleting user:', err)
        } finally {
            setIsDeleting(false)
        }
    }

    /**
     * Handle user edit
     */
    const handleEditSubmit = async (data: CreateUserFormData) => {
        try {
            setIsEditLoading(true)
            const updatePayload: UpdateUserPayload = {
                email: data.email,
                first_name: data.first_name,
                last_name: data.last_name,
                department_id: data.department_id,
                role_id: data.role_id,
            }
            await updateUser(userId, updatePayload)
            setIsEditModalOpen(false)
            // Refresh user data
            const updatedUser = await getUserById(userId)
            setUser(updatedUser)
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to update user'
            setError(message)
            console.error('❌ Error updating user:', err)
        } finally {
            setIsEditLoading(false)
        }
    }

    if (loading) {
        return (
            <main className="min-h-screen p-6" style={{ backgroundColor: '#f9f9ff' }}>
                <div className="max-w-4xl mx-auto">
                    <div className="h-12 bg-gray-200 rounded mb-4 animate-pulse" />
                    <div className="h-96 bg-gray-200 rounded animate-pulse" />
                </div>
            </main>
        )
    }

    if (error || !user) {
        return (
            <main className="min-h-screen p-6" style={{ backgroundColor: '#f9f9ff' }}>
                <div className="max-w-4xl mx-auto">
                    <button
                        onClick={() => router.back()}
                        className="flex items-center gap-2 text-blue-600 hover:text-blue-700 mb-6"
                    >
                        <ArrowLeft size={20} />
                        <span>Quay lại</span>
                    </button>

                    <div
                        className="p-6 rounded-lg"
                        style={{ backgroundColor: '#ffebee', color: '#c62828' }}
                    >
                        <h2 className="font-semibold mb-2">Lỗi</h2>
                        <p>{error || 'Không tìm thấy người dùng'}</p>
                    </div>
                </div>
            </main>
        )
    }

    const getInitials = () => {
        if (!user.full_name) return 'U'
        const parts = user.full_name.split(' ')
        return parts
            .slice(0, 2)
            .map((p) => p.charAt(0))
            .join('')
            .toUpperCase()
    }

    const getAllRoleNames = () => {
        if (!user.roles || user.roles.length === 0) return []
        return user.roles.map(r => r.name)
    }

    const getAllPermissions = () => {
        if (!user.roles || user.roles.length === 0) return []
        const permissionsSet = new Set<string>()
        user.roles.forEach(role => {
            if (role.permissions && Array.isArray(role.permissions)) {
                role.permissions.forEach(perm => permissionsSet.add(perm))
            }
        })
        return Array.from(permissionsSet).sort()
    }

    return (
        <main className="min-h-screen p-6" style={{ backgroundColor: '#f9f9ff' }}>
            <div className="max-w-4xl mx-auto">
                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                    <button
                        onClick={() => router.back()}
                        className="flex items-center gap-2 font-medium transition-colors hover:opacity-70"
                        style={{ color: '#9d4300' }}
                    >
                        <ArrowLeft size={20} />
                        <span>Quay lại</span>
                    </button>

                    <button
                        onClick={handleDelete}
                        disabled={isDeleting}
                        className="flex items-center gap-2 px-4 py-2 rounded-lg text-white font-medium transition-all hover:shadow-lg disabled:opacity-50"
                        style={{
                            backgroundColor: '#ba1a1a',
                        }}
                    >
                        <Trash2 size={18} />
                        <span>{isDeleting ? 'Đang xóa...' : 'Xóa người dùng'}</span>
                    </button>
                </div>

                {/* Main Card */}
                <div
                    className="rounded-lg overflow-hidden shadow-lg"
                    style={{ backgroundColor: '#ffffff' }}
                >
                    {/* Profile Header */}
                    <div
                        className="p-8 flex items-center gap-6"
                        style={{ backgroundColor: '#eff4ff' }}
                    >
                        <UserAvatar
                            src={user.avatar_url}
                            alt={user.full_name}
                            initials={getInitials()}
                            size="lg"
                        />

                        <div className="flex-1">
                            <h1 className="text-3xl font-bold mb-2" style={{ color: '#0d1c2e' }}>
                                {user.full_name}
                            </h1>
                            <p className="text-sm mb-3" style={{ color: '#584237' }}>
                                @{user.username}
                            </p>
                            <div className="flex items-center flex-wrap gap-2">
                                <StatusBadge status={user.status} />
                                {user.roles?.map((role) => (
                                    <RoleBadge key={role.id} role={role.name} />
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Details Grid */}
                    <div className="p-8 grid grid-cols-1 md:grid-cols-2 gap-8">
                        {/* Left Column */}
                        <div className="space-y-6">
                            {/* Email */}
                            <div>
                                <label
                                    className="flex items-center gap-2 text-sm font-semibold mb-2"
                                    style={{ color: '#584237' }}
                                >
                                    <Mail size={16} />
                                    Email
                                </label>
                                <p
                                    className="text-base"
                                    style={{ color: '#0d1c2e' }}
                                >
                                    {user.email}
                                </p>
                            </div>

                            {/* Department */}
                            <div>
                                <label
                                    className="flex items-center gap-2 text-sm font-semibold mb-2"
                                    style={{ color: '#584237' }}
                                >
                                    <Building size={16} />
                                    Phòng ban
                                </label>
                                <p
                                    className="text-base"
                                    style={{ color: '#0d1c2e' }}
                                >
                                    {user.department_name || 'N/A'}
                                </p>
                            </div>

                            {/* All Roles */}
                            <div>
                                <label
                                    className="flex items-center gap-2 text-sm font-semibold mb-2"
                                    style={{ color: '#584237' }}
                                >
                                    <Badge size={16} />
                                    Vai trò ({user.roles?.length || 0})
                                </label>
                                <div className="flex flex-wrap gap-2">
                                    {getAllRoleNames().length > 0 ? (
                                        user.roles?.map((role) => (
                                            <span
                                                key={role.id}
                                                className="px-3 py-1 rounded-full text-sm font-medium"
                                                style={{
                                                    backgroundColor: '#e8f5e9',
                                                    color: '#2e7d32',
                                                }}
                                            >
                                                {role.name}
                                            </span>
                                        ))
                                    ) : (
                                        <p
                                            className="text-base"
                                            style={{ color: '#0d1c2e' }}
                                        >
                                            N/A
                                        </p>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Right Column */}
                        <div className="space-y-6">
                            {/* Created Date */}
                            <div>
                                <label
                                    className="flex items-center gap-2 text-sm font-semibold mb-2"
                                    style={{ color: '#584237' }}
                                >
                                    <Calendar size={16} />
                                    Ngày tạo
                                </label>
                                <p
                                    className="text-base"
                                    style={{ color: '#0d1c2e' }}
                                >
                                    {new Date(user.created_at).toLocaleDateString('vi-VN')}
                                </p>
                            </div>

                            {/* Last Updated */}
                            <div>
                                <label
                                    className="flex items-center gap-2 text-sm font-semibold mb-2"
                                    style={{ color: '#584237' }}
                                >
                                    <Calendar size={16} />
                                    Cập nhật lần cuối
                                </label>
                                <p
                                    className="text-base"
                                    style={{ color: '#0d1c2e' }}
                                >
                                    {new Date(user.updated_at).toLocaleDateString('vi-VN')}
                                </p>
                            </div>

                            {/* Last Login */}
                            <div>
                                <label
                                    className="flex items-center gap-2 text-sm font-semibold mb-2"
                                    style={{ color: '#584237' }}
                                >
                                    <Clock size={16} />
                                    Lần đăng nhập cuối
                                </label>
                                <p
                                    className="text-base"
                                    style={{ color: '#0d1c2e' }}
                                >
                                    {user.last_login
                                        ? new Date(user.last_login).toLocaleDateString('vi-VN')
                                        : 'Chưa đăng nhập'}
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Permissions Section */}
                    {user.roles && user.roles.length > 0 && (
                        <div className="p-8 border-t" style={{ borderColor: '#dce2f3' }}>
                            <h3 className="text-lg font-semibold mb-6" style={{ color: '#0d1c2e' }}>
                                Quyền hạn ({getAllPermissions().length} quyền)
                            </h3>

                            {/* Permissions by Role */}
                            <div className="space-y-4">
                                {user.roles.map((role) => (
                                    <div key={role.id} className="p-3 rounded-lg" style={{ backgroundColor: '#f5f5f5' }}>
                                        <p className="text-sm font-semibold mb-3" style={{ color: '#0d1c2e' }}>
                                            📌 {role.name} ({role.permissions?.length || 0} quyền)
                                        </p>
                                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                                            {role.permissions && role.permissions.length > 0 ? (
                                                role.permissions.map((permission) => (
                                                    <span
                                                        key={permission}
                                                        className="text-xs px-2 py-1 rounded"
                                                        style={{
                                                            backgroundColor: '#e6eeff',
                                                            color: '#0058be',
                                                        }}
                                                        title={permission}
                                                    >
                                                        {permission.replace(/_/g, ' ')}
                                                    </span>
                                                ))
                                            ) : (
                                                <p className="text-xs text-gray-500">Không có quyền</p>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* Edit Button */}
                <div className="mt-6 flex justify-center">
                    <button
                        onClick={() => setIsEditModalOpen(true)}
                        className="flex items-center gap-2 px-8 py-3 rounded-lg text-white font-medium transition-all hover:shadow-lg"
                        style={{
                            backgroundColor: '#9d4300',
                            backgroundImage: 'linear-gradient(to bottom, #9d4300, #783200)',
                        }}
                    >
                        <Edit size={18} />
                        <span>Chỉnh sửa thông tin</span>
                    </button>
                </div>

                {/* Edit Modal */}
                <CreateUserModal
                    isOpen={isEditModalOpen}
                    onClose={() => setIsEditModalOpen(false)}
                    onSubmit={handleEditSubmit}
                    editingUser={user}
                    loading={isEditLoading}
                />
            </div>
        </main>
    )
}
