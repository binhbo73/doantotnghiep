'use client'

import React from 'react'

interface DashboardHeaderProps {
    userName?: string
    timeOfDay?: string
    daysLabel?: string
    onExport?: () => void
}

export function DashboardHeader({
    userName = 'Admin',
    timeOfDay = 'buổi sáng',
    daysLabel = '7 ngày qua',
    onExport,
}: DashboardHeaderProps) {
    return (
        <div
            className="flex items-center justify-between mb-4 p-3 rounded-lg"
            style={{
                backgroundColor: '#ffffff',
                border: '1px solid #dce2f3',
            }}
        >
            {/* Left: Greeting */}
            <div>
                <h1
                    className="text-xl font-bold mb-0.5"
                    style={{ color: '#151c27' }}
                >
                    Chào {timeOfDay}, {userName} 👋
                </h1>
                <p
                    className="text-xs"
                    style={{ color: '#727785' }}
                >
                    Hệ thống đang vận hành tốt. Duới đây là tóm tắt dữ liệu hôm nay.
                </p>
            </div>

            {/* Right: Time period and Export button */}
            <div className="flex items-center gap-2">
                <span
                    className="text-xs font-medium px-2 py-1 rounded-lg whitespace-nowrap"
                    style={{
                        backgroundColor: '#f0f3ff',
                        color: '#0058be',
                    }}
                >
                    📅 {daysLabel}
                </span>
                <button
                    onClick={onExport}
                    className="px-3 py-1 rounded-lg font-medium text-white transition-all hover:opacity-90 text-xs"
                    style={{
                        backgroundColor: '#b75b00',
                    }}
                >
                    🔖 Xuất báo cáo
                </button>
            </div>
        </div>
    )
}
