'use client'

import React from 'react'

interface QuickAction {
    id: string
    label: string
    icon: React.ReactNode
    onClick?: () => void
}

interface QuickActionButtonsProps {
    actions: QuickAction[]
}

export function QuickActionButtons({ actions }: QuickActionButtonsProps) {
    return (
        <div className="grid grid-cols-2 gap-2">
            {actions.map((action) => (
                <button
                    key={action.id}
                    onClick={action.onClick}
                    className="rounded-lg p-3 transition-all hover:bg-surface_container_low text-center"
                    style={{
                        backgroundColor: '#f0f3ff',
                        border: '1px solid #dce2f3',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '8px',
                        cursor: 'pointer',
                    }}
                >
                    <div
                        className="w-6 h-6 flex items-center justify-center"
                        style={{ color: '#0058be', fontSize: '16px' }}
                    >
                        {action.icon}
                    </div>
                    <span
                        className="text-xs font-medium text-center"
                        style={{ color: '#151c27' }}
                    >
                        {action.label}
                    </span>
                </button>
            ))}
        </div>
    )
}
