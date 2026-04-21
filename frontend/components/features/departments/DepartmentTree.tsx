import React, { useMemo } from 'react'
import { Department } from '@/types/api'

interface DepartmentTreeProps {
    departments: Department[]
    selectedId?: string | null
    onSelect?: (id: string) => void
}

const getIconForName = (name: string) => {
    if (name.includes('Giám Đốc') || name.includes('mẹ')) return { icon: 'corporate_fare', color: 'text-on-primary-container', bg: 'bg-primary-container' }
    if (name.includes('Tài Chính')) return { icon: 'payments', color: 'text-blue-600', bg: 'bg-blue-50' }
    if (name.includes('Công Nghệ') || name.includes('IT')) return { icon: 'engineering', color: 'text-orange-600', bg: 'bg-orange-50' }
    if (name.includes('Phần mềm') || name.includes('DevOps')) return { icon: 'code', color: 'text-slate-600', bg: 'bg-slate-200' }
    if (name.includes('An ninh') || name.includes('QA')) return { icon: 'security', color: 'text-slate-600', bg: 'bg-slate-200' }
    if (name.includes('Marketing') || name.includes('Kinh doanh')) return { icon: 'campaign', color: 'text-purple-600', bg: 'bg-purple-50' }
    return { icon: 'business', color: 'text-slate-600', bg: 'bg-slate-100' }
}

export function DepartmentTree({ departments, selectedId, onSelect }: DepartmentTreeProps) {
    const rootDepartments = useMemo(() => departments.filter((d) => !d.parent_id), [departments])
    
    const getChildren = (parentId: string) => departments.filter((d) => d.parent_id === parentId)

    const renderNode = (node: Department, depth: number = 0) => {
        const children = getChildren(node.id)
        const isSelected = selectedId === node.id
        const isRoot = depth === 0
        const isLevel2 = depth >= 2
        
        const { icon, color, bg } = getIconForName(node.name)

        return (
            <div key={node.id} className="relative">
                {depth > 0 && (
                    <div className="absolute left-[-28px] top-1/2 w-7 h-px bg-[#e0c0b1]"></div>
                )}
                
                <div 
                    onClick={() => onSelect?.(node.id)}
                    className={`p-2 rounded-xl cursor-pointer transition-all group ${
                        isRoot 
                            ? 'bg-[#ffeaa7]/30 border border-[#f97316]/30 flex items-center justify-between' 
                            : isLevel2
                                ? `py-1.5 px-2 rounded-lg flex items-center gap-2 hover:bg-white border border-transparent hover:border-[#e0c0b1] select-none ${isSelected ? 'bg-white ring-1 ring-[#9d4300] shadow-sm' : 'bg-slate-50'}`
                                : `bg-white shadow-sm border hover:border-[#f97316] select-none ${isSelected ? 'ring-2 ring-[#9d4300] border-transparent shadow-md' : 'border-transparent'}`
                    }`}
                >
                    {isLevel2 ? (
                        <>
                            <div className={`w-6 h-6 rounded-md flex items-center justify-center ${bg} ${color}`}>
                                <span className="material-symbols-outlined text-[10px]">{icon}</span>
                            </div>
                            <span className="text-xs font-medium text-slate-800">{node.name}</span>
                        </>
                    ) : (
                        <div className="flex items-center justify-between w-full">
                            <div className="flex items-center gap-2.5">
                                <div className={`w-7 h-7 ${isRoot ? 'w-8 h-8' : ''} rounded-lg flex items-center justify-center ${bg} ${color}`}>
                                    <span className={`material-symbols-outlined ${isRoot ? 'text-xl' : 'text-base'}`}>{icon}</span>
                                </div>
                                <div className="min-w-0">
                                    <h3 className={`font-semibold ${isRoot ? 'text-sm' : 'text-xs'} text-slate-900 leading-tight truncate`}>{node.name}</h3>
                                    <p className={`${isRoot ? 'text-[10px]' : 'text-[9px]'} text-slate-400 leading-tight mt-0.5 truncate max-w-[150px]`}>{node.description || 'Chưa có mô tả'}</p>
                                </div>
                            </div>
                            
                            {isRoot ? (
                                <div className="flex opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button className="p-1 hover:bg-white rounded-lg text-slate-400 hover:text-[#9d4300] transition-colors"><span className="material-symbols-outlined text-sm">edit</span></button>
                                    <button className="p-1 hover:bg-white rounded-lg text-slate-400 hover:text-red-500 transition-colors"><span className="material-symbols-outlined text-sm">delete</span></button>
                                </div>
                            ) : (
                                <span className={`material-symbols-outlined text-lg ${isSelected ? 'text-[#9d4300]' : 'text-slate-300'}`}>
                                    {isSelected ? 'radio_button_checked' : 'chevron_right'}
                                </span>
                            )}
                        </div>
                    )}
                </div>

                {children.length > 0 && (
                    <div className={`${depth === 0 ? 'ml-8 mt-3' : 'ml-6 mt-2.5'} space-y-${depth === 0 ? '3' : '2'} relative`}>
                        <div className={`absolute left-[-28px] ${depth === 0 ? 'top-[-12px]' : 'top-[-10px]'} w-px h-[calc(100%-12px)] bg-[#e0c0b1]`}></div>
                        {children.map(child => renderNode(child, depth + 1))}
                    </div>
                )}
            </div>
        )
    }

    return (
        <div className="col-span-12 lg:col-span-7 bg-[#ffffff] shadow-sm ring-1 ring-slate-100 p-5 rounded-2xl">
            <div className="flex justify-between items-center mb-5">
                <h2 className="text-base font-bold flex items-center gap-2 text-slate-800">
                    <span className="material-symbols-outlined text-[#9d4300] text-lg">account_tree</span>
                    Sơ đồ Tổ chức
                </h2>
            </div>

            <div className="space-y-4">
                {rootDepartments.map(node => renderNode(node, 0))}
                {rootDepartments.length === 0 && departments.length > 0 && (
                    <p className="text-xs text-slate-400 text-center py-10">Không tìm thấy gốc tổ chức. Kiểm tra dữ liệu phân cấp.</p>
                )}
            </div>
        </div>
    )
}
