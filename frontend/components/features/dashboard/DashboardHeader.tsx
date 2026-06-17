'use client'

import React from 'react'
import { useRBAC } from '@/hooks/useRBAC'

interface DashboardHeaderProps {
    userName?: string
    timeOfDay?: string
    daysLabel?: string
    onExport?: () => void
}

export function DashboardHeader({
    userName = 'Bạn',
    timeOfDay = 'buổi sáng',
    daysLabel = '7 ngày qua',
    onExport,
}: DashboardHeaderProps) {
    const { getRoleBadge } = useRBAC()
    const badge = getRoleBadge()

    return (
        <div
            className="flex items-center justify-between mb-4 p-3 rounded-lg"
            style={{
                backgroundColor: '#ffffff',
                border: '1px solid #dce2f3',
            }}
        >
            {/* Left: Greeting + Role Badge */}
            <div>
                <div className="flex items-center gap-2 mb-0.5">
                    <h1
                        className="text-xl font-bold"
                        style={{ color: '#151c27' }}
                    >
                        {userName}  
                    </h1>
                    <span
                        className="px-2 py-0.5 rounded-full text-[10px] font-bold border"
                        style={{
                            color: badge.color,
                            backgroundColor: badge.bgColor,
                            borderColor: badge.color + '30',
                        }}
                    >
                        {badge.label}
                    </span>
                </div>
         
            </div>

            {/* Right: Time period and Export button */}

        </div>
    )
}
