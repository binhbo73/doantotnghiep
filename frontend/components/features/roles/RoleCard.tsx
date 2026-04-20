'use client'

import React from 'react'

interface RoleCardProps {
    role: {
        id: string
        name: string
        code: string
        description: string
        memberCount: number
        permissionCount: number
    }
    isSelected?: boolean
    onViewDetails?: (roleId: string) => void
    onEdit?: (roleId: string) => void
}

export function RoleCard({ role, isSelected, onViewDetails, onEdit }: RoleCardProps) {
    return (
        <div
            className="p-4 rounded-lg transition border-2 flex flex-col"
            style={{
                backgroundColor: isSelected ? '#f0f3ff' : '#ffffff',
                borderColor: isSelected ? '#0058be' : '#dce2f3',
                minHeight: '220px',
                height: '100%',
            }}
        >
            {/* Header with Avatar */}
            <div className="flex items-start gap-2 mb-3">
                <div
                    className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-base flex-shrink-0"
                    style={{ backgroundColor: '#0058be' }}
                >
                    {role.name.charAt(0)}
                </div>
                <div className="flex-1">
                    <h3 className="font-bold text-base" style={{ color: '#151c27' }}>
                        {role.name}
                    </h3>
                    <p className="text-xs" style={{ color: '#727785' }}>
                        {role.code}
                    </p>
                </div>
            </div>

            {/* Description */}
            <p className="text-xs mb-3" style={{ color: '#424754', lineHeight: 1.4 }}>
                {role.description}
            </p>

            {/* Stats */}
            <div className="flex items-center gap-2 mb-3 mt-auto">
                <span
                    className="px-2 py-1 rounded-full text-xs font-bold"
                    style={{ backgroundColor: '#f0f3ff', color: '#0058be' }}
                >
                    👥 +{role.memberCount}
                </span>
                <span
                    className="px-2 py-1 rounded-full text-xs font-bold"
                    style={{ backgroundColor: '#f0e8f8', color: '#7c3aed' }}
                >
                    🔐 {role.permissionCount}
                </span>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2 flex-col">
                <button
                    onClick={() => onViewDetails?.(role.id)}
                    className="text-xs font-medium transition flex items-center justify-center gap-1 px-3 py-2 rounded-lg border-2"
                    style={{
                        backgroundColor: '#f0f3ff',
                        color: '#0058be',
                        borderColor: '#0058be',
                    }}
                >
                    👁️ Chi tiết
                </button>
                <button
                    onClick={() => onEdit?.(role.id)}
                    className="text-xs font-medium transition flex items-center justify-center gap-1 px-3 py-2 rounded-lg"
                    style={{ color: '#b75b00', backgroundColor: '#fff8f0' }}
                >
                    ✏️ Chỉnh sửa
                </button>
            </div>
        </div>
    )
}
