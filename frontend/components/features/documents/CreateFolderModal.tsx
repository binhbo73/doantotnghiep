'use client'

import { AppIcon } from '@/components/ui/AppIcon'
import { useEffect, useState } from 'react'
import { useDocumentStore } from '@/hooks/useDocumentStore'
import { useDepartments } from '@/hooks/useDepartments'
import { useRBAC } from '@/hooks/useRBAC'
import { useAuthContext } from '@/context'
import { createFolder } from '@/services/document'
import { filterVisibleDepartments } from '@/lib/departmentAccess'

interface CreateFolderModalProps {
    isOpen: boolean
    onClose: () => void
    onSuccess?: () => void
    defaultAccessScope?: 'company' | 'department' | 'personal'
    defaultDepartmentId?: string | null
    defaultParentFolderId?: string | null
    allowedScopes?: Array<'company' | 'department' | 'personal'>
}

const ACCESS_SCOPE_LABELS = {
    company: 'Toàn công ty',
    department: 'Theo phòng ban',
    personal: 'Cá nhân',
} as const

export function CreateFolderModal({
    isOpen,
    onClose,
    onSuccess,
    defaultAccessScope,
    defaultDepartmentId,
    defaultParentFolderId,
    allowedScopes: allowedScopesProp,
}: CreateFolderModalProps) {
    const { user } = useAuthContext()
    const { hasPermission } = useRBAC()

    const canUseGlobalFolderScopes = hasPermission('system_admin')
    const canReadFolders = hasPermission('folder_read')
    const canReadDocuments = hasPermission('document_read')
    const { tree, refetch } = useDocumentStore({
        enabled: isOpen && (canReadFolders || canReadDocuments),
        canReadFolders,
        canReadDocuments,
    })
    const canReadDepartments = hasPermission('department_read')
    const isDepartmentUser = !canUseGlobalFolderScopes
    const userDepartmentId = user?.department_id ?? ''
    const allowedScopes = allowedScopesProp ?? (canUseGlobalFolderScopes ? ['company', 'department', 'personal'] : ['department'])
    const shouldLoadDepartments = isOpen && allowedScopes.includes('department') && canReadDepartments
    const { departments } = useDepartments(undefined, shouldLoadDepartments)

    const isManager = departments.some(d => d.manager_id === user?.id || (Array.isArray(d.manager_ids) && d.manager_ids.includes(user?.id || '')))
    const visibleDepartments = filterVisibleDepartments({
        user,
        departments,
        isAdmin: hasPermission('system_admin'),
        isTruongPhong: isManager
    })

    const [folderName, setFolderName] = useState('')
    const [description, setDescription] = useState('')
    const [accessScope, setAccessScope] = useState<'company' | 'department' | 'personal'>(
        defaultAccessScope ?? (canUseGlobalFolderScopes ? 'company' : 'department')
    )
    const [departmentId, setDepartmentId] = useState<string>(canUseGlobalFolderScopes ? '' : userDepartmentId)
    const [parentFolderId, setParentFolderId] = useState<string>('')
    const [isCreating, setIsCreating] = useState(false)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        if (isOpen) {
            const initialAccessScope = defaultAccessScope ?? (canUseGlobalFolderScopes ? 'company' : 'department')
            setFolderName('')
            setDescription('')
            setAccessScope(initialAccessScope)
            setDepartmentId(defaultDepartmentId ?? (canUseGlobalFolderScopes ? '' : userDepartmentId))
            setParentFolderId(defaultParentFolderId ?? '')
            setError(null)
            setIsCreating(false)
        }
    }, [isOpen, defaultAccessScope, defaultDepartmentId, defaultParentFolderId, canUseGlobalFolderScopes, userDepartmentId])

    useEffect(() => {
        if (accessScope !== 'department' && !isDepartmentUser) {
            setDepartmentId('')
        } else if (accessScope === 'department') {
            if (visibleDepartments.length === 1 && !departmentId) {
                setDepartmentId(visibleDepartments[0].id)
            } else if (!departmentId && userDepartmentId && visibleDepartments.some(d => d.id === userDepartmentId)) {
                setDepartmentId(userDepartmentId)
            }
        }
    }, [accessScope, isDepartmentUser, visibleDepartments, departmentId, userDepartmentId])

    const flattenTree = (
        nodes: typeof tree,
        depth = 0
    ): { id: string, name: string, depth: number, department_id: string | null, access_scope: string }[] => {
        let result: { id: string, name: string, depth: number, department_id: string | null, access_scope: string }[] = []

        for (const node of nodes) {
            result.push({
                id: node.folder.id,
                name: node.folder.name,
                depth,
                department_id: node.folder.department_id,
                access_scope: node.folder.access_scope,
            })

            if (node.children && node.children.length > 0) {
                result = result.concat(flattenTree(node.children, depth + 1))
            }
        }

        return result
    }

    const foldersList = flattenTree(tree)
    const displayFoldersList = foldersList.filter((folder) => {
        if (allowedScopes.length === 1 && allowedScopes[0] === 'personal') {
            return folder.access_scope === 'personal'
        }

        if (folder.access_scope !== accessScope) return false

        if (accessScope === 'department' && departmentId) {
            return folder.department_id === departmentId
        }

        return true
    })

    const handleCreate = async () => {
        if (!folderName.trim()) {
            setError('Vui lòng nhập tên thư mục.')
            return
        }

        if (folderName.trim().length > 100) {
            setError('Tên thư mục không quá 100 ký tự.')
            return
        }

        if (accessScope === 'department' && !departmentId) {
            setError('Vui lòng chọn phòng ban.')
            return
        }

        setIsCreating(true)
        setError(null)

        try {
            const payload: Parameters<typeof createFolder>[0] = {
                name: folderName.trim(),
                access_scope: accessScope,
            }

            const trimmedDescription = description.trim()
            if (trimmedDescription) {
                payload.description = trimmedDescription
            }

            if (parentFolderId) {
                payload.parent_id = parentFolderId
            }

            if (accessScope === 'department' && departmentId) {
                payload.department_id = departmentId
            }

            await createFolder(payload)
            await refetch?.()
            onSuccess?.()
            onClose()
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Tạo thư mục thất bại.'
            setError(message)
        } finally {
            setIsCreating(false)
        }
    }

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
            <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col">
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
                    <div>
                        <h2 className="text-lg font-bold text-slate-800">Tạo thư mục</h2>
                        <p className="text-xs text-slate-500 mt-1">Tạo thư mục mới để lưu trữ tài liệu</p>
                    </div>
                    <button
                        onClick={onClose}
                        disabled={isCreating}
                        className="p-2 hover:bg-slate-100 rounded-full transition-colors text-slate-500 disabled:opacity-50"
                    >
                        <AppIcon name="close" className="text-xl" />
                    </button>
                </div>

                <div className="p-6 overflow-y-auto flex-1 space-y-5">
                    {error && (
                        <div className="p-3 bg-red-50 text-red-600 rounded-xl text-sm border border-red-100 flex items-start gap-2">
                            <AppIcon name="error" className="text-base flex-shrink-0 mt-0.5" />
                            <span>{error}</span>
                        </div>
                    )}

                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">
                            Tên thư mục <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            value={folderName}
                            onChange={(event) => setFolderName(event.target.value)}
                            placeholder="Nhập tên thư mục..."
                            disabled={isCreating}
                            className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#9d4300]/20 focus:border-[#9d4300]/40 transition-all disabled:bg-slate-50 disabled:text-slate-500"
                        />
                        <p className="text-xs text-slate-500 mt-1">{folderName.length}/100</p>
                    </div>

                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">
                            Mô tả
                        </label>
                        <textarea
                            value={description}
                            onChange={(event) => setDescription(event.target.value)}
                            placeholder="Nhập mô tả thư mục (tùy chọn)..."
                            disabled={isCreating}
                            rows={3}
                            className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#9d4300]/20 focus:border-[#9d4300]/40 transition-all disabled:bg-slate-50 disabled:text-slate-500 resize-none"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">
                            Phạm vi truy cập <span className="text-red-500">*</span>
                        </label>
                        {allowedScopes.length === 1 ? (
                            <div className="px-4 py-3 rounded-2xl bg-slate-50 border border-slate-200 text-sm text-slate-700">
                                {ACCESS_SCOPE_LABELS[allowedScopes[0]]}
                            </div>
                        ) : (
                            <select
                                value={accessScope}
                                onChange={(event) => setAccessScope(event.target.value as typeof accessScope)}
                                disabled={isCreating}
                                className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#9d4300]/20 focus:border-[#9d4300]/40 transition-all disabled:bg-slate-50 disabled:text-slate-500"
                            >
                                {allowedScopes.map((scope) => (
                                    <option key={scope} value={scope}>
                                        {ACCESS_SCOPE_LABELS[scope]}
                                    </option>
                                ))}
                            </select>
                        )}
                    </div>

                    {accessScope === 'department' && (
                        <div>
                            <label className="block text-sm font-semibold text-slate-700 mb-2">
                                Phòng ban <span className="text-red-500">*</span>
                            </label>
                            {visibleDepartments.length === 1 ? (
                                <div className="px-4 py-3 rounded-2xl bg-slate-50 border border-slate-200 text-slate-700">
                                    {visibleDepartments[0].name}
                                </div>
                            ) : (
                                <select
                                    value={departmentId}
                                    onChange={(event) => setDepartmentId(event.target.value)}
                                    disabled={isCreating}
                                    className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#9d4300]/20 focus:border-[#9d4300]/40 transition-all disabled:bg-slate-50 disabled:text-slate-500"
                                >
                                    <option value="">-- Chọn phòng ban --</option>
                                    {visibleDepartments.map((department) => (
                                        <option key={department.id} value={department.id}>{department.name}</option>
                                    ))}
                                </select>
                            )}
                            <p className="text-xs text-slate-500 mt-2">Chọn phòng ban cho thư mục này.</p>
                        </div>
                    )}

                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">
                            Thư mục cha
                        </label>
                        <select
                            value={parentFolderId}
                            onChange={(event) => setParentFolderId(event.target.value)}
                            disabled={isCreating}
                            className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#9d4300]/20 focus:border-[#9d4300]/40 transition-all disabled:bg-slate-50 disabled:text-slate-500"
                        >
                            <option value="">-- Không có thư mục cha --</option>
                            {displayFoldersList.map((folder) => (
                                <option key={folder.id} value={folder.id}>
                                    {'-'.repeat(folder.depth * 2)} {folder.name}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                <div className="border-t border-slate-100 px-6 py-4 bg-slate-50 flex items-center justify-end gap-3">
                    <button
                        onClick={onClose}
                        disabled={isCreating}
                        className="px-4 py-2 rounded-lg border border-slate-200 text-slate-700 font-medium hover:bg-slate-50 transition-colors disabled:opacity-50"
                    >
                        Hủy
                    </button>
                    <button
                        onClick={handleCreate}
                        disabled={isCreating || !folderName.trim()}
                        className="px-6 py-2 rounded-lg bg-[#9d4300] text-white font-semibold hover:bg-[#b75b00] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                        {isCreating ? (
                            <>
                                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                Đang tạo...
                            </>
                        ) : (
                            <>
                                <AppIcon name="add" className="text-base" />
                                Tạo thư mục
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    )
}
