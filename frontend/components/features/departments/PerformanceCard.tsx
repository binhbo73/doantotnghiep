'use client'

import React from 'react'
import { BarChart3 } from 'lucide-react'

interface PerformanceCardProps {
    title?: string
    percentage: number
    subtitle?: string
}

export function PerformanceCard({
    title = 'Hiệu suất tính toán',
    percentage = 92,
    subtitle = 'Mức độ hoàn thành của các dự án',
}: PerformanceCardProps) {
    return (
        <div
            className="rounded-lg p-6 text-white"
            style={{
                backgroundColor: '#d35400',
            }}
        >
            <div className="flex items-start justify-between">
                <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                        <BarChart3 className="w-4 h-4" />
                        <p className="text-sm font-semibold uppercase" style={{ letterSpacing: '0.05em' }}>
                            {title}
                        </p>
                    </div>
                    <h3 className="text-4xl font-bold mb-1">{percentage}%</h3>
                    <p className="text-sm opacity-90">{subtitle}</p>
                </div>

                {/* Chart Visual */}
                <div className="flex items-center gap-1">
                    <div className="w-2 h-16 rounded opacity-75" style={{ backgroundColor: 'rgba(255,255,255,0.3)' }} />
                    <div className="w-2 h-20 rounded" style={{ backgroundColor: 'rgba(255,255,255,0.5)' }} />
                    <div className="w-2 h-14 rounded opacity-75" style={{ backgroundColor: 'rgba(255,255,255,0.3)' }} />
                </div>
            </div>
        </div>
    )
}
