'use client'

import React from 'react'
import { FolderDocumentResponse, FolderResponse } from '@/services/folder'
import { getFileIcon, formatFileSize, getStatusConfig } from './DocumentRow'

interface DocumentSidebarProps {
    document: FolderDocumentResponse | null
    folder: FolderResponse | null
    onClose: () => void
}

function formatDate(dateStr: string): string {
    try {
        const d = new Date(dateStr)
        return d.toLocaleDateString('vi-VN', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
        })
    } catch {
        return dateStr
    }
}

export function DocumentSidebar({ document, folder, onClose }: DocumentSidebarProps) {
    if (!document) {
        return (
            <div className="col-span-12 lg:col-span-5 bg-white shadow-sm ring-1 ring-slate-100 rounded-2xl p-6 flex flex-col items-center justify-center min-h-[400px]">
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center mb-4">
                    <span className="material-symbols-outlined text-4xl text-slate-300">draft</span>
                </div>
                <p className="text-sm font-medium text-slate-500 mb-1">Chọn tài liệu</p>
                <p className="text-xs text-slate-400 text-center max-w-[200px]">
                    Nhấn vào tài liệu trong cây thư mục để xem chi tiết
                </p>
            </div>
        )
    }

    const fileIcon = getFileIcon(document.file_type)
    const statusConfig = getStatusConfig(document.status)
    const displayName = document.original_name || document.filename

    return (
        <div className="col-span-12 lg:col-span-5 bg-white shadow-sm ring-1 ring-slate-100 rounded-2xl overflow-hidden">
            {/* Preview Header */}
            <div className="relative h-44 bg-gradient-to-br from-[#f97316]/10 via-[#fff7ed] to-[#fef3c7] flex items-center justify-center">
                {/* Close button */}
                <button
                    onClick={onClose}
                    className="absolute top-3 right-3 w-7 h-7 rounded-lg bg-white/80 backdrop-blur-sm flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-white transition-all shadow-sm"
                >
                    <span className="material-symbols-outlined text-base">close</span>
                </button>

                {/* Large file icon */}
                <div className={`w-20 h-20 rounded-2xl flex items-center justify-center ${fileIcon.bg} ${fileIcon.color} shadow-lg`}>
                    <span className="material-symbols-outlined text-4xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                        {fileIcon.icon}
                    </span>
                </div>
            </div>

            {/* Content */}
            <div className="p-5 space-y-5">
                {/* File Name & Type */}
                <div>
                    <h3 className="text-sm font-bold text-slate-900 leading-snug mb-1">{displayName}</h3>
                    <p className="text-[11px] text-slate-400">
                        Tệp tin {document.file_type?.toUpperCase()} • {formatFileSize(document.file_size)}
                    </p>
                </div>

                {/* Detail Info Grid */}
                <div className="space-y-3">
                    <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Chi tiết tài liệu</h4>

                    <div className="grid grid-cols-2 gap-3">
                        {/* Status */}
                        <div className="space-y-1">
                            <span className="text-[10px] font-medium text-slate-400">Trạng thái</span>
                            <div className={`flex items-center gap-1 text-xs font-semibold ${statusConfig.color}`}>
                                <span className="material-symbols-outlined text-xs">{statusConfig.icon}</span>
                                {statusConfig.label}
                            </div>
                        </div>

                        {/* File Type */}
                        <div className="space-y-1">
                            <span className="text-[10px] font-medium text-slate-400">Định dạng</span>
                            <p className="text-xs font-semibold text-slate-700 uppercase">{document.file_type}</p>
                        </div>

                        {/* Created Date */}
                        <div className="space-y-1">
                            <span className="text-[10px] font-medium text-slate-400">Ngày tạo</span>
                            <p className="text-xs font-semibold text-slate-700">{formatDate(document.created_at)}</p>
                        </div>

                        {/* Updated Date */}
                        <div className="space-y-1">
                            <span className="text-[10px] font-medium text-slate-400">Lần cuối sửa</span>
                            <p className="text-xs font-semibold text-slate-700">{formatDate(document.updated_at)}</p>
                        </div>
                    </div>
                </div>

                {/* Folder Location */}
                {folder && (
                    <div className="space-y-2">
                        <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Phạm vi truy cập</h4>
                        <div className="flex items-center gap-2 px-3 py-2.5 bg-[#fef5ed] rounded-xl border border-[#f97316]/10">
                            <span className="material-symbols-outlined text-[#9d4300] text-base" style={{ fontVariationSettings: "'FILL' 1" }}>
                                folder
                            </span>
                            <div className="min-w-0">
                                <p className="text-xs font-semibold text-[#9d4300] truncate">{folder.name}</p>
                                <p className="text-[10px] text-[#9d4300]/60 capitalize">{folder.access_scope}</p>
                            </div>
                        </div>
                    </div>
                )}

                {/* AI Processing Section */}
                <div className="space-y-2">
                    <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">AI Processing</h4>
                    <div className="p-3 bg-gradient-to-r from-violet-50 to-indigo-50 rounded-xl border border-violet-100">
                        <p className="text-[11px] text-violet-700 leading-relaxed">
                            {document.status === 'completed'
                                ? 'Tài liệu đã được AI phân tích và trích xuất tri thức. Có thể sử dụng cho RAG và tìm kiếm ngữ nghĩa.'
                                : document.status === 'processing'
                                ? 'AI đang phân tích và trích xuất dữ liệu từ tài liệu...'
                                : document.status === 'failed'
                                ? 'Không thể xử lý tài liệu. Vui lòng thử tải lại.'
                                : 'Tài liệu đang chờ được AI xử lý và phân tích.'}
                        </p>
                    </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2 pt-2">
                    <button className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2.5 bg-[#9d4300] text-white rounded-xl text-xs font-bold hover:bg-[#b75b00] transition-colors shadow-sm hover:shadow-md">
                        <span className="material-symbols-outlined text-sm">download</span>
                        Tải về tệp tin
                    </button>
                    <button className="px-3 py-2.5 border border-slate-200 text-slate-600 rounded-xl text-xs font-medium hover:bg-slate-50 transition-colors" title="Chia sẻ">
                        <span className="material-symbols-outlined text-sm">share</span>
                    </button>
                    <button className="px-3 py-2.5 border border-red-200 text-red-500 rounded-xl text-xs font-medium hover:bg-red-50 transition-colors" title="Xóa">
                        <span className="material-symbols-outlined text-sm">delete</span>
                    </button>
                </div>
            </div>
        </div>
    )
}
