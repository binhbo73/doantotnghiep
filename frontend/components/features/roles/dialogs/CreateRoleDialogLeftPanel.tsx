'use client'

import React from 'react'
import { Shield, Lock, Check, Settings } from 'lucide-react'

interface CreateRoleDialogLeftPanelProps {
    isEdit?: boolean
}

export function CreateRoleDialogLeftPanel({ isEdit = false }: CreateRoleDialogLeftPanelProps) {
    return (
        <div
            className="hidden lg:flex flex-col justify-between p-4 rounded-l-2xl text-white w-[30%]"
            style={{ backgroundColor: '#b75b00' }}
        >
            {/* Header Content */}
            <div>
                {/* Icon - Shield with lock styling */}
                <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center mb-4"
                    style={{ backgroundColor: 'rgba(255, 255, 255, 0.25)' }}
                >
                    <Shield size={24} className="text-white" strokeWidth={1.5} />
                </div>

                {/* Title & Description */}
                <h2 className="text-xl font-bold mb-2 leading-tight">
                    {isEdit ? 'Chỉnh sửa vai trò' : 'Tạo vai trò mới'}
                </h2>
                <p className="text-xs leading-relaxed opacity-95 font-light">
                    {isEdit
                        ? 'Cập nhật thông tin vai trò và quyền hạn liên quan để điều chỉnh hành trị thực.'
                        : 'Thiết lập bộ khung quyền hạn ban đầu dành cho người dùng tương tác với hệ thống.'}
                </p>
            </div>

            {/* Footer - Security Standard */}
            <div>
                {/* Security Icons */}
                <div className="flex gap-2 mb-3">
                    <div className="w-8 h-8 rounded-lg bg-black/30 flex items-center justify-center">
                        <Lock size={16} className="text-white" />
                    </div>
                    <div className="w-8 h-8 rounded-lg bg-black/30 flex items-center justify-center">
                        <Check size={16} className="text-white" />
                    </div>
                    <div className="w-8 h-8 rounded-lg bg-black/30 flex items-center justify-center">
                        <Settings size={16} className="text-white" />
                    </div>
                </div>
                <p className="text-[10px] font-bold uppercase tracking-wider opacity-90">Enterprise Security Standard</p>
            </div>
        </div>
    )
}
