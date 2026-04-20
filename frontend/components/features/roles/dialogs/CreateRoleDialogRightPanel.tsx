'use client'

import React, { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { PermissionsSelector } from './PermissionsSelector'
import { CreatePermissionDialog } from './CreatePermissionDialog'
import { useCreateRole } from '@/hooks/useCreateRole'
import { usePermissions } from '@/hooks/usePermissions'
import { IamPermission } from '@/types/api'

interface Permission extends IamPermission {
    checked: boolean
}

interface CreateRoleDialogRightPanelProps {
    isEdit?: boolean
    onClose: () => void
    onSubmit?: (data: {
        code: string
        displayName: string
        description: string
        permissions: Permission[]
    }) => void
    initialData?: {
        code: string
        displayName: string
        description: string
        permissions: Permission[]
    }
}

export function CreateRoleDialogRightPanel({
    isEdit = false,
    onClose,
    onSubmit,
    initialData,
}: CreateRoleDialogRightPanelProps) {
    const [formData, setFormData] = useState({
        code: initialData?.code || '',
        displayName: initialData?.displayName || '',
        description: initialData?.description || '',
    })

    // Fetch permissions from API
    const { permissions: apiPermissions, loading: permissionsLoading, error: permissionsError } = usePermissions({
        page: 1,
        page_size: 100,
    })

    // Create role hook
    const { createRole, addPermissionsToRole, loading: createLoading, error: createError } = useCreateRole()

    const [permissions, setPermissions] = useState<Permission[]>([])
    const [isPermissionsSelectorOpen, setIsPermissionsSelectorOpen] = useState(false)
    const [isCreatePermissionDialogOpen, setIsCreatePermissionDialogOpen] = useState(false)
    const [isSubmitting, setIsSubmitting] = useState(false)

    // Initialize permissions from API
    useEffect(() => {
        if (apiPermissions && apiPermissions.length > 0) {
            const initialPermissions = apiPermissions.map((perm) => ({
                ...perm,
                checked: initialData?.permissions?.some((p) => p.id === perm.id) || false,
            }))
            setPermissions(initialPermissions)
        }
    }, [apiPermissions, initialData])

    // For edit mode, set initial checked state
    useEffect(() => {
        if (isEdit && initialData?.permissions) {
            setPermissions((prev) =>
                prev.map((p) => ({
                    ...p,
                    checked: initialData.permissions.some((ip) => ip.id === p.id),
                }))
            )
        }
    }, [isEdit, initialData])

    const handlePermissionToggle = (id: string) => {
        setPermissions(
            permissions.map((perm) =>
                perm.id === id ? { ...perm, checked: !perm.checked } : perm
            )
        )
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        if (!formData.code.trim()) {
            alert('Vui lòng nhập mã vai trò')
            return
        }

        if (!formData.displayName.trim()) {
            alert('Vui lòng nhập tên hiển thị')
            return
        }

        try {
            setIsSubmitting(true)

            if (isEdit && initialData?.code) {
                // For edit mode, just call onSubmit
                await onSubmit?.({
                    ...formData,
                    permissions: permissions.filter((p) => p.checked),
                })
            } else {
                // For create mode: create role first, then add permissions
                const newRole = await createRole({
                    code: formData.code,
                    name: formData.displayName,
                    description: formData.description,
                })

                const selectedPermissions = permissions.filter((p) => p.checked)
                if (selectedPermissions.length > 0) {
                    await addPermissionsToRole(newRole.id, {
                        permission_ids: selectedPermissions.map((p) => p.id),
                    })
                }

                // Notify parent component
                await onSubmit?.({
                    ...formData,
                    permissions: selectedPermissions,
                })
            }
        } catch (err) {
            const errorMsg =
                err instanceof Error ? err.message : (isEdit ? 'Có lỗi xảy ra khi cập nhật vai trò' : 'Có lỗi xảy ra khi tạo vai trò')
            alert(errorMsg)
            throw err
        } finally {
            setIsSubmitting(false)
        }
    }

    const checkedCount = permissions.filter((p) => p.checked).length

    return (
        <div className="flex flex-col p-4 lg:p-6 flex-1 overflow-hidden">
            {/* Close Button - Mobile */}
            <button
                onClick={onClose}
                className="lg:hidden absolute top-4 right-4 p-1 hover:bg-gray-100 rounded transition"
            >
                <X size={24} style={{ color: '#151c27' }} />
            </button>

            <form onSubmit={handleSubmit} className="flex flex-col gap-2 h-full overflow-y-auto pr-2">
                {/* Error Messages */}
                {(permissionsError || createError) && (
                    <div
                        className="p-3 rounded-lg text-sm border"
                        style={{ backgroundColor: '#ffebee', borderColor: '#ef5350', color: '#c62828' }}
                    >
                        {permissionsError?.message || createError?.message}
                    </div>
                )}

                {/* Permissions Loading State */}
                {permissionsLoading && (
                    <div
                        className="p-3 rounded-lg text-sm"
                        style={{ backgroundColor: '#e3f2fd', color: '#1976d2' }}
                    >
                        Đang tải danh sách quyền hạn...
                    </div>
                )}

                {/* Role Code & Display Name - Two Columns */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {/* Role Code */}
                    <div>
                        <label className="text-xs font-bold mb-2 block uppercase" style={{ color: '#727785' }}>
                            Mã vai trò
                        </label>
                        <input
                            type="text"
                            value={formData.code}
                            onChange={(e) =>
                                setFormData({ ...formData, code: e.target.value.toUpperCase() })
                            }
                            placeholder="e.g. DATA_ARCHITECT"
                            className="w-full px-4 py-3 rounded-lg border text-sm"
                            style={{
                                borderColor: '#dce2f3',
                                color: '#151c27',
                            }}
                            required
                        />
                    </div>

                    {/* Display Name */}
                    <div>
                        <label className="text-xs font-bold mb-2 block uppercase" style={{ color: '#727785' }}>
                            Tên hiển thị
                        </label>
                        <input
                            type="text"
                            value={formData.displayName}
                            onChange={(e) => setFormData({ ...formData, displayName: e.target.value })}
                            placeholder="Kiến trúc sư dữ liệu"
                            className="w-full px-4 py-3 rounded-lg border text-sm"
                            style={{
                                borderColor: '#dce2f3',
                                color: '#151c27',
                            }}
                            required
                        />
                    </div>
                </div>

                {/* Description */}
                <div>
                    <label className="text-xs font-bold mb-2 block uppercase" style={{ color: '#727785' }}>
                        Mô tả chức năng
                    </label>
                    <textarea
                        value={formData.description}
                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                        placeholder="Mô tả tóm tắt trách nhiệm của vai trò này..."
                        rows={2}
                        className="w-full px-4 py-3 rounded-lg border text-sm resize-none"
                        style={{
                            borderColor: '#dce2f3',
                            color: '#151c27',
                        }}
                    />
                </div>

                {/* Permission List Header */}
                <div className="flex items-center justify-between">
                    <label className="text-xs font-bold uppercase" style={{ color: '#727785' }}>
                        Danh sách quyền hạn
                    </label>
                    <span className="text-xs font-semibold" style={{ color: '#b75b00' }}>
                        {checkedCount} quyền đã chọn
                    </span>
                </div>

                {/* Permissions Quick View - Selected Permissions */}
                {checkedCount > 0 && (
                    <div className="max-h-[500px] overflow-y-auto p-3 rounded-lg border flex-grow" style={{ borderColor: '#dce2f3', backgroundColor: '#f9f9ff' }}>
                        <div className="flex flex-wrap gap-2">
                            {permissions
                                .filter((p) => p.checked)
                                .map((p) => (
                                    <span
                                        key={p.id}
                                        className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium text-white"
                                        style={{ backgroundColor: '#0058be' }}
                                    >
                                        {p.code}
                                        <button
                                            type="button"
                                            onClick={() => handlePermissionToggle(p.id)}
                                            className="hover:opacity-75 transition"
                                        >
                                            ✕
                                        </button>
                                    </span>
                                ))}
                        </div>
                    </div>
                )}

                {/* Open Permissions Selector Button */}
                <button
                    type="button"
                    onClick={() => setIsPermissionsSelectorOpen(true)}
                    disabled={permissionsLoading}
                    className="w-full px-4 py-2 rounded-lg font-medium text-sm transition border-2 mt-1 disabled:opacity-50"
                    style={{
                        backgroundColor: '#f0f3ff',
                        color: '#0058be',
                        borderColor: '#0058be',
                    }}
                >
                    📋 Chỉnh sửa quyền hạn
                </button>

                {/* Action Buttons */}
                <div className="flex gap-3 pt-3 mt-3 border-t" style={{ borderColor: '#dce2f3' }}>
                    <button
                        type="button"
                        onClick={onClose}
                        disabled={isSubmitting}
                        className="flex-1 px-4 py-2 rounded-lg font-medium text-sm transition border-2 disabled:opacity-50"
                        style={{
                            backgroundColor: '#ffffff',
                            color: '#0058be',
                            borderColor: '#0058be',
                        }}
                    >
                        Hủy bỏ
                    </button>
                    <button
                        type="submit"
                        disabled={isSubmitting || permissionsLoading}
                        className="flex-1 px-4 py-2 rounded-lg font-medium text-white text-sm transition disabled:opacity-50"
                        style={{ backgroundColor: '#b75b00' }}
                    >
                        {isSubmitting ? (
                            <>
                                <span>⏳ Đang xử lý...</span>
                            </>
                        ) : isEdit ? (
                            'Cập nhật vai trò'
                        ) : (
                            'Tạo mới vai trò'
                        )}
                    </button>
                </div>

                {/* Modals */}
                <PermissionsSelector
                    isOpen={isPermissionsSelectorOpen}
                    permissions={permissions}
                    onClose={() => setIsPermissionsSelectorOpen(false)}
                    onToggle={handlePermissionToggle}
                    onCreateNew={() => {
                        setIsPermissionsSelectorOpen(false)
                        setIsCreatePermissionDialogOpen(true)
                    }}
                />

                <CreatePermissionDialog
                    isOpen={isCreatePermissionDialogOpen}
                    onClose={() => setIsCreatePermissionDialogOpen(false)}
                    onSubmit={(data) => {
                        console.log('New permission:', data)
                        setIsCreatePermissionDialogOpen(false)
                    }}
                />
            </form>
        </div>
    )
}
