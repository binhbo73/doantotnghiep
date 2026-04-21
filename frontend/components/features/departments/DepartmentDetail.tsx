'use client'

import React from 'react'
import { ChevronLeft, Users, Mail, Building2, Edit2, Trash2 } from 'lucide-react'

interface DepartmentDetailProps {
    department: {
        id: string
        name: string
        description: string
        memberCount: number
        leadName: string
        leadEmail: string
    }
    onBack: () => void
    onEdit?: () => void
    onDelete?: () => void
}

export function DepartmentDetail({
    department,
    onBack,
    onEdit,
    onDelete,
}: DepartmentDetailProps) {
    return (
        <div
            className="rounded-lg p-6"
            style={{
                backgroundColor: '#ffffff',
                border: '1px solid #f0f0f0',
            }}
        >
            {/* Header */}
            <div className="flex items-start justify-between mb-6 pb-4 border-b" style={{ borderColor: '#e0e0e0' }}>
                <div className="flex items-center gap-4 flex-1">
                    <button
                        onClick={onBack}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-all"
                    >
                        <ChevronLeft className="w-5 h-5" style={{ color: '#727785' }} />
                    </button>
                    <div>
                        <h1
                            className="text-2xl font-bold"
                            style={{ color: '#151c27' }}
                        >
                            {department.name}
                        </h1>
                        <p
                            className="text-sm mt-1"
                            style={{ color: '#727785' }}
                        >
                            ID: {department.id}
                        </p>
                    </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                    {onEdit && (
                        <button
                            onClick={onEdit}
                            className="px-4 py-2 rounded-lg border flex items-center gap-2 transition-all hover:bg-gray-50"
                            style={{
                                backgroundColor: '#ffffff',
                                borderColor: '#e0e0e0',
                                color: '#727785',
                            }}
                        >
                            <Edit2 className="w-4 h-4" />
                            <span className="text-sm">Chỉnh sửa</span>
                        </button>
                    )}
                    {onDelete && (
                        <button
                            onClick={onDelete}
                            className="px-4 py-2 rounded-lg border flex items-center gap-2 transition-all hover:bg-red-50"
                            style={{
                                backgroundColor: '#ffffff',
                                borderColor: '#e0e0e0',
                                color: '#e74c3c',
                            }}
                        >
                            <Trash2 className="w-4 h-4" />
                            <span className="text-sm">Xóa</span>
                        </button>
                    )}
                </div>
            </div>

            {/* Content Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Left Column */}
                <div className="space-y-4">
                    {/* Description */}
                    <div
                        className="rounded-lg p-4"
                        style={{
                            backgroundColor: '#f9fafb',
                            border: '1px solid #f0f0f0',
                        }}
                    >
                        <h3
                            className="text-xs font-semibold mb-2 uppercase"
                            style={{ color: '#727785', letterSpacing: '0.05em' }}
                        >
                            Mô tả
                        </h3>
                        <p
                            className="text-sm"
                            style={{ color: '#151c27', lineHeight: '1.6' }}
                        >
                            {department.description}
                        </p>
                    </div>

                    {/* Member Count */}
                    <div
                        className="rounded-lg p-4 flex items-start gap-3"
                        style={{
                            backgroundColor: '#f9fafb',
                            border: '1px solid #f0f0f0',
                        }}
                    >
                        <div
                            className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                            style={{
                                backgroundColor: '#e8f4f8',
                            }}
                        >
                            <Users className="w-5 h-5" style={{ color: '#0984e3' }} />
                        </div>
                        <div>
                            <p
                                className="text-xs font-semibold"
                                style={{ color: '#727785' }}
                            >
                                Tổng thành viên
                            </p>
                            <p
                                className="text-lg font-bold mt-1"
                                style={{ color: '#0984e3' }}
                            >
                                {department.memberCount}
                            </p>
                        </div>
                    </div>
                </div>

                {/* Right Column */}
                <div className="space-y-4">
                    {/* Lead Information */}
                    <div
                        className="rounded-lg p-4"
                        style={{
                            backgroundColor: '#f9fafb',
                            border: '1px solid #f0f0f0',
                        }}
                    >
                        <h3
                            className="text-xs font-semibold mb-3 uppercase"
                            style={{ color: '#727785', letterSpacing: '0.05em' }}
                        >
                            Trưởng phòng
                        </h3>

                        <div className="flex items-center gap-3 mb-3">
                            <div
                                className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold text-white"
                                style={{ backgroundColor: '#d35400' }}
                            >
                                {department.leadName.charAt(0)}
                            </div>
                            <div>
                                <p
                                    className="text-sm font-medium"
                                    style={{ color: '#151c27' }}
                                >
                                    {department.leadName}
                                </p>
                                <p
                                    className="text-xs"
                                    style={{ color: '#727785' }}
                                >
                                    Trưởng phòng
                                </p>
                            </div>
                        </div>

                        <div className="flex items-center gap-2 pt-3 border-t" style={{ borderColor: '#e0e0e0' }}>
                            <Mail className="w-4 h-4" style={{ color: '#727785' }} />
                            <a
                                href={`mailto:${department.leadEmail}`}
                                className="text-sm"
                                style={{ color: '#0984e3' }}
                            >
                                {department.leadEmail}
                            </a>
                        </div>
                    </div>

                    {/* Department Info Card */}
                    <div
                        className="rounded-lg p-4 flex items-start gap-3"
                        style={{
                            backgroundColor: '#f9fafb',
                            border: '1px solid #f0f0f0',
                        }}
                    >
                        <div
                            className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                            style={{
                                backgroundColor: '#fff3e0',
                            }}
                        >
                            <Building2 className="w-5 h-5" style={{ color: '#d35400' }} />
                        </div>
                        <div>
                            <p
                                className="text-xs font-semibold"
                                style={{ color: '#727785' }}
                            >
                                Trạng thái
                            </p>
                            <p
                                className="text-sm font-medium mt-1"
                                style={{ color: '#00b894' }}
                            >
                                ✓ Hoạt động
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Team Members Section */}
            <div className="mt-6 pt-6 border-t" style={{ borderColor: '#e0e0e0' }}>
                <h3
                    className="text-lg font-semibold mb-4"
                    style={{ color: '#151c27' }}
                >
                    Thành viên ({department.memberCount})
                </h3>
                <div
                    className="rounded-lg p-6 text-center"
                    style={{
                        backgroundColor: '#f9fafb',
                        border: '1px dashed #e0e0e0',
                    }}
                >
                    <p
                        className="text-sm"
                        style={{ color: '#727785' }}
                    >
                        Danh sách thành viên sẽ được hiển thị tại đây
                    </p>
                </div>
            </div>
        </div>
    )
}
