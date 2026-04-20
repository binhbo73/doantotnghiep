'use client'

import React from 'react'
import { Shield, Lock, Check, Settings } from 'lucide-react'

export function CreatePermissionDialogLeftPanel() {
    return (
        <div
            className="hidden lg:flex flex-col justify-between p-8 rounded-l-2xl text-white w-96"
            style={{ backgroundColor: '#b75b00' }}
        >
            {/* Header Content */}
            <div>
                {/* Icon */}
                <div
                    className="w-16 h-16 rounded-2xl flex items-center justify-center mb-6"
                    style={{ backgroundColor: 'rgba(255, 255, 255, 0.25)' }}
                >
                    <Shield size={32} className="text-white" strokeWidth={1.5} />
                </div>

                {/* Title & Description */}
                <h2 className="text-4xl font-bold mb-4 leading-tight">
                    Tạo quyền hạn mới
                </h2>
                <p className="text-sm leading-relaxed opacity-95 font-light">
                    Định nghĩa quyền hạn mới để phân quyền chi tiết hơn cho người dùng hệ thống.
                </p>
            </div>

            {/* Footer - Security Standard */}
            <div>
                {/* Security Icons */}
                <div className="flex gap-3 mb-4">
                    <div className="w-10 h-10 rounded-lg bg-black/30 flex items-center justify-center">
                        <Lock size={20} className="text-white" />
                    </div>
                    <div className="w-10 h-10 rounded-lg bg-black/30 flex items-center justify-center">
                        <Check size={20} className="text-white" />
                    </div>
                    <div className="w-10 h-10 rounded-lg bg-black/30 flex items-center justify-center">
                        <Settings size={20} className="text-white" />
                    </div>
                </div>
                <p className="text-xs font-bold uppercase tracking-wider opacity-90">Enterprise Security<br />Standard</p>
            </div>
        </div>
    )
}
