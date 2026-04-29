'use client'

import React from 'react'
import { FolderDocumentResponse } from '@/services/folder'

interface DocumentRowProps {
    document: FolderDocumentResponse
    isSelected: boolean
    onSelect: () => void
    folderName?: string
    departmentName?: string
    depth?: number
}

// ─── Helpers ──────────────────────────────────────────────

function getFileIcon(fileType: string): { icon: string; color: string; bg: string } {
    const type = fileType?.toLowerCase() || ''
    if (type.includes('pdf')) return { icon: 'picture_as_pdf', color: 'text-red-600', bg: 'bg-red-50' }
    if (type.includes('doc') || type.includes('word')) return { icon: 'article', color: 'text-blue-600', bg: 'bg-blue-50' }
    if (type.includes('xls') || type.includes('excel') || type.includes('sheet')) return { icon: 'table_chart', color: 'text-green-600', bg: 'bg-green-50' }
    if (type.includes('ppt') || type.includes('powerpoint') || type.includes('presentation')) return { icon: 'slideshow', color: 'text-orange-600', bg: 'bg-orange-50' }
    if (type.includes('zip') || type.includes('rar') || type.includes('tar') || type.includes('gz')) return { icon: 'folder_zip', color: 'text-amber-600', bg: 'bg-amber-50' }
    if (type.includes('png') || type.includes('jpg') || type.includes('jpeg') || type.includes('gif') || type.includes('svg') || type.includes('webp')) return { icon: 'image', color: 'text-purple-600', bg: 'bg-purple-50' }
    if (type.includes('mp4') || type.includes('avi') || type.includes('mov') || type.includes('video')) return { icon: 'movie', color: 'text-pink-600', bg: 'bg-pink-50' }
    if (type.includes('txt') || type.includes('text')) return { icon: 'text_snippet', color: 'text-slate-600', bg: 'bg-slate-100' }
    if (type.includes('md') || type.includes('markdown')) return { icon: 'code', color: 'text-indigo-600', bg: 'bg-indigo-50' }
    if (type.includes('json') || type.includes('xml') || type.includes('yaml') || type.includes('yml')) return { icon: 'data_object', color: 'text-teal-600', bg: 'bg-teal-50' }
    return { icon: 'draft', color: 'text-slate-500', bg: 'bg-slate-100' }
}

function formatFileSize(bytes: number): string {
    const safeBytes = Number(bytes)
    if (!Number.isFinite(safeBytes) || safeBytes <= 0) return '0 B'

    const units = ['B', 'KB', 'MB', 'GB']
    const unitIndex = Math.min(Math.floor(Math.log(safeBytes) / Math.log(1024)), units.length - 1)
    const size = (safeBytes / Math.pow(1024, unitIndex)).toFixed(unitIndex > 0 ? 1 : 0)
    return `${size} ${units[unitIndex]}`
}

export function DocumentRow({
    document,
    isSelected,
    onSelect,
    folderName,
    departmentName,
}: DocumentRowProps) {
    const fileIcon = getFileIcon(document.file_type)
    const displayName = document.original_name || document.filename

    return (
        <div
            onClick={onSelect}
            className={`group flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-all duration-200 select-none ${isSelected
                ? 'bg-[#fff3e0] ring-1 ring-[#9d4300]/30 shadow-sm'
                : 'hover:bg-white hover:shadow-sm'
                }`}
        >
            {/* File Type Icon */}
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${fileIcon.bg} ${fileIcon.color} transition-transform group-hover:scale-105`}>
                <span className="material-symbols-outlined text-base">{fileIcon.icon}</span>
            </div>

            {/* File Info */}
            <div className="flex-1 min-w-0">
                <p className={`text-xs font-semibold truncate leading-tight ${isSelected ? 'text-[#9d4300]' : 'text-slate-800'}`}>
                    {displayName}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px] text-slate-400 uppercase font-medium">{document.file_type}</span>
                    <span className="text-[10px] text-slate-300">•</span>
                    <span className="text-[10px] text-slate-400">{formatFileSize(document.file_size)}</span>
                    {/* Folder and Department */}
                    {(folderName || departmentName) && (
                        <>
                            <span className="text-[10px] text-slate-300">•</span>
                            <div className="flex items-center gap-2">
                                {folderName && (
                                    <span className="text-[10px] bg-slate-50 px-2 py-0.5 rounded text-slate-500 border border-slate-100">{folderName}</span>
                                )}
                                {departmentName && (
                                    <span className="text-[10px] bg-slate-50 px-2 py-0.5 rounded text-slate-500 border border-slate-100">{departmentName}</span>
                                )}
                            </div>
                        </>
                    )}
                </div>
            </div>

        </div>
    )
}

// Re-export helpers for use in other components
export { getFileIcon, formatFileSize }
