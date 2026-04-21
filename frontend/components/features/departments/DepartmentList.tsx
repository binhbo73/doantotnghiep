'use client'

import React from 'react'
import { useRouter } from 'next/navigation'
import { Department } from '@/types/api'

interface DepartmentListProps {
    departments: Department[]
    onAdd?: () => void
    onExport?: () => void
}

export function DepartmentList({ departments, onAdd, onExport }: DepartmentListProps) {
    const router = useRouter()
    const totalDepartments = departments.length
    const totalMembers = departments.reduce((acc, d) => acc + (d.member_count || 0), 0)

    // Calculate max depth for "Cấp bậc tối đa"
    const levels = departments.some(d => d.parent_id) ? 2 : 1

    const getInitials = (name?: string) => {
        if (!name) return '??'
        return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
    }

    const handleNavigateToDepartmentDetail = (deptId: string) => {
        router.push(`/dashboard/departments/${deptId}`)
    }

    const getColorClass = (idx: number) => {
        const colors = [
            'bg-orange-100 text-orange-600',
            'bg-blue-100 text-blue-600',
            'bg-green-100 text-green-600',
            'bg-purple-100 text-purple-600',
            'bg-rose-100 text-rose-600'
        ]
        return colors[idx % colors.length]
    }

    return (
        <div className="w-full animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Dashboard Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className="p-4 bg-white rounded-xl shadow-sm border border-[#e0c0b1]/30">
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Tổng phòng ban</p>
                    <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-black text-slate-900">{totalDepartments}</span>
                        <span className="text-[11px] font-bold text-[#9d4300]">+2 tháng này</span>
                    </div>
                </div>
                <div className="p-4 bg-white rounded-xl shadow-sm border border-[#e0c0b1]/30">
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Nhân sự thực tế</p>
                    <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-black text-slate-900">{totalMembers}</span>
                        <span className="text-[11px] font-bold text-blue-600">98% Active</span>
                    </div>
                </div>
                <div className="p-4 bg-white rounded-xl shadow-sm border border-[#e0c0b1]/30">
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Cấp bậc tối đa</p>
                    <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-black text-slate-900">{`0${levels}`}</span>
                        <span className="text-[11px] font-bold text-slate-400">Tầng phân cấp</span>
                    </div>
                </div>
                <div
                    onClick={onAdd}
                    className="p-4 bg-gradient-to-br from-[#9d4300] to-[#f97316] rounded-xl shadow-lg flex items-center justify-between text-white cursor-pointer hover:shadow-orange-200 hover:-translate-y-1 transition-all active:scale-95"
                >
                    <div>
                        <p className="text-[10px] font-bold opacity-80 uppercase tracking-widest mb-1">Hành động</p>
                        <p className="text-base font-bold leading-tight">Thêm phòng<br />ban mới</p>
                    </div>
                    <span className="material-symbols-outlined text-3xl opacity-80">add_circle</span>
                </div>
            </div>

            {/* Filters & Search */}
            <div className="flex flex-col md:flex-row gap-3 mb-4 items-center justify-between">
                <div className="relative w-full md:w-96">
                    <span className="absolute inset-y-0 left-3 flex items-center text-slate-400">
                        <span className="material-symbols-outlined text-lg">search</span>
                    </span>
                    <input
                        className="w-full pl-10 pr-3 py-2 bg-white border border-[#e0c0b1]/30 rounded-xl text-xs focus:ring-2 focus:ring-[#9d4300]/20 transition-all outline-none"
                        placeholder="Tìm theo tên hoặc mã phòng ban..."
                        type="text"
                    />
                </div>
                <div className="flex gap-2 w-full md:w-auto">
                    <button className="flex-1 md:flex-none flex items-center justify-center gap-1.5 px-3 py-2 bg-white border border-[#e0c0b1]/30 rounded-xl text-xs font-medium text-slate-600 hover:bg-slate-50 transition-colors">
                        <span className="material-symbols-outlined text-base">filter_list</span>
                        Bộ lọc nâng cao
                    </button>
                    {onExport && (
                        <button onClick={onExport} className="flex-1 md:flex-none flex items-center justify-center gap-1.5 px-3 py-2 bg-white border border-[#e0c0b1]/30 rounded-xl text-xs font-medium text-slate-600 hover:bg-slate-50 transition-colors">
                            <span className="material-symbols-outlined text-base">download</span>
                            Xuất báo cáo
                        </button>
                    )}
                </div>
            </div>

            {/* List View Table */}
            <div className="bg-white rounded-2xl overflow-hidden shadow-sm border border-[#e0c0b1]/30">
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-slate-50/50 border-b border-slate-100">
                                <th className="px-5 py-3 text-[10px] font-black text-slate-400 uppercase tracking-widest whitespace-nowrap">Tên phòng ban</th>
                                <th className="px-5 py-3 text-[10px] font-black text-slate-400 uppercase tracking-widest whitespace-nowrap">Quản lý</th>
                                <th className="px-5 py-3 text-[10px] font-black text-slate-400 uppercase tracking-widest whitespace-nowrap">Phòng ban cha</th>
                                <th className="px-5 py-3 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center whitespace-nowrap">Thành viên</th>
                                <th className="px-5 py-3 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right whitespace-nowrap">Hành động</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-50">
                            {departments.map((dept, idx) => {
                                const initials = getInitials(dept.name)
                                const colorClass = getColorClass(idx)

                                return (
                                    <tr key={dept.id} className="hover:bg-slate-50/80 transition-colors group">
                                        <td className="px-5 py-3">
                                            <div className="flex items-center gap-3 cursor-pointer" onClick={() => handleNavigateToDepartmentDetail(dept.id)}>
                                                <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs ${colorClass}`}>
                                                    {initials}
                                                </div>
                                                <div>
                                                    <p className="text-sm font-semibold text-slate-900 group-hover:text-[#9d4300] transition-colors">{dept.name}</p>
                                                    <p className="text-[11px] text-slate-400 line-clamp-1 max-w-[200px]">{dept.description || 'Chưa có mô tả'}</p>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-5 py-3">
                                            <div className="flex items-center gap-2.5">
                                                <div className="w-7 h-7 rounded-full bg-slate-200 flex items-center justify-center text-[10px] font-bold text-slate-500 overflow-hidden">
                                                    {getInitials(dept.manager?.full_name)}
                                                </div>
                                                <div className="flex flex-col">
                                                    <span className="text-xs font-semibold text-slate-700">{dept.manager?.full_name || 'Chưa bổ nhiệm'}</span>
                                                    <span className="text-[10px] text-slate-400">{dept.manager?.email || 'N/A'}</span>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-5 py-3 text-xs text-slate-500">
                                            {dept.parent ? (
                                                <span className="px-2.5 py-0.5 bg-slate-100/80 rounded-md text-[11px] font-semibold text-slate-600 w-max inline-block">{dept.parent.name}</span>
                                            ) : (
                                                <span className="px-2.5 py-0.5 bg-orange-100 text-orange-700 rounded-md text-[11px] font-semibold w-max inline-block">Tổ chức cao nhất</span>
                                            )}
                                        </td>
                                        <td className="px-5 py-3 text-center">
                                            <span className="text-xs font-bold text-slate-800">{dept.member_count}</span>
                                        </td>
                                        <td className="px-5 py-3 text-right">
                                            <div className="flex items-center justify-end gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                                                <button
                                                    onClick={() => handleNavigateToDepartmentDetail(dept.id)}
                                                    className="p-1.5 text-slate-400 hover:text-[#9d4300] bg-white hover:bg-orange-50 rounded shadow-sm border border-transparent transition-all"
                                                    title="Xem chi tiết"
                                                >
                                                    <span className="material-symbols-outlined text-base">open_in_new</span>
                                                </button>
                                                <button className="p-1.5 text-slate-400 hover:text-[#9d4300] bg-white hover:bg-orange-50 rounded shadow-sm border border-transparent transition-all">
                                                    <span className="material-symbols-outlined text-base">edit</span>
                                                </button>
                                                <button className="p-1.5 text-slate-400 hover:text-red-600 bg-white hover:bg-red-50 rounded shadow-sm border border-transparent transition-all">
                                                    <span className="material-symbols-outlined text-base">delete</span>
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>

                {/* Pagination */}
                <div className="px-6 py-3 border-t border-slate-50 flex items-center justify-between bg-white">
                    <p className="text-[11px] font-medium text-slate-400">Hiển thị 1-{Math.min(10, totalDepartments)} trong số {totalDepartments} phòng ban</p>
                    <div className="flex gap-1">
                        <button className="w-7 h-7 flex items-center justify-center rounded-lg border border-slate-100 text-slate-400 hover:bg-slate-50 disabled:opacity-50" disabled>
                            <span className="material-symbols-outlined text-xs">chevron_left</span>
                        </button>
                        <button className="w-7 h-7 flex items-center justify-center rounded-lg bg-[#f97316] text-white text-[11px] font-bold shadow-md">1</button>
                        <button className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-slate-50 text-[11px] font-medium text-slate-600">2</button>
                        <button className="w-7 h-7 flex items-center justify-center rounded-lg border border-slate-100 text-slate-400 hover:bg-slate-50">
                            <span className="material-symbols-outlined text-xs">chevron_right</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}
