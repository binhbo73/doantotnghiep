'use client'

import React from 'react'
import { Shield, Lock, Check, Settings } from 'lucide-react'

export function CreatePermissionDialogLeftPanel() {
    return (
        <div
            className="hidden w-72 flex-col justify-between rounded-l-2xl p-6 text-white lg:flex"
            style={{ backgroundColor: '#b75b00' }}
        >
            {/* Header Content */}
            <div>
                {/* Icon */}
                <div
                    className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl"
                    style={{ backgroundColor: 'rgba(255, 255, 255, 0.25)' }}
                >
                    <Shield size={28} className="text-white" strokeWidth={1.5} />
                </div>

                {/* Title & Description */}
                <h2 className="mb-3 text-3xl font-bold leading-tight">
                    Tạo quyền hạn mới
                </h2>
                <p className="text-xs font-light leading-relaxed opacity-95">
                    Định nghĩa quyền hạn mới để phân quyền chi tiết hơn cho người dùng hệ thống.
                </p>
            </div>

            {/* Footer - Security Standard */}
            <div>
                {/* Security Icons */}
                <div className="mb-3 flex gap-2">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-black/30">
                        <Lock size={17} className="text-white" />
                    </div>
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-black/30">
                        <Check size={17} className="text-white" />
                    </div>
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-black/30">
                        <Settings size={17} className="text-white" />
                    </div>
                </div>
                <p className="text-[10px] font-bold uppercase tracking-wider opacity-90">Enterprise Security<br />Standard</p>
            </div>
        </div>
    )
}
