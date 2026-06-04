'use client'

import React from 'react'
import { Department } from '@/types/api'
import { useUserList } from '@/hooks/useUserList'
import { useRBAC } from '@/hooks/useRBAC'

interface EditDepartmentDialogProps {
    isOpen: boolean
    onClose: () => void
    onSubmit: (data: {
        name: string
        description: string
        manager_id: string | null
    }) => Promise<void>
    isLoading?: boolean
    department?: Department | null
}

export function EditDepartmentDialog({
    isOpen,
    onClose,
    onSubmit,
    isLoading = false,
    department,
}: EditDepartmentDialogProps) {
    const { hasPermission } = useRBAC()
    const canReadUsers = hasPermission('user_read')
    const { data: users = [], loading: usersLoading } = useUserList(100, isOpen && canReadUsers)

    const [formData, setFormData] = React.useState({
        name: '',
        description: '',
        manager_id: '',
    })

    const [errors, setErrors] = React.useState<Record<string, string>>({})
    const [showManagerSearch, setShowManagerSearch] = React.useState(false)
    const [managerSearch, setManagerSearch] = React.useState('')
    const [submitError, setSubmitError] = React.useState<string | null>(null)

    React.useEffect(() => {
        if (isOpen && department) {
            setFormData({
                name: department.name || '',
                description: department.description || '',
                manager_id: department.manager?.id || '',
            })
            setErrors({})
            setShowManagerSearch(false)
            setManagerSearch('')
            setSubmitError(null)
        }
    }, [isOpen, department])

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
                manager_id: formData.manager_id || null,
            }

            // Call onSubmit and handle errors
            onSubmit(submitData).catch((err) => {
                const errorMessage = err instanceof Error ? err.message : 'Không thể cập nhật phòng ban'
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

    if (!isOpen || !department) return null

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
                    <span className="px-3 py-1 bg-blue-100 text-blue-600 text-[10px] font-black uppercase tracking-widest rounded-full mb-3 inline-block">
                        Chỉnh sửa
                    </span>
                    <h2 className="text-xl font-extrabold text-[#0d1c2e] mb-1">
                        Cập nhật phòng ban
                    </h2>
                    <p className="text-[12px] text-slate-500 font-medium">
                        Thay đổi thông tin chi tiết phòng ban.
                    </p>
                </div>

                {/* Error Alert */}
                {submitError && (
                    <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl">
                        <div className="flex items-start gap-3">
                            <span className="material-symbols-outlined text-red-600 flex-shrink-0">error</span>
                            <div className="flex-1">
                                <p className="text-sm font-semibold text-red-900 mb-1">Lỗi cập nhật phòng ban</p>
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
                                placeholder="e.g., Marketing Department"
                                className={`w-full px-4 py-2.5 text-sm border-2 rounded-xl font-medium transition-all outline-none ${errors.name
                                        ? 'border-red-400 focus:border-red-500 focus:ring-2 focus:ring-red-200'
                                        : 'border-slate-200 focus:border-[#9d4300] focus:ring-2 focus:ring-[#9d4300]/20'
                                    }`}
                            />
                            {errors.name && (
                                <p className="text-xs text-red-500 mt-1 font-medium">{errors.name}</p>
                            )}
                        </div>

                        {/* Description */}
                        <div>
                            <label className="block text-[10px] font-bold text-slate-700 tracking-widest uppercase mb-2">
                                Mô tả
                            </label>
                            <textarea
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                placeholder="Describe the department's purpose and responsibilities..."
                                rows={4}
                                className="w-full px-4 py-2.5 text-sm border-2 border-slate-200 rounded-xl font-medium transition-all outline-none focus:border-[#9d4300] focus:ring-2 focus:ring-[#9d4300]/20 resize-none"
                            />
                        </div>
                    </div>

                    {/* Section: Quản lý */}
                    <div>
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                            <span className="material-symbols-outlined text-base">person_check</span>
                            Người quản lý
                        </h3>

                        {/* Manager Display & Edit */}
                        <div>
                            <label className="block text-[10px] font-bold text-slate-700 tracking-widest uppercase mb-2">
                                Người quản lý hiện tại
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
                                        onClick={() => setShowManagerSearch(!showManagerSearch)}
                                        className="p-1.5 text-blue-600 hover:text-blue-700 hover:bg-blue-100 transition-colors rounded-lg"
                                        title="Thay đổi người quản lý"
                                    >
                                        <span className="material-symbols-outlined text-base">edit</span>
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setFormData({ ...formData, manager_id: '' })
                                            setShowManagerSearch(false)
                                        }}
                                        className="p-1.5 text-blue-400 hover:text-red-600 transition-colors rounded-lg"
                                        title="Xóa người quản lý"
                                    >
                                        <span className="material-symbols-outlined text-base">delete</span>
                                    </button>
                                </div>
                            ) : (
                                <div>
                                    <div className="relative">
                                        <button
                                            type="button"
                                            onClick={() => setShowManagerSearch(!showManagerSearch)}
                                            className="w-full bg-slate-50 border-2 border-slate-200 px-4 py-3 rounded-xl text-[13px] outline-none focus:ring-2 focus:ring-[#9d4300]/20 transition-all font-medium text-slate-700 text-left flex items-center justify-between hover:bg-slate-100"
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
                                    <p className="text-[10px] text-slate-400 mt-1.5">Nếu để trống, phòng ban chưa có người quản lý</p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3 pt-4 border-t border-slate-100">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 px-4 py-2.5 text-sm font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-xl transition-all"
                        >
                            Hủy
                        </button>
                        <button
                            type="submit"
                            disabled={isLoading}
                            className="flex-1 px-4 py-2.5 text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl transition-all flex items-center justify-center gap-2"
                        >
                            {isLoading ? (
                                <>
                                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                    Đang lưu...
                                </>
                            ) : (
                                <>
                                    <span className="material-symbols-outlined text-base">check</span>
                                    Lưu thay đổi
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    )
}
