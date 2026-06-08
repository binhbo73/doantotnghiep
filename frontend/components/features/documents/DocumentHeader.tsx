'use client'

import { AppIcon } from '@/components/ui/AppIcon'
import React from 'react'
import { useRBAC } from '@/hooks/useRBAC'

interface DocumentHeaderProps {
    title: string
    subtitle?: string
    totalFolders: number
    totalDocuments: number
    searchQuery: string
    onSearchChange: (query: string) => void
    onCreateFolder?: () => void
    compact?: boolean
}

export function DocumentHeader({
    title,
    subtitle,
    totalFolders,
    totalDocuments,
    searchQuery,
    onSearchChange,
    onCreateFolder,
    compact = false,
}: DocumentHeaderProps) {
    const { getRoleBadge } = useRBAC()
    const badge = getRoleBadge()

    return (
        <div className={compact ? 'mb-3' : 'mb-6'}>
            {/* Title Row */}
            <div className={`flex justify-between items-start ${compact ? 'mb-2' : 'mb-4'}`}>
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <h1 className={`${compact ? 'text-xl' : 'text-2xl'} font-extrabold tracking-tight text-[#0d1c2e] flex items-center gap-2`}>
                            <AppIcon name="inventory_2" className={`text-[#9d4300] ${compact ? 'text-xl' : 'text-2xl'}`} />
                            {title}
                        </h1>
                        <span
                            className="px-2 py-0.5 rounded-full text-[10px] font-bold border"
                            style={{ color: badge.color, backgroundColor: badge.bgColor, borderColor: badge.color + '30' }}
                        >
                            {badge.label}
                        </span>
                    </div>
                    {subtitle && (
                        <p className={`${compact ? 'text-xs max-w-2xl' : 'text-sm max-w-xl'} text-[#584237]`}>{subtitle}</p>
                    )}
                </div>
                {onCreateFolder && !compact && (
                    <button
                        onClick={onCreateFolder}
                        className="px-4 py-2 bg-[#9d4300] text-white rounded-xl text-sm font-semibold hover:bg-[#b75b00] transition-colors flex items-center gap-2 shadow-sm hover:shadow-md"
                    >
                        <AppIcon name="create_new_folder" className="text-base" />
                        Tạo Thư Mục
                    </button>
                )}
            </div>

            {/* Stats + Search Row */}
            <div className={`flex items-center gap-4 ${compact ? 'flex-wrap' : ''}`}>
                {/* Stats Chips */}
                <div className="flex items-center gap-2">
                    <div className={`flex items-center gap-1.5 ${compact ? 'px-2.5 py-1' : 'px-3 py-1.5'} bg-[#fff3e0] rounded-lg border border-[#f97316]/20`}>
                        <AppIcon name="folder" className={`text-[#9d4300] ${compact ? 'text-sm' : 'text-base'}`} />
                        <span className={`${compact ? 'text-[11px]' : 'text-xs'} font-bold text-[#9d4300]`}>{totalFolders}</span>
                        <span className={`${compact ? 'text-[11px]' : 'text-xs'} text-[#9d4300]/70`}>thư mục</span>
                    </div>
                    <div className={`flex items-center gap-1.5 ${compact ? 'px-2.5 py-1' : 'px-3 py-1.5'} bg-blue-50 rounded-lg border border-blue-200/50`}>
                        <AppIcon name="description" className={`text-blue-600 ${compact ? 'text-sm' : 'text-base'}`} />
                        <span className={`${compact ? 'text-[11px]' : 'text-xs'} font-bold text-blue-700`}>{totalDocuments}</span>
                        <span className={`${compact ? 'text-[11px]' : 'text-xs'} text-blue-500`}>tài liệu</span>
                    </div>
                </div>

                {/* Search */}
                <div className={`flex-1 relative ${compact ? 'max-w-2xl min-w-[280px]' : 'max-w-md'}`}>
                    <AppIcon name="search" className={`absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 ${compact ? 'text-base' : 'text-lg'}`} />
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => onSearchChange(e.target.value)}
                        placeholder="Tìm kiếm thư mục hoặc tài liệu..."
                        className={`w-full ${compact ? 'pl-9 pr-4 py-1.5 text-[13px]' : 'pl-10 pr-4 py-2 text-sm'} bg-white border border-slate-200 rounded-xl text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#9d4300]/20 focus:border-[#9d4300]/40 transition-all`}
                    />
                    {searchQuery && (
                        <button
                            onClick={() => onSearchChange('')}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                        >
                            <AppIcon name="close" className={`${compact ? 'text-sm' : 'text-base'}`} />
                        </button>
                    )}
                </div>
            </div>
        </div>
    )
}
