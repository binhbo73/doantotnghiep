'use client'

import React, { useState, useMemo } from 'react'
import { Search, X } from 'lucide-react'
import { IamPermission } from '@/types/api'

interface PermissionWithChecked extends IamPermission {
    checked: boolean
}

interface PermissionsSelectorProps {
    isOpen: boolean
    permissions: PermissionWithChecked[]
    onClose: () => void
    onToggle: (permissionId: string) => void
    onCreateNew?: () => void
}

const RESOURCE_CATEGORIES: Record<string, { label: string; color: string }> = {
    users: { label: '👤 Người dùng', color: '#e8f4f8' },
    documents: { label: '📄 Tài liệu', color: '#f0f8e8' },
    chat: { label: '💬 AI/Chat', color: '#f8f4e8' },
    system: { label: '⚙️ Hệ thống', color: '#f4e8f8' },
    audit: { label: '📊 Kiểm toán', color: '#f8e8e8' },
    embeddings: { label: '🧠 Embeddings', color: '#f8f0e8' },
    rag: { label: '🔍 RAG', color: '#f0e8f8' },
    permissions: { label: '🔐 Quyền hạn', color: '#f8f4e8' },
    roles: { label: '👑 Vai trò', color: '#e8f8f4' },
}

export function PermissionsSelector({
    isOpen,
    permissions,
    onClose,
    onToggle,
    onCreateNew,
}: PermissionsSelectorProps) {
    const [searchQuery, setSearchQuery] = useState('')

    // Group permissions by resource and filter by search
    const groupedPermissions = useMemo(() => {
        const groups: Record<string, PermissionWithChecked[]> = {}

        permissions
            .filter((p) => {
                const searchLower = searchQuery.toLowerCase()
                return (
                    (p.code && p.code.toLowerCase().includes(searchLower)) ||
                    (p.description && p.description.toLowerCase().includes(searchLower))
                )
            })
            .forEach((perm) => {
                const resource = perm.resource || 'other'
                if (!groups[resource]) {
                    groups[resource] = []
                }
                groups[resource].push(perm)
            })

        return groups
    }, [permissions, searchQuery])

    const checkedCount = permissions.filter((p) => p.checked).length

    // Handle select all permissions in a category
    const handleSelectAllCategory = (category: string) => {
        const categoryPerms = groupedPermissions[category]
        if (!categoryPerms) return

        const allChecked = categoryPerms.every((p) => p.checked)

        categoryPerms.forEach((perm) => {
            // Only toggle if the state needs to change
            if (allChecked && perm.checked) {
                onToggle(perm.id)
            } else if (!allChecked && !perm.checked) {
                onToggle(perm.id)
            }
        })
    }

    if (!isOpen) return null

    return (
        <>
            {/* Overlay - Only on main content area */}
            <div className="fixed top-0 right-0 bottom-0 bg-black/30 z-20" style={{ left: '240px' }} onClick={onClose} />

            {/* Modal - Only on main content area */}
            <div className="fixed top-0 right-0 bottom-0 z-30 flex items-center justify-center p-4" style={{ left: '240px' }}>
                <div className="bg-white rounded-2xl shadow-2xl w-full max-w-6xl max-h-[90vh] flex flex-col overflow-hidden">
                    {/* Header */}
                    <div className="p-6 border-b" style={{ borderColor: '#dce2f3' }}>
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-2xl font-bold" style={{ color: '#151c27' }}>
                                Chọn Quyền Hạn
                            </h2>
                            <button
                                onClick={onClose}
                                className="p-1 hover:bg-gray-100 rounded transition"
                            >
                                <X size={24} style={{ color: '#151c27' }} />
                            </button>
                        </div>

                        {/* Search */}
                        <div className="relative">
                            <Search
                                size={18}
                                className="absolute left-3 top-3"
                                style={{ color: '#727785' }}
                            />
                            <input
                                type="text"
                                placeholder="Tìm kiếm quyền hạn..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full pl-10 pr-4 py-2 rounded-lg border text-sm"
                                style={{
                                    borderColor: '#dce2f3',
                                    color: '#151c27',
                                }}
                            />
                        </div>

                        {/* Info */}
                        <p className="text-xs mt-3" style={{ color: '#727785' }}>
                            Đã chọn <span style={{ color: '#0058be', fontWeight: 600 }}>{checkedCount}</span> quyền hạn
                        </p>
                    </div>

                    {/* Content - Grouped Permissions */}
                    <div className="flex-1 overflow-y-auto p-6 space-y-6">
                        {Object.entries(groupedPermissions).length === 0 ? (
                            <div className="text-center py-8">
                                <p style={{ color: '#727785' }}>Không tìm thấy quyền hạn</p>
                            </div>
                        ) : (
                            Object.entries(groupedPermissions).map(([resource, perms]) => {
                                const allChecked = perms.every((p) => p.checked)
                                const someChecked = perms.some((p) => p.checked)

                                return (
                                    <div key={resource}>
                                        {/* Category Header */}
                                        <div className="flex items-center gap-3 mb-3 px-3 py-2 rounded-lg cursor-pointer transition hover:opacity-80"
                                            style={{
                                                backgroundColor: RESOURCE_CATEGORIES[resource as keyof typeof RESOURCE_CATEGORIES]?.color || '#f9f9ff',
                                            }}
                                            onClick={() => handleSelectAllCategory(resource)}
                                        >
                                            <input
                                                type="checkbox"
                                                checked={allChecked}
                                                onChange={() => handleSelectAllCategory(resource)}
                                                className="w-5 h-5 rounded cursor-pointer"
                                                style={{ accentColor: '#0058be' }}
                                            />
                                            <h3 className="text-sm font-bold" style={{ color: '#151c27' }}>
                                                {RESOURCE_CATEGORIES[resource as keyof typeof RESOURCE_CATEGORIES]?.label || resource}
                                            </h3>
                                            {allChecked && (
                                                <span className="ml-auto text-lg" style={{ color: '#0058be' }}>
                                                    ✓
                                                </span>
                                            )}
                                        </div>

                                        {/* Permissions Grid */}
                                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-2">
                                            {perms.map((permission) => (
                                                <label
                                                    key={permission.id}
                                                    className="flex items-start gap-3 p-3 rounded-lg cursor-pointer transition border"
                                                    style={{
                                                        backgroundColor: permission.checked ? '#f0f3ff' : '#ffffff',
                                                        borderColor: permission.checked ? '#0058be' : '#dce2f3',
                                                    }}
                                                >
                                                    <div className="flex-shrink-0 mt-0.5">
                                                        <input
                                                            type="checkbox"
                                                            checked={permission.checked}
                                                            onChange={() => onToggle(permission.id)}
                                                            className="w-5 h-5 rounded cursor-pointer"
                                                            style={{ accentColor: '#0058be' }}
                                                        />
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <p
                                                            className="text-sm font-semibold"
                                                            style={{
                                                                color: permission.checked ? '#151c27' : '#727785',
                                                            }}
                                                        >
                                                            {permission.code}
                                                        </p>
                                                        {permission.description && (
                                                            <p className="text-xs mt-1" style={{ color: '#727785' }}>
                                                                {permission.description}
                                                            </p>
                                                        )}
                                                    </div>
                                                    {permission.checked && (
                                                        <span className="flex-shrink-0 text-lg" style={{ color: '#0058be' }}>
                                                            ✓
                                                        </span>
                                                    )}
                                                </label>
                                            ))}
                                        </div>
                                    </div>
                                )
                            })
                        )}
                    </div>

                    {/* Footer */}
                    <div className="p-6 border-t flex gap-3" style={{ borderColor: '#dce2f3' }}>
                        <button
                            onClick={onCreateNew}
                            className="flex-1 px-4 py-3 rounded-lg font-medium transition border-2"
                            style={{
                                backgroundColor: '#ffffff',
                                color: '#0058be',
                                borderColor: '#0058be',
                            }}
                        >
                            ➕ Tạo quyền hạn mới
                        </button>
                        <button
                            onClick={onClose}
                            className="flex-1 px-4 py-3 rounded-lg font-medium text-white transition"
                            style={{ backgroundColor: '#0058be' }}
                        >
                            Hoàn tất
                        </button>
                    </div>
                </div>
            </div>
        </>
    )
}
