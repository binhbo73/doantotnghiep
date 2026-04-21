'use client'

import React from 'react'
import { Department } from '@/types/api'

interface DepartmentTableProps {
    departments: Department[]
    isLoading?: boolean
    onEdit?: (id: string) => void
    onDelete?: (id: string) => void
    onRowClick?: (id: string) => void
}

export function DepartmentTable({
    departments,
    isLoading = false,
    onEdit,
    onDelete,
    onRowClick,
}: DepartmentTableProps) {
    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-12">
                <p style={{ color: '#727785' }} className="text-sm">
                    Đang tải...
                </p>
            </div>
        )
    }

    if (departments.length === 0) {
        return (
            <div
                className="flex flex-col items-center justify-center py-12 rounded-lg border-2 border-dashed"
                style={{
                    backgroundColor: '#fafafa',
                    borderColor: '#e0e0e0',
                }}
            >
                <p
                    className="text-sm font-medium"
                    style={{ color: '#151c27' }}
                >
                    Chưa có phòng ban nào
                </p>
            </div>
        )
    }

    return (
        <div className="overflow-x-auto">
            <table className="w-full">
                <thead>
                    <tr style={{ borderColor: '#e0e0e0', borderBottom: '1px solid #e0e0e0' }}>
                        <th
                            className="text-left py-3 px-4 text-xs font-semibold"
                            style={{ color: '#727785' }}
                        >
                            Tên phòng ban
                        </th>
                        <th
                            className="text-left py-3 px-4 text-xs font-semibold"
                            style={{ color: '#727785' }}
                        >
                            Mô tả
                        </th>
                        <th
                            className="text-center py-3 px-4 text-xs font-semibold"
                            style={{ color: '#727785' }}
                        >
                            Thành viên
                        </th>
                        <th
                            className="text-left py-3 px-4 text-xs font-semibold"
                            style={{ color: '#727785' }}
                        >
                            Trưởng phòng
                        </th>
                        <th
                            className="text-left py-3 px-4 text-xs font-semibold"
                            style={{ color: '#727785' }}
                        >
                            Email
                        </th>
                        <th
                            className="text-center py-3 px-4 text-xs font-semibold"
                            style={{ color: '#727785' }}
                        >
                            Hành động
                        </th>
                    </tr>
                </thead>
                <tbody>
                    {departments.map((dept) => (
                        <tr
                            key={dept.id}
                            className="border-b hover:bg-gray-50 cursor-pointer transition-all"
                            style={{ borderColor: '#e0e0e0' }}
                            onClick={() => onRowClick?.(dept.id)}
                        >
                            <td className="py-3 px-4">
                                <p
                                    className="text-sm font-medium"
                                    style={{ color: '#151c27' }}
                                >
                                    {dept.name}
                                </p>
                            </td>
                            <td className="py-3 px-4">
                                <p
                                    className="text-sm line-clamp-1"
                                    style={{ color: '#727785' }}
                                >
                                    {dept.description || 'N/A'}
                                </p>
                            </td>
                            <td className="py-3 px-4">
                                <p
                                    className="text-sm font-semibold text-center"
                                    style={{ color: '#d35400' }}
                                >
                                    {dept.member_count}
                                </p>
                            </td>
                            <td className="py-3 px-4">
                                <p
                                    className="text-sm"
                                    style={{ color: '#151c27' }}
                                >
                                    {dept.manager?.full_name || 'N/A'}
                                </p>
                            </td>
                            <td className="py-3 px-4">
                                <a
                                    href={dept.manager?.email ? `mailto:${dept.manager.email}` : '#'}
                                    className="text-sm"
                                    style={{ color: '#0984e3' }}
                                    onClick={(e) => e.stopPropagation()}
                                >
                                    {dept.manager?.email || 'N/A'}
                                </a>
                            </td>
                            <td className="py-3 px-4">
                                <div className="flex gap-2 justify-center">
                                    {onEdit && (
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation()
                                                onEdit(dept.id)
                                            }}
                                            className="px-2 py-1 text-xs rounded hover:bg-blue-100 transition-all"
                                            style={{ color: '#0984e3' }}
                                        >
                                            Sửa
                                        </button>
                                    )}
                                    {onDelete && (
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation()
                                                onDelete(dept.id)
                                            }}
                                            className="px-2 py-1 text-xs rounded hover:bg-red-100 transition-all"
                                            style={{ color: '#e74c3c' }}
                                        >
                                            Xóa
                                        </button>
                                    )}
                                </div>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}
