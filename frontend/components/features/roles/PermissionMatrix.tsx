'use client'

import React, { useState, useMemo } from 'react'
import { PermissionGroup } from './PermissionGroup'
import { CreatePermissionDialog } from './dialogs'
import { usePermissions } from '@/hooks/usePermissions'
import { createPermission } from '@/services/iam'
import { IamPermission } from '@/types/api'

interface PermissionMatrixProps {
    selectedRoleId: string
}

interface PermissionGroupData {
    id: string
    name: string
    icon: string
    permissions: Array<IamPermission & { checked: boolean }>
}

// Map resource types to group display names
const RESOURCE_GROUP_MAP: Record<string, { name: string; icon: string }> = {
    users: { name: 'Nhóm Người dùng', icon: '👤' },
    chat: { name: 'Nhóm AI/Chat', icon: '💬' },
    documents: { name: 'Nhóm Tài liệu', icon: '📄' },
    folders: { name: 'Nhóm Thư mục', icon: '📁' },
    system: { name: 'Nhóm Hệ thống', icon: '⚙️' },
    audit: { name: 'Nhóm Kiểm toán', icon: '📊' },
    embeddings: { name: 'Nhóm Embeddings', icon: '🧠' },
    rag: { name: 'Nhóm RAG', icon: '🔍' },
    permissions: { name: 'Nhóm Quyền hạn', icon: '🔐' },
    roles: { name: 'Nhóm Vai trò', icon: '👑' },
}

export function PermissionMatrix({ selectedRoleId }: PermissionMatrixProps) {
    const { permissions, loading: permissionsLoading, error: permissionsError, useFallback: permissionsUseFallback, refetch } = usePermissions({
        page: 1,
        page_size: 100,
    })

    const [checkedPermissions, setCheckedPermissions] = useState<Set<string>>(new Set())
    const [isCreatePermissionDialogOpen, setIsCreatePermissionDialogOpen] = useState(false)

    // Group permissions by resource
    const permissionGroups = useMemo<PermissionGroupData[]>(() => {
        const grouped: Record<string, PermissionGroupData> = {}

        permissions.forEach((perm) => {
            const groupId = perm.resource
            const groupConfig = RESOURCE_GROUP_MAP[groupId] || {
                name: `Nhóm ${perm.resource}`,
                icon: '📋',
            }

            if (!grouped[groupId]) {
                grouped[groupId] = {
                    id: groupId,
                    name: groupConfig.name,
                    icon: groupConfig.icon,
                    permissions: [],
                }
            }

            grouped[groupId].permissions.push({
                ...perm,
                checked: checkedPermissions.has(perm.id),
            })
        })

        return Object.values(grouped).sort((a, b) => a.name.localeCompare(b.name))
    }, [permissions, checkedPermissions])

    const togglePermission = (permissionId: string) => {
        const newChecked = new Set(checkedPermissions)
        if (newChecked.has(permissionId)) {
            newChecked.delete(permissionId)
        } else {
            newChecked.add(permissionId)
        }
        setCheckedPermissions(newChecked)
    }

    const getRoleName = () => {
        return selectedRoleId || 'Admin'
    }

    const handleCreatePermission = async (data: {
        code: string
        name: string
        resource: string
        action: string
        description: string
    }) => {
        try {
            await createPermission({
                code: data.code.trim().toLowerCase(),
                name: data.name.trim(),
                resource: data.resource.trim(),
                action: data.action.trim(),
                description: data.description.trim(),
            })

            setIsCreatePermissionDialogOpen(false)
            await refetch()
        } catch (error) {
            console.error('Failed to create permission:', error)
            throw error
        }
    }

    if (permissionsLoading) {
        return <div style={{ color: '#727785' }}>Đang tải quyền hạn...</div>
    }

    if (permissionsError) {
        return <div style={{ color: '#d32f2f' }}>Lỗi tải quyền hạn: {permissionsError.message}</div>
    }

    return (
        <div>
            {/* Status Message */}
           

            {/* Permission Groups */}
            {permissionGroups.length === 0 ? (
                <div style={{ color: '#727785' }} className="text-center py-8">
                    Không có quyền hạn nào
                </div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 mb-3">
                    {permissionGroups.map((group) => (
                        <PermissionGroup
                            key={group.id}
                            group={group}
                            onToggle={(permId) => togglePermission(permId)}
                        />
                    ))}
                </div>
            )}

            {/* Additional Actions */}
            <div className="flex flex-col sm:flex-row gap-1.5 mt-3">
                <button
                    type="button"
                    onClick={() => setIsCreatePermissionDialogOpen(true)}
                    className="px-3 py-1.5 rounded-lg font-medium text-xs transition flex items-center gap-1.5"
                    style={{
                        backgroundColor: '#ffffff',
                        color: '#0058be',
                        border: '1px solid #0058be',
                    }}
                >
                    <span>🔐</span> Tạo quyền hạn mới
                </button>
                <button
                    className="px-3 py-1.5 rounded-lg font-medium text-xs transition flex items-center gap-1.5"
                    style={{
                        backgroundColor: '#ffffff',
                        color: '#0058be',
                        border: '1px solid #0058be',
                    }}
                >
                    <span>👥</span> Tạo vai trò nhanh
                </button>
            </div>

            <CreatePermissionDialog
                isOpen={isCreatePermissionDialogOpen}
                onClose={() => setIsCreatePermissionDialogOpen(false)}
                onSubmit={handleCreatePermission}
            />

            {/* Bottom Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-1.5 mt-2 pt-2 border-t" style={{ borderColor: '#dce2f3' }}>
                <button
                    type="button"
                    className="px-3 py-1.5 rounded-lg font-medium text-xs text-white transition flex items-center gap-1.5"
                    style={{ backgroundColor: '#0058be' }}
                >
                    <span>💾</span> Lưu thay đổi
                </button>
                <button
                    type="button"
                    className="px-3 py-1.5 rounded-lg font-medium text-xs transition flex items-center gap-1.5"
                    style={{
                        backgroundColor: '#f0f3ff',
                        color: '#0058be',
                    }}
                >
                    <span>✅</span> Áp dụng ngay
                </button>
            </div>
        </div>
    )
}
