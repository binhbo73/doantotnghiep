'use client'

import React, { useState, useEffect } from 'react'
import Image from 'next/image'
import { useDepartmentOptions } from '@/hooks/useDepartmentOptions'
import { useRoleOptions } from '@/hooks/useRoleOptions'

interface AddEmployeeDialogProps {
    isOpen: boolean
    onClose: () => void
    onSubmit?: (formData: FormData) => Promise<void>
}

interface FormData {
    username: string
    email: string
    firstName: string
    lastName: string
    department: string
    role: string
}

export default function AddEmployeeDialog({
    isOpen,
    onClose,
    onSubmit,
}: AddEmployeeDialogProps) {
    const [formData, setFormData] = useState<FormData>({
        username: '',
        email: '',
        firstName: '',
        lastName: '',
        department: '',
        role: '',
    })

    const [isSubmitting, setIsSubmitting] = useState(false)
    const [error, setError] = useState<string | null>(null)

    // Fetch departments and roles
    const { data: departmentsRaw, loading: deptsLoading, error: deptsError } = useDepartmentOptions()
    const { data: rolesRaw, loading: rolesLoading, error: rolesError } = useRoleOptions()

    console.log('🎨 [AddEmployeeDialog] Roles data:', rolesRaw)
    console.log('🎨 [AddEmployeeDialog] Roles loading:', rolesLoading)
    console.log('🎨 [AddEmployeeDialog] Roles error:', rolesError)
    console.log('🎨 [AddEmployeeDialog] Departments data:', departmentsRaw)
    console.log('🎨 [AddEmployeeDialog] Departments loading:', deptsLoading)
    console.log('🎨 [AddEmployeeDialog] Departments error:', deptsError)

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

    const handleInputChange = (
        e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
    ) => {
        const { name, value } = e.target
        setFormData((prev) => ({ ...prev, [name]: value }))
    }

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault()
        setError(null)

        // Validate required fields
        if (
            !formData.username ||
            !formData.email ||
            !formData.firstName ||
            !formData.lastName ||
            !formData.department ||
            !formData.role
        ) {
            setError('Vui lòng điền đầy đủ các trường bắt buộc')
            return
        }

        setIsSubmitting(true)
        try {
            if (onSubmit) {
                await onSubmit(formData as any)
            }

            // Reset form
            setFormData({
                username: '',
                email: '',
                firstName: '',
                lastName: '',
                department: '',
                role: '',
            })
            onClose()
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Có lỗi xảy ra')
        } finally {
            setIsSubmitting(false)
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
                    className="bg-white rounded-xl shadow-2xl w-full max-w-md my-8"
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
                                Thêm nhân sự mới
                            </h2>
                            <p
                                className="text-sm mt-1"
                                style={{ color: '#727785' }}
                            >
                                Cấp quyền truy cập hệ thống Knowledge OS cho thành
                                viên mới.
                            </p>
                        </div>
                        <button
                            onClick={onClose}
                            className="text-gray-400 hover:text-gray-600"
                            aria-label="Close"
                        >
                            <svg
                                className="w-6 h-6"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M6 18L18 6M6 6l12 12"
                                />
                            </svg>
                        </button>
                    </div>

                    {/* Content */}
                    <form onSubmit={handleSubmit} className="p-6 space-y-5">
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
                                    name="username"
                                    placeholder="vd: nguyễn_anh"
                                    value={formData.username}
                                    onChange={handleInputChange}
                                    className="w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2"
                                    style={{
                                        backgroundColor: '#f0f3ff',
                                        borderColor: '#dce2f3',
                                        color: '#151c27',
                                    }}
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
                                    name="email"
                                    placeholder="example@company.com"
                                    value={formData.email}
                                    onChange={handleInputChange}
                                    className="w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2"
                                    style={{
                                        backgroundColor: '#f0f3ff',
                                        borderColor: '#dce2f3',
                                        color: '#151c27',
                                    }}
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
                                    name="firstName"
                                    placeholder="Nhập tên"
                                    value={formData.firstName}
                                    onChange={handleInputChange}
                                    className="w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2"
                                    style={{
                                        backgroundColor: '#f0f3ff',
                                        borderColor: '#dce2f3',
                                        color: '#151c27',
                                    }}
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
                                    name="lastName"
                                    placeholder="Nhập họ và tên đệm"
                                    value={formData.lastName}
                                    onChange={handleInputChange}
                                    className="w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2"
                                    style={{
                                        backgroundColor: '#f0f3ff',
                                        borderColor: '#dce2f3',
                                        color: '#151c27',
                                    }}
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
                                    name="department"
                                    value={formData.department}
                                    onChange={handleInputChange}
                                    className="w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2"
                                    style={{
                                        backgroundColor: '#f0f3ff',
                                        borderColor: '#dce2f3',
                                        color: '#151c27',
                                        maxHeight: '200px',
                                        overflowY: 'auto',
                                    }}
                                    disabled={deptsLoading}
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
                                {deptsError && (
                                    <p
                                        className="text-xs"
                                        style={{ color: '#ba1a1a' }}
                                    >
                                        {deptsError}
                                    </p>
                                )}
                            </div>
                            <div className="space-y-2">
                                <label
                                    className="text-sm font-semibold"
                                    style={{ color: '#151c27' }}
                                >
                                    Vai trò
                                </label>
                                <select
                                    name="role"
                                    value={formData.role}
                                    onChange={handleInputChange}
                                    className="w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2"
                                    style={{
                                        backgroundColor: '#f0f3ff',
                                        borderColor: '#dce2f3',
                                        color: '#151c27',
                                        maxHeight: '200px',
                                        overflowY: 'auto',
                                    }}
                                    disabled={rolesLoading}
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
                                {rolesError && (
                                    <p
                                        className="text-xs"
                                        style={{ color: '#ba1a1a' }}
                                    >
                                        {rolesError}
                                    </p>
                                )}
                            </div>
                        </div>

                        {/* Info Alert */}
                        <div
                            className="p-3 rounded-lg border-l-4 text-sm"
                            style={{
                                backgroundColor: '#fff4e0',
                                borderColor: '#924700',
                                color: '#924700',
                            }}
                        >
                            <div className="flex gap-2">
                                <span className="text-lg">⚠️</span>
                                <p className="text-xs">
                                    Mật khẩu tạm thời sẽ được gửi qua email
                                    cùng với liên kết xác minh. Nhân sự sẽ cần
                                    đặt lại mật khẩu lần đầu khi đăng nhập.
                                </p>
                            </div>
                        </div>

                        {/* Error Alert */}
                        {error && (
                            <div
                                className="p-3 rounded-lg border-l-4 text-sm"
                                style={{
                                    backgroundColor: '#ffe0e0',
                                    borderColor: '#ba1a1a',
                                    color: '#ba1a1a',
                                }}
                            >
                                <div className="flex gap-2">
                                    <span className="text-lg">❌</span>
                                    <p className="text-xs">{error}</p>
                                </div>
                            </div>
                        )}

                        {/* Buttons */}
                        <div className="flex gap-3 pt-4">
                            <button
                                type="button"
                                onClick={onClose}
                                disabled={isSubmitting}
                                className="flex-1 px-4 py-2 rounded-lg text-sm font-semibold border transition-colors"
                                style={{
                                    color: '#151c27',
                                    backgroundColor: '#f0f3ff',
                                    borderColor: '#dce2f3',
                                }}
                            >
                                Hủy
                            </button>
                            <button
                                type="submit"
                                disabled={isSubmitting}
                                className="flex-1 px-4 py-2 rounded-lg text-sm font-semibold text-white transition-all disabled:opacity-50"
                                style={{
                                    backgroundColor: '#924700',
                                }}
                            >
                                {isSubmitting
                                    ? 'Đang xử lý...'
                                    : 'Tạo tài khoản'}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </>
    )
}
