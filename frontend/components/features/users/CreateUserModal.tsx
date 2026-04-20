'use client'

/**
 * Create User Modal Component
 * Modal form for creating and editing users with proper dropdowns
 */

import React, { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { User } from '@/services/users'
import { useDepartmentOptions } from '@/hooks/useDepartmentOptions'
import { useRoleOptions } from '@/hooks/useRoleOptions'

interface CreateUserModalProps {
    isOpen: boolean
    onClose: () => void
    onSubmit: (data: CreateUserFormData) => Promise<void>
    editingUser?: User | null
    loading?: boolean
}

export interface CreateUserFormData {
    username: string
    email: string
    first_name: string
    last_name: string
    department_id: string
    role_id: string
    password?: string
}

export function CreateUserModal({
    isOpen,
    onClose,
    onSubmit,
    editingUser,
    loading = false,
}: CreateUserModalProps) {
    const [formData, setFormData] = useState<CreateUserFormData>({
        username: '',
        email: '',
        first_name: '',
        last_name: '',
        department_id: '',
        role_id: '',
        password: '',
    })
    const [error, setError] = useState('')
    const [success, setSuccess] = useState('')

    // Fetch departments and roles
    const { data: departmentsRaw, loading: deptsLoading } = useDepartmentOptions()
    const { data: rolesRaw, loading: rolesLoading } = useRoleOptions()

    // Flatten nested departments for dropdown
    const flattenDepartments = (depts: any[]): any[] => {
        if (!depts) return []
        const result: any[] = []

        const process = (list: any[], level = 0) => {
            list.forEach((dept) => {
                result.push({
                    ...dept,
                    indent: '  '.repeat(level),
                })
                if (dept.sub_departments && dept.sub_departments.length > 0) {
                    process(dept.sub_departments, level + 1)
                }
            })
        }

        process(depts)
        return result
    }

    const departments = flattenDepartments(departmentsRaw || [])
    const roles = rolesRaw || []

    useEffect(() => {
        if (editingUser) {
            setFormData({
                username: editingUser.username,
                email: editingUser.email,
                first_name: editingUser.first_name,
                last_name: editingUser.last_name,
                department_id: editingUser.department_id || '',
                role_id: editingUser.roles && editingUser.roles.length > 0 ? editingUser.roles[0].id : '',
            })
        } else {
            setFormData({
                username: '',
                email: '',
                first_name: '',
                last_name: '',
                department_id: '',
                role_id: '',
                password: '',
            })
        }
        setError('')
        setSuccess('')
    }, [editingUser, isOpen])

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        setSuccess('')

        try {
            if (!formData.username || !formData.email || !formData.first_name) {
                setError('Vui lòng điền tất cả các trường bắt buộc')
                return
            }

            if (!editingUser && !formData.password) {
                setError('Vui lòng nhập mật khẩu cho người dùng mới')
                return
            }

            await onSubmit(formData)
            setSuccess(editingUser ? 'Cập nhật người dùng thành công!' : 'Tạo người dùng thành công!')

            setTimeout(() => {
                onClose()
                setSuccess('')
            }, 1500)
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Có lỗi xảy ra')
        }
    }

    if (!isOpen) return null

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
                onClick={onClose}
                style={{
                    backgroundColor: 'rgba(0, 0, 0, 0.5)',
                }}
            />

            {/* Dialog */}
            <div className="fixed inset-0 flex items-center justify-center z-50 p-4 overflow-y-auto">
                <div
                    className="bg-white rounded-xl shadow-2xl w-full max-w-sm my-8"
                    style={{
                        backgroundColor: '#ffffff',
                        borderRadius: '12px',
                        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.15)',
                    }}
                >
                    {/* Header */}
                    <div
                        className="flex items-center justify-between p-6 border-b"
                        style={{
                            borderColor: '#dce2f3',
                        }}
                    >
                        <div>
                            <h2
                                className="text-lg font-bold"
                                style={{ color: '#151c27' }}
                            >
                                {editingUser ? 'Chỉnh sửa người dùng' : 'Thêm người dùng mới'}
                            </h2>
                            <p
                                className="text-sm mt-1"
                                style={{ color: '#727785' }}
                            >
                                {editingUser
                                    ? 'Cập nhật thông tin tài khoản người dùng.'
                                    : 'Cấp quyền truy cập hệ thống cho thành viên mới.'
                                }
                            </p>
                        </div>
                        <button
                            onClick={onClose}
                            className="text-gray-400 hover:text-gray-600 ml-4"
                            aria-label="Close"
                        >
                            <X size={20} />
                        </button>
                    </div>

                    {/* Content */}
                    <form onSubmit={handleSubmit} className="p-6 space-y-5">
                        {/* Error Alert */}
                        {error && (
                            <div
                                className="p-3 rounded-lg border-l-4 flex gap-2 text-sm"
                                style={{
                                    backgroundColor: '#ffe0e0',
                                    borderColor: '#ba1a1a',
                                    color: '#ba1a1a',
                                }}
                            >
                                <span style={{ fontSize: '16px' }}>❌</span>
                                <span>{error}</span>
                            </div>
                        )}

                        {success && (
                            <div
                                className="p-3 rounded-lg border-l-4 flex gap-2 text-sm"
                                style={{
                                    backgroundColor: '#e0f2e0',
                                    borderColor: '#2e7d32',
                                    color: '#2e7d32',
                                }}
                            >
                                <span style={{ fontSize: '16px' }}>✅</span>
                                <span>{success}</span>
                            </div>
                        )}

                        {/* Username & Email Row */}
                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-2">
                                <label
                                    className="text-sm font-semibold"
                                    style={{ color: '#151c27' }}
                                >
                                    Tên đăng nhập
                                </label>
                                <input
                                    type="text"
                                    value={formData.username}
                                    onChange={(e) =>
                                        setFormData({ ...formData, username: e.target.value })
                                    }
                                    placeholder="vd: nguyen_anh"
                                    className="w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2"
                                    style={{
                                        backgroundColor: '#f0f3ff',
                                        borderColor: '#dce2f3',
                                        color: '#151c27',
                                    }}
                                    disabled={loading || !!editingUser}
                                    required
                                />
                            </div>
                            <div className="space-y-2">
                                <label
                                    className="text-sm font-semibold"
                                    style={{ color: '#151c27' }}
                                >
                                    Email
                                </label>
                                <input
                                    type="email"
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                    placeholder="example@company.com"
                                    className="w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2"
                                    style={{
                                        backgroundColor: '#f0f3ff',
                                        borderColor: '#dce2f3',
                                        color: '#151c27',
                                    }}
                                    disabled={loading}
                                    required
                                />
                            </div>
                        </div>

                        {/* First Name & Last Name Row */}
                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-2">
                                <label
                                    className="text-sm font-semibold"
                                    style={{ color: '#151c27' }}
                                >
                                    Tên
                                </label>
                                <input
                                    type="text"
                                    value={formData.first_name}
                                    onChange={(e) =>
                                        setFormData({ ...formData, first_name: e.target.value })
                                    }
                                    placeholder="Nhập tên"
                                    className="w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2"
                                    style={{
                                        backgroundColor: '#f0f3ff',
                                        borderColor: '#dce2f3',
                                        color: '#151c27',
                                    }}
                                    disabled={loading}
                                    required
                                />
                            </div>
                            <div className="space-y-2">
                                <label
                                    className="text-sm font-semibold"
                                    style={{ color: '#151c27' }}
                                >
                                    Họ
                                </label>
                                <input
                                    type="text"
                                    value={formData.last_name}
                                    onChange={(e) =>
                                        setFormData({ ...formData, last_name: e.target.value })
                                    }
                                    placeholder="Nhập họ và tên đệm"
                                    className="w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2"
                                    style={{
                                        backgroundColor: '#f0f3ff',
                                        borderColor: '#dce2f3',
                                        color: '#151c27',
                                    }}
                                    disabled={loading}
                                    required
                                />
                            </div>
                        </div>

                        {/* Department & Role Row */}
                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-2">
                                <label
                                    className="text-sm font-semibold"
                                    style={{ color: '#151c27' }}
                                >
                                    Phòng ban
                                </label>
                                <select
                                    value={formData.department_id}
                                    onChange={(e) =>
                                        setFormData({ ...formData, department_id: e.target.value })
                                    }
                                    className="w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2"
                                    style={{
                                        backgroundColor: '#f0f3ff',
                                        borderColor: '#dce2f3',
                                        color: '#151c27',
                                    }}
                                    disabled={loading || deptsLoading}
                                    required
                                >
                                    <option value="">
                                        {deptsLoading ? 'Đang tải...' : 'Chọn phòng ban'}
                                    </option>
                                    {departments.map((dept) => (
                                        <option key={dept.id} value={dept.id}>
                                            {dept.indent}{dept.name}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div className="space-y-2">
                                <label
                                    className="text-sm font-semibold"
                                    style={{ color: '#151c27' }}
                                >
                                    Vai trò
                                </label>
                                <select
                                    value={formData.role_id}
                                    onChange={(e) => setFormData({ ...formData, role_id: e.target.value })}
                                    className="w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2"
                                    style={{
                                        backgroundColor: '#f0f3ff',
                                        borderColor: '#dce2f3',
                                        color: '#151c27',
                                    }}
                                    disabled={loading || rolesLoading}
                                    required
                                >
                                    <option value="">
                                        {rolesLoading ? 'Đang tải...' : 'Chọn vai trò'}
                                    </option>
                                    {roles.map((role) => (
                                        <option key={role.id} value={role.id}>
                                            {role.name}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        {/* Password - Only show for new users */}


                        {/* Warning Message */}
                        {!editingUser && (
                            <div
                                className="p-3 rounded-lg border-l-4 text-sm"
                                style={{
                                    backgroundColor: '#fff4e0',
                                    borderColor: '#924700',
                                    color: '#924700',
                                }}
                            >
                                <div className="flex gap-2">
                                    <span style={{ fontSize: '16px' }}>⚠️</span>
                                    <p className="text-xs">
                                        Mật khẩu tạm thời sẽ được gửi qua email cùng với liên kết xác minh. Nhân sự sẽ cần đặt lại mật khẩu lần đầu khi đăng nhập.
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* Footer */}
                        <div className="flex gap-3 justify-end pt-2 border-t" style={{ borderColor: '#dce2f3' }}>
                            <button
                                type="button"
                                onClick={onClose}
                                className="px-4 py-2 rounded-lg border font-medium transition-colors text-sm"
                                style={{
                                    borderColor: '#dce2f3',
                                    color: '#151c27',
                                }}
                                disabled={loading}
                            >
                                Hủy
                            </button>
                            <button
                                type="submit"
                                className="px-4 py-2 rounded-lg text-white font-medium transition-all hover:shadow-lg text-sm"
                                style={{
                                    backgroundColor: '#9d4300',
                                    backgroundImage: 'linear-gradient(to bottom, #9d4300, #783200)',
                                }}
                                disabled={loading}
                            >
                                {loading ? 'Đang xử lý...' : editingUser ? 'Cập nhật' : 'Tạo tài khoản'}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </>
    )
}

export default CreateUserModal
