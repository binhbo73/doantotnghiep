'use client'

/**
 * Create User Modal Component
 * Modal form for creating and editing users with proper dropdowns
 */

import React, { useState, useEffect, useMemo } from 'react'
import { X } from 'lucide-react'
import { User } from '@/services/users'
import { useDepartmentOptions, Department } from '@/hooks/useDepartmentOptions'
import { useRoleOptions } from '@/hooks/useRoleOptions'
import { useRBAC } from '@/hooks/useRBAC'

interface CreateUserModalProps {
    isOpen: boolean
    onClose: () => void
    onSubmit: (data: CreateUserFormData) => Promise<void>
    onBulkSubmit?: (data: CreateUsersBulkFormData) => Promise<void>
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
    role_code?: string
}

export interface CreateUsersBulkFormData {
    accounts: Array<{
        username: string
        email: string
        first_name: string
        last_name: string
    }>
    department_id: string
    role_id: string
    role_code?: string
}

export function CreateUserModal({
    isOpen,
    onClose,
    onSubmit,
    onBulkSubmit,
    editingUser,
    loading = false,
}: CreateUserModalProps) {
    const { hasPermission, hasAnyPermission } = useRBAC()
    const canReadDepartments = hasAnyPermission(['department_read', 'department_update', 'department_manage'])
    const canAssignRoles = hasPermission('role_manage')
    const [formData, setFormData] = useState<CreateUserFormData>({
        username: '',
        email: '',
        first_name: '',
        last_name: '',
        department_id: '',
        role_id: '',
    })
    const [createMode, setCreateMode] = useState<'single' | 'bulk'>('single')
    const [bulkText, setBulkText] = useState('')
    const [error, setError] = useState('')
    const [success, setSuccess] = useState('')

    // Fetch departments and roles
    const { data: departmentsRaw, loading: deptsLoading } = useDepartmentOptions(isOpen && canReadDepartments)
    const { data: rolesRaw, loading: rolesLoading } = useRoleOptions(100, isOpen && canAssignRoles)

    type SelectDepartment = Department & { indent: string }

    const departments = useMemo<SelectDepartment[]>(() => {
        const flattenDepartments = (depts: Department[], level = 0): SelectDepartment[] => {
            return depts.flatMap((dept) => [
                {
                    ...dept,
                    indent: '  '.repeat(level),
                },
                ...flattenDepartments(dept.sub_departments || [], level + 1),
            ])
        }

        return flattenDepartments(departmentsRaw || [])
    }, [departmentsRaw])
    const roles = rolesRaw || []
    const selectedRole = useMemo(
        () => roles.find((role) => String(role.id) === formData.role_id),
        [roles, formData.role_id]
    )
    const isAdminRoleSelected = selectedRole?.code === 'admin'
    const canChooseDepartment = canReadDepartments && departments.length > 0

    useEffect(() => {
        if (editingUser) {
            setFormData({
                username: editingUser.username,
                email: editingUser.email,
                first_name: editingUser.first_name,
                last_name: editingUser.last_name,
                department_id: editingUser.department_id ? String(editingUser.department_id) : '',
                role_id: editingUser.roles && editingUser.roles.length > 0 ? String(editingUser.roles[0].id) : '',
            })
        } else {
            setFormData({
                username: '',
                email: '',
                first_name: '',
                last_name: '',
                department_id: '',
                role_id: '',
            })
        }
        setCreateMode('single')
        setBulkText('')
        setError('')
        setSuccess('')
    }, [editingUser, isOpen])

    // Update department_id when departments load, in case it wasn't available initially
    useEffect(() => {
        if (editingUser && departments.length > 0 && !formData.department_id && editingUser.department_name) {
            const matchedDept = departments.find(
                (dept) => dept.name === editingUser.department_name
            )
            if (matchedDept) {
                setFormData((prev) => ({
                    ...prev,
                    department_id: String(matchedDept.id),
                }))
            }
        }
    }, [departments, editingUser, formData.department_id])

    useEffect(() => {
        if (!formData.department_id || departments.length === 0) return

        const selectedDepartmentAllowed = departments.some(
            (dept) => String(dept.id) === formData.department_id
        )
        if (!selectedDepartmentAllowed) {
            setFormData((prev) => ({
                ...prev,
                department_id: '',
            }))
        }
    }, [departments, formData.department_id])

    useEffect(() => {
        if (isAdminRoleSelected && formData.department_id) {
            setFormData((prev) => ({
                ...prev,
                department_id: '',
            }))
        }
    }, [isAdminRoleSelected, formData.department_id])

    const handleDepartmentChange = (departmentId: string) => {
        setFormData({
            ...formData,
            department_id: departmentId,
        })
    }

    const handleRoleChange = (roleId: string) => {
        const nextRole = roles.find((role) => String(role.id) === roleId)
        setFormData({
            ...formData,
            role_id: roleId,
            department_id: nextRole?.code === 'admin' ? '' : formData.department_id,
        })
    }

    const parseBulkAccounts = (input: string) => {
        return input
            .split(/\r?\n/)
            .map((line) => line.trim())
            .filter(Boolean)
            .map((line, index) => {
                const parts = line.split(/[,\t;]/).map((part) => part.trim())
                if (parts.length < 4 || parts.slice(0, 4).some((part) => !part)) {
                    throw new Error(`Dong ${index + 1} phai co dang: username,email,ten,ho`)
                }

                return {
                    username: parts[0],
                    email: parts[1],
                    first_name: parts[2],
                    last_name: parts[3],
                }
            })
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        setSuccess('')

        try {
            if (!editingUser && createMode === 'bulk') {
                if (!onBulkSubmit) {
                    setError('Chua cau hinh chuc nang tao nhieu tai khoan')
                    return
                }

                const accounts = parseBulkAccounts(bulkText)
                if (accounts.length === 0) {
                    setError('Vui long nhap it nhat mot dong tai khoan')
                    return
                }

                await onBulkSubmit({
                    accounts,
                    department_id: formData.department_id,
                    role_id: formData.role_id,
                    role_code: selectedRole?.code,
                })
                setSuccess(`Da xu ly ${accounts.length} tai khoan`)

                setTimeout(() => {
                    onClose()
                    setSuccess('')
                }, 1500)
                return
            }
            if (!formData.username || !formData.email || !formData.first_name) {
                setError('Vui lòng điền tất cả các trường bắt buộc')
                return
            }

            if (editingUser && canAssignRoles && !formData.role_id) {
                setError('Vui lòng chọn vai trò')
                return
            }

            await onSubmit({
                ...formData,
                role_code: selectedRole?.code,
            })
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
                    className="bg-white rounded-xl shadow-2xl w-full max-w-2xl my-8"
                    style={{
                        backgroundColor: '#ffffff',
                        borderRadius: '12px',
                        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.15)',
                        maxWidth: 'min(42rem, calc(100vw - 2rem))',
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

                        {!editingUser && (
                            <div className="inline-flex rounded-lg border p-1" style={{ borderColor: '#dce2f3', backgroundColor: '#f0f3ff' }}>
                                <button
                                    type="button"
                                    onClick={() => setCreateMode('single')}
                                    className="px-3 py-1.5 rounded-md text-sm font-medium"
                                    style={{
                                        backgroundColor: createMode === 'single' ? '#ffffff' : 'transparent',
                                        color: '#151c27',
                                    }}
                                >
                                    Một người
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setCreateMode('bulk')}
                                    className="px-3 py-1.5 rounded-md text-sm font-medium"
                                    style={{
                                        backgroundColor: createMode === 'bulk' ? '#ffffff' : 'transparent',
                                        color: '#151c27',
                                    }}
                                >
                                    Nhiều người
                                </button>
                            </div>
                        )}

                        {!editingUser && createMode === 'bulk' ? (
                            <div className="space-y-2">
                                <label
                                    className="text-sm font-semibold"
                                    style={{ color: '#151c27' }}
                                >
                                    Danh sách tài khoản
                                </label>
                                <textarea
                                    value={bulkText}
                                    onChange={(e) => setBulkText(e.target.value)}
                                    placeholder={'username,email,tên,họ\nnguyen_anh,anh@example.com,Anh,Nguyen Van\ntran_binh,binh@example.com,Binh,Tran Van'}
                                    className="w-full min-h-36 px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2 font-mono"
                                    style={{
                                        backgroundColor: '#f0f3ff',
                                        borderColor: '#dce2f3',
                                        color: '#151c27',
                                    }}
                                    disabled={loading}
                                    required
                                />
                                <p className="text-xs" style={{ color: '#727785' }}>
                                    Mỗi dòng một tài khoản. Cột: username, email, tên, họ. Có thể phân tách bằng dấu phẩy, tab hoặc dấu chấm phẩy.
                                </p>
                            </div>
                        ) : (
                            <>
                        {/* Username & Email Row */}
                        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
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
                        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
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
                            </>
                        )}

                        {/* Department & Role Row */}
                        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                            <div className="space-y-2">
                                <label
                                    className="text-sm font-semibold"
                                    style={{ color: '#151c27' }}
                                >
                                    Phòng ban
                                </label>
                                <select
                                    value={formData.department_id}
                                    onChange={(e) => handleDepartmentChange(e.target.value)}
                                    className="w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2"
                                    style={{
                                        backgroundColor: '#f0f3ff',
                                        borderColor: '#dce2f3',
                                        color: '#151c27',
                                    }}
                                    disabled={loading || deptsLoading || !canChooseDepartment || isAdminRoleSelected}
                                    required={false}
                                >
                                    <option value="">
                                        {isAdminRoleSelected ? 'Admin không thuộc phòng ban' : deptsLoading ? 'Đang tải...' : 'Không chọn phòng ban'}
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
                                    onChange={(e) => handleRoleChange(e.target.value)}
                                    className="w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2"
                                    style={{
                                        backgroundColor: '#f0f3ff',
                                        borderColor: '#dce2f3',
                                        color: '#151c27',
                                    }}
                                    disabled={loading || rolesLoading || !canAssignRoles}
                                    required={false}
                                >
                                    <option value="">
                                        {canAssignRoles
                                            ? (rolesLoading ? 'Đang tải...' : 'Chọn vai trò')
                                            : 'Mặc định: User'}
                                    </option>
                                    {roles.map((role) => (
                                        <option
                                            key={role.id}
                                            value={role.id}
                                            disabled={role.code === 'admin' && !!formData.department_id}
                                        >
                                            {role.name}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        </div>

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
