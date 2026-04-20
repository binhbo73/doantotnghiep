'use client'

import React, { useState } from 'react'
import { X } from 'lucide-react'
import { IamRole } from '@/types/api'
import { RoleDetailPermissions } from '../RoleDetailPermissions'
import { useRolePermissions } from '@/hooks/useRolePermissions'

interface RoleDetailDialogProps {
    isOpen: boolean
    role: IamRole | null
    onClose: () => void
    onEdit?: (roleId: string) => void
    onDelete?: (roleId: string) => Promise<void>
}

export function RoleDetailDialog({ isOpen, role, onClose, onEdit, onDelete }: RoleDetailDialogProps) {
    const [isDeleting, setIsDeleting] = useState(false)
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

    const { permissions, loading: permissionsLoading, error: permissionsError } = useRolePermissions(
        role?.id || ''
    )

    const handleDelete = async () => {
        if (!role || !onDelete) return

        try {
            setIsDeleting(true)
            await onDelete(role.id)
            setShowDeleteConfirm(false)
            onClose()
        } catch (error) {
            console.error('Failed to delete role:', error)
        } finally {
            setIsDeleting(false)
        }
    }

    if (!isOpen || !role) return null

    return (
        <>
            {/* Overlay */}
            <div
                className="fixed inset-0 bg-black/30 z-40 transition-opacity"
                onClick={onClose}
            />

            {/* Dialog */}
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                <div
                    className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden"
                    onClick={(e) => e.stopPropagation()}
                >
                    {/* Header */}
                    <div
                        className="px-6 py-4 border-b flex items-center justify-between"
                        style={{ borderColor: '#dce2f3', backgroundColor: '#f9f9ff' }}
                    >
                        <div className="flex-1">
                            <div className="flex items-center gap-3">
                                <div
                                    className="w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-lg flex-shrink-0"
                                    style={{ backgroundColor: '#0058be' }}
                                >
                                    {role.name.charAt(0)}
                                </div>
                                <div>
                                    <h2 className="text-2xl font-bold" style={{ color: '#151c27' }}>
                                        {role.name}
                                    </h2>
                                    <p className="text-sm" style={{ color: '#727785' }}>
                                        {role.code}
                                    </p>
                                </div>
                            </div>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-1 hover:bg-gray-100 rounded transition flex-shrink-0"
                        >
                            <X size={24} style={{ color: '#151c27' }} />
                        </button>
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-y-auto">
                        {/* Role Info Section */}
                        <div className="px-6 py-4 border-b" style={{ borderColor: '#dce2f3' }}>
                            <h3 className="text-sm font-bold mb-3 uppercase" style={{ color: '#727785' }}>
                                Thông tin vai trò
                            </h3>
                            <div className="space-y-3">
                                {role.description && (
                                    <div>
                                        <p className="text-xs font-semibold mb-1" style={{ color: '#727785' }}>
                                            Mô tả:
                                        </p>
                                        <p style={{ color: '#151c27' }}>{role.description}</p>
                                    </div>
                                )}
                                <div>
                                    <p className="text-xs font-semibold mb-1" style={{ color: '#727785' }}>
                                        Số thành viên:
                                    </p>
                                    <span
                                        className="inline-block px-2 py-1 rounded-full text-xs font-bold"
                                        style={{ backgroundColor: '#f0f3ff', color: '#0058be' }}
                                    >
                                        👥 Chưa có dữ liệu
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* Permissions Section */}
                        <div className="px-6 py-4">
                            <h3 className="text-sm font-bold mb-4 uppercase" style={{ color: '#727785' }}>
                                Danh sách quyền hạn ({role.permission_count || permissions.length})
                            </h3>
                            <RoleDetailPermissions
                                permissions={permissions}
                                loading={permissionsLoading}
                                error={permissionsError}
                            />
                        </div>
                    </div>

                    {/* Footer */}
                    <div
                        className="px-6 py-4 border-t flex gap-3"
                        style={{ borderColor: '#dce2f3', backgroundColor: '#f9f9ff' }}
                    >
                        <button
                            onClick={onClose}
                            className="flex-1 px-4 py-2 rounded-lg font-medium text-sm transition border-2"
                            style={{
                                backgroundColor: '#ffffff',
                                color: '#0058be',
                                borderColor: '#0058be',
                            }}
                        >
                            Đóng
                        </button>
                        <button
                            onClick={() => onEdit && onEdit(role.id)}
                            className="flex-1 px-4 py-2 rounded-lg font-medium text-white text-sm transition"
                            style={{ backgroundColor: '#b75b00' }}
                        >
                            ✏️ Chỉnh sửa vai trò
                        </button>
                        {onDelete && (
                            <button
                                onClick={() => setShowDeleteConfirm(true)}
                                className="px-4 py-2 rounded-lg font-medium text-white text-sm transition"
                                style={{ backgroundColor: '#dc3545' }}
                            >
                                🗑️ Xóa
                            </button>
                        )}
                    </div>

                    {/* Delete Confirmation Dialog */}
                    {showDeleteConfirm && (
                        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/40 rounded-2xl">
                            <div
                                className="bg-white rounded-xl p-6 shadow-xl mx-4 max-w-sm"
                                onClick={(e) => e.stopPropagation()}
                            >
                                <h3 className="text-lg font-bold mb-2" style={{ color: '#151c27' }}>
                                    Xác nhận xóa vai trò
                                </h3>
                                <p className="mb-4" style={{ color: '#727785' }}>
                                    Bạn có chắc chắn muốn xóa vai trò "<strong>{role.name}</strong>"? Hành động này không thể hoàn tác.
                                </p>
                                <div className="flex gap-3">
                                    <button
                                        onClick={() => setShowDeleteConfirm(false)}
                                        disabled={isDeleting}
                                        className="flex-1 px-4 py-2 rounded-lg font-medium text-sm transition border-2 disabled:opacity-50"
                                        style={{
                                            backgroundColor: '#ffffff',
                                            color: '#0058be',
                                            borderColor: '#0058be',
                                        }}
                                    >
                                        Hủy
                                    </button>
                                    <button
                                        onClick={handleDelete}
                                        disabled={isDeleting}
                                        className="flex-1 px-4 py-2 rounded-lg font-medium text-white text-sm transition disabled:opacity-50"
                                        style={{ backgroundColor: '#dc3545' }}
                                    >
                                        {isDeleting ? 'Đang xóa...' : 'Xóa vai trò'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </>
    )
}
