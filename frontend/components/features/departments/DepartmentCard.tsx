'use client'

import React from 'react'
import { ChevronRight } from 'lucide-react'
import { Department } from '@/types/api'

interface DepartmentCardProps {
    department: Department
    icon?: React.ReactNode
    bgColor?: string
    isSelected?: boolean
    isHighlighted?: boolean
    onSelect?: () => void
}

export function DepartmentCard({
    department,
    icon,
    bgColor = '#ffeaa7',
    isSelected = false,
    isHighlighted = false,
    onSelect,
}: DepartmentCardProps) {
    return (
        <div
            onClick={onSelect}
            className="p-4 rounded-lg transition-all cursor-pointer hover:bg-gray-50"
            style={{
                backgroundColor: isSelected ? '#f5f5f5' : '#ffffff',
                border: isHighlighted ? '2px solid #d35400' : '1px solid #e0e0e0',
                marginBottom: '8px',
            }}
        >
            {/* Container */}
            <div className="flex items-center gap-3">
                {/* Icon */}
                <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{
                        backgroundColor: bgColor,
                    }}
                >
                    {icon}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                    <h3
                        className="font-semibold text-sm"
                        style={{ color: '#151c27' }}
                    >
                        {department.name}
                    </h3>
                    <p
                        className="text-xs mt-0.5"
                        style={{ color: '#727785' }}
                    >
                        {department.member_count} Thành viên • {department.manager?.full_name || 'N/A'}
                    </p>
                </div>

                {/* Arrow */}
                <ChevronRight
                    className="w-5 h-5 flex-shrink-0"
                    style={{ color: '#d35400' }}
                />
            </div>
        </div>
    )
}
