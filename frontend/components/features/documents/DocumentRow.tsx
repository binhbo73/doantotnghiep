'use client'

import React from 'react'
import { FolderDocumentResponse } from '@/services/folder'

interface DocumentRowProps {
    document: FolderDocumentResponse
    isSelected: boolean
    onSelect: () => void
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
    if (!bytes || bytes === 0) return '0 B'
    const units = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    const size = (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0)
    return `${size} ${units[i]}`
}

function getStatusConfig(status: string): { label: string; color: string; bg: string; icon: string } {
    switch (status) {
        case 'completed':
            return { label: 'Hoàn thành', color: 'text-green-700', bg: 'bg-green-50 border-green-200', icon: 'check_circle' }
        case 'processing':
            return { label: 'Đang xử lý', color: 'text-amber-700', bg: 'bg-amber-50 border-amber-200', icon: 'hourglass_top' }
        case 'pending':
            return { label: 'Chờ xử lý', color: 'text-blue-700', bg: 'bg-blue-50 border-blue-200', icon: 'schedule' }
        case 'failed':
            return { label: 'Thất bại', color: 'text-red-700', bg: 'bg-red-50 border-red-200', icon: 'error' }
        default:
            return { label: status, color: 'text-slate-600', bg: 'bg-slate-50 border-slate-200', icon: 'help' }
    }
}

export function DocumentRow({ document, isSelected, onSelect }: DocumentRowProps) {
    const fileIcon = getFileIcon(document.file_type)
    const statusConfig = getStatusConfig(document.status)
    const displayName = document.original_name || document.filename

    return (
        <div
            onClick={onSelect}
            className={`group flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-all duration-200 select-none ${
                isSelected
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
                </div>
            </div>

            {/* Status Badge */}
            <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border ${statusConfig.bg} ${statusConfig.color}`}>
                <span className="material-symbols-outlined text-[10px]">{statusConfig.icon}</span>
                {statusConfig.label}
            </div>
        </div>
    )
}

// Re-export helpers for use in other components
export { getFileIcon, formatFileSize, getStatusConfig }
