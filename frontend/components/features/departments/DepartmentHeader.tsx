'use client'

import React from 'react'

interface DepartmentHeaderProps {
    title: string
    subtitle?: string
    viewMode?: 'tree' | 'list'
    onViewModeChange?: (mode: 'tree' | 'list') => void
}

export function DepartmentHeader({
    title,
    subtitle,
    viewMode = 'tree',
    onViewModeChange,
}: DepartmentHeaderProps) {
    return (
        <div className="flex justify-between items-end mb-8">
            <div>
                <h1 className="text-3xl font-extrabold tracking-tight text-[#0d1c2e] mb-1">{title}</h1>
                {subtitle && (
                    <p className="text-sm text-[#584237] max-w-xl">{subtitle}</p>
                )}
            </div>
            
            <div className="flex bg-[#e6eeff] p-1 rounded-xl shadow-inner">
                <button 
                    onClick={() => onViewModeChange?.('tree')}
                    className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-all ${viewMode === 'tree' ? 'text-primary bg-white shadow-sm font-bold rounded-lg' : 'text-slate-600 hover:text-slate-900'}`}
                >
                    <span className="material-symbols-outlined text-lg">account_tree</span>
                    Cây
                </button>
                <button 
                    onClick={() => onViewModeChange?.('list')}
                    className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-all ${viewMode === 'list' ? 'text-primary bg-white shadow-sm font-bold rounded-lg' : 'text-slate-600 hover:text-slate-900'}`}
                >
                    <span className="material-symbols-outlined text-lg" style={{ fontVariationSettings: "'FILL' 1" }}>list</span>
                    Danh sách
                </button>
            </div>
        </div>
    )
}
