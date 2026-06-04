'use client'

import React from 'react'
import { Department } from '@/types/api'
import { useUserList } from '@/hooks/useUserList'
import { useRBAC } from '@/hooks/useRBAC'

interface AddDepartmentDialogProps {
    isOpen: boolean
    onClose: () => void
    onSubmit: (data: {
        name: string
        description: string
        parent_id: string | null
        manager_id: string | null
    }) => Promise<void>
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
    const { hasPermission } = useRBAC()
    const canReadUsers = hasPermission('user_read')
    const { data: users = [], loading: usersLoading } = useUserList(100, isOpen && canReadUsers)

    const [formData, setFormData] = React.useState({
        name: '',
        description: '',
        parent_id: '' as string,
        manager_id: '' as string,
    })

    const [errors, setErrors] = React.useState<Record<string, string>>({})
    const [showManagerSearch, setShowManagerSearch] = React.useState(false)
    const [managerSearch, setManagerSearch] = React.useState('')
    const [submitError, setSubmitError] = React.useState<string | null>(null)

    React.useEffect(() => {
        if (isOpen) {
            setFormData({
                name: '',
                description: '',
                parent_id: '',
                manager_id: '',
            })
            setErrors({})
            setShowManagerSearch(false)
            setManagerSearch('')
            setSubmitError(null)
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
        setSubmitError(null)

        if (validateForm()) {
            const submitData = {
                name: formData.name.trim(),
                description: formData.description.trim(),
                parent_id: formData.parent_id || null,
                manager_id: formData.manager_id || null,
            }

            // Call onSubmit and handle errors
            onSubmit(submitData).catch((err) => {
                const errorMessage = err instanceof Error ? err.message : 'Không thể tạo phòng ban'
                setSubmitError(errorMessage)
            })
        }
    }

    const selectedManager = users?.find(u => u.id === formData.manager_id)
    const filteredManagers = users?.filter(u =>
        u.full_name?.toLowerCase().includes(managerSearch.toLowerCase()) ||
        u.email?.toLowerCase().includes(managerSearch.toLowerCase()) ||
        u.username?.toLowerCase().includes(managerSearch.toLowerCase())
    ) || []

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white rounded-[24px] w-full max-w-[600px] shadow-2xl relative overflow-hidden p-8 animate-in zoom-in-95 duration-200 max-h-[90vh] overflow-y-auto">
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
                        Tạo mới
                    </span>
                    <h2 className="text-xl font-extrabold text-[#0d1c2e] mb-1">
                        Tạo phòng ban mới
                    </h2>
                    <p className="text-[12px] text-slate-500 font-medium">
                        Thiết lập đơn vị vận hành mới trong hệ thống. Bạn có thể cấu hình thêm thông tin sau.
                    </p>
                </div>

                {/* Error Alert */}
                {submitError && (
                    <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl">
                        <div className="flex items-start gap-3">
                            <span className="material-symbols-outlined text-red-600 flex-shrink-0">error</span>
                            <div className="flex-1">
                                <p className="text-sm font-semibold text-red-900 mb-1">Lỗi tạo phòng ban</p>
                                <p className="text-xs text-red-700">{submitError}</p>
                            </div>
                            <button
                                type="button"
                                onClick={() => setSubmitError(null)}
                                className="text-red-400 hover:text-red-600 transition-colors"
                            >
                                <span className="material-symbols-outlined text-base">close</span>
                            </button>
                        </div>
                    </div>
                )}

                {/* Form */}
                <form onSubmit={handleSubmit} className="space-y-5">
                    {/* Section: Thông tin cơ bản */}
                    <div className="border-b border-slate-100 pb-5">
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                            <span className="material-symbols-outlined text-base">info</span>
                            Thông tin cơ bản
                        </h3>

                        {/* Department Name */}
                        <div className="mb-4">
                            <label className="block text-[10px] font-bold text-slate-700 tracking-widest uppercase mb-2">
                                Tên phòng ban <span className="text-[#9d4300]">*</span>
                            </label>
                            <input
                                type="text"
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                className={`w-full bg-[#f8f9ff] border-none px-4 py-3 rounded-xl text-[13px] outline-none focus:ring-2 focus:ring-[#9d4300]/20 transition-all font-medium text-slate-700 placeholder:text-slate-400 ${errors.name ? 'ring-2 ring-red-400/50 bg-red-50' : ''}`}
                                placeholder="Ví dụ: Marketing Department"
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
                                className="w-full bg-[#f8f9ff] border-none px-4 py-3 rounded-xl text-[13px] outline-none focus:ring-2 focus:ring-[#9d4300]/20 transition-all font-medium text-slate-700 placeholder:text-slate-400 resize-none h-[80px]"
                                placeholder="Nhập chức năng và nhiệm vụ chính của phòng ban..."
                            />
                        </div>
                    </div>

                    {/* Section: Cấu trúc tổ chức */}
                    <div className="border-b border-slate-100 pb-5">
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                            <span className="material-symbols-outlined text-base">account_tree</span>
                            Cấu trúc tổ chức
                        </h3>

                        {/* Parent Department */}
                        <div>
                            <label className="block text-[10px] font-bold text-slate-700 tracking-widest uppercase mb-2">
                                Phòng ban cha (Tùy chọn)
                            </label>
                            <select
                                value={formData.parent_id}
                                onChange={(e) => setFormData({ ...formData, parent_id: e.target.value })}
                                className="w-full bg-[#f8f9ff] border-none px-4 py-3 rounded-xl text-[13px] outline-none focus:ring-2 focus:ring-[#9d4300]/20 transition-all font-medium text-slate-700 cursor-pointer"
                            >
                                <option value="">📦 Không có (Phòng ban gốc)</option>
                                {departments.map((dept) => (
                                    <option key={dept.id} value={dept.id}>↳ {dept.name}</option>
                                ))}
                            </select>
                            <p className="text-[10px] text-slate-400 mt-1.5">Nếu để trống, phòng ban này sẽ là phòng ban cấp cao nhất</p>
                        </div>
                    </div>

                    {/* Section: Quản lý */}
                    <div>
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                            <span className="material-symbols-outlined text-base">person_check</span>
                            Người quản lý
                        </h3>

                        {/* Manager Selection */}
                        <div>
                            <label className="block text-[10px] font-bold text-slate-700 tracking-widest uppercase mb-2">
                                Gán người quản lý (Tùy chọn)
                            </label>

                            {selectedManager ? (
                                <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-xl border border-blue-100">
                                    <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-xs font-bold text-blue-600">
                                        {selectedManager.full_name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || '?'}
                                    </div>
                                    <div className="flex-1">
                                        <p className="text-xs font-semibold text-blue-900">{selectedManager.full_name}</p>
                                        <p className="text-[10px] text-blue-600">{selectedManager.email}</p>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setFormData({ ...formData, manager_id: '' })
                                            setShowManagerSearch(false)
                                        }}
                                        className="p-1.5 text-blue-400 hover:text-blue-600 transition-colors"
                                    >
                                        <span className="material-symbols-outlined text-base">close</span>
                                    </button>
                                </div>
                            ) : (
                                <div className="relative">
                                    <button
                                        type="button"
                                        onClick={() => setShowManagerSearch(!showManagerSearch)}
                                        className="w-full bg-[#f8f9ff] border-none px-4 py-3 rounded-xl text-[13px] outline-none focus:ring-2 focus:ring-[#9d4300]/20 transition-all font-medium text-slate-700 text-left flex items-center justify-between hover:bg-slate-100"
                                    >
                                        <span className="text-slate-400">Chọn người quản lý...</span>
                                        <span className="material-symbols-outlined text-base text-slate-400">expand_more</span>
                                    </button>

                                    {showManagerSearch && (
                                        <div className="absolute top-full left-0 right-0 mt-2 bg-white border border-slate-200 rounded-xl shadow-lg z-10">
                                            <input
                                                type="text"
                                                placeholder="Tìm theo tên, email..."
                                                value={managerSearch}
                                                onChange={(e) => setManagerSearch(e.target.value)}
                                                className="w-full px-4 py-2.5 border-b border-slate-100 text-sm outline-none focus:ring-0 rounded-t-xl"
                                            />
                                            <div className="max-h-[300px] overflow-y-auto">
                                                {usersLoading ? (
                                                    <div className="p-4 text-center text-sm text-slate-500">Đang tải...</div>
                                                ) : filteredManagers.length > 0 ? (
                                                    filteredManagers.map(user => (
                                                        <button
                                                            key={user.id}
                                                            type="button"
                                                            onClick={() => {
                                                                setFormData({ ...formData, manager_id: user.id })
                                                                setShowManagerSearch(false)
                                                                setManagerSearch('')
                                                            }}
                                                            className="w-full px-4 py-3 text-left hover:bg-slate-50 border-b border-slate-50 last:border-b-0 transition-colors flex items-center gap-3"
                                                        >
                                                            <div className="w-7 h-7 rounded-full bg-slate-200 flex items-center justify-center text-[10px] font-bold text-slate-600">
                                                                {user.full_name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || '?'}
                                                            </div>
                                                            <div className="flex-1">
                                                                <p className="text-xs font-semibold text-slate-900">{user.full_name}</p>
                                                                <p className="text-[10px] text-slate-500">{user.email}</p>
                                                            </div>
                                                        </button>
                                                    ))
                                                ) : (
                                                    <div className="p-4 text-center text-sm text-slate-500">Không tìm thấy người dùng</div>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                            <p className="text-[10px] text-slate-400 mt-1.5">Nếu để trống, phòng ban chưa có người quản lý</p>
                        </div>
                    </div>

                    {/* Footer Actions */}
                    <div className="flex items-center justify-end gap-3 pt-6 mt-2 border-t border-slate-100">
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
                            {isLoading ? 'Đang tạo...' : 'Tạo phòng ban'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    )
}
