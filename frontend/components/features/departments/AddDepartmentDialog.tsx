'use client'

import React from 'react'
import { Department } from '@/types/api'

interface AddDepartmentDialogProps {
    isOpen: boolean
    onClose: () => void
    onSubmit: (data: {
        name: string
        description: string
        parent_id: string | null
        manager_id: string | null
    }) => void
    isLoading?: boolean
    departments?: Department[] // For parent selection dropdown
}

export function AddDepartmentDialog({
    isOpen,
    onClose,
    onSubmit,
    isLoading = false,
    departments = [],
}: AddDepartmentDialogProps) {
    const [formData, setFormData] = React.useState({
        name: '',
        description: '',
        parent_id: '' as string,
    })

    const [errors, setErrors] = React.useState<Record<string, string>>({})

    React.useEffect(() => {
        if (isOpen) {
            setFormData({
                name: '',
                description: '',
                parent_id: '',
            })
            setErrors({})
        }
    }, [isOpen])

    const validateForm = () => {
        const newErrors: Record<string, string> = {}
        if (!formData.name.trim()) newErrors.name = 'Tên phòng ban là bắt buộc'
        setErrors(newErrors)
        return Object.keys(newErrors).length === 0
    }

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        if (validateForm()) {
            onSubmit({
                name: formData.name.trim(),
                description: formData.description.trim(),
                parent_id: formData.parent_id || null,
                manager_id: null, // Can be extended later with a user selector
            })
        }
    }

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white rounded-[24px] w-full max-w-[500px] shadow-2xl relative overflow-hidden p-8 animate-in zoom-in-95 duration-200">
                {/* Close Button */}
                <button
                    onClick={onClose}
                    className="absolute top-6 right-6 text-slate-400 hover:text-slate-700 transition-colors bg-slate-50 hover:bg-slate-100 p-1.5 rounded-full"
                >
                    <span className="material-symbols-outlined text-xl block">close</span>
                </button>

                {/* Header */}
                <div className="mb-6">
                    <span className="px-3 py-1 bg-orange-100 text-[#9d4300] text-[10px] font-black uppercase tracking-widest rounded-full mb-3 inline-block">
                        System Node
                    </span>
                    <h2 className="text-xl font-extrabold text-[#0d1c2e] mb-1">
                        Tạo phòng ban mới
                    </h2>
                    <p className="text-[12px] text-slate-500 font-medium">
                        Thiết lập đơn vị vận hành mới trong hệ thống kiến thức.
                    </p>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="space-y-5">
                    {/* Department Name */}
                    <div>
                        <label className="block text-[10px] font-bold text-slate-700 tracking-widest uppercase mb-2">
                            Tên phòng ban <span className="text-[#9d4300]">*</span>
                        </label>
                        <input
                            type="text"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            className={`w-full bg-[#f8f9ff] border-none px-4 py-3 rounded-xl text-[13px] outline-none focus:ring-2 focus:ring-[#9d4300]/20 transition-all font-medium text-slate-700 placeholder:text-slate-400 ${errors.name ? 'ring-2 ring-red-400/50 bg-red-50' : ''}`}
                            placeholder="Ví dụ: Phòng Nghiên cứu & Phát triển"
                        />
                        {errors.name && <p className="text-[11px] font-medium text-red-500 mt-1.5">{errors.name}</p>}
                    </div>

                    {/* Description */}
                    <div>
                        <label className="block text-[10px] font-bold text-slate-700 tracking-widest uppercase mb-2">
                            Mô tả
                        </label>
                        <textarea
                            value={formData.description}
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            className="w-full bg-[#f8f9ff] border-none px-4 py-3 rounded-xl text-[13px] outline-none focus:ring-2 focus:ring-[#9d4300]/20 transition-all font-medium text-slate-700 placeholder:text-slate-400 resize-none h-[100px]"
                            placeholder="Nhập chức năng và nhiệm vụ chính của phòng ban..."
                        />
                    </div>

                    {/* Parent Department */}
                    <div>
                        <label className="block text-[10px] font-bold text-slate-700 tracking-widest uppercase mb-2">
                            Phòng ban cha
                        </label>
                        <select
                            value={formData.parent_id}
                            onChange={(e) => setFormData({ ...formData, parent_id: e.target.value })}
                            className="w-full bg-[#f8f9ff] border-none px-4 py-3 rounded-xl text-[13px] outline-none focus:ring-2 focus:ring-[#9d4300]/20 transition-all font-medium text-slate-700 cursor-pointer appearance-none"
                        >
                            <option value="">Không có (Phòng ban gốc)</option>
                            {departments.map((dept) => (
                                <option key={dept.id} value={dept.id}>{dept.name}</option>
                            ))}
                        </select>
                    </div>

                    {/* Footer Actions */}
                    <div className="flex items-center justify-end gap-3 pt-6 mt-2">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-5 py-2.5 rounded-xl text-[13px] font-bold text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                        >
                            Hủy bỏ
                        </button>
                        <button
                            type="submit"
                            disabled={isLoading}
                            className="px-5 py-2.5 bg-[#9d4300] hover:bg-[#833800] text-white rounded-xl text-[13px] font-bold flex items-center gap-2 transition-all shadow-lg shadow-orange-200 disabled:opacity-50 active:scale-95"
                        >
                            <span className="material-symbols-outlined text-base">check</span>
                            {isLoading ? 'Đang tạo...' : 'Xác nhận tạo'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    )
}
