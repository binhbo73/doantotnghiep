'use client'

/**
 * Page Header Component
 * Displays title, description, and action buttons
 */

import React from 'react'
import { Users, Plus } from 'lucide-react'

interface PageHeaderProps {
    title: string
    description?: string
    onAddNew?: () => void
    actionLabel?: string
    icon?: React.ReactNode
}

export function PageHeader({
    title,
    description,
    onAddNew,
    actionLabel = 'Thêm mới',
    icon,
}: PageHeaderProps) {
    return (
        <div className="mb-8">
            {/* Title and Icon */}
            <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">

                    <h1 className="text-3xl font-bold" style={{ color: '#0d1c2e' }}>
                        {title}
                    </h1>
                </div>

                {onAddNew && (
                    <button
                        onClick={onAddNew}
                        className="flex items-center gap-2 px-6 py-2.5 rounded-lg text-white font-medium transition-all hover:shadow-lg"
                        style={{
                            backgroundColor: '#9d4300',
                            backgroundImage: 'linear-gradient(to bottom, #9d4300, #783200)',
                        }}
                    >
                        <Plus size={20} />
                        <span>{actionLabel}</span>
                    </button>
                )}
            </div>

            {/* Description */}
            {description && (
                <p className="text-sm" style={{ color: '#584237' }}>
                    {description}
                </p>
            )}
        </div>
    )
}

export default PageHeader
