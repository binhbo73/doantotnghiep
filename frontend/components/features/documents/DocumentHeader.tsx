'use client'

import React from 'react'

interface DocumentHeaderProps {
    title: string
    subtitle?: string
    totalFolders: number
    totalDocuments: number
    searchQuery: string
    onSearchChange: (query: string) => void
}

export function DocumentHeader({
    title,
    subtitle,
    totalFolders,
    totalDocuments,
    searchQuery,
    onSearchChange,
}: DocumentHeaderProps) {
    return (
        <div className="mb-6">
            {/* Title Row */}
            <div className="flex justify-between items-start mb-4">
                <div>
                    <h1 className="text-2xl font-extrabold tracking-tight text-[#0d1c2e] mb-1 flex items-center gap-2">
                        <span className="material-symbols-outlined text-[#9d4300] text-2xl">inventory_2</span>
                        {title}
                    </h1>
                    {subtitle && (
                        <p className="text-sm text-[#584237] max-w-xl">{subtitle}</p>
                    )}
                </div>
            </div>

            {/* Stats + Search Row */}
            <div className="flex items-center gap-4">
                {/* Stats Chips */}
                <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#fff3e0] rounded-lg border border-[#f97316]/20">
                        <span className="material-symbols-outlined text-[#9d4300] text-base">folder</span>
                        <span className="text-xs font-bold text-[#9d4300]">{totalFolders}</span>
                        <span className="text-xs text-[#9d4300]/70">thư mục</span>
                    </div>
                    <div className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 rounded-lg border border-blue-200/50">
                        <span className="material-symbols-outlined text-blue-600 text-base">description</span>
                        <span className="text-xs font-bold text-blue-700">{totalDocuments}</span>
                        <span className="text-xs text-blue-500">tài liệu</span>
                    </div>
                </div>

                {/* Search */}
                <div className="flex-1 max-w-md relative">
                    <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-lg">search</span>
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => onSearchChange(e.target.value)}
                        placeholder="Tìm kiếm thư mục hoặc tài liệu..."
                        className="w-full pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#9d4300]/20 focus:border-[#9d4300]/40 transition-all"
                    />
                    {searchQuery && (
                        <button
                            onClick={() => onSearchChange('')}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                        >
                            <span className="material-symbols-outlined text-base">close</span>
                        </button>
                    )}
                </div>
            </div>
        </div>
    )
}
