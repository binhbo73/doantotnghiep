'use client'

import React from 'react'
import { Department } from '@/types/api'

interface DepartmentSidebarProps {
    department: Department | null
    onClose?: () => void
    members?: Array<{
        id: string
        name: string
        avatar?: string
    }>
    files?: Array<{
        id: string
        name: string
        size: string
    }>
}

export function DepartmentSidebar({
    department,
    onClose,
    members = [],
    files = [],
}: DepartmentSidebarProps) {
    if (!department) {
        return (
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-[#e0c0b1]/30 h-full flex items-center justify-center min-h-[400px]">
                <p className="text-sm text-slate-500 font-medium text-center">
                    Chọn phòng ban để xem chi tiết
                </p>
            </div>
        )
    }

    const member_count = department.member_count || 0

    return (
        <div className="bg-white p-4 rounded-xl shadow-sm border border-[#e0c0b1]/30 relative">
            {onClose && (
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 p-2 hover:bg-slate-100 rounded-lg transition-colors"
                >
                    <span className="material-symbols-outlined text-slate-400">close</span>
                </button>
            )}

            <div className="flex justify-between items-start mb-3 pt-1">
                <div>
                    <span className="px-2 py-0.5 bg-orange-100 text-orange-700 text-[9px] font-bold uppercase rounded tracking-wider mb-1 inline-block">Đang xem chi tiết</span>
                    <h2 className="text-lg font-black text-[#0d1c2e] leading-none mb-1">{department.name}</h2>
                </div>
                <div className="w-10 h-10 rounded-lg overflow-hidden bg-slate-100">
                    <img alt="Team activity" className="w-full h-full object-cover" src="https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&q=80&w=200"/>
                </div>
            </div>

            {/* Manager Section */}
            <div className="mb-5">
                <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Người quản lý</h3>
                <div className="flex items-center gap-2 bg-[#eff4ff] p-2 rounded-lg">
                    <div className="w-8 h-8 rounded-full ring-2 ring-white bg-blue-100 flex items-center justify-center text-[10px] font-bold text-blue-600">
                        {department.manager?.full_name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || '??'}
                    </div>
                    <div className="flex-1">
                        <p className="text-xs font-bold text-[#0d1c2e]">{department.manager?.full_name || 'Chưa bổ nhiệm'}</p>
                        <p className="text-[10px] text-[#584237] truncate max-w-[150px]">{department.description || 'Quản lý phòng ban'}</p>
                    </div>
                    {department.manager?.email && (
                        <a href={`mailto:${department.manager.email}`} className="p-1 text-[#9d4300] hover:bg-[#9d4300]/10 rounded-full transition-colors flex items-center justify-center">
                            <span className="material-symbols-outlined text-base">mail</span>
                        </a>
                    )}
                </div>
            </div>

            {/* Members Section */}
            <div className="mb-5">
                <div className="flex justify-between items-center mb-2">
                    <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Thành viên ({member_count})</h3>
                    <a className="text-[10px] font-bold text-[#9d4300] hover:underline" href="#">Xem tất cả</a>
                </div>
                <div className="flex -space-x-2">
                    {[1, 2, 3, 4].map((i) => (
                        <div key={i} className="w-7 h-7 rounded-full border-2 border-white bg-slate-200 flex items-center justify-center text-[8px] font-bold text-slate-500 overflow-hidden">
                            <span className="material-symbols-outlined text-sm">person</span>
                        </div>
                    ))}
                    {member_count > 4 && (
                        <div className="w-7 h-7 rounded-full bg-slate-100 border-2 border-white flex items-center justify-center text-[9px] font-bold text-slate-500">
                            +{member_count - 4}
                        </div>
                    )}
                </div>
            </div>

            {/* Documents Section */}
            <div>
                <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Tài liệu bộ phận</h3>
                <div className="space-y-1.5">
                    {files.length > 0 ? files.map((file, idx) => (
                        <div key={file.id} className="flex items-center gap-2 p-2 border border-[#e0c0b1]/30 rounded-lg hover:bg-slate-50 transition-colors cursor-pointer group">
                            <span className={`material-symbols-outlined text-lg ${idx % 2 === 0 ? 'text-orange-400' : 'text-blue-400'}`}>{idx % 2 === 0 ? 'description' : 'table_chart'}</span>
                            <div className="flex-1">
                                <p className="text-xs font-semibold text-[#0d1c2e] leading-tight">{file.name}</p>
                                <p className="text-[9px] text-slate-400">{file.size}</p>
                            </div>
                            <span className="material-symbols-outlined text-base text-slate-300 group-hover:text-[#9d4300] transition-colors">download</span>
                        </div>
                    )) : (
                        <div className="flex items-center gap-2 p-2 border border-slate-100 rounded-lg bg-slate-50">
                            <div className="flex-1 text-center">
                                <p className="text-[10px] text-slate-500">Chưa có tài liệu</p>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
