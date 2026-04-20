'use client'

import React, { useState } from 'react'
import { X } from 'lucide-react'

interface CreatePermissionDialogRightPanelProps {
    onClose: () => void
    onSubmit?: (data: {
        name: string
        description: string
        category: string
    }) => void
}

const PERMISSION_CATEGORIES = [
    { value: 'users', label: '👤 Người dùng' },
    { value: 'documents', label: '📄 Tài liệu' },
    { value: 'ai_chat', label: '💬 AI/Chat' },
    { value: 'system', label: '⚙️ Hệ thống' },
    { value: 'audit', label: '📊 Kiểm toán' },
]

export function CreatePermissionDialogRightPanel({
    onClose,
    onSubmit,
}: CreatePermissionDialogRightPanelProps) {
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        category: 'users',
    })

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        onSubmit?.(formData)
    }

    return (
        <div className="flex flex-col p-6 lg:p-8 flex-1 overflow-hidden">
            {/* Close Button - Mobile */}
            <button
                onClick={onClose}
                className="lg:hidden absolute top-4 right-4 p-1 hover:bg-gray-100 rounded transition"
            >
                <X size={24} style={{ color: '#151c27' }} />
            </button>

            <form onSubmit={handleSubmit} className="flex flex-col gap-6 h-full overflow-y-auto pr-2">
                {/* Permission Name */}
                <div>
                    <label className="text-xs font-bold mb-2 block uppercase" style={{ color: '#727785' }}>
                        Tên quyền hạn
                    </label>
                    <input
                        type="text"
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        placeholder="e.g. Đọc dữ liệu"
                        className="w-full px-4 py-3 rounded-lg border text-sm"
                        style={{
                            borderColor: '#dce2f3',
                            color: '#151c27',
                        }}
                        required
                    />
                </div>

                {/* Category */}
                <div>
                    <label className="text-xs font-bold mb-2 block uppercase" style={{ color: '#727785' }}>
                        Danh mục
                    </label>
                    <select
                        value={formData.category}
                        onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                        className="w-full px-4 py-3 rounded-lg border text-sm"
                        style={{
                            borderColor: '#dce2f3',
                            color: '#151c27',
                        }}
                    >
                        {PERMISSION_CATEGORIES.map((cat) => (
                            <option key={cat.value} value={cat.value}>
                                {cat.label}
                            </option>
                        ))}
                    </select>
                </div>

                {/* Description */}
                <div>
                    <label className="text-xs font-bold mb-2 block uppercase" style={{ color: '#727785' }}>
                        Mô tả chi tiết
                    </label>
                    <textarea
                        value={formData.description}
                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                        placeholder="Mô tả chi tiết về quyền hạn này..."
                        rows={4}
                        className="w-full px-4 py-3 rounded-lg border text-sm resize-none"
                        style={{
                            borderColor: '#dce2f3',
                            color: '#151c27',
                        }}
                        required
                    />
                </div>

                {/* Spacer */}
                <div className="flex-1" />

                {/* Action Buttons */}
                <div className="flex gap-3 pt-6 mt-6 border-t" style={{ borderColor: '#dce2f3' }}>
                    <button
                        type="button"
                        onClick={onClose}
                        className="flex-1 px-6 py-3 rounded-lg font-medium transition border-2"
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
                        className="flex-1 px-6 py-3 rounded-lg font-medium text-white transition"
                        style={{ backgroundColor: '#b75b00' }}
                    >
                        Tạo quyền hạn
                    </button>
                </div>
            </form>
        </div>
    )
}
