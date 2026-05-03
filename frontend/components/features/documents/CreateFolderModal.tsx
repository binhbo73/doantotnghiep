'use client'

import React, { useState, useEffect } from 'react'
import { env } from '@/config/environment'
import { authService } from '@/services/auth'
import { useDocumentStore } from '@/hooks/useDocumentStore'
import { useDepartments } from '@/hooks/useDepartments'

interface CreateFolderModalProps {
    isOpen: boolean
    onClose: () => void
    onSuccess?: () => void
}

export function CreateFolderModal({ isOpen, onClose, onSuccess }: CreateFolderModalProps) {
    const { tree, refetch } = useDocumentStore()
    const { departments } = useDepartments()

    const [folderName, setFolderName] = useState('')
    const [description, setDescription] = useState('')
    const [accessScope, setAccessScope] = useState<'company' | 'department' | 'personal'>('company')
    const [departmentId, setDepartmentId] = useState<string>('')
    const [parentFolderId, setParentFolderId] = useState<string>('')

    const [isCreating, setIsCreating] = useState(false)
    const [error, setError] = useState<string | null>(null)

    // Reset state when modal opens
    useEffect(() => {
        if (isOpen) {
            setFolderName('')
            setDescription('')
            setAccessScope('company')
            setDepartmentId('')
            setParentFolderId('')
            setError(null)
            setIsCreating(false)
        }
    }, [isOpen])

    // Reset parent folder when department changes
    useEffect(() => {
        setParentFolderId('')
    }, [departmentId, accessScope])

    // Flatten folder tree for select options
    const flattenTree = (nodes: typeof tree, depth = 0): { id: string, name: string, depth: number, department_id: string | null }[] => {
        let result: { id: string, name: string, depth: number, department_id: string | null }[] = []
        for (const node of nodes) {
            result.push({ id: node.folder.id, name: node.folder.name, depth, department_id: node.folder.department_id })
            if (node.children && node.children.length > 0) {
                result = result.concat(flattenTree(node.children, depth + 1))
            }
        }
        return result
    }

    const foldersList = flattenTree(tree)
    const displayFoldersList = departmentId
        ? foldersList.filter(f => f.department_id === departmentId)
        : foldersList

    const handleCreate = async () => {
        if (!folderName.trim()) {
            setError('Vui lòng nhập tên thư mục.')
            return
        }

        if (folderName.trim().length > 100) {
            setError('Tên thư mục không quá 100 ký tự.')
            return
        }

        // Enforce department requirement when scope is 'department'
        if (accessScope === 'department' && !departmentId) {
            setError('Vui lòng chọn phòng ban cho thư mục khi phạm vi là Theo Phòng Ban.')
            return
        }

        setIsCreating(true)
        setError(null)

        try {
            const payload: any = {
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

            // Send department_id if selected (allowed for any scope)
            if (departmentId) {
                payload.department_id = departmentId
            }

            const token = authService.getAuthToken()
            if (!token) {
                throw new Error('Bạn chưa đăng nhập hoặc phiên đã hết hạn. Vui lòng đăng nhập lại.')
            }

            const response = await fetch(`${env.apiUrl}/folders`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify(payload),
            })

            if (!response.ok) {
                const data = await response.json()
                throw new Error(data.message || 'Tạo thư mục thất bại.')
            }

            // Refresh data
            if (refetch) {
                await refetch()
            }

            if (onSuccess) onSuccess()
            onClose()
        } catch (err: any) {
            setError(err.message || 'Tạo thư mục thất bại.')
        } finally {
            setIsCreating(false)
        }
    }

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
            <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
                    <div>
                        <h2 className="text-lg font-bold text-slate-800">Tạo Thư Mục</h2>
                        <p className="text-xs text-slate-500 mt-1">Tạo thư mục mới để lưu trữ tài liệu</p>
                    </div>
                    <button
                        onClick={onClose}
                        disabled={isCreating}
                        className="p-2 hover:bg-slate-100 rounded-full transition-colors text-slate-500 disabled:opacity-50"
                    >
                        <span className="material-symbols-outlined text-xl">close</span>
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 overflow-y-auto flex-1 space-y-5">
                    {error && (
                        <div className="p-3 bg-red-50 text-red-600 rounded-xl text-sm border border-red-100 flex items-start gap-2">
                            <span className="material-symbols-outlined text-base flex-shrink-0 mt-0.5">error</span>
                            <span>{error}</span>
                        </div>
                    )}

                    {/* Folder Name */}
                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">
                            Tên Thư Mục <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            value={folderName}
                            onChange={(e) => setFolderName(e.target.value)}
                            placeholder="Nhập tên thư mục..."
                            disabled={isCreating}
                            className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#9d4300]/20 focus:border-[#9d4300]/40 transition-all disabled:bg-slate-50 disabled:text-slate-500"
                        />
                        <p className="text-xs text-slate-500 mt-1">{folderName.length}/100</p>
                    </div>

                    {/* Description */}
                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">
                            Mô Tả
                        </label>
                        <textarea
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder="Nhập mô tả thư mục (tùy chọn)..."
                            disabled={isCreating}
                            rows={3}
                            className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#9d4300]/20 focus:border-[#9d4300]/40 transition-all disabled:bg-slate-50 disabled:text-slate-500 resize-none"
                        />
                    </div>

                    {/* Access Scope */}
                    {/* Department (always shown at top) */}
                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">
                            Phòng Ban {accessScope === 'department' && <span className="text-red-500">*</span>}
                        </label>
                        <select
                            value={departmentId}
                            onChange={(e) => setDepartmentId(e.target.value)}
                            disabled={isCreating}
                            className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#9d4300]/20 focus:border-[#9d4300]/40 transition-all disabled:bg-slate-50 disabled:text-slate-500"
                        >
                            <option value="">-- Không chọn --</option>
                            {departments.map((dept) => (
                                <option key={dept.id} value={dept.id}>{dept.name}</option>
                            ))}
                        </select>
                        <p className="text-xs text-slate-500 mt-2">Phòng ban có thể để trống đối với phạm vi Toàn Công Ty hoặc Cá Nhân. Nếu phạm vi là "Theo Phòng Ban" thì bắt buộc chọn.</p>
                    </div>

                    {/* Access Scope */}
                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">
                            Phạm Vi Truy Cập <span className="text-red-500">*</span>
                        </label>
                        <select
                            value={accessScope}
                            onChange={(e) => setAccessScope(e.target.value as any)}
                            disabled={isCreating}
                            className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#9d4300]/20 focus:border-[#9d4300]/40 transition-all disabled:bg-slate-50 disabled:text-slate-500"
                        >
                            <option value="company">Toàn Công Ty</option>
                            <option value="department">Theo Phòng Ban</option>
                            <option value="personal">Cá Nhân</option>
                        </select>
                    </div>

                    {/* Parent Folder */}
                    <div>
                        <label className="block text-sm font-semibold text-slate-700 mb-2">
                            Thư Mục Cha
                        </label>
                        <select
                            value={parentFolderId}
                            onChange={(e) => setParentFolderId(e.target.value)}
                            disabled={isCreating}
                            className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#9d4300]/20 focus:border-[#9d4300]/40 transition-all disabled:bg-slate-50 disabled:text-slate-500"
                        >
                            <option value="">-- Không có Thư Mục Cha --</option>
                            {displayFoldersList.map((folder) => (
                                <option key={folder.id} value={folder.id}>
                                    {'─'.repeat(folder.depth * 2)} {folder.name}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Footer */}
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
                                <span className="material-symbols-outlined text-base">add</span>
                                Tạo Thư Mục
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    )
}
