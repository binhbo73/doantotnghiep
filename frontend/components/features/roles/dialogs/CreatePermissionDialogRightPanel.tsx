'use client'

import React, { useState } from 'react'
import { X } from 'lucide-react'

interface CreatePermissionDialogRightPanelProps {
    onClose: () => void
    onSubmit?: (data: {
        code: string
        name: string
        description: string
        resource: string
        action: string
    }) => void
}

const PERMISSION_RESOURCES = [
    { value: 'users', label: '👤 Người dùng' },
    { value: 'documents', label: '📄 Tài liệu' },
    { value: 'chat', label: '💬 AI/Chat' },
    { value: 'system', label: '⚙️ Hệ thống' },
    { value: 'audit', label: '📊 Kiểm toán' },
    { value: 'folders', label: '📁 Thư mục' },
    { value: 'roles', label: '👑 Vai trò' },
    { value: 'permissions', label: '🔐 Quyền hạn' },
    { value: 'embeddings', label: '🧠 Embeddings' },
    { value: 'rag', label: '🔍 RAG' },
]

export function CreatePermissionDialogRightPanel({
    onClose,
    onSubmit,
}: CreatePermissionDialogRightPanelProps) {
    const [formData, setFormData] = useState({
        code: '',
        name: '',
        description: '',
        resource: 'documents',
        action: 'approve',
    })
    const [isSubmitting, setIsSubmitting] = useState(false)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        try {
            setIsSubmitting(true)
            await onSubmit?.(formData)
        } finally {
            setIsSubmitting(false)
        }
    }

    return (
        <div className="flex flex-1 flex-col p-5">
            {/* Close Button - Mobile */}
            <button
                onClick={onClose}
                className="lg:hidden absolute top-4 right-4 p-1 hover:bg-gray-100 rounded transition"
            >
                <X size={24} style={{ color: '#151c27' }} />
            </button>

            <form onSubmit={handleSubmit} className="flex flex-col gap-3">
                {/* Permission Code */}
                <div>
                    <label className="mb-1 block text-[11px] font-bold uppercase" style={{ color: '#727785' }}>
                        Mã quyền hạn
                    </label>
                    <input
                        type="text"
                        value={formData.code}
                        onChange={(e) => setFormData({ ...formData, code: e.target.value.toLowerCase() })}
                        placeholder="document_approve"
                        className="w-full rounded-lg border px-3 py-2 text-sm"
                        style={{
                            borderColor: '#dce2f3',
                            color: '#151c27',
                        }}
                        required
                    />
                </div>

                {/* Permission Name */}
                <div>
                    <label className="mb-1 block text-[11px] font-bold uppercase" style={{ color: '#727785' }}>
                        Tên quyền hạn
                    </label>
                    <input
                        type="text"
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        placeholder="e.g. Đọc dữ liệu"
                        className="w-full rounded-lg border px-3 py-2 text-sm"
                        style={{
                            borderColor: '#dce2f3',
                            color: '#151c27',
                        }}
                        required
                    />
                </div>

                {/* Category */}
                <div>
                    <label className="mb-1 block text-[11px] font-bold uppercase" style={{ color: '#727785' }}>
                        Resource
                    </label>
                    <select
                        value={formData.resource}
                        onChange={(e) => setFormData({ ...formData, resource: e.target.value })}
                        className="w-full rounded-lg border px-3 py-2 text-sm"
                        style={{
                            borderColor: '#dce2f3',
                            color: '#151c27',
                        }}
                    >
                        {PERMISSION_RESOURCES.map((cat) => (
                            <option key={cat.value} value={cat.value}>
                                {cat.label}
                            </option>
                        ))}
                    </select>
                </div>

                {/* Action */}
                <div>
                    <label className="mb-1 block text-[11px] font-bold uppercase" style={{ color: '#727785' }}>
                        Action
                    </label>
                    <input
                        type="text"
                        value={formData.action}
                        onChange={(e) => setFormData({ ...formData, action: e.target.value.toLowerCase() })}
                        placeholder="approve"
                        className="w-full rounded-lg border px-3 py-2 text-sm"
                        style={{
                            borderColor: '#dce2f3',
                            color: '#151c27',
                        }}
                        required
                    />
                </div>

                {/* Description */}
                <div>
                    <label className="mb-1 block text-[11px] font-bold uppercase" style={{ color: '#727785' }}>
                        Mô tả chi tiết
                    </label>
                    <textarea
                        value={formData.description}
                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                        placeholder="Mô tả chi tiết về quyền hạn này..."
                        rows={3}
                        className="w-full resize-none rounded-lg border px-3 py-2 text-sm"
                        style={{
                            borderColor: '#dce2f3',
                            color: '#151c27',
                        }}
                        required
                    />
                </div>

                {/* Action Buttons */}
                <div className="mt-2 flex gap-3 border-t pt-4" style={{ borderColor: '#dce2f3' }}>
                    <button
                        type="button"
                        onClick={onClose}
                        className="flex-1 rounded-lg border-2 px-4 py-2 text-sm font-medium transition"
                        style={{
                            backgroundColor: '#ffffff',
                            color: '#b75b00',
                            borderColor: '#b75b00',
                        }}
                    >
                        Hủy bỏ
                    </button>
                    <button
                        type="submit"
                        disabled={isSubmitting}
                        className="flex-1 rounded-lg px-4 py-2 text-sm font-medium text-white transition disabled:opacity-60"
                        style={{ backgroundColor: '#b75b00' }}
                    >
                        {isSubmitting ? 'Đang tạo...' : 'Tạo quyền hạn'}
                    </button>
                </div>
            </form>
        </div>
    )
}
