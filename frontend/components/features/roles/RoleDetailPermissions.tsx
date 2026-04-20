'use client'

import React, { useMemo } from 'react'
import { IamPermission } from '@/types/api'

interface RoleDetailPermissionsProps {
    permissions: IamPermission[]
    loading: boolean
    error: Error | null
}

const RESOURCE_DISPLAY: Record<string, { label: string; icon: string }> = {
    users: { label: 'Người dùng', icon: '👤' },
    chat: { label: 'AI/Chat', icon: '💬' },
    documents: { label: 'Tài liệu', icon: '📄' },
    folders: { label: 'Thư mục', icon: '📁' },
    system: { label: 'Hệ thống', icon: '⚙️' },
    audit: { label: 'Kiểm toán', icon: '📊' },
    embeddings: { label: 'Embeddings', icon: '🧠' },
    rag: { label: 'RAG', icon: '🔍' },
    permissions: { label: 'Quyền hạn', icon: '🔐' },
    roles: { label: 'Vai trò', icon: '👑' },
}

export function RoleDetailPermissions({
    permissions,
    loading,
    error,
}: RoleDetailPermissionsProps) {
    // Group permissions by resource
    const groupedPermissions = useMemo(() => {
        const groups: Record<string, IamPermission[]> = {}

        permissions.forEach((perm) => {
            const resource = perm.resource || 'other'
            if (!groups[resource]) {
                groups[resource] = []
            }
            groups[resource].push(perm)
        })

        return Object.entries(groups).sort((a, b) => a[0].localeCompare(b[0]))
    }, [permissions])

    if (loading) {
        return (
            <div className="p-6 text-center">
                <div style={{ color: '#727785' }}>⏳ Đang tải danh sách quyền hạn...</div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="p-6">
                <div
                    className="p-3 rounded-lg text-sm border"
                    style={{ backgroundColor: '#ffebee', borderColor: '#ef5350', color: '#c62828' }}
                >
                    ❌ {error.message}
                </div>
            </div>
        )
    }

    if (permissions.length === 0) {
        return (
            <div className="p-6 text-center">
                <div style={{ color: '#727785' }}>Vai trò này chưa có quyền hạn nào</div>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            {groupedPermissions.map(([resource, perms]) => {
                const displayInfo = RESOURCE_DISPLAY[resource] || { label: resource, icon: '📋' }

                return (
                    <div key={resource}>
                        {/* Resource Header */}
                        <div className="flex items-center gap-2 mb-3 pb-2 border-b" style={{ borderColor: '#dce2f3' }}>
                            <span className="text-xl">{displayInfo.icon}</span>
                            <h4 className="font-bold text-sm" style={{ color: '#151c27' }}>
                                {displayInfo.label}
                            </h4>
                            <span
                                className="ml-auto text-xs px-2 py-1 rounded-full font-medium"
                                style={{ backgroundColor: '#f0f3ff', color: '#0058be' }}
                            >
                                {perms.length}
                            </span>
                        </div>

                        {/* Permissions Grid */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                            {perms.map((perm) => (
                                <div
                                    key={perm.id}
                                    className="p-3 rounded-lg border"
                                    style={{ backgroundColor: '#f9f9ff', borderColor: '#dce2f3' }}
                                >
                                    <div className="flex items-start justify-between gap-2">
                                        <div className="flex-1 min-w-0">
                                            <p
                                                className="text-sm font-semibold truncate"
                                                style={{ color: '#0058be' }}
                                            >
                                                {perm.code}
                                            </p>
                                            {perm.action && (
                                                <p className="text-xs mt-1" style={{ color: '#727785' }}>
                                                    Action: <span className="font-medium">{perm.action}</span>
                                                </p>
                                            )}
                                            {perm.description && (
                                                <p className="text-xs mt-2" style={{ color: '#727785' }}>
                                                    {perm.description}
                                                </p>
                                            )}
                                        </div>
                                        <span className="text-lg flex-shrink-0">✓</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )
            })}
        </div>
    )
}
